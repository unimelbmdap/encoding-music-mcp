"""Musical incipit UI viewer - generates interactive HTML file."""

import html
from pathlib import Path
from string import Template
from music21 import converter, musicxml
import verovio

from .helpers import get_mei_filepath

__all__ = ["render_musical_incipit_ui"]


def render_musical_incipit_ui(
    filename: str,
    start_measure: int = 1,
    end_measure: int | None = None,
    output_dir: str | None = None,
) -> str:
    """Generate interactive HTML file with SVG notation and MIDI playback, saved to disk.

    Creates an HTML viewer with vector graphics notation and audio playback,
    saves it to a file, and returns the path for opening in a browser.

    Args:
        filename: Name of the MEI file (e.g., "Bach_BWV_0772.mei")
        start_measure: First measure to render (default: 1)
        end_measure: Last measure to render (default: same as start_measure)
        output_dir: Directory to save HTML (default: ~/Desktop)

    Returns:
        Success message with file path to open in browser

    Examples:
        # Render first 4 measures - saves to Desktop
        render_musical_incipit_ui("Bach_BWV_0772.mei", start_measure=1, end_measure=4)

        # Save to Downloads folder
        render_musical_incipit_ui("Bach_BWV_0772.mei", start_measure=1, end_measure=8,
                                  output_dir="~/Downloads")
    """
    mei_filepath = get_mei_filepath(filename)

    # If end_measure not specified, render only the start_measure
    if end_measure is None:
        end_measure = start_measure

    # Load MEI file with music21
    score = converter.parse(str(mei_filepath))

    # Extract the specified measure range
    excerpt = score.measures(start_measure, end_measure)

    # Export to MusicXML string (in memory)
    exporter = musicxml.m21ToXml.GeneralObjectExporter(excerpt)
    musicxml_bytes = exporter.parse()
    musicxml_string = musicxml_bytes.decode('utf-8')

    # Initialize Verovio toolkit
    tk = verovio.toolkit()

    # Configure rendering options for web display
    options = {
        "pageWidth": 2100,
        "pageHeight": 60000,
        "scale": 50,
        "adjustPageHeight": True,
        "breaks": "auto",
        "footer": "none",
        "header": "none",
        "pageMarginBottom": 150,
    }
    tk.setOptions(options)

    # Load and render to SVG
    tk.loadData(musicxml_string)
    svg_output = tk.renderToSVG(1)

    # Render to MIDI (returns base64 encoded string)
    midi_base64 = tk.renderToMIDI()

    # Create measure range text
    measure_text = f"measure {start_measure}" if start_measure == end_measure else f"measures {start_measure}-{end_measure}"

    # Load HTML template
    template_path = Path(__file__).parent.parent / "templates" / "incipit_viewer.html"
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()

    # Use Template for safe substitution
    template = Template(template_content)

    # Safely inject content
    html_output = template.substitute(
        title=html.escape(f"{filename} - {measure_text}"),
        filename=html.escape(filename),
        measure_text=html.escape(measure_text.capitalize()),
        midi_base64=midi_base64,  # Already base64, safe
        svg_content=svg_output  # SVG from verovio, trusted
    )

    # Determine output directory
    if output_dir is None:
        output_path = Path.home() / "Desktop"
    else:
        output_path = Path(output_dir).expanduser()

    # Create output filename
    safe_filename = filename.replace('.mei', '').replace(' ', '_')
    output_filename = f"{safe_filename}_m{start_measure}-{end_measure}_incipit.html"
    output_file = output_path / output_filename

    # Save HTML file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_output)

    return f"✓ Interactive incipit saved to: {output_file}\n\nOpen this file in your browser to view the notation and play audio."
