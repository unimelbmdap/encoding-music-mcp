"""Musical incipit rendering tool using Verovio."""

import cairosvg
import verovio
from music21 import converter, musicxml
from mcp.server.fastmcp import Image

from .helpers import get_mei_filepath

__all__ = ["render_musical_incipit"]


def render_musical_incipit(
    filename: str,
    start_measure: int = 1,
    end_measure: int | None = None,
    page_width: int = 2100,
    page_height: int = 800,
    scale: int = 40,
) -> Image:
    """Render a musical incipit (excerpt) from an MEI file as a PNG image.

    Creates a visual representation of musical notation for a specified range
    of measures from an MEI file. Perfect for displaying short musical excerpts
    or themes that can be analysed with other tools.

    Args:
        filename: Name of the MEI file (e.g., "Bach_BWV_0772.mei")
        start_measure: First measure to render (default: 1)
        end_measure: Last measure to render (default: same as start_measure for single measure)
        page_width: SVG page width in pixels (default: 2100)
        page_height: SVG page height in pixels (default: 800)
        scale: Rendering scale factor (default: 40, higher = larger notation)

    Returns:
        Image object containing the rendered PNG

    Examples:
        # Render first measure only
        render_musical_incipit("Bach_BWV_0772.mei")

        # Render measures 1-4 (opening incipit)
        render_musical_incipit("Bach_BWV_0772.mei", start_measure=1, end_measure=4)

        # Render measure 10 with larger scale for detail
        render_musical_incipit("Bach_BWV_0772.mei", start_measure=10, scale=60)
    """
    filepath = get_mei_filepath(filename)

    # If end_measure not specified, render only the start_measure
    if end_measure is None:
        end_measure = start_measure

    # Load MEI file with music21
    score = converter.parse(str(filepath))

    # Extract the specified measure range
    excerpt = score.measures(start_measure, end_measure)

    # Export to MusicXML string (in memory)
    exporter = musicxml.m21ToXml.GeneralObjectExporter(excerpt)
    musicxml_bytes = exporter.parse()
    musicxml_string = musicxml_bytes.decode('utf-8')

    # Initialize Verovio toolkit
    tk = verovio.toolkit()

    # Configure rendering options
    options = {
        "pageWidth": page_width,
        "pageHeight": page_height,
        "scale": scale,
        "adjustPageHeight": True,
        "breaks": "none",
        "footer": "none",
        "header": "none",
    }
    tk.setOptions(options)

    # Load and render the MusicXML
    tk.loadData(musicxml_string)
    svg_output = tk.renderToSVG(1)  # Page number as positional argument

    # Convert SVG to PNG
    png_bytes = cairosvg.svg2png(bytestring=svg_output.encode('utf-8'))

    return Image(data=png_bytes, format="png")