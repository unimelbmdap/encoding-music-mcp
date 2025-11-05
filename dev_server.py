"""Standalone dev server for mcp dev command.

This file uses absolute imports so it can be run directly by `mcp dev`.

Usage:
    uv run mcp dev dev_server.py:mcp

This will start the MCP Inspector at http://localhost:6274 for interactive testing.

Note: Requires the package to be installed. Run `uv sync` first if needed.
"""

from encoding_music_mcp.server import mcp

if __name__ == "__main__":
    mcp.run()
