"""Tests for show_notation tool."""

import pytest

from src.encoding_music_mcp.tools.notation import show_notation


def test_show_notation_full_piece():
    """Test showing full piece without measure range."""
    result = show_notation("Bach_BWV_0772.mei")

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


def test_show_notation_measure_range():
    """Test showing specific measure range."""
    result = show_notation("Bach_BWV_0772.mei", start_measure=1, end_measure=4)

    assert result.structured_content is not None
    assert "svg" in result.structured_content
    assert result.structured_content["start_measure"] == 1
    assert result.structured_content["end_measure"] == 4

    svg = result.structured_content["svg"]
    assert isinstance(svg, str)
    assert svg.startswith("<svg")


def test_show_notation_measure_range_fewer_pages():
    """Test that filtering measures produces fewer pages than full piece."""
    full = show_notation("Bach_BWV_0772.mei")
    subset = show_notation("Bach_BWV_0772.mei", start_measure=19, end_measure=22)

    assert subset.structured_content["total_pages"] < full.structured_content["total_pages"]


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

    assert result.content is not None
    assert len(result.content) > 0
    text = result.content[0].text
    assert isinstance(text, str)
    assert "Bach_BWV_0772.mei" in text


def test_show_notation_page_navigation():
    """Test page navigation for multi-page pieces."""
    result_p1 = show_notation("Bach_BWV_0772.mei", page=1)
    total = result_p1.structured_content["total_pages"]

    if total > 1:
        result_p2 = show_notation("Bach_BWV_0772.mei", page=2)
        assert result_p2.structured_content["page"] == 2
        assert result_p2.structured_content["svg"] != result_p1.structured_content["svg"]


def test_show_notation_page_clamping():
    """Test that out-of-range pages are clamped."""
    result = show_notation("Bach_BWV_0772.mei", page=9999)
    total = result.structured_content["total_pages"]
    assert result.structured_content["page"] == total

    result_low = show_notation("Bach_BWV_0772.mei", page=0)
    assert result_low.structured_content["page"] == 1
