"""Musical incipit rendering tool using Verovio."""

import xml.etree.ElementTree as ET
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

    # Calculate number of measures for intelligent layout
    num_measures = end_measure - start_measure + 1

    # Adjust page height dynamically based on number of measures
    # Rough estimate: ~400px per system (line) of music, ~4 measures per system
    systems_needed = max(1, (num_measures + 3) // 4)  # Round up
    adjusted_height = max(page_height, systems_needed * 500)

    # Initialize Verovio toolkit
    tk = verovio.toolkit()

    # Configure rendering options
    options = {
        "pageWidth": page_width,
        "pageHeight": adjusted_height,
        "scale": scale,
        "adjustPageHeight": True,
        "breaks": "auto",  # Let verovio automatically break lines
        "footer": "none",
        "header": "none",
    }
    tk.setOptions(options)

    # Load and render the MusicXML
    tk.loadData(musicxml_string)
    svg_output = tk.renderToSVG(1)  # Page number as positional argument

    # Add label with filename and measure range
    svg_with_label = _add_label_to_svg(
        svg_output,
        filename,
        start_measure,
        end_measure
    )

    # Convert SVG to PNG
    png_bytes = cairosvg.svg2png(bytestring=svg_with_label.encode('utf-8'))

    return Image(data=png_bytes, format="png")


def _add_label_to_svg(
    svg_string: str,
    filename: str,
    start_measure: int,
    end_measure: int,
    label_height: int = 60
) -> str:
    """Add a label to the top of an SVG with filename and measure range.

    Args:
        svg_string: Original SVG content
        filename: MEI filename to display
        start_measure: Starting measure number
        end_measure: Ending measure number
        label_height: Height in pixels to allocate for label (default: 60)

    Returns:
        Modified SVG string with label added
    """
    # Parse SVG
    # Register namespace to avoid ns0 prefix
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    root = ET.fromstring(svg_string)

    # Get current height and increase it (strip 'px' if present)
    height_str = root.get('height', '1000')
    current_height = int(height_str.replace('px', ''))
    new_height = current_height + label_height
    root.set('height', f'{new_height}px')

    # Adjust viewBox to match
    viewbox = root.get('viewBox')
    if viewbox:
        parts = viewbox.split()
        parts[3] = str(int(float(parts[3])) + label_height)
        root.set('viewBox', ' '.join(parts))

    # Create label text
    measure_text = f"measure {start_measure}" if start_measure == end_measure else f"measures {start_measure}-{end_measure}"
    label_text = f"{filename}, {measure_text}"

    # Create text element
    text = ET.Element('{http://www.w3.org/2000/svg}text')
    text.set('x', '20')
    text.set('y', '35')
    text.set('font-family', 'Arial, sans-serif')
    text.set('font-size', '20')
    text.set('font-weight', 'bold')
    text.set('fill', '#333333')
    text.text = label_text

    # Create a group for the original music notation, shifted down
    group = ET.Element('{http://www.w3.org/2000/svg}g')
    group.set('transform', f'translate(0, {label_height})')

    # Move all existing children to the group
    for child in list(root):
        root.remove(child)
        group.append(child)

    # Add text label first, then the group with shifted content
    root.append(text)
    root.append(group)

    return ET.tostring(root, encoding='unicode')