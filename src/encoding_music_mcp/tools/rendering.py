"""MEI rendering tools using verovio."""

from typing import Any

import verovio
from music21 import converter

from .helpers import get_mei_filepath

__all__ = ["render_notation"]


def render_notation(
    filename: str,
    start_measure: int = 1,
    end_measure: int = 4,
    page_width: int = 1200,
) -> dict[str, Any]:
    """Render a musical excerpt as SVG notation.

    Uses music21 to select specific measures and verovio to render to SVG.
    This allows you to display small, focused musical examples without requiring
    external dependencies like LilyPond or MuseScore.

    Args:
        filename: Name of the MEI file (e.g., "Bach_BWV_0772.mei")
        start_measure: First measure to render (default: 1)
        end_measure: Last measure to render (default: 4)
        page_width: Width of the rendered page in pixels (default: 1200)

    Returns:
        Dictionary containing:
        - filename: The input filename
        - measures: String describing the measure range (e.g., "1-4")
        - svg: SVG markup as a string
        - format: Always "svg"

    Raises:
        FileNotFoundError: If the MEI file cannot be found
        ValueError: If measure numbers are invalid
    """
    if start_measure < 1:
        raise ValueError("start_measure must be >= 1")
    if end_measure < start_measure:
        raise ValueError("end_measure must be >= start_measure")

    filepath = get_mei_filepath(filename)

    # Load with music21
    score = converter.parse(str(filepath))

    # Select specific measures
    excerpt = score.measures(start_measure, end_measure)

    if excerpt is None or len(excerpt.flatten().notes) == 0:
        raise ValueError(
            f"No music found in measures {start_measure}-{end_measure}. "
            f"The score may have fewer measures than requested."
        )

    # Export to MusicXML (music21's most reliable format for verovio)
    musicxml_data = excerpt.write("musicxml")

    # Render with verovio
    tk = verovio.toolkit()
    tk.loadData(musicxml_data)
    tk.setOptions(
        {
            "pageWidth": page_width,
            "adjustPageHeight": True,
            "breaks": "none",
            "scale": 40,
        }
    )
    svg = tk.renderToSVG()

    return {
        "filename": filename,
        "measures": f"{start_measure}-{end_measure}",
        "svg": svg,
        "format": "svg",
    }
