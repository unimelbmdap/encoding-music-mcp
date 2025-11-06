"""Musical incipit rendering tool using Verovio."""

import cairosvg
from mcp.server.fastmcp import Image

__all__ = ["render_musical_incipit"]


def render_musical_incipit() -> Image:
    """Render a musical incipit (excerpt) as a PNG image.

    Currently returns a minimal test SVG converted to PNG to verify
    the Image class works with Claude Code.

    Returns:
        Image object containing a PNG
    """
    # Minimal SVG with a musical note shape for testing
    minimal_svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
    <!-- Simple musical note -->
    <circle cx="50" cy="150" r="20" fill="black"/>
    <rect x="68" y="60" width="4" height="90" fill="black"/>
    <text x="100" y="100" font-family="Arial" font-size="16" fill="black">Test PNG</text>
</svg>"""

    # Convert SVG to PNG bytes
    png_bytes = cairosvg.svg2png(bytestring=minimal_svg.encode('utf-8'))

    return Image(data=png_bytes, format="png")
