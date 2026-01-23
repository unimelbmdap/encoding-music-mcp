"""MCP server for MEI file analysis."""

import os

from fastmcp import FastMCP
from starlette.responses import JSONResponse

# Create MCP server
mcp = FastMCP("encoding-music-mcp")


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for container orchestration."""
    return JSONResponse({"status": "healthy"})

# Import tools, resources, and prompts to trigger registration
from .tools import registry as _tools_registry  # noqa: E402, F401
from .resources import registry as _resources_registry  # noqa: E402, F401
from .prompts import registry as _prompts_registry  # noqa: E402, F401


def main():
    """Entry point for the MCP server.

    Supports two transport modes controlled by MCP_TRANSPORT env var:
    - "stdio" (default): Local MCP client communication via stdin/stdout
    - "http": Remote HTTP server for deployment behind reverse proxy
    """
    transport = os.environ.get("MCP_TRANSPORT", "stdio")

    if transport == "http":
        host = os.environ.get("MCP_HOST", "0.0.0.0")
        port = int(os.environ.get("MCP_PORT", "8000"))
        mcp.run(transport="http", host=host, port=port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
