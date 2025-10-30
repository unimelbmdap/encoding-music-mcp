"""Tool registry - all tools are registered here."""

from ..server import mcp
from .metadata import get_mei_metadata

# Register all tools here
# To add a new tool: import it, then add mcp.tool()(your_tool) below
mcp.tool()(get_mei_metadata)
