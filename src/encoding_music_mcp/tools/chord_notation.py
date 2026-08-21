"""Chord-reduction notation rendered through the existing notation MCP App."""

from pathlib import Path

from anyio import to_process
from mcp.types import TextContent
from music21 import chord, converter, stream
from music21.musicxml.m21ToXml import GeneralObjectExporter

from fastmcp import Context
from fastmcp.tools.tool import ToolResult

from .helpers import get_mei_filepath
from .notation import (
    _NOTATION_PROCESS_CONCURRENCY,
    _resolve_notation_filename,
    render_notation_data,
)

__all__ = ["show_chord_notation"]


def _validate_measure_range(
    start_measure: int | None, end_measure: int | None
) -> tuple[int | None, int | None]:
    """Validate and normalize an inclusive measure range."""
    if start_measure is None and end_measure is not None:
        raise ValueError("end_measure requires start_measure")
    if start_measure is not None and start_measure < 1:
        raise ValueError("start_measure must be at least 1")
    if end_measure is not None and end_measure < 1:
        raise ValueError("end_measure must be at least 1")
    if start_measure is not None and end_measure is None:
        end_measure = start_measure
    if (
        start_measure is not None
        and end_measure is not None
        and start_measure > end_measure
    ):
        raise ValueError("start_measure must be less than or equal to end_measure")
    return start_measure, end_measure


def _build_chordified_score(
    filepath: Path, start_measure: int | None, end_measure: int | None
) -> stream.Score:
    """Parse a score and append its chord reduction as the final part."""
    display_score = converter.parse(filepath)
    reduction = display_score.chordify()
    for sonority in reduction.recurse().getElementsByClass(chord.Chord):
        sonority.closedPosition(forceOctave=4, inPlace=True)
    display_score.insert(0, reduction)

    if start_measure is not None and end_measure is not None:
        display_score = display_score.measures(start_measure, end_measure)
        if not any(
            True
            for part in display_score.parts
            for _measure in part.getElementsByClass(stream.Measure)
        ):
            raise ValueError(
                f"No measures found in requested range {start_measure}-{end_measure}"
            )

    return display_score


def _render_chord_notation_page(
    filepath: Path,
    start_measure: int | None,
    end_measure: int | None,
    page: int,
) -> tuple[str, int, int]:
    """Build and render a chord reduction synchronously in a worker process."""
    display_score = _build_chordified_score(filepath, start_measure, end_measure)
    musicxml = GeneralObjectExporter(display_score).parse().decode("utf-8")
    return render_notation_data(musicxml, page)


async def show_chord_notation(
    filename: str | None = None,
    start_measure: int | None = None,
    end_measure: int | None = None,
    page: int = 1,
    ctx: Context | None = None,
) -> ToolResult:
    """Display an MEI score with an appended chord-reduction staff."""
    should_elicit = ctx is not None and (
        filename is None or not get_mei_filepath(filename).exists()
    )
    filename = await _resolve_notation_filename(filename, ctx, should_elicit)
    filepath = get_mei_filepath(filename)
    if not filepath.is_file():
        raise FileNotFoundError(f"MEI file not found: {filename}")
    start_measure, end_measure = _validate_measure_range(start_measure, end_measure)

    process_limiter = to_process.current_default_process_limiter()
    process_limiter.total_tokens = _NOTATION_PROCESS_CONCURRENCY
    svg, page, total_pages = await to_process.run_sync(
        _render_chord_notation_page,
        filepath,
        start_measure,
        end_measure,
        page,
        limiter=process_limiter,
    )

    structured = {
        "filename": filename,
        "svg": svg,
        "page": page,
        "total_pages": total_pages,
        "notation_mode": "chord_reduction",
    }
    if start_measure is not None:
        structured["start_measure"] = start_measure
        structured["end_measure"] = end_measure

    range_text = (
        ""
        if start_measure is None
        else (
            f", measure {start_measure}"
            if start_measure == end_measure
            else f", measures {start_measure}-{end_measure}"
        )
    )
    description = (
        f"Showing {filename} with chord reduction{range_text}, "
        f"page {page} of {total_pages}"
    )
    return ToolResult(
        content=[TextContent(type="text", text=description)],
        structured_content=structured,
    )
