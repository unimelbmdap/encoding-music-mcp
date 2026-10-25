"""Shared pytest fixtures."""

import asyncio

import pytest

from src.encoding_music_mcp.server import mcp


@pytest.fixture
def mcp_session_id() -> str:
    """Create a valid session ID for calls through the registered MCP boundary."""
    result = asyncio.run(mcp.call_tool("create_session", {}))
    assert result.structured_content is not None
    return str(result.structured_content["result"])
