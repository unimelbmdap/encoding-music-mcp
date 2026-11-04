"""This function turns a JSONL report file into a structured ConversationReport that the replay code can execute."""

import json
from typing import Any

from .models import ConversationReport, RecordedCall, ReportHeader
from .settings import MAX_REPORT_BYTES, MAX_REPORT_CALLS, REPORT_VERSION


def parse_report_jsonl(
    text: str,
    *,
    max_bytes: int = MAX_REPORT_BYTES,
    max_calls: int = MAX_REPORT_CALLS,
) -> ConversationReport:
    """Parse JSONL completely before any tool is executed."""

    if len(text.encode("utf-8")) > max_bytes:
        raise ValueError(f"Report is larger than the {max_bytes:,}-byte limit.")

    raw_lines = [
        (number, line)
        for number, line in enumerate(text.splitlines(), 1)
        if line.strip()
    ]
    if not raw_lines:
        raise ValueError("Report is empty. Add a conversation report header.")
    if len(raw_lines) - 1 > max_calls:
        raise ValueError(
            f"Report contains more than the {max_calls} permitted tool calls."
        )

    records: list[tuple[int, dict[str, Any]]] = []
    for line_number, line in raw_lines:
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Line {line_number} is not valid JSON: {exc.msg}."
            ) from exc
        if not isinstance(value, dict):
            raise ValueError(f"Line {line_number} must contain one JSON object.")
        records.append((line_number, value))

    header_line, header_value = records[0]
    if header_value.get("type") != "conversation_report":
        raise ValueError(
            f"Line {header_line} must be a conversation_report header."
        )
    version = header_value.get("version")
    if version != REPORT_VERSION:
        raise ValueError(
            f"Report version {version!r} is not supported; expected {REPORT_VERSION!r}."
        )
    session_id = header_value.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        raise ValueError(
            f"Line {header_line} must contain a non-empty string session_id."
        )

    calls: list[RecordedCall] = []
    for position, (line_number, value) in enumerate(records[1:]):
        if value.get("type") == "conversation_report":
            raise ValueError(
                f"Line {line_number} contains a duplicate report header."
            )
        tool_name = value.get("tool_name")
        arguments = value.get("args")
        if not isinstance(tool_name, str) or not tool_name:
            raise ValueError(
                f"Line {line_number} must contain a non-empty string tool_name."
            )
        if not isinstance(arguments, dict):
            raise ValueError(f"Line {line_number} must contain an args object.")
        if "session_id" in arguments:
            raise ValueError(
                f"Line {line_number} cannot provide or override session_id."
            )
        calls.append(
            RecordedCall(
                id=f"call-{position + 1:04d}",
                position=position,
                tool_name=tool_name,
                arguments=arguments,
            )
        )

    return ConversationReport(
        header=ReportHeader(version=version, session_id=session_id),
        calls=tuple(calls),
    )
