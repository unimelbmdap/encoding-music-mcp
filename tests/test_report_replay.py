"""Tests for conversation report replay and HTML export."""

import asyncio
import json
from types import SimpleNamespace

import pytest
from mcp.types import TextContent
from starlette.requests import Request

from src.encoding_music_mcp.tools.reports.html import render_upload_page
from src.encoding_music_mcp.tools.reports.parser import (
    ReportParseError,
    parse_report_jsonl,
)
from src.encoding_music_mcp.tools.reports.replay import replay_report
from src.encoding_music_mcp.tools.reports.routes import register_report_routes


def _report(*records: dict[str, object]) -> str:
    header = {
        "type": "conversation_report",
        "version": "1",
        "session_id": "historical-session",
    }
    return "\n".join(json.dumps(item) for item in (header, *records))


def test_parser_preserves_call_order_and_arguments():
    report = parse_report_jsonl(
        _report(
            {"tool_name": "first", "args": {"filename": "a.mei"}},
            {"tool_name": "second", "args": {"n": 4}},
        )
    )

    assert [call.id for call in report.calls] == ["call-0001", "call-0002"]
    assert [call.tool_name for call in report.calls] == ["first", "second"]
    assert report.calls[1].arguments == {"n": 4}


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("", "empty"),
        ('{"type":"conversation_report"}', "not supported"),
        (_report({"tool_name": "x", "args": []}), "args object"),
        (
            _report({"tool_name": "x", "args": {"session_id": "injected"}}),
            "cannot provide",
        ),
        (_report({"type": "conversation_report", "args": {}}), "duplicate"),
    ],
)
def test_parser_rejects_invalid_reports_before_replay(source: str, message: str):
    with pytest.raises(ReportParseError, match=message):
        parse_report_jsonl(source)


class FakeMCP:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object], bool]] = []
        self.tools = {
            "first": SimpleNamespace(
                parameters={
                    "type": "object",
                    "properties": {
                        "value": {"type": "integer"},
                        "session_id": {"type": "string"},
                    },
                    "required": ["value", "session_id"],
                }
            ),
            "fails": SimpleNamespace(
                parameters={
                    "type": "object",
                    "properties": {"session_id": {"type": "string"}},
                    "required": ["session_id"],
                }
            ),
            "register_mei_file_from_path": SimpleNamespace(
                parameters={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "session_id": {"type": "string"},
                    },
                    "required": ["session_id"],
                }
            ),
        }

    async def get_tool(self, name: str):
        return self.tools.get(name)

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, object],
        *,
        run_middleware: bool,
    ):
        self.calls.append((name, dict(arguments), run_middleware))
        if name == "create_session":
            return SimpleNamespace(
                structured_content={"result": "fresh-session"},
                content=[],
                is_error=False,
            )
        if name == "end_session":
            return SimpleNamespace(structured_content={}, content=[], is_error=False)
        if name == "fails":
            raise RuntimeError("known failure")
        return SimpleNamespace(
            structured_content={"received": arguments.get("value")},
            content=[TextContent(type="text", text="done")],
            is_error=False,
        )


def test_replay_uses_fresh_session_continues_after_error_and_skips_unsafe_call():
    source = _report(
        {"tool_name": "fails", "args": {}},
        {"tool_name": "first", "args": {"value": 7}},
        {
            "tool_name": "register_mei_file_from_path",
            "args": {"file_path": "/server/secret.mei"},
        },
    )
    fake = FakeMCP()

    result = asyncio.run(replay_report(parse_report_jsonl(source), fake))

    assert [call.status for call in result.calls] == ["error", "success", "skipped"]
    assert result.status == "partial"
    replayed = next(args for name, args, _ in fake.calls if name == "first")
    assert replayed == {"value": 7, "session_id": "fresh-session"}
    assert "historical-session" not in json.dumps(fake.calls)
    assert not any(
        name == "register_mei_file_from_path" for name, _args, _run in fake.calls
    )
    assert all(run_middleware is False for _name, _args, run_middleware in fake.calls)
    assert fake.calls[-1][0] == "end_session"


def test_unknown_tool_is_visible_and_does_not_prevent_later_replay():
    fake = FakeMCP()
    report = parse_report_jsonl(
        _report(
            {"tool_name": "removed_tool", "args": {"old": True}},
            {"tool_name": "first", "args": {"value": 2}},
        )
    )

    result = asyncio.run(replay_report(report, fake))

    assert [call.status for call in result.calls] == ["skipped", "success"]
    assert "not registered" in result.calls[0].message


def test_upload_page_displays_json_values_as_plain_text():
    upload = render_upload_page()
    assert "Replay tools" in upload
    assert 'aria-live="polite"' in upload
    assert "application/json" in upload
    assert "<svg" not in upload
    assert "visualization" not in upload.lower()


def test_session_replay_page_does_not_embed_the_report():
    class RouteRegistry(FakeMCP):
        def __init__(self):
            super().__init__()
            self.routes = {}

        def custom_route(self, path, methods):
            assert methods == ["GET", "POST"]

            def register(handler):
                self.routes[path] = handler
                return handler

            return register

    registry = RouteRegistry()
    register_report_routes(registry)
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/reports/replay/session-123",
            "headers": [],
            "path_params": {"session_id": "session-123"},
        }
    )

    response = asyncio.run(registry.routes["/reports/replay/{session_id}"](request))
    page = response.body.decode()

    assert response.media_type == "text/html"
    assert "This session's conversation report is ready to replay." in page
    assert "historical-session" not in page
    assert "const sessionMode = true" in page
    assert 'id="report-file"' not in page


def test_replay_endpoint_returns_json_values_not_visualizations():
    class RouteRegistry(FakeMCP):
        def custom_route(self, _path, methods):
            assert methods == ["GET", "POST"]

            def register(handler):
                self.handler = handler
                return handler

            return register

    registry = RouteRegistry()
    register_report_routes(registry)
    body = _report({"tool_name": "first", "args": {"value": 7}}).encode()

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    request = Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/reports/replay",
            "raw_path": b"/reports/replay",
            "query_string": b"",
            "headers": [(b"content-type", b"application/jsonl")],
            "server": ("testserver", 80),
            "client": ("testclient", 1234),
        },
        receive,
    )

    response = asyncio.run(registry.handler(request))
    payload = json.loads(response.body)

    assert response.media_type == "application/json"
    assert payload["calls"][0]["tool_name"] == "first"
    assert payload["calls"][0]["status"] == "success"
    assert payload["calls"][0]["output"] == {"received": 7}
    assert "visualization_svg" not in payload["calls"][0]
