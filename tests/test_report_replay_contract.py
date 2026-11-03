"""Contract tests for the report replay MCP tool."""

import asyncio
import inspect
from types import SimpleNamespace

from src.encoding_music_mcp.tools.report_replay import replay_report
from src.encoding_music_mcp.tools.reports import settings


def test_mcp_app_tool_list_matches_registered_app_tools():
    assert settings.MCP_APP_TOOLS == [
        "show_notation",
        "show_notation_highlight",
        "plot_voice_ranges",
        "plot_weighted_note_distribution",
        "plot_melodic_ngram_heatmap",
        "plot_sonority_ngram_progress",
        "play_excerpt",
    ]
    assert set(settings.MCP_APP_ALLOWED_CALLS) == set(settings.MCP_APP_TOOLS)
    assert settings.MCP_APP_ALLOWED_CALLS["show_notation"] == {"show_notation"}
    assert settings.MCP_APP_ALLOWED_CALLS["show_notation_highlight"] == {
        "show_notation_highlight"
    }
    assert settings.MCP_APP_ALLOWED_CALLS["play_excerpt"] == {
        "load_audio_resource"
    }


def test_replay_report_derives_url_from_http_request(monkeypatch):
    monkeypatch.setattr(
        settings,
        "get_http_request",
        lambda: SimpleNamespace(base_url="http://127.0.0.1:8000/"),
    )
    signature = inspect.signature(replay_report)

    assert list(signature.parameters) == ["session_id"]
    assert signature.parameters["session_id"].default is None
    assert signature.return_annotation in {str, "str"}
    assert asyncio.run(replay_report("session-123")) == (
        "http://127.0.0.1:8000/reports/replay/session-123"
    )


def test_replay_report_returns_upload_url_without_session(monkeypatch):
    monkeypatch.setattr(
        settings,
        "get_http_request",
        lambda: SimpleNamespace(base_url="https://example.test/"),
    )

    assert asyncio.run(replay_report()) == "https://example.test/reports/replay"


def test_base_url_defaults_to_relative_replay_page_without_http_request(monkeypatch):
    def no_http_request():
        raise RuntimeError

    monkeypatch.setattr(settings, "get_http_request", no_http_request)

    assert settings.base_url() == "/reports/replay"
