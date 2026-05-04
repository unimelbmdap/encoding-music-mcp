"""Notation display tool using MCP Apps extension with Verovio."""

import xml.etree.ElementTree as ET
from pathlib import Path

import verovio
from mcp.types import TextContent

from fastmcp import Context
from fastmcp.server.elicitation import CancelledElicitation, DeclinedElicitation
from fastmcp.tools.tool import ToolResult

from .helpers import get_mei_collections, get_mei_filepath, register_uploaded_mei_from_path

# Resolve the Verovio resource path from the installed package.
# The verovio __init__.py sets this via importlib.resources, but that can
# fail in some process contexts (e.g. MCP server launched by Claude Desktop).
_VEROVIO_RESOURCE_PATH = str(Path(verovio.__file__).parent / "data")

__all__ = [
    "show_notation",
    "show_notation_highlight",
]

_MEI_NS = "http://www.music-encoding.org/ns/mei"
_MEI_TAG = "{" + _MEI_NS + "}"

# Register namespaces so ET.tostring preserves them.
ET.register_namespace("", _MEI_NS)
ET.register_namespace("xml", "http://www.w3.org/XML/1998/namespace")

# Verovio options for web-friendly SVG output.
# Scale and page height are tuned so each page SVG stays under ~80KB
# to avoid MCP structured content transport limits.
_VEROVIO_OPTIONS = {
    "scale": 40,
    "pageWidth": 2000,
    "pageHeight": 800,
    "adjustPageHeight": True,
    "systemMaxPerPage": 1,
    "breaks": "auto",
    "footer": "none",
    "pageMarginLeft": 20,
    "pageMarginRight": 20,
    "pageMarginTop": 20,
    "pageMarginBottom": 20,
}


def _filter_measures(mei_data: str, start: int, end: int) -> str:
    """Return MEI XML containing only measures in [start, end]."""
    root = ET.fromstring(mei_data)
    for section in root.findall(f".//{_MEI_TAG}section"):
        for measure in section.findall(f"{_MEI_TAG}measure"):
            n = int(measure.get("n", 0))
            if n < start or n > end:
                section.remove(measure)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
        root, encoding="unicode"
    )


def _create_toolkit(mei_data: str) -> verovio.toolkit:
    """Create a Verovio toolkit loaded with MEI data."""
    tk = verovio.toolkit()
    tk.setResourcePath(_VEROVIO_RESOURCE_PATH)
    tk.setOptions(_VEROVIO_OPTIONS)
    if not tk.loadData(mei_data):
        raise ValueError(
            f"Verovio failed to load MEI data "
            f"(data length={len(mei_data)}, "
            f"resource_path={tk.getResourcePath()})"
        )
    return tk


def _normalise_svg_text(svg: str) -> str:
    """Replace fragile Unicode text and preserve SVG text spacing."""
    normalised = (
        svg.replace("\u2013", "-")
        .replace("\u00a0", " ")
        .replace("\u00e2\u20ac\u201c", "-")
    )
    return normalised.replace("<text ", '<text xml:space="preserve" ')


def _missing_registration_filename(filename: str | None) -> str | None:
    """Reuse a missing requested basename when registering an elicited local path."""
    if filename is None or "/" in filename or "\\" in filename:
        return None
    if Path(filename).name != filename or get_mei_filepath(filename).exists():
        return None
    return filename


async def _resolve_notation_filename(
    filename: str | None,
    ctx: Context | None,
    should_elicit: bool,
) -> str:
    """Choose or register the score to render."""
    if not should_elicit:
        if filename is None:
            raise ValueError("filename is required to show notation")
        return filename

    if ctx is None:
        if filename is None:
            raise ValueError(
                "filename is required to show notation when no MCP context is available"
            )
        return filename

    available_files = get_mei_collections().get("all_files", [])
    options = available_files
    if filename and filename not in options:
        options = [filename, *options]

    missing_hint = ""
    if filename:
        missing_hint = (
            f" I could not find a registered MEI file, local file, or folder for "
            f"'{filename}'."
        )
    prompt = (
        "Which MEI file would you like to show?"
        f"{missing_hint} Choose one of the available files, type another registered "
        "filename, or type a local path to a .mei file on this computer."
    )
    elicitation = await ctx.elicit(prompt, options or str)
    if isinstance(elicitation, DeclinedElicitation | CancelledElicitation):
        raise ValueError("filename or local MEI path is required to show notation")

    selected = str(elicitation.data).strip()
    if not selected:
        raise ValueError("filename or local MEI path is required to show notation")

    is_path_like = "/" in selected or "\\" in selected or Path(selected).is_absolute()
    path = Path(selected).expanduser()
    if is_path_like and path.exists():
        registered_filename = _missing_registration_filename(filename)
        return register_uploaded_mei_from_path(selected, registered_filename)["filename"]

    selected_filepath = get_mei_filepath(selected)
    if selected_filepath.exists():
        return selected

    if path.exists():
        registered_filename = _missing_registration_filename(filename)
        return register_uploaded_mei_from_path(selected, registered_filename)["filename"]

    raise FileNotFoundError(
        f"MEI file not found as a registered filename or local path: {selected}"
    )


async def show_notation(
    filename: str | None = None,
    start_measure: int | None = None,
    end_measure: int | None = None,
    page: int = 1,
    ctx: Context | None = None,
) -> ToolResult:
    """Display musical notation for an MEI file.

    Renders one page of notation at a time. Use the page parameter to
    navigate through longer pieces.

    Args:
        filename: Name of the MEI file (e.g., "Bach_BWV_0772.mei")
        start_measure: First measure to display (optional, defaults to showing full piece)
        end_measure: Last measure to display (optional, defaults to start_measure if only start given)
        page: Page number to display (default 1). Use total_pages from the result to navigate.

    Returns:
        ToolResult with SVG notation for the MCP App viewer
    """
    should_elicit = ctx is not None and (
        filename is None or not get_mei_filepath(filename).exists()
    )
    filename = await _resolve_notation_filename(filename, ctx, should_elicit)
    filepath = get_mei_filepath(filename)

    if not filepath.exists():
        raise FileNotFoundError(f"MEI file not found: {filename}")

    mei_data = filepath.read_text(encoding="utf-8")

    if start_measure is not None:
        if end_measure is None:
            end_measure = start_measure
        mei_data = _filter_measures(mei_data, start_measure, end_measure)

    tk = _create_toolkit(mei_data)
    total_pages = tk.getPageCount()

    page = max(1, min(page, total_pages))
    svg = _normalise_svg_text(tk.renderToSVG(page))

    if start_measure is not None:
        measure_text = (
            f"measure {start_measure}"
            if start_measure == end_measure
            else f"measures {start_measure}-{end_measure}"
        )
        description = f"Showing {filename}, {measure_text}, page {page} of {total_pages}"
    else:
        description = f"Showing {filename}, page {page} of {total_pages}"

    structured = {
        "filename": filename,
        "svg": svg,
        "page": page,
        "total_pages": total_pages,
    }
    if start_measure is not None:
        structured["start_measure"] = start_measure
        structured["end_measure"] = end_measure

    return ToolResult(
        content=[TextContent(type="text", text=description)],
        structured_content=structured,
    )


async def show_notation_highlight(
    filename: str,
    highlight_note_ids: list[str],
    start_measure: int | None = None,
    end_measure: int | None = None,
    page: int = 1,
    ctx: Context | None = None,
) -> ToolResult:
    """Display notation with a supplied set of highlighted note IDs.

    Call this tool once for the requested excerpt and let the widget handle
    navigation across all pages. Avoid making one tool call per page unless
    the user explicitly asks for a specific page number.
    """
    result = await show_notation(
        filename=filename,
        start_measure=start_measure,
        end_measure=end_measure,
        page=page,
        ctx=ctx,
    )

    structured = dict(result.structured_content or {})
    structured["highlight_note_ids"] = highlight_note_ids

    return ToolResult(
        content=result.content,
        structured_content=structured,
    )
