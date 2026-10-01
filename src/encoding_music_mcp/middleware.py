from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.sessions import  Session
from fastmcp.server.dependencies import get_session
import json
from typing import Any


class ConversationReportMiddleware(Middleware):
    """Middleware to log conversation reports for each request."""

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """Intercept tool calls to log the conversation report."""
        # Extract the tool name and arguments from the context
        tool_name = context.message.name
        args = context.message.arguments
        session_id = args.get("session_id")
        result = await call_next(context)


        # If client not providing session_id, skip logging to session
        if session_id is None:
            return result
        session = await get_session(session_id)
        
        # Otherwise, log the tool call to the session's conversation report
        await self.log_to_session(
            session,
            {
                "tool_name": tool_name,
                "args": {
                    key: self.make_jsonable(value)
                    for key, value in args.items()
                    if key != "session_id"
                },
                "result": result
            }
        )
        return result

    async def log_to_session(self, session: Session, event: dict):
        """Log the conversation report to the user session."""
        if session:
            # Append the new history to the existing conversation report
            existing_history = await session.get("conversation_report", [])
            existing_history.append(event)
            await session.set("conversation_report", existing_history)

    async def report_as_jsonl(self, session: Session) -> str:
        history = await session.get("conversation_report", default=[])

        return "\n".join(
            json.dumps(event, ensure_ascii=False, separators=(",", ":"))
            for event in history
        )
            
    def make_jsonable(self, value: Any) -> Any:
        # Convert non-JSON-serializable values to JSON-serializable representations.
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")

        try:
            json.dumps(value)
            return value
        except (TypeError, ValueError):
            return str(value)
