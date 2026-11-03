"""End-to-end tests for notation over the installed HTTP server."""

import asyncio
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from fastmcp import Client


def _unused_tcp_port() -> int:
    """Reserve an ephemeral port long enough to discover its number."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_http_server(process: subprocess.Popen[str], port: int) -> None:
    """Wait until the server health endpoint is ready or the process exits."""
    health_url = f"http://127.0.0.1:{port}/health"
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError("HTTP server exited during startup")
        try:
            with urllib.request.urlopen(health_url, timeout=0.5) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(0.1)
    raise AssertionError("HTTP server did not become healthy within 15 seconds")


def test_show_notation_over_installed_http_entry_point_returns_svg():
    """The installed HTTP server should render notation in an AnyIO worker."""
    entry_point = Path(sys.executable).parent / "encoding-music-mcp"
    assert entry_point.is_file(), (
        "encoding-music-mcp console entry point is not installed"
    )

    port = _unused_tcp_port()
    env = os.environ.copy()
    env.update(
        {
            "MCP_TRANSPORT": "http",
            "MCP_HOST": "127.0.0.1",
            "MCP_PORT": str(port),
        }
    )
    process = subprocess.Popen(
        [str(entry_point)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        _wait_for_http_server(process, port)

        async def call_notation_tools():
            async with Client(f"http://127.0.0.1:{port}/mcp") as client:
                session = await client.call_tool("create_session", {})
                assert session.structured_content is not None
                session_id = str(session.structured_content["result"])
                notation = await client.call_tool(
                    "show_notation",
                    {
                        "filename": "Bartok_Mikrokosmos_058.mei",
                        "session_id": session_id,
                    },
                )
                highlighted_notation = await client.call_tool(
                    "show_notation_highlight",
                    {
                        "filename": "Bartok_Mikrokosmos_058.mei",
                        "highlight_note_ids": [],
                        "session_id": session_id,
                    },
                )
                return notation, highlighted_notation

        notation, highlighted_notation = asyncio.run(call_notation_tools())

        assert notation.structured_content is not None
        assert notation.structured_content["svg"].startswith("<svg")
        assert highlighted_notation.structured_content is not None
        assert highlighted_notation.structured_content["svg"].startswith("<svg")
        assert highlighted_notation.structured_content["highlight_note_ids"] == []
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
