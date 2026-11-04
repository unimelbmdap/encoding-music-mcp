"""HTTP adapter for opening and replaying conversation reports."""

import asyncio
from typing import Any
from urllib.parse import quote

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from ..conversation_report import ConversationReport
from .html import render_upload_page
from .parser import parse_report_jsonl
from .replay import CALL_TIMEOUT_SECONDS, _app_output, app_resource_uri, replay_report
from .settings import (
    MCP_APP_ALLOWED_CALLS,
    MCP_APP_TOOLS,
    REPLAY_APP_CALL_PATH,
    REPLAY_APP_PATH,
    REPLAY_APP_RESOURCE_PATH,
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

    @mcp.custom_route(REPLAY_APP_RESOURCE_PATH, methods=["POST"])
    async def replay_app_read_resource(request: Request) -> JSONResponse:
        """Forward notation page reads from replay widgets without a session."""
        try:
            payload = await request.json()
            uri = payload["uri"]
            if not isinstance(uri, str) or not uri.startswith("notation://pages/"):
                return _error_response(
                    "Only notation page resources are supported.", 400
                )
            result = await asyncio.wait_for(
                mcp.read_resource(uri, run_middleware=False),
                timeout=CALL_TIMEOUT_SECONDS,
            )
            return JSONResponse(
                result.to_mcp_result(uri).model_dump(
                    mode="json", by_alias=True, exclude_none=True
                )
            )
        except Exception as exc:
            return _error_response(str(exc) or type(exc).__name__, 500)

    # Register this static path before /reports/replay/{session_id}, otherwise
    # Starlette can interpret "app-call" as a session ID.
    @mcp.custom_route(REPLAY_APP_CALL_PATH, methods=["POST"])
    async def replay_app_call(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            return _error_response("The app call body must be valid JSON.", 400)

        if not isinstance(payload, dict):
            return _error_response("The app call body must be a JSON object.", 400)
        source_tool = payload.get("source_tool")
        tool_name = payload.get("tool_name")
        arguments = payload.get("arguments")
        if not isinstance(source_tool, str) or not isinstance(tool_name, str):
            return _error_response("source_tool and tool_name must be strings.", 400)
        if not isinstance(arguments, dict):
            return _error_response("arguments must be an object.", 400)
        if "session_id" in arguments:
            return _error_response("App calls cannot provide session_id.", 400)
        if tool_name not in MCP_APP_ALLOWED_CALLS.get(source_tool, set()):
            return _error_response(
                "This app tool call is not permitted during replay.", 403
            )

        tool = await mcp.get_tool(tool_name)
        if tool is None:
            return _error_response("The requested app tool is not registered.", 404)

        replay_session_id: str | None = None
        call_arguments = dict(arguments)
        try:
            tool_properties = getattr(tool, "parameters", {}).get("properties", {})
            if "session_id" in tool_properties:
                create_result = await asyncio.wait_for(
                    mcp.call_tool("create_session", {}, run_middleware=False),
                    timeout=CALL_TIMEOUT_SECONDS,
                )
                replay_session_id = (create_result.structured_content or {}).get(
                    "result"
                )
                if not isinstance(replay_session_id, str) or not replay_session_id:
                    raise RuntimeError("Could not create an isolated app session.")
                call_arguments["session_id"] = replay_session_id

            result = await asyncio.wait_for(
                mcp.call_tool(tool_name, call_arguments, run_middleware=False),
                timeout=CALL_TIMEOUT_SECONDS,
            )
            return JSONResponse(_tool_result_payload(result))
        except asyncio.TimeoutError:
            return _error_response("The app tool call timed out.", 504)
        except Exception as exc:
            return _error_response(str(exc) or type(exc).__name__, 500)
        finally:
            if replay_session_id is not None:
                try:
                    await asyncio.wait_for(
                        mcp.call_tool(
                            "end_session",
                            {"session_id": replay_session_id},
                            run_middleware=False,
                        ),
                        timeout=5,
                    )
                except Exception:
                    pass

    @mcp.custom_route(REPLAY_APP_PATH, methods=["GET"])
    async def replay_app_resource(request: Request) -> HTMLResponse | JSONResponse:
        tool_name = request.path_params["tool_name"]
        if tool_name not in MCP_APP_TOOLS:
            return _error_response("The requested replay app is not registered.", 404)

        tool = await mcp.get_tool(tool_name)
        resource_uri = app_resource_uri(tool_name, tool)
        if resource_uri is None:
            return _error_response("The tool has no valid MCP App resource.", 404)

        try:
            resource = await mcp.read_resource(resource_uri, run_middleware=False)
        except Exception as exc:
            return _error_response(
                str(exc) or "The app resource could not be read.", 500
            )
        contents = getattr(resource, "contents", [])
        if not contents or not isinstance(contents[0].content, str):
            return _error_response("The app resource does not contain HTML.", 500)
        return HTMLResponse(
            contents[0].content,
            media_type="text/html;profile=mcp-app",
            headers={"Content-Security-Policy": _APP_CSP},
        )

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
