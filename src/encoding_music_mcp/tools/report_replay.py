"""MCP tool for opening a session's conversation report replay page."""

from fastmcp.server.sessions import SessionId

from .reports.settings import base_url


async def replay_report(
    session_id: SessionId | None = None,
) -> str:
    """Return the browser URL that can replay one active session's report.
    If none is provided, return the upload page URL."""
    root_url = base_url()
    if session_id is None:
        return root_url
    return f"{root_url}/{session_id}"
