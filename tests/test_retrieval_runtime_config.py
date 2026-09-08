"""Both retrieval tools must discover the same explicitly prepared runtime."""

import sys
from pathlib import Path

import pytest

from encoding_music_mcp.score_embeddings import runtime_config as runtime
from encoding_music_mcp.tools import prototype_retrieval, semantic_axis_retrieval


@pytest.fixture(params=[prototype_retrieval, semantic_axis_retrieval])
def tool(request):
    return request.param


@pytest.fixture
def checkout(tmp_path, monkeypatch):
    root = tmp_path / "checkout with spaces"
    root.mkdir()
    monkeypatch.setattr(runtime, "repository_root", lambda: root)
    return root


def prepare(root):
    python = runtime.environment_python(root / ".venv-clamp")
    python.parent.mkdir(parents=True)
    python.touch()
    cache = root / ".clamp3-cache"
    cache.mkdir()
    (cache / "setup-manifest.json").write_text('{"offline_ready": true}')
    return python, cache


def test_both_tools_use_checkout_even_from_another_cwd(
    tool, checkout, tmp_path, monkeypatch
):
    python, cache = prepare(checkout)
    monkeypatch.chdir(tmp_path)
    config = tool.config_from_environment({})
    assert config.clamp.python_executable == python
    assert config.clamp.cache_dir == cache
    assert config.database_path == tool.STATIC_DATABASE_PATH


def test_overrides_take_precedence_over_checkout(tool, checkout):
    prepare(checkout)
    cache = checkout / "external-cache"
    config = tool.config_from_environment(
        {
            runtime.CLAMP_PYTHON_ENV: sys.executable,
            runtime.CLAMP_CACHE_ENV: str(cache),
            runtime.CLAMP_TIMEOUT_ENV: "12.5",
        }
    )
    assert config.clamp.python_executable == Path(sys.executable).absolute()
    assert config.clamp.cache_dir == cache
    assert config.clamp.timeout_seconds == 12.5


def test_invalid_override_never_falls_back(tool, checkout):
    prepare(checkout)
    with pytest.raises(RuntimeError, match="Fix the override"):
        tool.config_from_environment(
            {runtime.CLAMP_PYTHON_ENV: str(checkout / "missing")}
        )


@pytest.mark.parametrize("prepared", ["nothing", "python", "cache"])
def test_incomplete_setup_tells_user_to_bootstrap(tool, checkout, prepared):
    python, cache = prepare(checkout)
    if prepared in {"nothing", "cache"}:
        python.unlink()
    if prepared in {"nothing", "python"}:
        (cache / "setup-manifest.json").unlink()
    with pytest.raises(RuntimeError, match="encoding-music-embeddings bootstrap"):
        tool.config_from_environment({})


def test_external_runtime_still_works_without_checkout(tool, monkeypatch):
    monkeypatch.setattr(runtime, "repository_root", lambda: None)
    config = tool.config_from_environment({runtime.CLAMP_PYTHON_ENV: sys.executable})
    assert config.clamp.python_executable == Path(sys.executable).absolute()
    with pytest.raises(RuntimeError, match=runtime.CLAMP_PYTHON_ENV):
        tool.config_from_environment({})


@pytest.mark.parametrize("timeout", ["bad", "nan", "inf", "0", "-1", ""])
def test_invalid_timeout_rejected_by_both_tools(tool, checkout, timeout):
    prepare(checkout)
    with pytest.raises(RuntimeError, match="positive finite"):
        tool.config_from_environment({runtime.CLAMP_TIMEOUT_ENV: timeout})


def test_source_root_discovery_does_not_use_cwd(tmp_path, monkeypatch):
    expected = Path(runtime.__file__).resolve().parents[3]
    monkeypatch.chdir(tmp_path)
    assert runtime.repository_root() == expected


@pytest.mark.parametrize(
    "os_name, relative", [("nt", "Scripts/python.exe"), ("posix", "bin/python")]
)
def test_platform_interpreter_layout(monkeypatch, os_name, relative):
    root = Path("clamp")
    # Replace the module's os binding, without changing pathlib's global OS.
    from types import SimpleNamespace

    monkeypatch.setattr(runtime, "os", SimpleNamespace(name=os_name))
    assert runtime.environment_python(root) == root / relative


def test_interpreter_symlink_is_preserved(checkout):
    python = runtime.environment_python(checkout / ".venv-clamp")
    python.parent.mkdir(parents=True)
    python.symlink_to(sys.executable)
    config = runtime.resolve_clamp_runtime(
        {
            runtime.CLAMP_PYTHON_ENV: str(python),
            runtime.CLAMP_CACHE_ENV: str(checkout / "cache"),
        }
    )
    assert config.python_executable == python
