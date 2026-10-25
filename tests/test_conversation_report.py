"""Unit tests for conversation report recording and export."""

import asyncio
import json
from typing import Any

from mcp.types import EmbeddedResource, TextContent, TextResourceContents
from pydantic import BaseModel

from src.encoding_music_mcp.tools import conversation_report
from src.encoding_music_mcp.tools.conversation_report import ConversationReport


class FakeSession:
    """Minimal in-memory stand-in for FastMCP's session state boundary."""

    def __init__(
        self,
        session_id: str = "session-123",
        state: dict[str, Any] | None = None,
    ) -> None:
        self.id = session_id
        self.state = dict(state or {})

    async def get(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)

    async def set(self, key: str, value: Any) -> None:
        self.state[key] = value


def test_first_record_contains_report_metadata_and_tool_call():
    """The first recorded call should establish a replayable report header."""
    session = FakeSession()
    event = {
        "tool_name": "get_melodic_ngrams",
        "args": {"filename": "Bach_BWV_0772.mei", "n": 4},
    }

    asyncio.run(ConversationReport.record_tool(session, event))

    assert session.state["conversation_report"] == [
        {
            "type": "conversation_report",
            "version": "1",
            "session_id": "session-123",
        },
        event,
    ]


def test_later_records_append_without_repeating_metadata():
    """Subsequent calls should retain order and use one report header."""
    first_event = {"tool_name": "list_available_mei_files", "args": {}}
    session = FakeSession(
        state={
            "conversation_report": [
                {
                    "type": "conversation_report",
                    "version": "1",
                    "session_id": "session-123",
                },
                first_event,
            ]
        }
    )
    second_event = {
        "tool_name": "get_melodic_ngrams",
        "args": {"filename": "Bach_BWV_0775.mei", "kind": "d", "n": 4},
    }

    asyncio.run(ConversationReport.record_tool(session, second_event))

    assert session.state["conversation_report"] == [
        {
            "type": "conversation_report",
            "version": "1",
            "session_id": "session-123",
        },
        first_event,
        second_event,
    ]


def test_report_as_jsonl_serializes_events_in_order(monkeypatch):
    """Report generation should emit compact JSON Lines without escaping Unicode."""
    history = [
        {
            "type": "conversation_report",
            "version": "1",
            "session_id": "session-123",
        },
        {
            "tool_name": "get_mei_metadata",
            "args": {"filename": "Bartók.mei"},
        },
    ]
    session = FakeSession(state={"conversation_report": history})

    async def fake_get_session(session_id: str) -> FakeSession:
        assert session_id == "session-123"
        return session

    monkeypatch.setattr(conversation_report, "get_session", fake_get_session)

    result = asyncio.run(ConversationReport.report_as_jsonl("session-123"))

    assert result == (
        '{"type":"conversation_report","version":"1",'
        '"session_id":"session-123"}\n'
        '{"tool_name":"get_mei_metadata",'
        '"args":{"filename":"Bartók.mei"}}'
    )


def test_get_conversation_report_returns_named_jsonl_attachment(monkeypatch):
    """The export should contain a user-facing message and JSONL resource."""
    jsonl = '{"type":"conversation_report","version":"1","session_id":"session-123"}'

    async def fake_report_as_jsonl(cls, session_id: str) -> str:
        assert session_id == "session-123"
        return jsonl

    monkeypatch.setattr(
        ConversationReport,
        "report_as_jsonl",
        classmethod(fake_report_as_jsonl),
    )

    result = asyncio.run(ConversationReport.get_conversation_report("session-123"))

    assert result.structured_content == {
        "filename": "conversation-report.jsonl",
        "mime_type": "application/jsonl",
    }
    assert len(result.content) == 2
    assert isinstance(result.content[0], TextContent)
    assert result.content[0].text == "The conversation report is attached."
    assert isinstance(result.content[1], EmbeddedResource)
    assert isinstance(result.content[1].resource, TextResourceContents)
    assert result.content[1].resource.uri == "file:///conversation-report.jsonl"
    assert result.content[1].resource.mime_type == "application/jsonl"
    assert result.content[1].resource.text == jsonl


def test_make_jsonable_preserves_json_and_converts_other_values():
    """Logged arguments should be safe for JSON encoding."""

    class ExampleModel(BaseModel):
        title: str

    plain_value = {"notes": ["C4", "D4"]}

    assert ConversationReport.make_jsonable(plain_value) is plain_value
    assert ConversationReport.make_jsonable(ExampleModel(title="Fugue")) == {
        "title": "Fugue"
    }
    assert ConversationReport.make_jsonable(complex(2, 3)) == "(2+3j)"
    json.dumps(ConversationReport.make_jsonable(complex(2, 3)))
