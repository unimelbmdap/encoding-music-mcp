"""Tool registry - all tools are registered here."""

from fastmcp.server.apps import AppConfig

from ..server import mcp
from .comprehensive_analysis import run_comprehensive_analysis
from .metadata import get_mei_metadata
from .discovery import list_available_mei_files
from .key_analysis import analyze_key
from .intervals import (
    get_notes,
    get_melodic_intervals,
    get_harmonic_intervals,
    get_melodic_ngrams,
    count_melodic_ngrams,
    get_melodic_ngram_matches,
    get_first_occur_melodic_ngrams,
    get_cadences,
)
from .notation import (
    show_notation,
    show_notation_highlight,
)
from .play_excerpt import load_audio_resource, play_excerpt
from .sampling_diagnostics import diagnose_sampling
from .uploads import register_mei_file_from_path
from .visualisation.voice_ranges import plot_voice_ranges
from .visualisation.weighted_note_distribution import plot_weighted_note_distribution
from .visualisation.melodic_ngram_heatmap import plot_melodic_ngram_heatmap
from .visualisation.sonority_ngram_progress import plot_sonority_ngram_progress

# Register all tools here
# To add a new tool: import it, then add mcp.tool()(your_tool) below
mcp.tool()(run_comprehensive_analysis)
mcp.tool()(diagnose_sampling)
mcp.tool()(list_available_mei_files)
mcp.tool()(register_mei_file_from_path)
mcp.tool()(get_mei_metadata)
mcp.tool()(analyze_key)
mcp.tool()(get_notes)
mcp.tool()(get_melodic_intervals)
mcp.tool()(get_harmonic_intervals)
mcp.tool()(get_melodic_ngrams)
mcp.tool()(count_melodic_ngrams)
mcp.tool()(get_melodic_ngram_matches)
mcp.tool()(get_cadences)
mcp.tool(
    app=AppConfig(resource_uri="ui://notation/view.html"),
)(show_notation)
mcp.tool(
    app=AppConfig(resource_uri="ui://notation/highlight.html"),
)(show_notation_highlight)
mcp.tool(
    app=AppConfig(resource_uri="ui://voice-ranges/view.html"),
)(plot_voice_ranges)
mcp.tool(
    app=AppConfig(resource_uri="ui://weighted-note-distribution/view.html"),
)(plot_weighted_note_distribution)
mcp.tool(
    app=AppConfig(resource_uri="ui://melodic-ngram-heatmap/view.html"),
)(plot_melodic_ngram_heatmap)
mcp.tool(
    app=AppConfig(resource_uri="ui://sonority-ngram-progress/view.html"),
)(plot_sonority_ngram_progress)
mcp.tool()(get_first_occur_melodic_ngrams)
mcp.tool()(load_audio_resource)
mcp.tool(
    app=AppConfig(resource_uri="ui://play_excerpt/v2.html"),
)(play_excerpt)
