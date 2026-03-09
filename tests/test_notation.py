"""Tests for show_notation tool."""

import pytest

from src.encoding_music_mcp.tools.notation import show_notation


def test_show_notation_full_piece():
    """Test showing full piece without measure range."""
    result = show_notation("Bach_BWV_0772.mei")

    assert result.content is not None, "Should have text content fallback"
    assert result.structured_content is not None, "Should have structured content"
    assert "xml" in result.structured_content, "Structured content should contain xml"
    assert "filename" in result.structured_content, "Should contain filename"
    assert result.structured_content["filename"] == "Bach_BWV_0772.mei"

    # Full piece returns raw MEI, should contain MEI namespace
    xml = result.structured_content["xml"]
    assert "mei" in xml.lower(), "Full piece should return MEI XML"


def test_show_notation_measure_range():
    """Test showing specific measure range."""
    result = show_notation("Bach_BWV_0772.mei", start_measure=1, end_measure=4)

    assert result.structured_content is not None
    assert "xml" in result.structured_content
    assert result.structured_content["start_measure"] == 1
    assert result.structured_content["end_measure"] == 4

    # Measure range uses music21 export, returns MusicXML
    xml = result.structured_content["xml"]
    assert len(xml) > 0, "Should return non-empty XML"


def test_show_notation_single_measure():
    """Test showing a single measure (only start_measure given)."""
    result = show_notation("Bach_BWV_0772.mei", start_measure=3)

    assert result.structured_content is not None
    assert result.structured_content["start_measure"] == 3
    assert result.structured_content["end_measure"] == 3


def test_show_notation_invalid_file():
    """Test that invalid filename raises appropriate error."""
    with pytest.raises(FileNotFoundError):
        show_notation("nonexistent_file.mei")


def test_show_notation_text_fallback():
    """Test that text content fallback is descriptive."""
    result = show_notation("Bach_BWV_0772.mei", start_measure=1, end_measure=4)

    # ToolResult wraps string content into a list of TextContent objects
    assert result.content is not None
    assert len(result.content) > 0
    text = result.content[0].text
    assert isinstance(text, str)
    assert "Bach_BWV_0772.mei" in text
