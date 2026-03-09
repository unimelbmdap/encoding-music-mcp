"""Resource registry - all resources are registered here."""

from ..server import mcp
from .mei import mei_collections_list, mei_file_content

# Register all resources here
# To add a new resource: import it, then add mcp.resource(uri)(your_resource) below
mcp.resource("mei://collections/list")(mei_collections_list)
mcp.resource("mei://files/{filename}")(mei_file_content)
