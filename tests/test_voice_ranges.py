"""Tests for the voice range plotting tool."""

import pytest

from src.encoding_music_mcp.tools.visualisation.voice_ranges import plot_voice_ranges


def test_plot_voice_ranges_bach():
    """Test voice-range extraction for a two-staff Bach score."""
    result = plot_voice_ranges("Bach_BWV_0772.mei")

    assert result.content is not None
    assert result.structured_content is not None

    structured = result.structured_content
    assert structured["filename"] == "Bach_BWV_0772.mei"
    assert structured["title"]
    assert structured["composer"] == "Bach, Johann Sebastian"
    assert len(structured["staff_ranges"]) == 2
    assert structured["x_min_midi"] == 36
    assert structured["x_max_midi"] == 84

    upper_staff = structured["staff_ranges"][0]
    lower_staff = structured["staff_ranges"][1]

    assert upper_staff["staff"] == "1"
    assert upper_staff["lowest_note"] == "C4"
    assert upper_staff["highest_note"] == "C6"
    assert upper_staff["range_semitones"] == 24

    assert lower_staff["staff"] == "2"
    assert lower_staff["lowest_note"] == "C2"
    assert lower_staff["highest_note"] == "B-4"
    assert lower_staff["range_semitones"] == 34


def test_plot_voice_ranges_axis_ticks():
    """Test that the voice-range payload includes note-labelled axis ticks."""
    result = plot_voice_ranges("Bartok_Mikrokosmos_022.mei")
    structured = result.structured_content

    assert structured is not None
    assert structured["tick_values"][0] == structured["x_min_midi"]
    assert structured["tick_values"][-1] == structured["x_max_midi"]
    assert structured["tick_labels"][0] == "B3"
    assert structured["tick_labels"][-1] == "D5"


def test_plot_voice_ranges_staff_record_shape():
    """Test that each staff range record contains the expected fields."""
    result = plot_voice_ranges("Bach_BWV_0772.mei")
    staff = result.structured_content["staff_ranges"][0]

    assert "staff" in staff
    assert "label" in staff
    assert "colour" in staff
    assert "lowest_midi" in staff
    assert "highest_midi" in staff
    assert "lowest_note" in staff
    assert "highest_note" in staff
    assert "range_semitones" in staff


def test_plot_voice_ranges_invalid_file():
    """Test that invalid filenames raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        plot_voice_ranges("nonexistent_file.mei")
