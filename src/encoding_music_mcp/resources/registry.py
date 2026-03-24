"""Resource registry - all resources are registered here."""

from pathlib import Path

from fastmcp.server.apps import AppConfig, ResourceCSP

from ..server import mcp
from .mei import mei_collections_list, mei_file_content

# Register all resources here
# To add a new resource: import it, then add mcp.resource(uri)(your_resource) below
mcp.resource("mei://collections/list")(mei_collections_list)
mcp.resource("mei://files/{filename}")(mei_file_content)

_notation_html_path = Path(__file__).parent / "notation_app.html"
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
