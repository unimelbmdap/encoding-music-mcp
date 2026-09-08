"""Bootstrap orchestration must isolate environments and fail before model setup."""

import subprocess
from types import SimpleNamespace

import pytest

from encoding_music_mcp.score_embeddings import bootstrap
from encoding_music_mcp.score_embeddings.clamp_extractor import ClampSetupError
from encoding_music_mcp.score_embeddings.pipeline import cli


@pytest.fixture
def host(tmp_path, monkeypatch):
    monkeypatch.setattr(bootstrap, "repository_root", lambda: tmp_path)
    monkeypatch.setattr(bootstrap.sys, "platform", "linux")
    monkeypatch.setattr(bootstrap.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(bootstrap.shutil, "which", lambda name: f"/tools/{name}")
    return tmp_path


@pytest.mark.parametrize("profile", ["cpu", "cu128"])
def test_bootstrap_is_locked_isolated_and_repeatable(host, monkeypatch, profile):
    commands = []
    configs = []
    monkeypatch.setenv("UV_PROJECT_ENVIRONMENT", "/wrong/environment")
    monkeypatch.setenv("VIRTUAL_ENV", "/server/environment")
    monkeypatch.setenv("ENCODING_MUSIC_CLAMP_PYTHON", "/external/python")
    monkeypatch.setattr(
        bootstrap.subprocess, "run", lambda cmd, **kw: commands.append((cmd, kw))
    )
    expected = SimpleNamespace(offline_ready=True)

    def setup(config):
        configs.append(config)
        return expected

    monkeypatch.setattr(bootstrap, "setup_clamp3", setup)
    for _ in range(2):
        assert bootstrap.bootstrap_clamp3(profile=profile) is expected
    assert commands[:2] == commands[2:]
    sync, options = commands[0]
    assert sync[:2] == ["/tools/uv", "sync"]
    assert "--locked" in sync
    assert sync[sync.index("--extra") + 1] == profile
    assert sync[sync.index("--python") + 1] == bootstrap.PYTHON_VERSION
    assert options["env"]["UV_PROJECT_ENVIRONMENT"] == str(host / ".venv-clamp")
    assert "VIRTUAL_ENV" not in options["env"]
    assert options["check"] is True
    assert configs[0].python_executable == host / ".venv-clamp/bin/python"
    assert configs[0].cache_dir == host / ".clamp3-cache"
    probe = commands[1][0]
    assert probe[0] == str(configs[0].python_executable)
    assert ("torch.cuda.synchronize()" in probe[-1]) == (profile == "cu128")


@pytest.mark.parametrize("failed_step", [1, 2])
def test_install_or_gpu_probe_failure_does_not_download_models(
    host, monkeypatch, failed_step
):
    count = 0

    def run(cmd, **kwargs):
        nonlocal count
        count += 1
        if count == failed_step:
            raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(bootstrap.subprocess, "run", run)
    monkeypatch.setattr(
        bootstrap, "setup_clamp3", lambda _: pytest.fail("Downloaded models")
    )
    with pytest.raises(ClampSetupError, match="rerun bootstrap"):
        bootstrap.bootstrap_clamp3(profile="cu128")
    assert count == failed_step


@pytest.mark.parametrize(
    "problem", ["platform", "checkout", "uv", "git", "profile", "timeout"]
)
def test_preflight_failures_do_not_install(host, monkeypatch, problem):
    kwargs = {}
    if problem == "platform":
        monkeypatch.setattr(bootstrap.platform, "machine", lambda: "arm64")
    elif problem == "checkout":
        monkeypatch.setattr(bootstrap, "repository_root", lambda: None)
    elif problem in {"uv", "git"}:
        monkeypatch.setattr(
            bootstrap.shutil, "which", lambda name: None if name == problem else name
        )
    elif problem == "profile":
        kwargs["profile"] = "unknown"
    else:
        kwargs["timeout_seconds"] = float("nan")
    monkeypatch.setattr(
        bootstrap.subprocess, "run", lambda *a, **k: pytest.fail("Installed packages")
    )
    with pytest.raises(ClampSetupError):
        bootstrap.bootstrap_clamp3(**kwargs)


def test_bootstrap_cli_reports_result_and_failure(tmp_path, monkeypatch, capsys):
    calls = []

    def setup(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(checkout_dir=tmp_path / "source", offline_ready=True)

    monkeypatch.setattr(bootstrap, "bootstrap_clamp3", setup)
    assert cli(["bootstrap", "--profile", "cu128", "--timeout", "123"]) == 0
    assert calls == [{"profile": "cu128", "timeout_seconds": 123.0}]
    assert '"offline_ready": true' in capsys.readouterr().out

    def fail(**kwargs):
        raise ClampSetupError("No compatible device")

    monkeypatch.setattr(bootstrap, "bootstrap_clamp3", fail)
    assert cli(["bootstrap"]) == 1
