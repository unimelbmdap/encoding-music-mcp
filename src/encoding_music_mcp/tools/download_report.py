from fastmcp.server.sessions import SessionId
from ..middleware import ConversationReportMiddleware

async def get_conversation_report(session_id: SessionId) -> str:
    """Retrieve the conversation report as JSONL for a given session ID."""
    return await ConversationReportMiddleware.report_as_jsonl(session_id)