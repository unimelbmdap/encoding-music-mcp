from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.dependencies import get_session

from encoding_music_mcp.tools.conversation_report import ConversationReport


EXCLUDED_TOOLS = {
    "get_conversation_report",
}
"""
VISUALISATION_TOOLS = { 
    "plot_melodic_ngram_heatmap",
    "plot_sonority_ngram_progress",
    "plot_voice_ranges",
    "plot_weighted_note_distribution",
    }
"""


class ConversationReportMiddleware(Middleware):
    """Middleware to log conversation reports for each request."""

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """Intercept tool calls to log the conversation report."""
        tool_name = context.message.name
        args = context.message.arguments
        session_id = args.get("session_id")
        result = await call_next(context)

        # If client not providing session_id, skip logging to session
        if session_id is None or tool_name in EXCLUDED_TOOLS:
            return result
        session = await get_session(session_id)

        # Otherwise, log the tool call to the session's conversation report
        if not result.is_error:
            await ConversationReport.record_tool(
                session,
                {
                    "tool_name": tool_name,
                    "args": {
                        key: ConversationReport.make_jsonable(value)
                        for key, value in args.items()
                        if key != "session_id"
                    },
                    # "result": result
                },
            )
            return result
