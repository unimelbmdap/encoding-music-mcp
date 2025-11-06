"""Musical incipit viewer resource using MCP UI."""

from music21 import converter, musicxml
import verovio

from ..tools.helpers import get_mei_filepath

__all__ = ["musical_incipit_viewer"]


def musical_incipit_viewer(
    filename: str,
    start_measure: str = "1",
    end_measure: str | None = None,
) -> str:
    """Generate interactive HTML viewer for musical incipit.

    Args:
        filename: Name of the MEI file
        start_measure: First measure to render (as string from URI parameter)
        end_measure: Last measure to render (as string from URI parameter)

    Returns:
        HTML string with embedded SVG and MIDI audio player
    """
    # Convert string parameters to integers
    start = int(start_measure)
    end = int(end_measure) if end_measure else start

    filepath = get_mei_filepath(filename)

    # Load MEI file with music21
    score = converter.parse(str(filepath))

    # Extract the specified measure range
    excerpt = score.measures(start, end)

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
    measure_text = f"measure {start}" if start == end else f"measures {start}-{end}"

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
        button {{
            background: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            font-size: 14px;
            cursor: pointer;
            margin-right: 10px;
        }}
        button:hover {{
            background: #0056b3;
        }}
        button:disabled {{
            background: #ccc;
            cursor: not-allowed;
        }}
        #stopButton {{
            background: #dc3545;
        }}
        #stopButton:hover:not(:disabled) {{
            background: #c82333;
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
        <button id="playButton" onclick="playMidi()">▶ Play</button>
        <button id="stopButton" onclick="stopMidi()" disabled>⏹ Stop</button>
        <p id="status" style="margin-top: 10px; color: #666; font-size: 14px;">
            Note: MIDI playback requires soundfont loading (may take a moment)
        </p>
    </div>

    <script src="https://cdn.jsdelivr.net/combine/npm/tone@14.7.58,npm/@magenta/music@1.23.1/es6/core.js,npm/focus-visible@5,npm/html-midi-player@1.5.0"></script>
    <midi-player
        src="data:audio/midi;base64,{midi_base64}"
        sound-font
        visualizer="#myVisualizer"
        id="midiPlayer"
        style="display: none;">
    </midi-player>

    <script>
        const player = document.querySelector('midi-player');
        const playButton = document.getElementById('playButton');
        const stopButton = document.getElementById('stopButton');
        const status = document.getElementById('status');

        player.addEventListener('load', () => {{
            status.textContent = 'Ready to play!';
            status.style.color = '#28a745';
        }});

        player.addEventListener('start', () => {{
            playButton.disabled = true;
            stopButton.disabled = false;
            status.textContent = 'Playing...';
            status.style.color = '#007bff';
        }});

        player.addEventListener('stop', () => {{
            playButton.disabled = false;
            stopButton.disabled = true;
            status.textContent = 'Stopped';
            status.style.color = '#666';
        }});

        function playMidi() {{
            player.start();
        }}

        function stopMidi() {{
            player.stop();
        }}

        // Auto-load on page load
        window.addEventListener('load', () => {{
            status.textContent = 'Loading MIDI player...';
        }});
    </script>

    <div class="notation">
        {svg_output}
    </div>
</body>
</html>"""

    return html
