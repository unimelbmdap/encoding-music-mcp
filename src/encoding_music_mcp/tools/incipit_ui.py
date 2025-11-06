"""Musical incipit UI viewer - generates interactive HTML file with Verovio app."""

import html
from datetime import datetime
from pathlib import Path
from string import Template
from music21 import converter, musicxml

from .helpers import get_mei_filepath

__all__ = ["render_musical_incipit_ui"]


def render_musical_incipit_ui(
    filename: str,
    start_measure: int = 1,
    end_measure: int | None = None,
    output_dir: str | None = None,
) -> str:
    """Generate interactive HTML file with Verovio app (notation + MIDI playback), saved to disk.

    Creates an HTML viewer with the full Verovio interactive app featuring:
    - Vector graphics notation rendering
    - MIDI playback with synchronized note highlighting
    - Interactive controls (play/pause, zoom, navigation)
    - Click-to-play functionality

    Args:
        filename: Name of the MEI file (e.g., "Bach_BWV_0772.mei")
        start_measure: First measure to render (default: 1)
        end_measure: Last measure to render (default: same as start_measure)
        output_dir: Directory to save HTML (default: ~/Downloads)

    Returns:
        File path in tilde notation (e.g., "~/Downloads/filename.html")

    Examples:
        # Render first 4 measures - saves to Downloads
        render_musical_incipit_ui("Bach_BWV_0772.mei", start_measure=1, end_measure=4)

        # Save to Desktop folder
        render_musical_incipit_ui("Bach_BWV_0772.mei", start_measure=1, end_measure=8,
                                  output_dir="~/Desktop")
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

    # Create measure range text
    measure_text = f"measure {start_measure}" if start_measure == end_measure else f"measures {start_measure}-{end_measure}"

    # Replace music21's default title with our filename and measure range
    title_replacement = f"{filename} - {measure_text}"
    musicxml_string = musicxml_string.replace(
        '<movement-title>Music21 Fragment</movement-title>',
        f'<movement-title>{html.escape(title_replacement)}</movement-title>'
    )

    # Escape backticks in MusicXML for safe embedding in JavaScript template literal
    musicxml_escaped = musicxml_string.replace('`', '\\`').replace('${', '\\${')

    # Load HTML template (using Verovio app)
    template_path = Path(__file__).parent.parent / "templates" / "incipit_verovio_app.html"
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()

    # Use Template for safe substitution
    template = Template(template_content)

    # Safely inject content
    html_output = template.substitute(
        title=html.escape(f"{filename} : {measure_text}"),
        filename=html.escape(filename),
        measure_text=html.escape(measure_text.capitalize()),
        musicxml_data=musicxml_escaped  # Escaped for JavaScript template literal
    )

    # Determine output directory
    if output_dir is None:
        output_path = Path.home() / "Downloads"
    else:
        output_path = Path(output_dir).expanduser()

    # Create output filename with timestamp to avoid collisions
    safe_filename = filename.replace('.mei', '').replace(' ', '_')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_filename = f"{safe_filename}_m{start_measure}-{end_measure}_{timestamp}_incipit.html"
    output_file = output_path / output_filename

    # Save HTML file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_output)

    # Return simplified path with tilde notation
    try:
        # Try to make it relative to home directory
        relative_to_home = output_file.relative_to(Path.home())
        return f"~/{relative_to_home}"
    except ValueError:
        # If not in home directory, return full path
        return str(output_file)
