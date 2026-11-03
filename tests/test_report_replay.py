"""Tests for conversation report replay and HTML export."""

import asyncio
import json
from types import SimpleNamespace

import pytest
from mcp.types import TextContent
from fastmcp.resources import ResourceContent, ResourceResult
from starlette.requests import Request

from src.encoding_music_mcp.tools.reports.html import render_upload_page
from src.encoding_music_mcp.tools.reports.parser import (
    ReportParseError,
    parse_report_jsonl,
)
from src.encoding_music_mcp.tools.reports.replay import (
    MAX_OUTPUT_STRING_CHARS,
    replay_report,
)
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
            "plot_voice_ranges": SimpleNamespace(
                meta={"ui": {"resourceUri": "ui://voice-ranges/view.html"}},
                parameters={
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string"},
                        "session_id": {"type": "string"},
                    },
                    "required": ["filename", "session_id"],
                },
            ),
            "show_notation": SimpleNamespace(
                meta={"ui": {"resourceUri": "ui://notation/view.html"}},
                parameters={
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string"},
                        "page": {"type": "integer"},
                        "session_id": {"type": "string"},
                    },
                    "required": ["filename", "session_id"],
                },
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
        if name == "plot_voice_ranges":
            return SimpleNamespace(
                structured_content={
                    "filename": arguments.get("filename"),
                    "large_app_value": "x" * (MAX_OUTPUT_STRING_CHARS + 1),
                },
                content=[TextContent(type="text", text="voice ranges")],
                is_error=False,
            )
        if name == "show_notation":
            return SimpleNamespace(
                structured_content={
                    "filename": arguments.get("filename"),
                    "page": arguments.get("page", 1),
                    "svg": "<svg></svg>",
                },
                content=[TextContent(type="text", text="notation")],
                is_error=False,
            )
        return SimpleNamespace(
            structured_content={"received": arguments.get("value")},
            content=[TextContent(type="text", text="done")],
            is_error=False,
        )

    async def read_resource(self, uri: str, *, run_middleware: bool):
        assert run_middleware is False
        return ResourceResult(
            contents=[
                ResourceContent(
                    content=f"<!doctype html><title>{uri}</title>",
                    mime_type="text/html;profile=mcp-app",
                )
            ]
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


def test_app_uri_comes_from_tool_metadata_and_app_output_is_not_shortened():
    fake = FakeMCP()
    report = parse_report_jsonl(
        _report(
            {
                "tool_name": "plot_voice_ranges",
                "args": {"filename": "Bach_BWV_0772.mei"},
            }
        )
    )

    result = asyncio.run(replay_report(report, fake))

    call = result.calls[0]
    assert call.app_resource_uri == "ui://voice-ranges/view.html"
    assert len(call.structured_output["large_app_value"]) == (
        MAX_OUTPUT_STRING_CHARS + 1
    )


def test_upload_page_displays_json_values_as_plain_text():
    upload = render_upload_page()
    assert "Replay tools" in upload
    assert 'aria-live="polite"' in upload
    assert "application/json" in upload
    assert 'class="replay-results"' in upload
    assert 'toolCall.className = "tool-call"' in upload
    assert 'labelledValue("tool-arguments", "Arguments", call.arguments)' in upload
    assert '"tool-response"' in upload
    assert "output.replaceChildren()" in upload
    assert 'frame.setAttribute("sandbox", "allow-scripts")' in upload
    assert "new AppBridge(" in upload
    assert "bridge.sendToolInput" in upload
    assert "bridge.sendToolResult" in upload
    assert "showJsonFallback" in upload
    assert "<svg" not in upload
    assert "visualization" not in upload.lower()


def test_session_replay_page_does_not_embed_the_report():
    class RouteRegistry(FakeMCP):
        def __init__(self):
            super().__init__()
            self.routes = {}

        def custom_route(self, path, methods):
            def register(handler):
                self.routes[path] = (methods, handler)
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

    methods, handler = registry.routes["/reports/replay/{session_id}"]
    assert methods == ["GET", "POST"]
    response = asyncio.run(handler(request))
    page = response.body.decode()

    assert response.media_type == "text/html"
    assert "This session's conversation report is ready to replay." in page
    assert "historical-session" not in page
    assert "const sessionMode = true" in page
    assert 'id="report-file"' not in page


def test_replay_endpoint_returns_json_values_not_visualizations():
    class RouteRegistry(FakeMCP):
        def __init__(self):
            super().__init__()
            self.routes = {}

        def custom_route(self, path, methods):
            def register(handler):
                self.routes[path] = (methods, handler)
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

    _methods, handler = registry.routes["/reports/replay"]
    response = asyncio.run(handler(request))
    payload = json.loads(response.body)

    assert response.media_type == "application/json"
    assert payload["calls"][0]["tool_name"] == "first"
    assert payload["calls"][0]["arguments"] == {"value": 7}
    assert payload["calls"][0]["status"] == "success"
    assert payload["calls"][0]["output"] == {"received": 7}
    assert "visualization_svg" not in payload["calls"][0]


def test_replay_endpoint_includes_app_descriptor_and_complete_result():
    class RouteRegistry(FakeMCP):
        def __init__(self):
            super().__init__()
            self.routes = {}

        def custom_route(self, path, methods):
            def register(handler):
                self.routes[path] = (methods, handler)
                return handler

            return register

    registry = RouteRegistry()
    register_report_routes(registry)
    body = _report(
        {
            "tool_name": "plot_voice_ranges",
            "args": {"filename": "Bach_BWV_0772.mei"},
        }
    ).encode()

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/reports/replay",
            "headers": [],
        },
        receive,
    )
    _methods, handler = registry.routes["/reports/replay"]

    response = asyncio.run(handler(request))
    payload = json.loads(response.body)
    call = payload["calls"][0]

    assert call["app"]["resource_uri"] == "ui://voice-ranges/view.html"
    assert call["app"]["resource_url"] == (
        "/reports/replay/apps/plot_voice_ranges"
    )
    assert call["app"]["result"]["structuredContent"] == call["output"]
    assert len(call["output"]["large_app_value"]) == MAX_OUTPUT_STRING_CHARS + 1


def test_app_resource_route_serves_registered_html_and_rejects_non_app():
    class RouteRegistry(FakeMCP):
        def __init__(self):
            super().__init__()
            self.routes = {}

        def custom_route(self, path, methods):
            def register(handler):
                self.routes[path] = (methods, handler)
                return handler

            return register

    registry = RouteRegistry()
    register_report_routes(registry)
    methods, handler = registry.routes["/reports/replay/apps/{tool_name}"]
    assert methods == ["GET"]

    app_request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/reports/replay/apps/plot_voice_ranges",
            "headers": [],
            "path_params": {"tool_name": "plot_voice_ranges"},
        }
    )
    response = asyncio.run(handler(app_request))
    assert response.status_code == 200
    assert response.media_type == "text/html;profile=mcp-app"
    assert "ui://voice-ranges/view.html" in response.body.decode()
    assert "Content-Security-Policy" in response.headers

    non_app_request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/reports/replay/apps/first",
            "headers": [],
            "path_params": {"tool_name": "first"},
        }
    )
    rejected = asyncio.run(handler(non_app_request))
    assert rejected.status_code == 404


def test_app_call_route_allows_only_scoped_tools_and_injects_fresh_session():
    class RouteRegistry(FakeMCP):
        def __init__(self):
            super().__init__()
            self.routes = {}

        def custom_route(self, path, methods):
            def register(handler):
                self.routes[path] = (methods, handler)
                return handler

            return register

    async def post(handler, payload):
        body = json.dumps(payload).encode()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/reports/replay/app-call",
                "headers": [(b"content-type", b"application/json")],
            },
            receive,
        )
        return await handler(request)

    registry = RouteRegistry()
    register_report_routes(registry)
    methods, handler = registry.routes["/reports/replay/app-call"]
    assert methods == ["POST"]

    allowed = asyncio.run(
        post(
            handler,
            {
                "source_tool": "show_notation",
                "tool_name": "show_notation",
                "arguments": {"filename": "Bach_BWV_0772.mei", "page": 2},
            },
        )
    )
    assert allowed.status_code == 200
    payload = json.loads(allowed.body)
    assert payload["structuredContent"]["page"] == 2
    notation_args = next(
        args for name, args, _run in registry.calls if name == "show_notation"
    )
    assert notation_args["session_id"] == "fresh-session"
    assert registry.calls[-1][0] == "end_session"

    forbidden = asyncio.run(
        post(
            handler,
            {
                "source_tool": "show_notation",
                "tool_name": "first",
                "arguments": {"value": 1},
            },
        )
    )
    assert forbidden.status_code == 403

    injected = asyncio.run(
        post(
            handler,
            {
                "source_tool": "show_notation",
                "tool_name": "show_notation",
                "arguments": {"session_id": "stolen"},
            },
        )
    )
    assert injected.status_code == 400
