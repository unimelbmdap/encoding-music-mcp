"""MCP server for MEI file analysis."""

from mcp.server.fastmcp import FastMCP

# Create MCP server
mcp = FastMCP("encoding-music-mcp")

# Import registry to trigger tool registration
from .tools import registry


def main():
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
