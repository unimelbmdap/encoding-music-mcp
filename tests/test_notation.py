"""Tests for show_notation tools."""

import asyncio
from pathlib import Path

import pytest

from src.encoding_music_mcp.server import mcp
from src.encoding_music_mcp.tools.helpers import remove_uploaded_mei
from src.encoding_music_mcp.tools.notation import show_notation, show_notation_highlight


class _AcceptedElicitation:
    def __init__(self, data: str):
        self.data = data


class _FakeContext:
    def __init__(self, response: str):
        self.response = response
        self.messages = []

    async def elicit(self, message, response_type):
        self.messages.append((message, response_type))
        return _AcceptedElicitation(self.response)


def _sample_mei_path() -> Path:
    return (
        Path(__file__).parent.parent
        / "src"
        / "encoding_music_mcp"
        / "resources"
        / "mei_files"
        / "Bach_BWV_0772.mei"
    )


def test_show_notation_full_piece():
    """Test showing full piece without measure range."""
    result = asyncio.run(show_notation("Bach_BWV_0772.mei"))

    assert result.content is not None, "Should have text content fallback"
    assert result.structured_content is not None, "Should have structured content"
    assert "svg" in result.structured_content, "Should contain svg"
    assert "filename" in result.structured_content, "Should contain filename"
    assert result.structured_content["filename"] == "Bach_BWV_0772.mei"
    assert result.structured_content["page"] == 1
    assert result.structured_content["total_pages"] >= 1

    svg = result.structured_content["svg"]
    assert isinstance(svg, str)
    assert svg.startswith("<svg"), "Should be SVG content"


def test_show_notation_elicits_choice_when_context_is_available():
    """Notation asks which score to show when no filename is supplied."""
    ctx = _FakeContext("Bach_BWV_0772.mei")

    result = asyncio.run(show_notation(ctx=ctx))

    assert ctx.messages
    assert "Which MEI file" in ctx.messages[0][0]
    assert "Bach_BWV_0772.mei" in ctx.messages[0][1]
    assert result.structured_content["filename"] == "Bach_BWV_0772.mei"
    assert result.structured_content["svg"].startswith("<svg")


def test_show_notation_elicits_local_path_for_missing_file():
    """The free-form elicitation response can be a local MEI path."""
    filename = "Elicited_Bach_Copy.mei"
    remove_uploaded_mei(filename)
    ctx = _FakeContext(str(_sample_mei_path()))

    try:
        result = asyncio.run(show_notation(ctx=ctx))
    finally:
        remove_uploaded_mei(filename)

    assert ctx.messages
    assert result.structured_content["filename"] == "Bach_BWV_0772.mei"
    assert result.structured_content["svg"].startswith("<svg")


def test_show_notation_uses_supplied_filename_without_elicitation():
    """Explicit filename calls should behave like normal direct tool calls."""
    ctx = _FakeContext("Bach_BWV_0773.mei")

    result = asyncio.run(show_notation("Bach_BWV_0772.mei", ctx=ctx))

    assert ctx.messages == []
    assert result.structured_content["filename"] == "Bach_BWV_0772.mei"


def test_show_notation_elicits_when_supplied_filename_is_unavailable():
    """Missing filenames can be resolved by eliciting a visible local path."""
    filename = "Elicited_Bach_Copy.mei"
    remove_uploaded_mei(filename)
    ctx = _FakeContext(str(_sample_mei_path()))

    try:
        result = asyncio.run(show_notation(filename, ctx=ctx))
    finally:
        remove_uploaded_mei(filename)

    assert ctx.messages
    assert result.structured_content["filename"] == filename
    assert result.structured_content["svg"].startswith("<svg")


def test_show_notation_measure_range():
    """Test showing specific measure range."""
    result = asyncio.run(
        show_notation("Bach_BWV_0772.mei", start_measure=1, end_measure=4)
    )

    assert result.structured_content is not None
    assert "svg" in result.structured_content
    assert result.structured_content["start_measure"] == 1
    assert result.structured_content["end_measure"] == 4

    svg = result.structured_content["svg"]
    assert isinstance(svg, str)
    assert svg.startswith("<svg")


def test_show_notation_measure_range_fewer_pages():
    """Test that filtering measures produces fewer pages than full piece."""
    full = asyncio.run(show_notation("Bach_BWV_0772.mei"))
    subset = asyncio.run(
        show_notation("Bach_BWV_0772.mei", start_measure=19, end_measure=22)
    )

    assert subset.structured_content["total_pages"] < full.structured_content["total_pages"]


def test_show_notation_single_measure():
    """Test showing a single measure (only start_measure given)."""
    result = asyncio.run(show_notation("Bach_BWV_0772.mei", start_measure=3))

    assert result.structured_content is not None
    assert result.structured_content["start_measure"] == 3
    assert result.structured_content["end_measure"] == 3


def test_show_notation_invalid_file():
    """Test that invalid filename raises appropriate error."""
    with pytest.raises(FileNotFoundError):
        asyncio.run(show_notation("nonexistent_file.mei"))


def test_show_notation_text_fallback():
    """Test that text content fallback is descriptive."""
    result = asyncio.run(
        show_notation("Bach_BWV_0772.mei", start_measure=1, end_measure=4)
    )

    assert result.content is not None
    assert len(result.content) > 0
    text = result.content[0].text
    assert isinstance(text, str)
    assert "Bach_BWV_0772.mei" in text


def test_show_notation_page_navigation():
    """Test page navigation for multi-page pieces."""
    result_p1 = asyncio.run(show_notation("Bach_BWV_0772.mei", page=1))
    total = result_p1.structured_content["total_pages"]

    if total > 1:
        result_p2 = asyncio.run(show_notation("Bach_BWV_0772.mei", page=2))
        assert result_p2.structured_content["page"] == 2
        assert result_p2.structured_content["svg"] != result_p1.structured_content["svg"]


def test_show_notation_page_clamping():
    """Test that out-of-range pages are clamped."""
    result = asyncio.run(show_notation("Bach_BWV_0772.mei", page=9999))
    total = result.structured_content["total_pages"]
    assert result.structured_content["page"] == total

    result_low = asyncio.run(show_notation("Bach_BWV_0772.mei", page=0))
    assert result_low.structured_content["page"] == 1


def test_show_notation_highlight_includes_note_ids():
    """Test highlight-capable notation payload includes requested note IDs."""
    result = asyncio.run(
        show_notation_highlight(
            "Bach_BWV_0772.mei",
            highlight_note_ids=["nz7y0rb", "n1ecjh8t"],
        )
    )

    assert result.structured_content is not None
    assert result.structured_content["highlight_note_ids"] == [
        "nz7y0rb",
        "n1ecjh8t",
    ]
    assert result.structured_content["svg"].startswith("<svg")


def test_notation_tools_advertise_output_schemas():
    """App-backed notation tools should still be discoverable as JSON tools."""
    tools = {tool.name: tool for tool in asyncio.run(mcp.list_tools())}

    notation_schema = tools["show_notation"].output_schema
    highlight_schema = tools["show_notation_highlight"].output_schema

    assert notation_schema is not None
    assert notation_schema["required"] == ["filename", "svg", "page", "total_pages"]
    assert "svg" in notation_schema["properties"]

    assert highlight_schema is not None
    assert "highlight_note_ids" in highlight_schema["required"]
    assert highlight_schema["properties"]["highlight_note_ids"]["type"] == "array"
