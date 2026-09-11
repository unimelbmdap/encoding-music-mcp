"""Explicit, repeatable provisioning of the repository-local CLaMP runtime."""

from __future__ import annotations

import math
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from .clamp_extractor import (
    ClampRuntimeConfig,
    ClampSetupError,
    ClampSetupResult,
    setup_clamp3,
)
from .runtime_config import environment_python, repository_root

PYTHON_VERSION = "3.10.16"
PROFILES = ("cpu", "cu128")
RUNTIME_PROJECT = Path(__file__).parent / "clamp_runtime"


def _run(
    command: list[str], *, root: Path, environment: dict[str, str], timeout: float
):
    try:
        subprocess.run(command, cwd=root, env=environment, timeout=timeout, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ClampSetupError(
            f"CLaMP bootstrap failed while running {command[0]}: {exc}. "
            "Fix the reported error and rerun bootstrap; completed downloads are reused."
        ) from exc


def bootstrap_clamp3(
    *, profile: str = "cpu", timeout_seconds: float = 3600.0
) -> ClampSetupResult:
    """Sync a locked Python environment, probe hardware, then prepare model assets.

    Only this explicitly invoked operation installs dependencies. It never uses
    the retrieval environment overrides or installs into the MCP environment.
    """
    if profile not in PROFILES:
        raise ClampSetupError(f"Unsupported profile {profile!r}; choose {PROFILES}")
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ClampSetupError("Bootstrap timeout must be a positive finite number")
    machine = platform.machine().lower()
    apple_silicon = sys.platform == "darwin" and machine == "arm64"
    if sys.platform == "darwin" and not apple_silicon:
        raise ClampSetupError(
            "Mac bootstrap requires Apple Silicon and a native arm64 Python. "
            "On Apple Silicon, run uv from a native terminal rather than Rosetta. "
            "Intel Macs are not supported by the pinned PyTorch 2.7.1 runtime."
        )
    if apple_silicon and profile != "cpu":
        raise ClampSetupError(
            "CUDA is not available on macOS; rerun bootstrap --profile cpu."
        )
    if not apple_silicon and not (
        sys.platform in {"win32", "linux"} and machine in {"amd64", "x86_64"}
    ):
        raise ClampSetupError(
            "Bootstrap supports Windows x64, Linux x86_64, and macOS Apple Silicon (CPU). "
            "On other platforms provision CLaMP separately and use setup --clamp-python."
        )
    root = repository_root()
    if root is None:
        raise ClampSetupError(
            "Bootstrap requires a source checkout. Clone encoding-music-mcp and run "
            "`uv run --extra score-embeddings --locked encoding-music-embeddings bootstrap` "
            "from its root; installed packages can use setup --clamp-python instead."
        )
    uv = shutil.which("uv")
    if uv is None:
        raise ClampSetupError(
            "uv is required on PATH to bootstrap the CLaMP environment"
        )
    if shutil.which("git") is None:
        raise ClampSetupError(
            "Git is required on PATH to prepare the pinned CLaMP source"
        )

    python = environment_python(root / ".venv-clamp")
    environment = os.environ.copy()
    # uv run sets VIRTUAL_ENV to the MCP environment. The nested sync must use
    # only the separate runtime, including when the caller customizes uv's env.
    environment.pop("VIRTUAL_ENV", None)
    environment["UV_PROJECT_ENVIRONMENT"] = str(root / ".venv-clamp")
    print(
        f"Preparing CLaMP {profile} environment at {python.parent.parent}",
        file=sys.stderr,
    )
    _run(
        [
            uv,
            "sync",
            "--project",
            str(RUNTIME_PROJECT),
            "--python",
            PYTHON_VERSION,
            "--locked",
            "--no-dev",
            "--extra",
            profile,
        ],
        root=root,
        environment=environment,
        timeout=timeout_seconds,
    )
    # Fail before downloading multi-GB model assets if the selected GPU profile
    # cannot actually execute on this host. The CPU profile must have no CUDA
    # runtime; macOS wheels can also include MPS, which CLaMP does not select.
    probe = (
        "import sys, torch; "
        f"assert sys.version_info[:3] == {tuple(map(int, PYTHON_VERSION.split('.')))!r}; "
        "assert torch.__version__.split('+')[0] == '2.7.1'; "
    )
    if profile == "cu128":
        probe += (
            "assert torch.version.cuda == '12.8', 'Expected CUDA 12.8 wheel'; "
            "assert torch.cuda.is_available(), "
            "'CUDA unavailable: check the NVIDIA driver or rerun bootstrap --profile cpu'; "
            "torch.ones(1, device='cuda').add_(1); torch.cuda.synchronize()"
        )
    else:
        probe += (
            "assert torch.version.cuda is None, 'Expected a PyTorch wheel without CUDA'; "
            "assert torch.ones(1, device='cpu').add_(1).item() == 2"
        )
    _run([str(python), "-c", probe], root=root, environment=environment, timeout=60.0)
    print("Preparing and verifying pinned CLaMP model assets", file=sys.stderr)
    return setup_clamp3(
        ClampRuntimeConfig(
            python_executable=python,
            cache_dir=root / ".clamp3-cache",
            timeout_seconds=timeout_seconds,
        )
    )
