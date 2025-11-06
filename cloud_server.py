"""Entrypoint for fastmcp cloud deployment.

This file is specifically for cloud deployment where the FastMCP platform
manages the asyncio event loop. For local development, use dev_server.py instead.
"""

from encoding_music_mcp.server import mcp

# FastMCP cloud handles running the server in its own event loop
# Expose the mcp instance at module level (required by fastmcp cloud)
__all__ = ["mcp"]
