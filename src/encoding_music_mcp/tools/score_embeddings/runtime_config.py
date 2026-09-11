"""Call-time discovery of the separate CLaMP runtime; never installs anything."""

from __future__ import annotations

import math
import os
import tomllib
from collections.abc import Mapping
from pathlib import Path

from .clamp_extractor import ClampRuntimeConfig

CLAMP_PYTHON_ENV = "ENCODING_MUSIC_CLAMP_PYTHON"
CLAMP_CACHE_ENV = "ENCODING_MUSIC_CLAMP_CACHE_DIR"
CLAMP_TIMEOUT_ENV = "ENCODING_MUSIC_CLAMP_TIMEOUT_SECONDS"
DEFAULT_TIMEOUT_SECONDS = 3600.0
BOOTSTRAP_COMMAND = (
    "uv run --extra score-embeddings --locked encoding-music-embeddings bootstrap"
)


class RuntimeConfigurationError(ValueError):
    """The external runtime needs setup or an explicit configuration fix."""


def repository_root() -> Path | None:
    """Find this source checkout, independent of the client's working directory.

    Installed wheels must not accidentally select an unrelated parent project.
    """
    source = Path(__file__).resolve()
    root = source.parents[4]
    manifest = root / "pyproject.toml"
    if not manifest.is_file() or source != (
        root / "src/encoding_music_mcp/tools/score_embeddings/runtime_config.py"
    ):
        return None
    with manifest.open("rb") as stream:
        project = tomllib.load(stream).get("project", {})
    return root if project.get("name") == "encoding-music-mcp" else None


def environment_python(directory: Path) -> Path:
    """Select the interpreter layout for the OS running the MCP server."""
    return directory / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def resolve_clamp_runtime(environment: Mapping[str, str]) -> ClampRuntimeConfig:
    """Prefer explicit overrides, then the runtime prepared beside this checkout.

    Explicit external interpreters retain the historical user-cache default when
    there is no repository cache. Invalid overrides never silently fall back.
    """
    root = repository_root()
    setup_hint = f"Run `{BOOTSTRAP_COMMAND}` from the repository root."
    python_text = environment.get(CLAMP_PYTHON_ENV, "").strip()
    if python_text:
        python = Path(python_text).expanduser().absolute()
        if not python.is_file():
            raise RuntimeConfigurationError(
                f"Configured CLaMP interpreter does not exist: {python} "
                f"(from {CLAMP_PYTHON_ENV}). Fix the override or unset it. {setup_hint}"
            )
    else:
        python = environment_python(root / ".venv-clamp") if root else None
        if python is None or not python.is_file():
            raise RuntimeConfigurationError(
                f"CLaMP runtime is not prepared ({python or 'no source checkout'}). "
                f"{setup_hint} Alternatively set {CLAMP_PYTHON_ENV} to a prepared "
                f"CLaMP interpreter and {CLAMP_CACHE_ENV} to its model cache."
            )

    timeout_text = environment.get(
        CLAMP_TIMEOUT_ENV, str(DEFAULT_TIMEOUT_SECONDS)
    ).strip()
    try:
        timeout = float(timeout_text)
    except ValueError:
        timeout = float("nan")
    if not math.isfinite(timeout) or timeout <= 0:
        raise RuntimeConfigurationError(
            f"{CLAMP_TIMEOUT_ENV} must be a positive finite number; got {timeout_text!r}"
        )

    cache_text = environment.get(CLAMP_CACHE_ENV, "").strip()
    if cache_text:
        cache = Path(cache_text).expanduser().absolute()
    elif root and (not python_text or (root / ".clamp3-cache").is_dir()):
        cache = root / ".clamp3-cache"
        if not (cache / "setup-manifest.json").is_file():
            raise RuntimeConfigurationError(
                f"Repository CLaMP cache is not prepared: {cache}. {setup_hint}"
            )
    else:
        # Preserve existing deployments with an explicitly configured interpreter.
        return ClampRuntimeConfig(python_executable=python, timeout_seconds=timeout)
    return ClampRuntimeConfig(
        python_executable=python, cache_dir=cache, timeout_seconds=timeout
    )
