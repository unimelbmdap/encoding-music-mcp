"""Pinned CLaMP 3 setup checks and offline batch extraction adapter."""

from __future__ import annotations

import atexit
import hashlib
import json
import logging
import math
import os
import queue
import shutil
import subprocess
import tempfile
import threading
import time
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

import numpy as np

LOGGER = logging.getLogger(__name__)

CLAMP_REPOSITORY_URL = "https://github.com/sanderwood/clamp3.git"
CLAMP_COMMIT = "9016d2b0c8d12d1aa79c2e0ab201e6822bdc83a8"
CLAMP_MODEL_REVISION = "791815a04a3a2bd9ab64cf590ba8307930c179e6"
CLAMP_C2_WEIGHT_FILENAME = (
    "weights_clamp3_c2_h_size_768_t_model_FacebookAI_xlm-roberta-base_"
    "t_length_128_a_size_768_a_layers_12_a_length_128_s_size_768_"
    "s_layers_12_p_size_64_p_length_512.pth"
)
CLAMP_C2_WEIGHT_URL = (
    "https://huggingface.co/sander-wood/clamp3/resolve/"
    f"{CLAMP_MODEL_REVISION}/{CLAMP_C2_WEIGHT_FILENAME}"
)
CLAMP_C2_WEIGHT_SHA256 = (
    "e6fb0d139b24a1ec20836bb65bd652303d570ea9af2cddb20a1fc161421d64af"
)
CLAMP_EXPECTED_DIMENSION = 768
SETUP_MANIFEST_VERSION = 1


class ClampError(RuntimeError):
    """Base exception for the external CLaMP boundary."""


class ClampSetupError(ClampError):
    """Raised when the pinned runtime cannot be acquired or verified."""


class ClampExecutionError(ClampError):
    """Raised when an external CLaMP process fails."""


class EmbeddingValidationError(ClampError):
    """Raised when CLaMP output is missing, malformed, or unsafe."""


def default_cache_dir() -> Path:
    """Return a platform-appropriate default cache location."""
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        root = Path(os.environ["LOCALAPPDATA"])
    elif os.environ.get("XDG_CACHE_HOME"):
        root = Path(os.environ["XDG_CACHE_HOME"])
    else:
        root = Path.home() / ".cache"
    return root / "encoding-music-mcp" / "clamp3"


@dataclass(slots=True)
class ClampRuntimeConfig:
    """Configuration for a pinned external CLaMP runtime."""

    python_executable: Path
    cache_dir: Path = field(default_factory=default_cache_dir)
    timeout_seconds: float = 3600.0
    repository_url: str = CLAMP_REPOSITORY_URL
    commit: str = CLAMP_COMMIT
    model_revision: str = CLAMP_MODEL_REVISION
    weight_url: str = CLAMP_C2_WEIGHT_URL
    weight_sha256: str = CLAMP_C2_WEIGHT_SHA256
    weight_filename: str = CLAMP_C2_WEIGHT_FILENAME
    expected_dimension: int = CLAMP_EXPECTED_DIMENSION

    def __post_init__(self) -> None:
        # Preserve virtual-environment interpreter symlinks: resolving them can
        # silently bypass the environment and its installed CLaMP dependencies.
        self.python_executable = Path(self.python_executable).expanduser().absolute()
        self.cache_dir = Path(self.cache_dir).expanduser().resolve()
        if not self.commit or len(self.commit) < 7:
            raise ValueError("commit must identify a pinned CLaMP revision")
        if len(self.weight_sha256) != 64:
            raise ValueError("weight_sha256 must be a SHA-256 hex digest")
        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a positive finite number")
        if self.expected_dimension <= 0:
            raise ValueError("expected_dimension must be positive")

    @property
    def checkout_dir(self) -> Path:
        """Return the managed source checkout path."""
        return self.cache_dir / "source"

    @property
    def weight_path(self) -> Path:
        """Return the model path expected by the configured CLaMP scripts."""
        return self.checkout_dir / "code" / self.weight_filename

    @property
    def manifest_path(self) -> Path:
        """Return the setup artifact-manifest path."""
        return self.cache_dir / "setup-manifest.json"


@dataclass(frozen=True, slots=True)
class ClampSetupResult:
    """Verified paths and provenance for a prepared runtime."""

    checkout_dir: Path
    weight_path: Path
    manifest_path: Path
    commit: str
    model_revision: str
    weight_sha256: str
    offline_ready: bool


@dataclass(frozen=True, slots=True)
class EmbeddingBatch:
    """Ordered raw and normalized global embeddings."""

    stems: tuple[str, ...]
    raw: np.ndarray
    normalized: np.ndarray


@dataclass(frozen=True, slots=True)
class ClampModelIdentity:
    """Exact CLaMP model identity used for an embedding operation."""

    model_commit: str
    model_revision: str
    model_weight_sha256: str
    dimension: int


@dataclass(frozen=True, slots=True)
class TextEmbeddingBatch:
    """Ordered text embeddings and their shared CLaMP model identity."""

    texts: tuple[str, ...]
    stems: tuple[str, ...]
    raw: np.ndarray
    normalized: np.ndarray
    model_identity: ClampModelIdentity


CommandRunner = Callable[
    [Sequence[str], Path, Mapping[str, str], float],
    subprocess.CompletedProcess[str],
]


@dataclass(frozen=True, slots=True)
class ClampWorkerIdentity:
    """Settings that determine whether a resident text worker is reusable."""

    python_executable: Path
    checkout_dir: Path
    weight_path: Path
    commit: str
    model_revision: str
    weight_sha256: str
    expected_dimension: int

    @classmethod
    def from_config(cls, config: ClampRuntimeConfig) -> ClampWorkerIdentity:
        return cls(
            python_executable=config.python_executable,
            checkout_dir=config.checkout_dir,
            weight_path=config.weight_path,
            commit=config.commit,
            model_revision=config.model_revision,
            weight_sha256=config.weight_sha256,
            expected_dimension=config.expected_dimension,
        )


class _ClampTextWorker:
    """One serialized JSON-lines connection to a resident CLaMP process."""

    def __init__(self, config: ClampRuntimeConfig) -> None:
        self.identity = ClampWorkerIdentity.from_config(config)
        self._responses: queue.Queue[dict[str, Any] | None] = queue.Queue()
        self._stderr: deque[str] = deque(maxlen=40)
        self._request_id = 0
        worker_script = Path(__file__).with_name("clamp_text_worker.py")
        started = time.perf_counter()
        try:
            self._process = subprocess.Popen(
                [str(config.python_executable), "-u", str(worker_script)],
                cwd=str(config.checkout_dir / "code"),
                env=_runtime_environment(config, offline=True),
                text=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1,
            )
        except (OSError, ValueError) as exc:
            raise ClampExecutionError(
                f"Could not start persistent CLaMP text worker with "
                f"{config.python_executable}: {exc}"
            ) from exc
        self._stdout_thread = threading.Thread(
            target=self._read_stdout,
            name="clamp-text-worker-stdout",
            daemon=True,
        )
        self._stderr_thread = threading.Thread(
            target=self._read_stderr,
            name="clamp-text-worker-stderr",
            daemon=True,
        )
        self._stdout_thread.start()
        self._stderr_thread.start()
        try:
            boot = self._receive(config.timeout_seconds, stage="interpreter startup")
            if boot.get("event") != "booted":
                raise self._protocol_error("boot acknowledgement", boot)
            interpreter_seconds = time.perf_counter() - started
            self._send(
                {
                    "operation": "initialize",
                    "checkout_dir": str(config.checkout_dir),
                    "weight_path": str(config.weight_path),
                    "expected_dimension": config.expected_dimension,
                }
            )
            ready = self._receive(config.timeout_seconds, stage="model initialization")
            if ready.get("event") != "ready":
                raise self._protocol_error("ready acknowledgement", ready)
        except Exception:
            self.close()
            raise
        timings = ready.get("timings", {})
        startup_timings = {
            "interpreter_startup_seconds": interpreter_seconds,
            "model_and_tokenizer_load_seconds": float(
                timings.get("model_and_tokenizer_load_seconds", 0.0)
            ),
            "checkpoint_load_seconds": float(
                timings.get("checkpoint_load_seconds", 0.0)
            ),
            "warmup_seconds": float(timings.get("warmup_seconds", 0.0)),
        }
        LOGGER.info(
            "CLaMP text worker started: interpreter=%.6fs model_tokenizer=%.6fs "
            "checkpoint=%.6fs warmup=%.6fs device=%s precision=%s",
            interpreter_seconds,
            startup_timings["model_and_tokenizer_load_seconds"],
            startup_timings["checkpoint_load_seconds"],
            startup_timings["warmup_seconds"],
            ready.get("device", "unknown"),
            ready.get("precision", "unknown"),
            extra={
                "timing_category": "clamp_worker_startup",
                "timings": startup_timings,
            },
        )

    def _read_stdout(self) -> None:
        assert self._process.stdout is not None
        try:
            for line in self._process.stdout:
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    value = {
                        "event": "protocol_error",
                        "error": f"non-JSON worker output: {line.strip()!r}",
                    }
                self._responses.put(value)
        finally:
            self._responses.put(None)

    def _read_stderr(self) -> None:
        assert self._process.stderr is not None
        for line in self._process.stderr:
            self._stderr.append(line.rstrip())

    def _diagnostics(self) -> str:
        details = "\n".join(self._stderr).strip()
        return details or "no worker diagnostics were captured"

    def _protocol_error(
        self, expected: str, response: dict[str, Any]
    ) -> ClampExecutionError:
        return ClampExecutionError(
            f"Persistent CLaMP worker did not return {expected}: "
            f"{response.get('error', response)!s}. Diagnostics: {self._diagnostics()}"
        )

    def _send(self, payload: dict[str, Any]) -> None:
        if self._process.poll() is not None or self._process.stdin is None:
            raise ClampExecutionError(
                f"Persistent CLaMP worker exited with code {self._process.poll()}. "
                f"Diagnostics: {self._diagnostics()}"
            )
        try:
            self._process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
            self._process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise ClampExecutionError(
                f"Persistent CLaMP worker stopped while accepting a request. "
                f"Diagnostics: {self._diagnostics()}"
            ) from exc

    def _receive(self, timeout: float, *, stage: str) -> dict[str, Any]:
        try:
            response = self._responses.get(timeout=timeout)
        except queue.Empty as exc:
            self.terminate()
            raise ClampExecutionError(
                f"Persistent CLaMP worker timed out after {timeout:g}s during {stage}; "
                "the worker was terminated and will be restarted on the next request"
            ) from exc
        if response is None:
            raise ClampExecutionError(
                f"Persistent CLaMP worker exited during {stage} with code "
                f"{self._process.poll()}. Diagnostics: {self._diagnostics()}"
            )
        return response

    def encode(self, texts: tuple[str, ...], timeout: float) -> np.ndarray:
        self._request_id += 1
        request_id = self._request_id
        self._send(
            {
                "operation": "encode",
                "request_id": request_id,
                "texts": list(texts),
            }
        )
        response = self._receive(timeout, stage="ordered text inference")
        if response.get("event") != "encoded" or response.get("request_id") != request_id:
            raise self._protocol_error("the matching encoded response", response)
        if tuple(response.get("texts", ())) != texts:
            raise ClampExecutionError(
                "Persistent CLaMP worker returned embeddings in an unexpected text order"
            )
        timings = {
            "tokenisation_seconds": float(
                response.get("timings", {}).get("tokenisation_seconds", 0.0)
            ),
            "model_inference_seconds": float(
                response.get("timings", {}).get("model_inference_seconds", 0.0)
            ),
        }
        LOGGER.info(
            "CLaMP warm text encoding: tokenisation=%.6fs inference=%.6fs count=%d",
            timings["tokenisation_seconds"],
            timings["model_inference_seconds"],
            len(texts),
            extra={
                "timing_category": "clamp_text_encoding",
                "timings": timings,
            },
        )
        return np.asarray(response.get("raw"), dtype=np.float32)

    def close(self) -> None:
        process = getattr(self, "_process", None)
        if process is None:
            return
        if process.poll() is None:
            try:
                self._send({"operation": "shutdown"})
                process.wait(timeout=2.0)
            except (ClampExecutionError, subprocess.TimeoutExpired):
                self.terminate()
                return
        self._close_streams()

    def terminate(self) -> None:
        """Stop an unresponsive or failed worker without a graceful request."""
        process = getattr(self, "_process", None)
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2.0)
        self._close_streams()

    def _close_streams(self) -> None:
        for stream in (
            self._process.stdin,
            self._process.stdout,
            self._process.stderr,
        ):
            if stream is not None and not stream.closed:
                stream.close()


class PersistentClampTextEncoder:
    """Lazily own one compatible worker and serialize concurrent requests."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._worker: _ClampTextWorker | None = None

    def encode(self, texts: tuple[str, ...], config: ClampRuntimeConfig) -> np.ndarray:
        identity = ClampWorkerIdentity.from_config(config)
        with self._lock:
            if self._worker is not None and self._worker.identity != identity:
                self._worker.close()
                self._worker = None
            if self._worker is None:
                check_clamp3_setup(config, verify_checksum=False)
                self._worker = _ClampTextWorker(config)
            try:
                return self._worker.encode(texts, config.timeout_seconds)
            except Exception:
                self._worker.close()
                self._worker = None
                raise

    def close(self) -> None:
        with self._lock:
            if self._worker is not None:
                self._worker.close()
                self._worker = None


_PERSISTENT_TEXT_ENCODER = PersistentClampTextEncoder()
atexit.register(_PERSISTENT_TEXT_ENCODER.close)


def close_persistent_clamp_text_encoder() -> None:
    """Terminate the lazily created text worker, if one exists."""
    _PERSISTENT_TEXT_ENCODER.close()


def _run_command(
    args: Sequence[str],
    cwd: Path,
    env: Mapping[str, str],
    timeout: float,
) -> subprocess.CompletedProcess[str]:
    """Run one external command without a shell and raise an actionable error."""
    command = [str(arg) for arg in args]
    LOGGER.debug("Running external command in %s: %s", cwd, command)
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd),
            env=dict(env),
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise ClampExecutionError(f"Executable not found: {command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ClampExecutionError(
            f"Command timed out after {timeout:g}s: {command}"
        ) from exc

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        details = stderr or stdout or "no captured diagnostics"
        raise ClampExecutionError(
            f"Command failed with exit code {result.returncode}: {command}. "
            f"Diagnostics: {details}"
        )
    return result


def _sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _download_file(
    url: str,
    destination: Path,
    expected_sha256: str,
    timeout: float,
) -> None:
    """Download one artifact atomically and verify its SHA-256 digest."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and _sha256_file(destination) == expected_sha256:
        return

    partial = destination.with_suffix(destination.suffix + ".clamp3-download")
    if partial.exists():
        partial.unlink()
    try:
        with urlopen(url, timeout=timeout) as response, partial.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
    except (URLError, OSError) as exc:
        partial.unlink(missing_ok=True)
        raise ClampSetupError(f"Failed to download {url}: {exc}") from exc

    actual_sha256 = _sha256_file(partial)
    if actual_sha256 != expected_sha256:
        partial.unlink(missing_ok=True)
        raise ClampSetupError(
            "Downloaded model checksum mismatch: "
            f"expected {expected_sha256}, received {actual_sha256}"
        )
    os.replace(partial, destination)


def _ensure_checkout(
    config: ClampRuntimeConfig,
    runner: CommandRunner,
) -> None:
    checkout = config.checkout_dir
    environment = os.environ.copy()
    if checkout.exists():
        if not (checkout / ".git").is_dir():
            raise ClampSetupError(
                f"CLaMP cache exists but is not a Git checkout: {checkout}"
            )
        result = runner(
            ["git", "rev-parse", "HEAD"],
            checkout,
            environment,
            config.timeout_seconds,
        )
        actual_commit = result.stdout.strip()
        if actual_commit != config.commit:
            raise ClampSetupError(
                f"CLaMP checkout is {actual_commit}, expected {config.commit}. "
                "Use a different cache directory or remove the stale managed cache."
            )
        return

    if shutil.which("git") is None:
        raise ClampSetupError("Git is required by the explicit CLaMP setup command")

    config.cache_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".clamp3-checkout-",
        dir=config.cache_dir,
    ) as temporary:
        staging = Path(temporary) / "source"
        runner(
            ["git", "clone", "--no-checkout", config.repository_url, str(staging)],
            config.cache_dir,
            environment,
            config.timeout_seconds,
        )
        runner(
            ["git", "checkout", "--detach", config.commit],
            staging,
            environment,
            config.timeout_seconds,
        )
        os.replace(staging, checkout)


def _configure_symbolic_c2(checkout_dir: Path) -> None:
    """Apply the pinned upstream configuration switch for symbolic C2 weights."""
    config_path = checkout_dir / "code" / "config.py"
    if not config_path.is_file():
        raise ClampSetupError(f"Pinned CLaMP config is missing: {config_path}")
    content = config_path.read_text(encoding="utf-8")
    if '"weights_clamp3_c2"' in content:
        return
    marker = '"weights_clamp3_saas"'
    if content.count(marker) != 1:
        raise ClampSetupError(
            "Pinned CLaMP config no longer has the expected SAAS model marker"
        )
    config_path.write_text(
        content.replace(marker, '"weights_clamp3_c2"', 1), encoding="utf-8"
    )


def _runtime_environment(
    config: ClampRuntimeConfig, *, offline: bool
) -> dict[str, str]:
    environment = os.environ.copy()
    huggingface_root = config.cache_dir / "huggingface"
    environment.update(
        {
            "HF_HOME": str(huggingface_root),
            "HF_HUB_CACHE": str(huggingface_root / "hub"),
            "TOKENIZERS_PARALLELISM": "false",
        }
    )
    if offline:
        environment.update(
            {
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
            }
        )
    else:
        environment.pop("HF_HUB_OFFLINE", None)
        environment.pop("TRANSFORMERS_OFFLINE", None)
    return environment


def _verify_interpreter(
    config: ClampRuntimeConfig,
    runner: CommandRunner,
) -> None:
    if not config.python_executable.is_file():
        raise ClampSetupError(
            f"Configured CLaMP interpreter does not exist: {config.python_executable}"
        )
    try:
        runner(
            [str(config.python_executable), "--version"],
            config.cache_dir,
            os.environ.copy(),
            min(config.timeout_seconds, 30.0),
        )
    except ClampExecutionError as exc:
        raise ClampSetupError(f"CLaMP interpreter check failed: {exc}") from exc


def _run_readiness_check(
    config: ClampRuntimeConfig,
    runner: CommandRunner,
    *,
    offline: bool,
) -> None:
    script = config.checkout_dir / "code" / "extract_clamp3.py"
    if not script.is_file():
        raise ClampSetupError(f"Pinned extraction script is missing: {script}")
    with tempfile.TemporaryDirectory(
        prefix="clamp3-readiness-",
        dir=config.cache_dir,
    ) as temporary:
        root = Path(temporary)
        input_dir = root / "input"
        output_dir = root / "output"
        input_dir.mkdir()
        output_dir.mkdir()
        # The pinned extractor's .txt path exercises the aligned text encoder
        # used at query time. The contents are local and intentionally minimal.
        (input_dir / "readiness.txt").write_text("calm", encoding="utf-8")
        try:
            runner(
                [
                    str(config.python_executable),
                    str(script),
                    str(input_dir),
                    str(output_dir),
                    "--get_global",
                ],
                script.parent,
                _runtime_environment(config, offline=offline),
                config.timeout_seconds,
            )
        except ClampExecutionError as exc:
            mode = "offline" if offline else "online prefetch"
            raise ClampSetupError(
                f"CLaMP {mode} readiness check failed: {exc}"
            ) from exc


def _artifact_inventory(config: ClampRuntimeConfig) -> list[dict[str, object]]:
    """Inventory cached model assets without hashing the full source checkout."""
    inventory: list[dict[str, object]] = []
    for root in (config.checkout_dir / "code", config.cache_dir / "huggingface"):
        if not root.exists():
            continue
        for path in sorted(
            candidate for candidate in root.rglob("*") if candidate.is_file()
        ):
            if ".git" in path.parts or path == config.manifest_path:
                continue
            inventory.append(
                {
                    "path": str(path.relative_to(config.cache_dir)),
                    "size": path.stat().st_size,
                }
            )
    return inventory


def _write_manifest(
    config: ClampRuntimeConfig,
    *,
    offline_ready: bool,
) -> None:
    manifest: dict[str, Any] = {
        "manifest_version": SETUP_MANIFEST_VERSION,
        "repository_url": config.repository_url,
        "commit": config.commit,
        "model_revision": config.model_revision,
        "weight_filename": config.weight_filename,
        "weight_sha256": config.weight_sha256,
        "expected_dimension": config.expected_dimension,
        "python_executable": str(config.python_executable),
        "offline_ready": offline_ready,
        "artifacts": _artifact_inventory(config),
    }
    temporary = config.manifest_path.with_suffix(".json.clamp3-download")
    temporary.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, config.manifest_path)


def setup_clamp3(
    config: ClampRuntimeConfig,
    *,
    runner: CommandRunner = _run_command,
    perform_readiness: bool = True,
) -> ClampSetupResult:
    """Acquire, configure, and verify the pinned CLaMP runtime explicitly."""
    config.cache_dir.mkdir(parents=True, exist_ok=True)
    _ensure_checkout(config, runner)
    _configure_symbolic_c2(config.checkout_dir)
    _download_file(
        config.weight_url,
        config.weight_path,
        config.weight_sha256,
        config.timeout_seconds,
    )
    _verify_interpreter(config, runner)

    offline_ready = False
    if perform_readiness:
        _run_readiness_check(config, runner, offline=False)
        _run_readiness_check(config, runner, offline=True)
        offline_ready = True
    _write_manifest(config, offline_ready=offline_ready)
    return check_clamp3_setup(
        config,
        runner=runner,
        require_offline_ready=perform_readiness,
    )


def check_clamp3_setup(
    config: ClampRuntimeConfig,
    *,
    runner: CommandRunner = _run_command,
    require_offline_ready: bool = True,
    verify_checksum: bool = True,
) -> ClampSetupResult:
    """Validate cached source, model, interpreter, and setup provenance."""
    if not config.manifest_path.is_file():
        raise ClampSetupError(
            f"CLaMP setup manifest is missing: {config.manifest_path}"
        )
    try:
        manifest = json.loads(config.manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ClampSetupError(f"Invalid CLaMP setup manifest: {exc}") from exc

    expected = {
        "manifest_version": SETUP_MANIFEST_VERSION,
        "commit": config.commit,
        "model_revision": config.model_revision,
        "weight_filename": config.weight_filename,
        "weight_sha256": config.weight_sha256,
        "expected_dimension": config.expected_dimension,
    }
    mismatches = [key for key, value in expected.items() if manifest.get(key) != value]
    if mismatches:
        raise ClampSetupError(
            "CLaMP setup manifest does not match configuration: "
            + ", ".join(mismatches)
        )
    if require_offline_ready and not manifest.get("offline_ready"):
        raise ClampSetupError("CLaMP setup has not passed its offline readiness check")
    if not config.checkout_dir.is_dir():
        raise ClampSetupError(f"CLaMP checkout is missing: {config.checkout_dir}")
    if not (config.checkout_dir / ".git").is_dir():
        raise ClampSetupError(
            f"CLaMP checkout metadata is missing: {config.checkout_dir / '.git'}"
        )
    try:
        revision = runner(
            ["git", "rev-parse", "HEAD"],
            config.checkout_dir,
            os.environ.copy(),
            min(config.timeout_seconds, 30.0),
        ).stdout.strip()
    except ClampExecutionError as exc:
        raise ClampSetupError(
            f"Could not verify CLaMP checkout revision: {exc}"
        ) from exc
    if revision != config.commit:
        raise ClampSetupError(
            f"CLaMP checkout is {revision}, expected pinned revision {config.commit}"
        )
    if not config.weight_path.is_file():
        raise ClampSetupError(f"CLaMP C2 weights are missing: {config.weight_path}")
    if verify_checksum:
        actual_sha256 = _sha256_file(config.weight_path)
        if actual_sha256 != config.weight_sha256:
            raise ClampSetupError(
                "CLaMP C2 weight checksum mismatch: "
                f"expected {config.weight_sha256}, received {actual_sha256}"
            )
    _verify_interpreter(config, runner)
    return ClampSetupResult(
        checkout_dir=config.checkout_dir,
        weight_path=config.weight_path,
        manifest_path=config.manifest_path,
        commit=config.commit,
        model_revision=config.model_revision,
        weight_sha256=config.weight_sha256,
        offline_ready=bool(manifest.get("offline_ready")),
    )


def _require_script(path: Path) -> Path:
    if not path.is_file():
        raise ClampExecutionError(f"Required pinned CLaMP script is missing: {path}")
    return path


def run_clamp3_extraction(
    input_dir: str | Path,
    output_dir: str | Path,
    config: ClampRuntimeConfig,
    *,
    runner: CommandRunner = _run_command,
    verify_setup: bool = True,
) -> tuple[subprocess.CompletedProcess[str], ...]:
    """Run pinned XML preprocessing and global embedding extraction offline."""
    source = Path(input_dir).expanduser().resolve()
    destination = Path(output_dir).expanduser().resolve()
    if not source.is_dir():
        raise ClampExecutionError(f"CLaMP input directory does not exist: {source}")
    xml_files = sorted(source.rglob("*.xml"))
    if not xml_files:
        raise ClampExecutionError(f"CLaMP input contains no .xml files: {source}")
    if destination.exists() and any(destination.iterdir()):
        raise ClampExecutionError(
            f"CLaMP output directory must be absent or empty: {destination}"
        )
    destination.mkdir(parents=True, exist_ok=True)
    if verify_setup:
        check_clamp3_setup(config, runner=runner)
    elif not config.python_executable.is_file():
        raise ClampExecutionError(
            f"Configured CLaMP interpreter does not exist: {config.python_executable}"
        )

    xml_to_abc = _require_script(
        config.checkout_dir / "preprocessing" / "abc" / "batch_xml2abc.py"
    )
    interleave_abc = _require_script(
        config.checkout_dir / "preprocessing" / "abc" / "batch_interleaved_abc.py"
    )
    extract = _require_script(config.checkout_dir / "code" / "extract_clamp3.py")
    environment = _runtime_environment(config, offline=True)

    with tempfile.TemporaryDirectory(prefix="clamp3-extraction-") as temporary:
        workspace = Path(temporary)
        standard_abc = workspace / "standard-abc"
        interleaved_abc = workspace / "interleaved-abc"
        commands = (
            (
                [
                    str(config.python_executable),
                    str(xml_to_abc),
                    str(source),
                    str(standard_abc),
                ],
                xml_to_abc.parent,
            ),
            (
                [
                    str(config.python_executable),
                    str(interleave_abc),
                    str(standard_abc),
                    str(interleaved_abc),
                ],
                interleave_abc.parent,
            ),
            (
                [
                    str(config.python_executable),
                    str(extract),
                    str(interleaved_abc),
                    str(destination),
                    "--get_global",
                ],
                extract.parent,
            ),
        )
        results = tuple(
            runner(args, cwd, environment, config.timeout_seconds)
            for args, cwd in commands
        )
    return results


def _model_identity(config: ClampRuntimeConfig) -> ClampModelIdentity:
    """Project runtime configuration into storage-compatible model identity."""
    return ClampModelIdentity(
        model_commit=config.commit,
        model_revision=config.model_revision,
        model_weight_sha256=config.weight_sha256,
        dimension=config.expected_dimension,
    )


def embed_clamp3_texts(
    texts: Sequence[str],
    config: ClampRuntimeConfig,
    *,
    runner: CommandRunner | None = None,
    verify_setup: bool = True,
) -> TextEmbeddingBatch:
    """Encode ordered text strings with a lazy resident CLaMP text worker.

    The default path keeps the verified tokenizer, trained text encoder, and
    text projection resident. Supplying a command runner retains the isolated
    subprocess adapter for setup tests and output-parity verification.
    """
    ordered_texts = tuple(texts)
    if not ordered_texts:
        raise EmbeddingValidationError("At least one text input is required")
    for index, value in enumerate(ordered_texts):
        if not isinstance(value, str):
            raise EmbeddingValidationError(
                f"Text input at index {index} must be a string"
            )
        if not value.strip():
            raise EmbeddingValidationError(
                f"Text input at index {index} must not be blank"
            )

    if runner is not None or not verify_setup:
        return _embed_clamp3_texts_subprocess(
            ordered_texts,
            config,
            runner=_run_command if runner is None else runner,
            verify_setup=verify_setup,
        )

    raw = _PERSISTENT_TEXT_ENCODER.encode(ordered_texts, config)
    expected_shape = (len(ordered_texts), config.expected_dimension)
    if raw.shape != expected_shape:
        raise EmbeddingValidationError(
            f"Persistent CLaMP worker returned shape {raw.shape}; "
            f"expected {expected_shape}"
        )
    if not np.isfinite(raw).all():
        raise EmbeddingValidationError(
            "Persistent CLaMP worker returned non-finite text embeddings"
        )
    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    normalized = np.divide(raw, norms, out=np.zeros_like(raw), where=norms != 0)
    stems = tuple(f"text_{index:06d}" for index in range(len(ordered_texts)))
    return TextEmbeddingBatch(
        texts=ordered_texts,
        stems=stems,
        raw=raw,
        normalized=normalized,
        model_identity=_model_identity(config),
    )


def _embed_clamp3_texts_subprocess(
    ordered_texts: tuple[str, ...],
    config: ClampRuntimeConfig,
    *,
    runner: CommandRunner,
    verify_setup: bool,
) -> TextEmbeddingBatch:
    """Run the original one-process-per-batch encoder for tests and parity."""
    if verify_setup:
        check_clamp3_setup(config, runner=runner)
    elif not config.python_executable.is_file():
        raise ClampExecutionError(
            f"Configured CLaMP interpreter does not exist: {config.python_executable}"
        )

    extract = _require_script(config.checkout_dir / "code" / "extract_clamp3.py")
    environment = _runtime_environment(config, offline=True)
    stems = tuple(f"text_{index:06d}" for index in range(len(ordered_texts)))

    with tempfile.TemporaryDirectory(prefix="clamp3-text-") as temporary:
        workspace = Path(temporary)
        input_dir = workspace / "input"
        output_dir = workspace / "output"
        input_dir.mkdir()
        output_dir.mkdir()
        for stem, value in zip(stems, ordered_texts, strict=True):
            (input_dir / f"{stem}.txt").write_text(value, encoding="utf-8")

        runner(
            [
                str(config.python_executable),
                str(extract),
                str(input_dir),
                str(output_dir),
                "--get_global",
            ],
            extract.parent,
            environment,
            config.timeout_seconds,
        )
        embeddings = load_and_normalize_embeddings(
            output_dir,
            expected_dim=config.expected_dimension,
            expected_stems=stems,
        )

    return TextEmbeddingBatch(
        texts=ordered_texts,
        stems=embeddings.stems,
        raw=embeddings.raw,
        normalized=embeddings.normalized,
        model_identity=_model_identity(config),
    )


def _coerce_global_embedding(path: Path, expected_dim: int) -> np.ndarray:
    try:
        loaded = np.load(path, allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise EmbeddingValidationError(
            f"Failed to load embedding {path}: {exc}"
        ) from exc
    if not np.issubdtype(loaded.dtype, np.number):
        raise EmbeddingValidationError(f"Embedding is not numeric: {path}")
    if loaded.shape == (1, expected_dim):
        loaded = loaded[0]
    if loaded.shape != (expected_dim,):
        raise EmbeddingValidationError(
            f"Embedding {path} has shape {loaded.shape}; expected ({expected_dim},) "
            f"or (1, {expected_dim})"
        )
    embedding = np.asarray(loaded, dtype=np.float32)
    if not np.isfinite(embedding).all():
        raise EmbeddingValidationError(f"Embedding contains non-finite values: {path}")
    return embedding


def load_and_normalize_embeddings(
    output_dir: str | Path,
    *,
    expected_dim: int = CLAMP_EXPECTED_DIMENSION,
    expected_stems: Sequence[str] | None = None,
    allow_missing_expected: bool = False,
) -> EmbeddingBatch:
    """Load global CLaMP outputs in deterministic order and L2-normalize them.

    When ``allow_missing_expected`` is true, absent expected stems are omitted
    while present stems retain their requested order. Unexpected and malformed
    outputs remain errors. Callers are responsible for deciding whether an
    empty partial batch is usable.
    """
    if expected_dim <= 0:
        raise ValueError("expected_dim must be positive")
    directory = Path(output_dir).expanduser().resolve()
    if not directory.is_dir():
        raise EmbeddingValidationError(
            f"Embedding output directory does not exist: {directory}"
        )

    files = sorted(
        directory.rglob("*.npy"),
        key=lambda path: path.relative_to(directory).as_posix(),
    )
    by_stem: dict[str, Path] = {}
    for path in files:
        if path.stem in by_stem:
            raise EmbeddingValidationError(
                f"Duplicate embedding stem {path.stem!r}: {by_stem[path.stem]} and {path}"
            )
        by_stem[path.stem] = path

    if expected_stems is None:
        stems = tuple(sorted(by_stem))
    else:
        stems = tuple(expected_stems)
        if len(stems) != len(set(stems)):
            raise EmbeddingValidationError(
                "Expected embedding stems contain duplicates"
            )
        missing = [stem for stem in stems if stem not in by_stem]
        unexpected = sorted(set(by_stem) - set(stems))
        if unexpected or (missing and not allow_missing_expected):
            raise EmbeddingValidationError(
                f"Embedding file mismatch; missing={missing}, unexpected={unexpected}"
            )
        if allow_missing_expected:
            stems = tuple(stem for stem in stems if stem in by_stem)

    if not stems:
        empty = np.empty((0, expected_dim), dtype=np.float32)
        return EmbeddingBatch(stems=(), raw=empty, normalized=empty.copy())

    raw = np.vstack(
        [_coerce_global_embedding(by_stem[stem], expected_dim) for stem in stems]
    ).astype(np.float32, copy=False)
    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    normalized = np.divide(
        raw,
        norms,
        out=np.zeros_like(raw),
        where=norms != 0,
    )
    return EmbeddingBatch(stems=stems, raw=raw, normalized=normalized)


def config_to_dict(config: ClampRuntimeConfig) -> dict[str, object]:
    """Return a JSON-compatible configuration snapshot without runtime state."""
    values = asdict(config)
    values["python_executable"] = str(config.python_executable)
    values["cache_dir"] = str(config.cache_dir)
    return values


class TextEncoder:
    """Shared text encoder coordinating with the persistent CLaMP worker."""

    def __init__(self, config: ClampRuntimeConfig | None = None) -> None:
        self.config = config

    def encode(
        self,
        texts: Sequence[str],
        config: ClampRuntimeConfig | None = None,
        *,
        runner: CommandRunner | None = None,
        verify_setup: bool = True,
    ) -> TextEmbeddingBatch:
        """Encode ordered text descriptions into CLaMP embeddings."""
        cfg = config or self.config
        if cfg is None:
            raise ClampExecutionError("ClampRuntimeConfig is required for text encoding")
        return embed_clamp3_texts(texts, cfg, runner=runner, verify_setup=verify_setup)

    def encode_batch(
        self,
        texts: Sequence[str],
        config: ClampRuntimeConfig | None = None,
        *,
        runner: CommandRunner | None = None,
        verify_setup: bool = True,
    ) -> TextEmbeddingBatch:
        """Encode all prompt strings in a single batch to maximize throughput."""
        return self.encode(texts, config, runner=runner, verify_setup=verify_setup)
