"""Tool registry - all tools are registered here."""

from ..server import mcp
from .metadata import get_mei_metadata
from .discovery import list_available_mei_files
from .key_analysis import analyze_key
from .intervals import (
    get_notes,
    get_melodic_intervals,
    get_harmonic_intervals,
    get_melodic_ngrams,
)

# Register all tools here
# To add a new tool: import it, then add mcp.tool()(your_tool) below
mcp.tool()(list_available_mei_files)
mcp.tool()(get_mei_metadata)
mcp.tool()(analyze_key)
mcp.tool()(get_notes)
mcp.tool()(get_melodic_intervals)
mcp.tool()(get_harmonic_intervals)
mcp.tool()(get_melodic_ngrams)
