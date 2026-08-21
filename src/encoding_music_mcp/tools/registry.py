"""Tool registry - all tools are registered here."""

from fastmcp.apps import AppConfig

from ..server import mcp
from .metadata import get_mei_metadata
from .discovery import list_available_mei_files
from .key_analysis import analyze_key
from .chord_notation import show_chord_notation
from .get_chord_progression import get_chord_progression, inspect_harmony
from .intervals import (
    get_notes,
    get_melodic_intervals,
    get_harmonic_intervals,
    get_melodic_ngrams,
    count_melodic_ngrams,
    resolve_note_ids_for_highlight,
    get_melodic_ngram_matches,
    get_first_occur_melodic_ngrams,
    get_cadences,
)
from .notation import (
    show_notation,
    show_notation_highlight,
)
from .play_excerpt import load_audio_resource, play_excerpt
from .uploads import register_mei_file_from_path
from .performance import limit_analysis_concurrency, performant_analysis_tool
from .output_schemas import (
    LOAD_AUDIO_RESOURCE_OUTPUT_SCHEMA,
    MELODIC_NGRAM_HEATMAP_OUTPUT_SCHEMA,
    PLAY_EXCERPT_OUTPUT_SCHEMA,
    SHOW_NOTATION_HIGHLIGHT_OUTPUT_SCHEMA,
    SHOW_NOTATION_OUTPUT_SCHEMA,
    SHOW_CHORD_NOTATION_OUTPUT_SCHEMA,
    SONORITY_NGRAM_PROGRESS_OUTPUT_SCHEMA,
    VOICE_RANGES_OUTPUT_SCHEMA,
    WEIGHTED_NOTE_DISTRIBUTION_OUTPUT_SCHEMA,
)
from .visualisation.voice_ranges import plot_voice_ranges
from .visualisation.weighted_note_distribution import plot_weighted_note_distribution
from .visualisation.melodic_ngram_heatmap import plot_melodic_ngram_heatmap
from .visualisation.sonority_ngram_progress import plot_sonority_ngram_progress

# Register all tools here
# To add a new tool: import it, then add mcp.tool()(your_tool) below
mcp.tool()(list_available_mei_files)
mcp.tool()(register_mei_file_from_path)
mcp.tool()(get_mei_metadata)
mcp.tool()(performant_analysis_tool(analyze_key))
mcp.tool()(performant_analysis_tool(inspect_harmony))
mcp.tool()(performant_analysis_tool(get_chord_progression))
mcp.tool()(performant_analysis_tool(get_notes))
mcp.tool()(performant_analysis_tool(get_melodic_intervals))
mcp.tool()(performant_analysis_tool(get_harmonic_intervals))
mcp.tool()(performant_analysis_tool(get_melodic_ngrams))
mcp.tool()(performant_analysis_tool(count_melodic_ngrams))
mcp.tool()(performant_analysis_tool(resolve_note_ids_for_highlight))
mcp.tool()(performant_analysis_tool(get_melodic_ngram_matches))
mcp.tool()(performant_analysis_tool(get_cadences))
mcp.tool(
    app=AppConfig(resource_uri="ui://notation/view.html"),
    output_schema=SHOW_NOTATION_OUTPUT_SCHEMA,
)(show_notation)
mcp.tool(
    app=AppConfig(resource_uri="ui://notation/view.html"),
    output_schema=SHOW_CHORD_NOTATION_OUTPUT_SCHEMA,
)(show_chord_notation)
mcp.tool(
    app=AppConfig(resource_uri="ui://notation/highlight.html"),
    output_schema=SHOW_NOTATION_HIGHLIGHT_OUTPUT_SCHEMA,
)(show_notation_highlight)
mcp.tool(
    app=AppConfig(resource_uri="ui://voice-ranges/view.html"),
    output_schema=VOICE_RANGES_OUTPUT_SCHEMA,
)(limit_analysis_concurrency(plot_voice_ranges))
mcp.tool(
    app=AppConfig(resource_uri="ui://weighted-note-distribution/view.html"),
    output_schema=WEIGHTED_NOTE_DISTRIBUTION_OUTPUT_SCHEMA,
)(limit_analysis_concurrency(plot_weighted_note_distribution))
mcp.tool(
    app=AppConfig(resource_uri="ui://melodic-ngram-heatmap/view.html"),
    output_schema=MELODIC_NGRAM_HEATMAP_OUTPUT_SCHEMA,
)(limit_analysis_concurrency(plot_melodic_ngram_heatmap))
mcp.tool(
    app=AppConfig(resource_uri="ui://sonority-ngram-progress/view.html"),
    output_schema=SONORITY_NGRAM_PROGRESS_OUTPUT_SCHEMA,
)(limit_analysis_concurrency(plot_sonority_ngram_progress))
mcp.tool()(performant_analysis_tool(get_first_occur_melodic_ngrams))
mcp.tool(output_schema=LOAD_AUDIO_RESOURCE_OUTPUT_SCHEMA)(load_audio_resource)
mcp.tool(
    app=AppConfig(resource_uri="ui://play_excerpt/v2.html"),
    output_schema=PLAY_EXCERPT_OUTPUT_SCHEMA,
)(play_excerpt)
