"""Tool registry - all tools are registered here."""

from fastmcp.server.apps import AppConfig

from ..server import mcp
from .metadata import get_mei_metadata
from .discovery import list_available_mei_files
from .key_analysis import analyze_key
from .intervals import (
    get_notes,
    get_melodic_intervals,
    get_harmonic_intervals,
    get_melodic_ngrams,
    get_cadences,
)
from .notation import show_notation
from .melodic_patterns import get_first_occurrence_melodic_ngrams
from .play_excerpt import load_audio_resource, play_excerpt

# Register all tools here
# To add a new tool: import it, then add mcp.tool()(your_tool) below
mcp.tool()(list_available_mei_files)
mcp.tool()(get_mei_metadata)
mcp.tool()(analyze_key)
mcp.tool()(get_notes)
mcp.tool()(get_melodic_intervals)
mcp.tool()(get_harmonic_intervals)
mcp.tool()(get_melodic_ngrams)
mcp.tool()(get_cadences)
mcp.tool(
    app=AppConfig(resource_uri="ui://notation/view.html"),
)(show_notation)
mcp.tool()(get_first_occurrence_melodic_ngrams)
mcp.tool()(load_audio_resource)
mcp.tool(
    app=AppConfig(resource_uri="ui://play_excerpt/v2.html"),
)(play_excerpt)
