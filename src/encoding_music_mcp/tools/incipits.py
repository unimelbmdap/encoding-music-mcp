"""Musical incipit rendering tool using Verovio."""

from mcp.server.fastmcp import Image

__all__ = ["render_musical_incipit"]


def render_musical_incipit() -> Image:
    """Render a musical incipit (excerpt) as an SVG image.

    Currently returns a minimal test SVG to verify the Image class
    can handle SVG format properly.

    Returns:
        Image object containing a test SVG
    """
    # Minimal SVG with a musical note shape for testing
    minimal_svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
    <!-- Simple musical note -->
    <circle cx="50" cy="150" r="20" fill="black"/>
    <rect x="68" y="60" width="4" height="90" fill="black"/>
    <text x="100" y="100" font-family="Arial" font-size="16" fill="black">Test SVG</text>
</svg>"""

    # Convert SVG string to bytes
    svg_bytes = minimal_svg.encode('utf-8')

    # Try format="svg+xml" to get MIME type "image/svg+xml"
    return Image(data=svg_bytes, format="svg+xml")
