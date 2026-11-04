"""Ordered, bounded replay of conversation report tool calls."""

import asyncio
import time
from typing import Any

from .models import ConversationReport, ReplayResult, ReplayedCall

CALL_TIMEOUT_SECONDS = 120
TOTAL_TIMEOUT_SECONDS = 600
MAX_OUTPUT_STRING_CHARS = 20_000

# Uploaded reports are untrusted. These calls either mutate session/filesystem state,
# depend on ephemeral resources, or recursively export a report.
NON_REPLAYABLE_TOOLS = {
    "create_session",
    "end_session",
    "get_conversation_report",
    "load_audio_resource",
    "replay_report",
    "register_mei_file_from_path",
}


async def replay_report(
    report: ConversationReport,
    mcp: Any,
    *,
    call_timeout: float = CALL_TIMEOUT_SECONDS,
    total_timeout: float = TOTAL_TIMEOUT_SECONDS,
) -> ReplayResult:
    """Replay valid calls in order using a fresh, isolated session."""

    started = time.monotonic()
    prepared: list[tuple[Any, Any]] = []

    for source in report.calls:
        tool = await mcp.get_tool(source.tool_name)
        prepared.append((source, tool))

    needs_session = any(
        tool is not None and source.tool_name not in NON_REPLAYABLE_TOOLS
        for source, tool in prepared
    )
    replay_session_id: str | None = None
    calls: list[ReplayedCall] = []

    try:
        if needs_session:
            create_result = await asyncio.wait_for(
                mcp.call_tool("create_session", {}, run_middleware=False),
                timeout=min(call_timeout, total_timeout),
            )
            replay_session_id = (create_result.structured_content or {}).get("result")
            if not isinstance(replay_session_id, str) or not replay_session_id:
                raise RuntimeError("Could not create an isolated replay session.")

        for source, tool in prepared:
            elapsed = time.monotonic() - started
            remaining = total_timeout - elapsed

            if tool is None:
                calls.append(
                    ReplayedCall(
                        source=source,
                        status="skipped",
                        message="This tool is not registered in the current server.",
                    )
                )
                continue
            if source.tool_name in NON_REPLAYABLE_TOOLS:
                calls.append(
                    ReplayedCall(
                        source=source,
                        status="skipped",
                        message=(
                            "This filesystem, resource, report, or session-management "
                            "call is preserved but is not executed from an uploaded report."
                        ),
                    )
                )
                continue
            if remaining <= 0:
                calls.append(
                    ReplayedCall(
                        source=source,
                        status="skipped",
                        message="The total replay time limit was reached.",
                    )
                )
                continue

            arguments = dict(source.arguments)
            tool_properties = getattr(tool, "parameters", {}).get("properties", {})
            if "session_id" in tool_properties:
                arguments["session_id"] = replay_session_id

            try:
                result = await asyncio.wait_for(
                    mcp.call_tool(
                        source.tool_name,
                        arguments,
                        run_middleware=False,
                    ),
                    timeout=min(call_timeout, remaining),
                )
                text_output = _text_output(result)
                structured_output = _summarize_output(result.structured_content)
                if result.is_error:
                    calls.append(
                        ReplayedCall(
                            source=source,
                            status="error",
                            text_output=text_output,
                            structured_output=structured_output,
                            message="The tool returned an error.",
                        )
                    )
                else:
                    calls.append(
                        ReplayedCall(
                            source=source,
                            status="success",
                            text_output=text_output,
                            structured_output=structured_output,
                        )
                    )
            except asyncio.TimeoutError:
                calls.append(
                    ReplayedCall(
                        source=source,
                        status="error",
                        message=f"The tool exceeded the {call_timeout:g}-second time limit.",
                    )
                )
            except Exception as exc:
                calls.append(
                    ReplayedCall(
                        source=source,
                        status="error",
                        message=str(exc) or type(exc).__name__,
                    )
                )
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
                # Cleanup must not replace the replay result.
                pass

    statuses = [call.status for call in calls]
    if not statuses:
        overall_status = "empty"
    elif all(status == "success" for status in statuses):
        overall_status = "success"
    elif any(status == "success" for status in statuses):
        overall_status = "partial"
    elif any(status == "error" for status in statuses):
        overall_status = "failed"
    else:
        overall_status = "partial"

    return ReplayResult(
        calls=tuple(calls),
        status=overall_status,
    )


def _text_output(result: Any) -> list[str]:
    output: list[str] = []
    for item in result.content or []:
        if getattr(item, "type", None) == "text":
            output.append(_bounded_string(str(getattr(item, "text", ""))))
        else:
            output.append(f"[{getattr(item, 'type', 'binary')} content omitted]")
    return output


def _summarize_output(value: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        return "[nested output omitted]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _bounded_string(value)
    if isinstance(value, bytes):
        return f"[binary output omitted: {len(value):,} bytes]"
    if isinstance(value, list):
        return [_summarize_output(item, depth=depth + 1) for item in value[:500]]
    if isinstance(value, dict):
        summarized: dict[str, Any] = {}
        for key, item in list(value.items())[:500]:
            label = str(key)
            if "base64" in label.lower():
                length = len(item) if isinstance(item, (str, bytes)) else 0
                summarized[label] = f"[base64 output omitted: {length:,} characters]"
            else:
                summarized[label] = _summarize_output(item, depth=depth + 1)
        return summarized
    if hasattr(value, "model_dump"):
        return _summarize_output(value.model_dump(mode="json"), depth=depth + 1)
    return _bounded_string(str(value))


def _bounded_string(value: str) -> str:
    if len(value) <= MAX_OUTPUT_STRING_CHARS:
        return value
    omitted = len(value) - MAX_OUTPUT_STRING_CHARS
    return f"{value[:MAX_OUTPUT_STRING_CHARS]}\n[… {omitted:,} characters omitted]"
