"""Resource registry - all resources are registered here."""

from pathlib import Path

from fastmcp.resources import ResourceContent, ResourceResult
from fastmcp.server.apps import AppConfig, ResourceCSP

from ..server import mcp
from .mei import mei_collections_list, mei_file_content
from ..tools.play_excerpt import get_registered_audio

# Register all resources here
# To add a new resource: import it, then add mcp.resource(uri)(your_resource) below
mcp.resource("mei://collections/list")(mei_collections_list)
mcp.resource("mei://files/{filename}")(mei_file_content)

_templates_dir = Path(__file__).parent / "templates"
_notation_html_path = _templates_dir / "notation_app.html"
_notation_highlight_html_path = _templates_dir / "notation_highlight.html"
_voice_ranges_html_path = _templates_dir / "voice_ranges_app.html"
_weighted_note_distribution_html_path = (
    _templates_dir / "weighted_note_distribution_app.html"
)
_melodic_ngram_heatmap_html_path = _templates_dir / "melodic_ngram_heatmap_app.html"
_sonority_ngram_progress_html_path = (
    _templates_dir / "sonority_ngram_progress_app.html"
)
_play_excerpt_html_path = _templates_dir / "play_excerpt_app.html"


@mcp.resource(
    "ui://notation/view.html",
    name="Notation Viewer",
    description="Interactive sheet music viewer powered by Verovio",
    app=AppConfig(
        csp=ResourceCSP(
            resource_domains=[
                "https://unpkg.com",
            ],
        ),
    ),
)
def notation_viewer() -> str:
    """Return the HTML template for the notation viewer app."""
    return _notation_html_path.read_text(encoding="utf-8")


@mcp.resource(
    "ui://notation/highlight.html",
    name="Notation Highlight Viewer",
    description="Interactive sheet music viewer with note highlighting",
    app=AppConfig(
        csp=ResourceCSP(
            resource_domains=[
                "https://unpkg.com",
            ],
        ),
    ),
)
def notation_highlight_viewer() -> str:
    """Return the HTML template for highlighted notation rendering."""
    return _notation_highlight_html_path.read_text(encoding="utf-8")


@mcp.resource(
    "ui://voice-ranges/view.html",
    name="Voice Range Viewer",
    description="Interactive chart for staff pitch ranges within one score",
    app=AppConfig(
        csp=ResourceCSP(
            resource_domains=[
                "https://unpkg.com",
            ],
        ),
    ),
)
def voice_ranges_viewer() -> str:
    """Return the HTML template for the voice range visualisation app."""
    return _voice_ranges_html_path.read_text(encoding="utf-8")


@mcp.resource(
    "ui://weighted-note-distribution/view.html",
    name="Weighted Note Distribution Viewer",
    description="Interactive radar chart for duration-weighted pitch-class distributions",
    app=AppConfig(
        csp=ResourceCSP(
            resource_domains=[
                "https://unpkg.com",
            ],
        ),
    ),
)
def weighted_note_distribution_viewer() -> str:
    """Return the HTML template for the weighted note distribution app."""
    return _weighted_note_distribution_html_path.read_text(encoding="utf-8")


@mcp.resource(
    "ui://melodic-ngram-heatmap/view.html",
    name="Melodic N-gram Heatmap",
    description="Timeline heatmap for top melodic n-gram patterns by score and staff",
    app=AppConfig(
        csp=ResourceCSP(
            resource_domains=[
                "https://unpkg.com",
            ],
        ),
    ),
)
def melodic_ngram_heatmap_viewer() -> str:
    """Return the HTML template for the melodic n-gram heatmap app."""
    return _melodic_ngram_heatmap_html_path.read_text(encoding="utf-8")


@mcp.resource(
    "ui://sonority-ngram-progress/view.html",
    name="Sonority N-gram Progress",
    description="Scatter plot of sonority n-grams by normalized score progress",
    app=AppConfig(
        csp=ResourceCSP(
            resource_domains=[
                "https://unpkg.com",
            ],
        ),
    ),
)
def sonority_ngram_progress_viewer() -> str:
    """Return the HTML template for the sonority n-gram progress app."""
    return _sonority_ngram_progress_html_path.read_text(encoding="utf-8")


@mcp.resource(
    "ui://play_excerpt/v2.html",
    name="Excerpt Player",
    description="Interactive audio excerpt player",
    app=AppConfig(
        csp=ResourceCSP(
            resource_domains=[
                "https://unpkg.com",
            ],
        ),
    ),
)
def play_excerpt_viewer() -> str:
    """Return the HTML template for the excerpt playback app."""
    return _play_excerpt_html_path.read_text(encoding="utf-8")


@mcp.resource("audio://files/{token}")
def audio_file_resource(token: str) -> ResourceResult:
    """Expose prepared audio files as MCP resources for stdio-compatible apps.

    Args:
        token: Opaque token from an ``audio://files/{token}`` URI.

    Returns:
        Resource result containing the prepared audio bytes and MIME type.

    Raises:
        FileNotFoundError: If the token is unknown or the cached audio file is
            no longer present.
    """
    audio_entry = get_registered_audio(token)
    if not audio_entry:
        raise FileNotFoundError(f"Audio resource not found for token: {token}")

    audio_path = audio_entry["path"]
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file no longer exists for token: {token}")

    return ResourceResult(
        contents=[
            ResourceContent(
                content=audio_path.read_bytes(),
                mime_type=audio_entry["mime_type"],
            )
        ]
    )
