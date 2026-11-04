"""HTTP adapter for opening and replaying conversation reports."""

from typing import Any

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from ..conversation_report import ConversationReport
from .html import render_upload_page
from .parser import parse_report_jsonl
from .replay import replay_report
from .settings import REPLAY_PATH, REPLAY_SESSION_PATH


def register_report_routes(mcp: Any) -> None:
    """Register the report upload page and replay endpoint."""

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

    return JSONResponse(
        {
            "status": result.status,
            "calls": [
                {
                    "tool_name": call.source.tool_name,
                    "status": call.status,
                    "output": call.structured_output or call.text_output,
                }
                for call in result.calls
            ],
        }
    )
