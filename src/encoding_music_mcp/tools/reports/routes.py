"""HTTP adapter for opening and replaying conversation reports."""

import asyncio
from typing import Any
from urllib.parse import quote

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from ..conversation_report import ConversationReport
from .html import render_upload_page
from .parser import parse_report_jsonl
from .replay import CALL_TIMEOUT_SECONDS, _app_output, replay_report
from .settings import (
    REPLAY_APP_CALL_PATH,
    REPLAY_APP_PATH,
    REPLAY_PATH,
    REPLAY_SESSION_PATH,
)

_APP_CSP = (
    "default-src 'none'; "
    "script-src 'unsafe-inline' https://unpkg.com; "
    "style-src 'unsafe-inline'; "
    "img-src data: blob:; "
    "media-src blob:; "
    "connect-src https://unpkg.com"
)


def register_report_routes(mcp: Any) -> None:
    """Register the report upload page and replay endpoint."""

    # Register this static path before /reports/replay/{session_id}, otherwise
    # Starlette can interpret "app-call" as a session ID.
    @mcp.custom_route(REPLAY_APP_CALL_PATH, methods=["POST"])
    async def replay_app_call(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
            tool_name = payload["tool_name"]
            call_arguments = dict(payload["arguments"])
            result = await asyncio.wait_for(
                mcp.call_tool(tool_name, call_arguments, run_middleware=False),
                timeout=CALL_TIMEOUT_SECONDS,
            )
            return JSONResponse(_tool_result_payload(result))
        except Exception as exc:
            return _error_response(str(exc) or type(exc).__name__, 500)

    @mcp.custom_route(REPLAY_APP_PATH, methods=["GET"])
    async def replay_app_resource(request: Request) -> HTMLResponse | JSONResponse:
        """Return the HTML resource for a given app tool name."""
        try:
            tool_name = request.path_params["tool_name"]
            tool = await mcp.get_tool(tool_name)
            resource_uri = tool.meta["ui"]["resourceUri"]
            resource = await mcp.read_resource(resource_uri, run_middleware=False)
            return HTMLResponse(
                resource.contents[0].content,
                media_type="text/html;profile=mcp-app",
                headers={"Content-Security-Policy": _APP_CSP},
            )
        except Exception as exc:
            return _error_response(str(exc) or type(exc).__name__, 500)

    @mcp.custom_route(REPLAY_SESSION_PATH, methods=["GET", "POST"])
    async def replay_session(request: Request) -> HTMLResponse | JSONResponse:
        if request.method == "GET":
            return HTMLResponse(render_upload_page(session_mode=True))

        session_id = request.path_params["session_id"]
        source = await ConversationReport.report_as_jsonl(session_id)
        return await _replay_response(source, mcp)

    @mcp.custom_route(REPLAY_PATH, methods=["GET", "POST"])
    async def report_replay(request: Request) -> HTMLResponse | JSONResponse:
        if request.method == "GET":
            return HTMLResponse(render_upload_page())

        source = (await request.body()).decode("utf-8")
        return await _replay_response(source, mcp)


async def _replay_response(source: str, mcp: Any) -> JSONResponse:
    """Parse a conversation report and replay its tool calls."""
    report = parse_report_jsonl(source)
    result = await replay_report(report, mcp)

    calls: list[dict[str, Any]] = []
    for call in result.calls:
        output = (
            call.structured_output
            if call.structured_output is not None
            else call.text_output
        )
        item: dict[str, Any] = {
            "tool_name": call.source.tool_name,
            "arguments": call.source.arguments,
            "status": call.status,
            "output": output,
        }
        if call.message:
            item["message"] = call.message
        if call.status == "success" and call.app_resource_uri:
            tool_name = quote(call.source.tool_name, safe="")
            item["app"] = {
                "resource_uri": call.app_resource_uri,
                "resource_url": f"{REPLAY_PATH}/apps/{tool_name}",
                "result": {
                    "content": [
                        {"type": "text", "text": text} for text in call.text_output
                    ],
                    "structuredContent": call.structured_output,
                    "isError": False,
                },
            }
        calls.append(item)

    return JSONResponse({"status": result.status, "calls": calls})


def _tool_result_payload(result: Any) -> dict[str, Any]:
    """Return a JSON-serializable payload for a tool result, including structured content if available."""
    content: list[dict[str, Any]] = []
    for item in result.content or []:
        if hasattr(item, "model_dump"):
            content.append(
                item.model_dump(mode="json", by_alias=True, exclude_none=True)
            )
        elif getattr(item, "type", None) == "text":
            content.append({"type": "text", "text": str(getattr(item, "text", ""))})
    return {
        "content": content,
        "structuredContent": _app_output(result.structured_content),
        "isError": bool(result.is_error),
    }


def _error_response(message: str, status_code: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status_code)
