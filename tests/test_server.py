"""Tests for server transport configuration."""

from src.encoding_music_mcp import server
from src.encoding_music_mcp import score_embeddings
from src.encoding_music_mcp.score_embeddings import clamp_extractor
from src.encoding_music_mcp.tools import semantic_axis_retrieval
from src.encoding_music_mcp.tools import prototype_retrieval


def test_http_server_configures_proxy_and_keep_alive(monkeypatch):
    """HTTP deployment settings should be passed through to Uvicorn."""
    captured = {}

    def fake_run(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(server.mcp, "run", fake_run)
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    monkeypatch.setenv("MCP_HOST", "127.0.0.2")
    monkeypatch.setenv("MCP_PORT", "8123")
    monkeypatch.setenv("MCP_FORWARDED_ALLOW_IPS", "*")
    monkeypatch.setenv("MCP_HTTP_KEEP_ALIVE", "42")

    server.main()

    assert captured == {
        "transport": "http",
        "host": "127.0.0.2",
        "port": 8123,
        "uvicorn_config": {
            "proxy_headers": True,
            "forwarded_allow_ips": "*",
            "timeout_keep_alive": 42,
        },
    }


def test_stdio_remains_the_default_transport(monkeypatch):
    """Local clients should retain the zero-argument stdio entrypoint."""
    calls = []
    monkeypatch.delenv("MCP_TRANSPORT", raising=False)
    monkeypatch.setattr(server.mcp, "run", lambda **kwargs: calls.append(kwargs))

    server.main()

    assert calls == [{}]


def test_server_startup_is_clamp_lazy_and_shutdown_closes_resources(monkeypatch):
    clamp_extractor.close_persistent_clamp_text_encoder()
    closed = []
    monkeypatch.setattr(server.mcp, "run", lambda **kwargs: None)
    monkeypatch.setattr(
        score_embeddings,
        "close_persistent_clamp_text_encoder",
        lambda: closed.append("worker"),
    )
    monkeypatch.setattr(
        semantic_axis_retrieval,
        "close_semantic_axis_retrieval_resources",
        lambda: closed.append("repository"),
    )
    monkeypatch.setattr(
        prototype_retrieval,
        "close_prototype_retrieval_resources",
        lambda: closed.append("prototype-repository"),
    )

    server.main()

    assert clamp_extractor._PERSISTENT_TEXT_ENCODER._worker is None
    assert closed == ["prototype-repository", "repository", "worker"]
