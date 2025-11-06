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
