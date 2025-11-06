"""Musical incipit UI viewer using MCP UI (HTML with SVG and MIDI)."""

from music21 import converter, musicxml
import verovio

from .helpers import get_mei_filepath

__all__ = ["render_musical_incipit_ui"]


def render_musical_incipit_ui(
    filename: str,
    start_measure: int = 1,
    end_measure: int | None = None,
) -> str:
    """Render a musical incipit as interactive HTML with SVG notation and MIDI playback.

    Creates an HTML viewer with vector graphics notation and audio playback
    for a specified range of measures from an MEI file.

    Args:
        filename: Name of the MEI file (e.g., "Bach_BWV_0772.mei")
        start_measure: First measure to render (default: 1)
        end_measure: Last measure to render (default: same as start_measure)

    Returns:
        HTML string with embedded SVG and MIDI audio player

    Examples:
        # Render first 4 measures with audio
        render_musical_incipit_ui("Bach_BWV_0772.mei", start_measure=1, end_measure=4)
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

    # Generate HTML with embedded SVG and MIDI
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{filename} - {measure_text}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: #fafafa;
        }}
        .header {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 24px;
            color: #333;
        }}
        .header p {{
            margin: 0;
            color: #666;
            font-size: 14px;
        }}
        .controls {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .controls h2 {{
            margin: 0 0 10px 0;
            font-size: 16px;
            color: #333;
        }}
        audio {{
            width: 100%;
            outline: none;
        }}
        .notation {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow-x: auto;
        }}
        .notation svg {{
            max-width: 100%;
            height: auto;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{filename}</h1>
        <p>{measure_text.capitalize()}</p>
    </div>

    <div class="controls">
        <h2>🎵 Audio Playback</h2>
        <audio controls>
            <source src="data:audio/midi;base64,{midi_base64}" type="audio/midi">
            Your browser doesn't support MIDI playback.
        </audio>
    </div>

    <div class="notation">
        {svg_output}
    </div>
</body>
</html>"""

    return html
