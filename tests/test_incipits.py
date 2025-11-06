"""Tests for musical incipit rendering."""

from src.encoding_music_mcp.tools.incipits import render_musical_incipit


def test_render_single_measure():
    """Test rendering a single measure."""
    img = render_musical_incipit("Bach_BWV_0772.mei", start_measure=1)

    assert img is not None
    assert img._mime_type == "image/png"
    assert len(img.data) > 0
    # Verify PNG signature
    assert img.data[:8] == b'\x89PNG\r\n\x1a\n'


def test_render_measure_range():
    """Test rendering a range of measures."""
    img = render_musical_incipit("Bach_BWV_0772.mei", start_measure=1, end_measure=4)

    assert img is not None
    assert img._mime_type == "image/png"
    # Range should be larger than single measure
    assert len(img.data) > 10000


def test_render_with_custom_scale():
    """Test rendering with custom scale parameter."""
    img_small = render_musical_incipit("Bach_BWV_0772.mei", start_measure=1, scale=30)
    img_large = render_musical_incipit("Bach_BWV_0772.mei", start_measure=1, scale=60)

    # Larger scale should produce larger image
    assert len(img_large.data) > len(img_small.data)


def test_render_long_excerpt():
    """Test that longer excerpts wrap across multiple lines."""
    # 16 measures should produce a multi-line rendering
    img_long = render_musical_incipit("Bach_BWV_0772.mei", start_measure=1, end_measure=16)

    # Should be substantially larger than a short excerpt
    img_short = render_musical_incipit("Bach_BWV_0772.mei", start_measure=1, end_measure=2)

    assert img_long is not None
    assert len(img_long.data) > len(img_short.data) * 2


def test_label_added():
    """Test that images include filename and measure information."""
    from src.encoding_music_mcp.tools.incipits import _add_label_to_svg

    # Simple SVG for testing
    test_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="2100px" height="800px" viewBox="0 0 2100 800">
    <rect width="100" height="100" fill="black"/>
</svg>"""

    # Add label
    result = _add_label_to_svg(test_svg, "Bach_BWV_0772.mei", 1, 4)

    # Check that label text is in result
    assert "Bach_BWV_0772.mei" in result
    assert "measures 1-4" in result

    # Check that height increased
    assert "860px" in result  # 800 + 60

    # Test single measure
    result_single = _add_label_to_svg(test_svg, "test.mei", 5, 5)
    assert "measure 5" in result_single
    assert "measures" not in result_single  # Should be singular
