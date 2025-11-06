"""Resource registry - all resources are registered here."""

from ..server import mcp
from .mei import mei_collections_list, mei_file_content
from .incipit_viewer import musical_incipit_viewer

# Register all resources here
# To add a new resource: import it, then add mcp.resource(uri)(your_resource) below
mcp.resource("mei://collections/list")(mei_collections_list)
mcp.resource("mei://files/{filename}")(mei_file_content)
mcp.resource(
    "ui://incipit/{filename}/{start_measure}/{end_measure}",
    name="Musical Incipit Viewer",
    description="Interactive HTML viewer with SVG notation and MIDI playback",
    mime_type="text/html",
)(musical_incipit_viewer)
