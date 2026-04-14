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

_notation_html_path = Path(__file__).parent / "notation_app.html"
_notation_highlight_html_path = Path(__file__).parent / "notation_highlight.html"
_voice_ranges_html_path = Path(__file__).parent / "voice_ranges_app.html"
_weighted_note_distribution_html_path = (
    Path(__file__).parent / "weighted_note_distribution_app.html"
)
_play_excerpt_html_path = Path(__file__).parent / "play_excerpt_app.html"


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
    return _weighted_note_distribution_html_path.read_text(encoding="utf-8")


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
    return _play_excerpt_html_path.read_text(encoding="utf-8")


@mcp.resource("audio://files/{token}")
def audio_file_resource(token: str) -> ResourceResult:
    """Expose prepared audio files as MCP resources for stdio-compatible apps."""
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
