"""Tests for pinned CLaMP setup and extraction."""

from __future__ import annotations

import hashlib
import inspect
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np
import pytest

from encoding_music_mcp.score_embeddings import clamp_extractor, clamp_text_worker
from encoding_music_mcp.score_embeddings.clamp_extractor import (
    ClampExecutionError,
    ClampRuntimeConfig,
    EmbeddingValidationError,
    PersistentClampTextEncoder,
    embed_clamp3_texts,
    load_and_normalize_embeddings,
    run_clamp3_extraction,
    setup_clamp3,
)


def _completed(args: list[str], stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")


def _write_fake_checkout(path: Path) -> None:
    (path / ".git").mkdir(parents=True)
    (path / "code").mkdir()
    (path / "preprocessing" / "abc").mkdir(parents=True)
    (path / "code" / "config.py").write_text(
        'CLAMP3_WEIGHTS_PATH = "weights_clamp3_saas"\n',
        encoding="utf-8",
    )
    for script in (
        path / "code" / "extract_clamp3.py",
        path / "preprocessing" / "abc" / "batch_xml2abc.py",
        path / "preprocessing" / "abc" / "batch_interleaved_abc.py",
    ):
        script.write_text("# fake\n", encoding="utf-8")


class _ResidentWorkerStub:
    created: list[_ResidentWorkerStub] = []
    delay = 0.0
    failure: Exception | None = None

    def __init__(self, config: ClampRuntimeConfig):
        self.identity = clamp_extractor.ClampWorkerIdentity.from_config(config)
        self.calls: list[tuple[str, ...]] = []
        self.closed = False
        type(self).created.append(self)

    def encode(self, texts: tuple[str, ...], timeout: float) -> np.ndarray:
        self.calls.append(texts)
        if self.delay:
            time.sleep(self.delay)
        if self.failure is not None:
            raise self.failure
        return np.ones((len(texts), self.identity.expected_dimension), dtype=np.float32)

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def resident_worker_stub(monkeypatch: pytest.MonkeyPatch):
    _ResidentWorkerStub.created = []
    _ResidentWorkerStub.delay = 0.0
    _ResidentWorkerStub.failure = None
    monkeypatch.setattr(clamp_extractor, "_ClampTextWorker", _ResidentWorkerStub)
    monkeypatch.setattr(clamp_extractor, "check_clamp3_setup", lambda config: None)
    return _ResidentWorkerStub


def _resident_config(tmp_path: Path, *, revision: str = "revision-a"):
    return ClampRuntimeConfig(
        python_executable=Path(sys.executable),
        cache_dir=tmp_path / revision,
        commit="c" * 40,
        model_revision=revision,
        weight_sha256="d" * 64,
        expected_dimension=3,
    )


def test_resident_encoder_reuses_one_worker_without_query_caching(
    tmp_path: Path,
    resident_worker_stub,
):
    manager = PersistentClampTextEncoder()
    config = _resident_config(tmp_path)

    first = manager.encode(("first positive", "first negative"), config)
    second = manager.encode(("second positive", "second negative"), config)

    assert len(resident_worker_stub.created) == 1
    assert resident_worker_stub.created[0].calls == [
        ("first positive", "first negative"),
        ("second positive", "second negative"),
    ]
    assert first.shape == second.shape == (2, 3)


def test_resident_encoder_restarts_only_for_relevant_configuration_changes(
    tmp_path: Path,
    resident_worker_stub,
):
    manager = PersistentClampTextEncoder()
    first_config = _resident_config(tmp_path, revision="revision-a")
    timeout_only = _resident_config(tmp_path, revision="revision-a")
    timeout_only.timeout_seconds = 0.5
    changed = _resident_config(tmp_path, revision="revision-b")

    manager.encode(("one",), first_config)
    manager.encode(("two",), timeout_only)
    manager.encode(("three",), changed)

    assert len(resident_worker_stub.created) == 2
    assert resident_worker_stub.created[0].closed is True
    assert resident_worker_stub.created[0].calls == [("one",), ("two",)]
    assert resident_worker_stub.created[1].calls == [("three",)]


def test_simultaneous_first_requests_create_one_resident_worker(
    tmp_path: Path,
    resident_worker_stub,
):
    manager = PersistentClampTextEncoder()
    config = _resident_config(tmp_path)
    resident_worker_stub.delay = 0.01
    barrier = threading.Barrier(5)
    errors: list[BaseException] = []

    def encode(index: int) -> None:
        try:
            barrier.wait()
            manager.encode((f"prompt {index}",), config)
        except BaseException as exc:  # pragma: no cover - assertion reports details
            errors.append(exc)

    threads = [threading.Thread(target=encode, args=(index,)) for index in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(resident_worker_stub.created) == 1
    assert len(resident_worker_stub.created[0].calls) == 5


@pytest.mark.parametrize(
    "failure",
    [
        ClampExecutionError("timed out after 0.1s"),
        ClampExecutionError("worker exited with code 9"),
    ],
)
def test_resident_encoder_discards_failed_worker_and_restarts(
    tmp_path: Path,
    resident_worker_stub,
    failure: Exception,
):
    manager = PersistentClampTextEncoder()
    config = _resident_config(tmp_path)
    resident_worker_stub.failure = failure

    with pytest.raises(ClampExecutionError, match=str(failure)):
        manager.encode(("first",), config)

    assert resident_worker_stub.created[0].closed is True
    resident_worker_stub.failure = None
    manager.encode(("second",), config)
    assert len(resident_worker_stub.created) == 2


def test_resident_encoder_shutdown_closes_worker(
    tmp_path: Path,
    resident_worker_stub,
):
    manager = PersistentClampTextEncoder()
    manager.encode(("prompt",), _resident_config(tmp_path))

    manager.close()

    assert resident_worker_stub.created[0].closed is True
    assert manager._worker is None


def test_resident_encoding_never_invokes_download_setup(
    tmp_path: Path,
    resident_worker_stub,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        clamp_extractor,
        "_download_file",
        lambda *args, **kwargs: pytest.fail("query encoding must never download assets"),
    )
    manager = PersistentClampTextEncoder()

    manager.encode(("offline prompt",), _resident_config(tmp_path))

    assert len(resident_worker_stub.created) == 1


def test_worker_uses_one_full_precision_ordered_inference_batch():
    initialization = inspect.getsource(clamp_text_worker.TextRuntime.__init__)
    encoding = inspect.getsource(clamp_text_worker.TextRuntime.encode)

    assert encoding.count("self.tokenizer(") == 1
    assert encoding.count("self.model.get_text_features(") == 1
    assert encoding.count("torch.inference_mode()") == 1
    assert encoding.count(".to(") == 1
    assert ".eval()" in initialization
    assert "autocast" not in initialization + encoding
    assert "float16" not in initialization + encoding


def test_worker_receive_enforces_timeout_and_terminates(monkeypatch):
    worker = object.__new__(clamp_extractor._ClampTextWorker)
    worker._responses = queue.Queue()
    closed = []
    monkeypatch.setattr(worker, "terminate", lambda: closed.append(True))

    with pytest.raises(ClampExecutionError, match="timed out after 0.001s"):
        worker._receive(0.001, stage="ordered text inference")

    assert closed == [True]


def test_worker_releases_checkpoint_before_device_transfer_and_warmup(monkeypatch):
    import weakref
    from types import SimpleNamespace
    from unittest.mock import Mock

    tensors = []
    stages = []

    def load_checkpoint(*args, **kwargs):
        tensor = np.ones(3, dtype=np.float32)
        tensors.append(weakref.ref(tensor))
        return {"model": {"weight": tensor}}

    def load_state(state, *, strict):
        assert strict is True
        assert tensors[0]() is state["weight"]
        stages.append("loaded")

    model = Mock()
    # A Mock would retain the checkpoint in its recorded call arguments.
    model.load_state_dict = load_state

    def transfer(device):
        assert tensors[0]() is None, "checkpoint still retained during transfer"
        stages.append("transferred")
        return model

    def warmup(self, texts):
        assert tensors[0]() is None, "checkpoint still retained during warm-up"
        stages.append("warmed")

    model.to.side_effect = transfer
    torch = Mock()
    torch.cuda.is_available.return_value = False
    torch.load.side_effect = load_checkpoint
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "transformers", Mock())
    monkeypatch.setitem(
        sys.modules, "utils", SimpleNamespace(CLaMP3Model=Mock(return_value=model))
    )
    monkeypatch.setattr(
        clamp_text_worker,
        "_load_config",
        lambda _: SimpleNamespace(
            MAX_TEXT_LENGTH=128,
            TEXT_MODEL_NAME="test-model",
            AUDIO_HIDDEN_SIZE=768,
            AUDIO_NUM_LAYERS=12,
            MAX_AUDIO_LENGTH=128,
            M3_HIDDEN_SIZE=768,
            PATCH_NUM_LAYERS=12,
            PATCH_LENGTH=512,
            CLAMP3_LOAD_M3=False,
        ),
    )
    monkeypatch.setattr(clamp_text_worker.TextRuntime, "encode", warmup)
    # Runtime initialization prepends the external checkout to the import path.
    monkeypatch.setattr(sys, "path", list(sys.path))

    clamp_text_worker.TextRuntime(
        {
            "checkout_dir": "test-checkout",
            "weight_path": "test-checkpoint",
            "expected_dimension": 768,
        }
    )

    assert stages == ["loaded", "transferred", "warmed"]
    model.eval.assert_called_once()


def test_setup_is_idempotent_and_records_pinned_symbolic_runtime(tmp_path: Path):
    payload = b"test c2 weights"
    source_weight = tmp_path / "source-weight.pth"
    source_weight.write_bytes(payload)
    commit = "a" * 40
    calls: list[list[str]] = []

    config = ClampRuntimeConfig(
        python_executable=Path(sys.executable),
        cache_dir=tmp_path / "cache",
        commit=commit,
        model_revision="model-revision",
        weight_url=source_weight.as_uri(),
        weight_sha256=hashlib.sha256(payload).hexdigest(),
        weight_filename="weights.pth",
    )

    def runner(args, cwd, env, timeout):
        command = [str(value) for value in args]
        calls.append(command)
        if command[:3] == ["git", "clone", "--no-checkout"]:
            _write_fake_checkout(Path(command[-1]))
        if command[:3] == ["git", "rev-parse", "HEAD"]:
            return _completed(command, stdout=commit + "\n")
        return _completed(command)

    first = setup_clamp3(config, runner=runner, perform_readiness=False)
    second = setup_clamp3(config, runner=runner, perform_readiness=False)

    assert first.weight_path.read_bytes() == payload
    assert second.commit == commit
    assert first.offline_ready is False
    assert sum(command[:2] == ["git", "clone"] for command in calls) == 1
    assert '"weights_clamp3_c2"' in (
        config.checkout_dir / "code" / "config.py"
    ).read_text(encoding="utf-8")
    assert config.manifest_path.is_file()


def test_setup_runs_online_then_offline_readiness(tmp_path: Path):
    payload = b"weights"
    source_weight = tmp_path / "source.pth"
    source_weight.write_bytes(payload)
    commit = "b" * 40
    readiness_offline: list[bool] = []
    config = ClampRuntimeConfig(
        python_executable=Path(sys.executable),
        cache_dir=tmp_path / "cache",
        commit=commit,
        model_revision="revision",
        weight_url=source_weight.as_uri(),
        weight_sha256=hashlib.sha256(payload).hexdigest(),
        weight_filename="weights.pth",
    )

    def runner(args, cwd, env, timeout):
        command = [str(value) for value in args]
        if command[:3] == ["git", "clone", "--no-checkout"]:
            _write_fake_checkout(Path(command[-1]))
        elif command[-1:] == ["--get_global"]:
            readiness_offline.append(env.get("HF_HUB_OFFLINE") == "1")
        return _completed(
            command, stdout=commit + "\n" if "rev-parse" in command else ""
        )

    result = setup_clamp3(config, runner=runner)

    assert readiness_offline == [False, True]
    assert result.offline_ready is True


def test_run_extraction_uses_three_argument_array_commands_and_offline_env(
    tmp_path: Path,
):
    checkout = tmp_path / "cache" / "source"
    _write_fake_checkout(checkout)
    input_dir = tmp_path / "xml"
    input_dir.mkdir()
    (input_dir / "score.xml").write_text("<score-partwise/>", encoding="utf-8")
    output_dir = tmp_path / "features"
    calls: list[tuple[list[str], Path, dict[str, str]]] = []
    config = ClampRuntimeConfig(
        python_executable=Path(sys.executable),
        cache_dir=tmp_path / "cache",
    )

    def runner(args, cwd, env, timeout):
        calls.append(([str(value) for value in args], cwd, dict(env)))
        return _completed(list(args))

    results = run_clamp3_extraction(
        input_dir,
        output_dir,
        config,
        runner=runner,
        verify_setup=False,
    )

    assert len(results) == 3
    assert all(isinstance(command, list) for command, _, _ in calls)
    assert all(environment["HF_HUB_OFFLINE"] == "1" for _, _, environment in calls)
    assert calls[-1][0][-1] == "--get_global"


def test_run_extraction_propagates_process_failure(tmp_path: Path):
    checkout = tmp_path / "cache" / "source"
    _write_fake_checkout(checkout)
    input_dir = tmp_path / "xml"
    input_dir.mkdir()
    (input_dir / "score.xml").write_text("<score-partwise/>", encoding="utf-8")
    config = ClampRuntimeConfig(
        python_executable=Path(sys.executable),
        cache_dir=tmp_path / "cache",
    )

    def runner(args, cwd, env, timeout):
        raise ClampExecutionError("fake failure")

    with pytest.raises(ClampExecutionError, match="fake failure"):
        run_clamp3_extraction(
            input_dir,
            tmp_path / "output",
            config,
            runner=runner,
            verify_setup=False,
        )


def test_run_extraction_translates_subprocess_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    checkout = tmp_path / "cache" / "source"
    _write_fake_checkout(checkout)
    input_dir = tmp_path / "xml"
    input_dir.mkdir()
    (input_dir / "score.xml").write_text("<score-partwise/>", encoding="utf-8")
    config = ClampRuntimeConfig(
        python_executable=Path(sys.executable),
        cache_dir=tmp_path / "cache",
        timeout_seconds=12.5,
    )

    def time_out(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", time_out)

    with pytest.raises(ClampExecutionError, match="timed out after 12.5s"):
        run_clamp3_extraction(
            input_dir,
            tmp_path / "output",
            config,
            verify_setup=False,
        )


def test_run_extraction_rejects_missing_pinned_script(tmp_path: Path):
    checkout = tmp_path / "cache" / "source"
    _write_fake_checkout(checkout)
    missing = checkout / "preprocessing" / "abc" / "batch_interleaved_abc.py"
    missing.unlink()
    input_dir = tmp_path / "xml"
    input_dir.mkdir()
    (input_dir / "score.xml").write_text("<score-partwise/>", encoding="utf-8")
    config = ClampRuntimeConfig(
        python_executable=Path(sys.executable),
        cache_dir=tmp_path / "cache",
    )

    with pytest.raises(
        ClampExecutionError,
        match="Required pinned CLaMP script is missing",
    ):
        run_clamp3_extraction(
            input_dir,
            tmp_path / "output",
            config,
            verify_setup=False,
        )


def test_load_and_normalize_embeddings_preserves_expected_order_and_zero(
    tmp_path: Path,
):
    first = np.zeros(768, dtype=np.float32)
    second = np.zeros((1, 768), dtype=np.float64)
    second[0, :2] = [3.0, 4.0]
    np.save(tmp_path / "b.npy", first)
    np.save(tmp_path / "a.npy", second)

    batch = load_and_normalize_embeddings(
        tmp_path,
        expected_stems=["b", "a"],
    )

    assert batch.stems == ("b", "a")
    assert batch.raw.dtype == np.float32
    assert np.array_equal(batch.normalized[0], np.zeros(768, dtype=np.float32))
    assert batch.normalized[1, :2] == pytest.approx([0.6, 0.8])


@pytest.mark.parametrize(
    "array",
    [
        np.zeros(767, dtype=np.float32),
        np.full(768, np.nan, dtype=np.float32),
    ],
)
def test_load_embeddings_rejects_bad_shape_and_non_finite(
    tmp_path: Path,
    array: np.ndarray,
):
    np.save(tmp_path / "bad.npy", array)

    with pytest.raises(EmbeddingValidationError):
        load_and_normalize_embeddings(tmp_path)


def test_load_embeddings_rejects_missing_and_unexpected_stems(tmp_path: Path):
    np.save(tmp_path / "unexpected.npy", np.zeros(768, dtype=np.float32))

    with pytest.raises(EmbeddingValidationError, match="missing=.*expected"):
        load_and_normalize_embeddings(tmp_path, expected_stems=["expected"])


def test_load_embeddings_allows_missing_expected_in_requested_order(tmp_path: Path):
    np.save(tmp_path / "third.npy", np.full(768, 3.0, dtype=np.float32))
    np.save(tmp_path / "first.npy", np.full(768, 1.0, dtype=np.float32))

    batch = load_and_normalize_embeddings(
        tmp_path,
        expected_stems=["first", "missing", "third"],
        allow_missing_expected=True,
    )

    assert batch.stems == ("first", "third")
    assert batch.raw[:, 0].tolist() == [1.0, 3.0]


def test_load_embeddings_partial_mode_still_rejects_unexpected_stems(tmp_path: Path):
    np.save(tmp_path / "expected.npy", np.zeros(768, dtype=np.float32))
    np.save(tmp_path / "unexpected.npy", np.zeros(768, dtype=np.float32))

    with pytest.raises(EmbeddingValidationError, match="unexpected=.*unexpected"):
        load_and_normalize_embeddings(
            tmp_path,
            expected_stems=["expected", "missing"],
            allow_missing_expected=True,
        )


def test_embed_texts_preserves_order_and_uses_safe_offline_command(tmp_path: Path):
    checkout = tmp_path / "cache" / "source"
    _write_fake_checkout(checkout)
    config = ClampRuntimeConfig(
        python_executable=Path(sys.executable),
        cache_dir=tmp_path / "cache",
        commit="c" * 40,
        model_revision="text-model",
        weight_sha256="d" * 64,
        expected_dimension=3,
        timeout_seconds=17.0,
    )
    calls: list[tuple[list[str], Path, dict[str, str], float]] = []
    workspace: Path | None = None

    def runner(args, cwd, env, timeout):
        nonlocal workspace
        command = [str(value) for value in args]
        calls.append((command, cwd, dict(env), timeout))
        input_dir = Path(command[2])
        output_dir = Path(command[3])
        workspace = input_dir.parent
        assert [path.name for path in sorted(input_dir.iterdir())] == [
            "text_000000.txt",
            "text_000001.txt",
        ]
        assert (input_dir / "text_000000.txt").read_text(encoding="utf-8") == "joy"
        assert (input_dir / "text_000001.txt").read_text(encoding="utf-8") == "sad"
        np.save(output_dir / "text_000001.npy", np.array([0.0, 3.0, 4.0]))
        np.save(output_dir / "text_000000.npy", np.array([1.0, 0.0, 0.0]))
        return _completed(command)

    result = embed_clamp3_texts(
        ["joy", "sad"],
        config,
        runner=runner,
        verify_setup=False,
    )

    extract = checkout / "code" / "extract_clamp3.py"
    command, cwd, environment, timeout = calls[0]
    assert command[:2] == [str(config.python_executable), str(extract)]
    assert command[-1] == "--get_global"
    assert Path(command[2]).name == "input"
    assert Path(command[3]).name == "output"
    assert "joy" not in command and "sad" not in command
    assert cwd == extract.parent
    assert timeout == 17.0
    assert environment["HF_HUB_OFFLINE"] == "1"
    assert environment["TRANSFORMERS_OFFLINE"] == "1"
    assert result.texts == ("joy", "sad")
    assert result.stems == ("text_000000", "text_000001")
    assert result.raw.tolist() == [[1.0, 0.0, 0.0], [0.0, 3.0, 4.0]]
    assert np.allclose(
        result.normalized,
        np.array([[1.0, 0.0, 0.0], [0.0, 0.6, 0.8]]),
    )
    assert result.model_identity.model_commit == "c" * 40
    assert result.model_identity.model_revision == "text-model"
    assert result.model_identity.model_weight_sha256 == "d" * 64
    assert result.model_identity.dimension == 3
    assert workspace is not None and not workspace.exists()


@pytest.mark.parametrize("text", ["", " ", "\n\t"])
def test_embed_texts_rejects_blank_input_actionably(tmp_path: Path, text: str):
    config = ClampRuntimeConfig(
        python_executable=Path(sys.executable),
        cache_dir=tmp_path,
    )

    with pytest.raises(
        EmbeddingValidationError,
        match="Text input at index 1 must not be blank",
    ):
        embed_clamp3_texts(["valid", text], config, verify_setup=False)


def test_embed_texts_cleans_workspace_after_runner_failure(tmp_path: Path):
    checkout = tmp_path / "cache" / "source"
    _write_fake_checkout(checkout)
    config = ClampRuntimeConfig(
        python_executable=Path(sys.executable),
        cache_dir=tmp_path / "cache",
    )
    workspace: Path | None = None

    def runner(args, cwd, env, timeout):
        nonlocal workspace
        workspace = Path(args[2]).parent
        raise ClampExecutionError("text inference failed")

    with pytest.raises(ClampExecutionError, match="text inference failed"):
        embed_clamp3_texts(
            ["calm"],
            config,
            runner=runner,
            verify_setup=False,
        )

    assert workspace is not None and not workspace.exists()


@pytest.mark.parametrize(
    ("malformation", "message"),
    [
        ("missing", "missing=.*text_000001"),
        ("unexpected", "unexpected=.*other"),
        ("duplicate", "Duplicate embedding stem 'text_000000'"),
        ("dimension", r"has shape .* expected \(3,\)"),
        ("nonfinite", "contains non-finite values"),
    ],
)
def test_embed_texts_rejects_malformed_outputs(
    tmp_path: Path,
    malformation: str,
    message: str,
):
    checkout = tmp_path / "cache" / "source"
    _write_fake_checkout(checkout)
    config = ClampRuntimeConfig(
        python_executable=Path(sys.executable),
        cache_dir=tmp_path / "cache",
        expected_dimension=3,
    )

    def runner(args, cwd, env, timeout):
        output_dir = Path(args[3])
        first = np.array([1.0, 2.0, 3.0])
        second = np.array([4.0, 5.0, 6.0])
        if malformation == "dimension":
            first = np.array([1.0, 2.0])
        elif malformation == "nonfinite":
            first = np.array([1.0, np.nan, 3.0])
        np.save(output_dir / "text_000000.npy", first)
        if malformation != "missing":
            np.save(output_dir / "text_000001.npy", second)
        if malformation == "unexpected":
            np.save(output_dir / "other.npy", second)
        elif malformation == "duplicate":
            nested = output_dir / "nested"
            nested.mkdir()
            np.save(nested / "text_000000.npy", first)
        return _completed(list(args))

    with pytest.raises(EmbeddingValidationError, match=message):
        embed_clamp3_texts(
            ["positive", "negative"],
            config,
            runner=runner,
            verify_setup=False,
        )
