import asyncio
import json
from typing import Any
from fastmcp.server.sessions import SessionId, Session
from mcp.types import (
    EmbeddedResource,
    TextContent,
    TextResourceContents,
)
from fastmcp.tools import ToolResult
from fastmcp.server.dependencies import get_session

class ConversationReport:
    _VERSION = "1" 
    _REPORT_LOCK = asyncio.Lock() #prevents lost update problem
    _HISTORY_KEY = "conversation_report"

    

    @classmethod
    async def get_conversation_report(cls, session_id: SessionId) -> ToolResult:
        """Return the conversation report as an attached JSONL file.

        Call this when the user asks to save, export, or download their analysis
        session. Present the attached file to the user; do not paste its complete
        contents unless explicitly requested.

        IMPORTANT: Calling this tool does not itself deliver the file to the user.
        After receiving the result, use your available file-creation capability to
        create `conversation-report.jsonl` from the embedded resource's exact text,
        then attach that generated file to your response. Do not merely summarize or
        display the report inline.
        """

        jsonl = await cls().report_as_jsonl(session_id)

        attachment = EmbeddedResource(
                type="resource",
                resource=TextResourceContents(
                    uri="file:///conversation-report.jsonl",
                    mime_type="application/jsonl",
                    text=jsonl,
                ),
            )

        return ToolResult(
            content=[
                TextContent(
                    type="text",
                    text="The conversation report is attached.",
                ),
                attachment,
            ],
            structured_content={
                "filename": "conversation-report.jsonl",
                "mime_type": "application/jsonl",
            },
        )
    
    @classmethod
    async def report_as_jsonl(
            self,
            session_id: SessionId) -> str:
        session = await get_session(session_id)
        history = await session.get(self._HISTORY_KEY, default=[])

        return "\n".join(
            json.dumps(event, ensure_ascii=False, separators=(",", ":"))
            for event in history
        )
    
    @classmethod
    async def record_tool(
        self,
        session: Session,
        record: dict[str, Any],
        ) -> None:
        """Record a successful tool call in the conversation report."""
        async with self._REPORT_LOCK:
            if session:
                history = list(
                await session.get(self._HISTORY_KEY, [])
                )
                #set metadata for the first record in the conversation report
                if history == []:
                    metadata = {
                        "type": "conversation_report",
                        "version": self._VERSION,
                        "session_id": session.id,
                        }   
                    history.append(metadata)
                history.append(record)
                await session.set(self._HISTORY_KEY, history)

    @staticmethod
    def make_jsonable(value: Any) -> Any:
            # Convert non-JSON-serializable values to JSON-serializable representations.
            if hasattr(value, "model_dump"):
                return value.model_dump(mode="json")
            try:
                json.dumps(value)
                return value
            except (TypeError, ValueError):
                return str(value)
