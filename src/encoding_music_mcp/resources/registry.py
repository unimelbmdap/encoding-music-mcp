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


@mcp.resource(
    "ui://notation/view.html",
    name="Notation Viewer",
    description="Interactive sheet music viewer powered by Verovio",
    app=AppConfig(
        csp=ResourceCSP(
            resource_domains=[
                "https://editor.verovio.org",
                "https://unpkg.com",
            ],
        ),
    ),
)
def notation_viewer() -> str:
    return _notation_html_path.read_text(encoding="utf-8")
