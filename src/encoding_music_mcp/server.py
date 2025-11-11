"""MCP server for MEI file analysis."""

from fastmcp import FastMCP

# Create MCP server
mcp = FastMCP("encoding-music-mcp")

# Import tools, resources, and prompts to trigger registration
from .tools import registry as _tools_registry  # noqa: E402, F401
from .resources import registry as _resources_registry  # noqa: E402, F401
from .prompts import registry as _prompts_registry  # noqa: E402, F401


def main():
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
