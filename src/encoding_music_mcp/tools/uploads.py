"""Tools for registering user-supplied MEI files."""

from typing import Any

from fastmcp import Context
from fastmcp.server.elicitation import CancelledElicitation, DeclinedElicitation

from .helpers import (
    get_uploaded_mei_files,
    register_uploaded_mei_from_path,
)

__all__ = [
    "register_mei_file_from_path",
    "list_uploaded_mei_files",
]


async def register_mei_file_from_path(
    file_path: str | None = None,
    filename: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Register a local MEI file path exposed by the user.

    If ``file_path`` is omitted and the client supports elicitation, the server
    asks the user to provide a local path that is visible to the MCP server
    process.

    Args:
        file_path: Local path to an MEI file. If omitted, elicitation is used
            when an MCP context is available.
        filename: Optional simple ``.mei`` filename to use for the session
            registration. Defaults to the source path basename.
        ctx: MCP context used for elicitation when ``file_path`` is omitted.

    Returns:
        Dictionary containing:
        - filename: Registered filename to pass to other tools
        - source_path: Absolute path of the local MEI file
        - registered: Always ``True`` on success
        - message: Human-readable registration summary
    """
    if file_path is None:
        if ctx is None:
            raise ValueError(
                "file_path is required when no MCP context is available for elicitation"
            )

        elicitation = await ctx.elicit(
            "Enter the local path to the MEI file on this computer.",
            str,
        )
        if isinstance(elicitation, DeclinedElicitation | CancelledElicitation):
            raise ValueError("file_path is required to register a local MEI file")

        file_path = elicitation.data

    registered = register_uploaded_mei_from_path(file_path, filename)
    return {
        **registered,
        "registered": True,
        "message": (
            f"Registered {registered['filename']} from {registered['source_path']}. "
            "You can now use this filename with the analysis and notation tools."
        ),
    }


def list_uploaded_mei_files() -> dict[str, list[str]]:
    """List MEI filenames registered from user-supplied content.

    Returns:
        Dictionary containing:
        - uploaded_mei_files: Sorted registered filenames whose source paths
          still exist
    """
    return {"uploaded_mei_files": get_uploaded_mei_files()}
