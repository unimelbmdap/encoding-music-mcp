"""Notation display tool using MCP Apps extension."""

from music21 import converter, musicxml

from fastmcp.tools.tool import ToolResult

from .helpers import get_mei_filepath

__all__ = ["show_notation"]


def show_notation(
    filename: str,
    start_measure: int | None = None,
    end_measure: int | None = None,
) -> ToolResult:
    """Display musical notation for an MEI file, optionally showing a specific measure range.

    Args:
        filename: Name of the MEI file (e.g., "Bach_BWV_0772.mei")
        start_measure: First measure to display (optional, defaults to showing full piece)
        end_measure: Last measure to display (optional, defaults to start_measure if only start given)

    Returns:
        ToolResult with notation XML data for the MCP App viewer
    """
    filepath = get_mei_filepath(filename)

    if not filepath.exists():
        raise FileNotFoundError(f"MEI file not found: {filename}")

    if start_measure is None:
        # No measure range - return raw MEI
        xml = filepath.read_text(encoding="utf-8")
        description = f"Showing full score: {filename}"
        structured = {
            "filename": filename,
            "xml": xml,
        }
    else:
        # Extract measure range with music21
        if end_measure is None:
            end_measure = start_measure

        score = converter.parse(str(filepath))
        excerpt = score.measures(start_measure, end_measure)

        exporter = musicxml.m21ToXml.GeneralObjectExporter(excerpt)
        musicxml_bytes = exporter.parse()
        xml = musicxml_bytes.decode("utf-8")

        measure_text = (
            f"measure {start_measure}"
            if start_measure == end_measure
            else f"measures {start_measure}-{end_measure}"
        )
        description = f"Showing {filename}, {measure_text}"
        structured = {
            "filename": filename,
            "start_measure": start_measure,
            "end_measure": end_measure,
            "xml": xml,
        }

    return ToolResult(
        content=description,
        structured_content=structured,
    )
