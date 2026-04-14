"""Tests for weighted note-distribution visualisation."""

import math

import pytest

from src.encoding_music_mcp.tools.visualisation.weighted_note_distribution import (
    plot_weighted_note_distribution,
)


def test_plot_weighted_note_distribution_bach():
    """Combined score view should return one scaled trace."""
    result = plot_weighted_note_distribution("Bach_BWV_0772.mei")
    structured = result.structured_content

    assert structured is not None
    assert structured["filename"] == "Bach_BWV_0772.mei"
    assert structured["pitch_class_order"] == "fifths"
    assert structured["group_by_staff"] is False
    assert structured["limit_to_active"] is True
    assert isinstance(structured["categories"], list)
    assert len(structured["categories"]) > 0
    assert len(structured["traces"]) == 1

    trace = structured["traces"][0]
    assert trace["label"] == "Score"
    assert len(trace["values"]) == len(structured["categories"])
    assert len(trace["raw_weights_ppq"]) == len(structured["categories"])
    assert trace["total_weight_ppq"] > 0
    assert trace["note_count"] > 0
    assert math.isclose(sum(trace["values"]), 1.0, rel_tol=1e-9, abs_tol=1e-9)


def test_plot_weighted_note_distribution_group_by_staff():
    """Staff grouping should expose multiple traces for a keyboard score."""
    result = plot_weighted_note_distribution(
        "Bach_BWV_0772.mei",
        group_by_staff=True,
    )
    structured = result.structured_content

    assert structured is not None
    assert structured["group_by_staff"] is True
    assert len(structured["traces"]) >= 2
    assert all(trace["label"].startswith("Staff ") for trace in structured["traces"])
    assert all(
        len(trace["values"]) == len(structured["categories"])
        for trace in structured["traces"]
    )


def test_plot_weighted_note_distribution_category_order():
    """Returned categories should preserve the requested pitch-class order."""
    result = plot_weighted_note_distribution(
        "Bach_BWV_0772.mei",
        pitch_class_order="chromatic",
        limit_to_active=False,
    )
    structured = result.structured_content

    assert structured is not None
    assert structured["categories"] == [
        "C",
        "C#",
        "D",
        "E-",
        "E",
        "F",
        "F#",
        "G",
        "A-",
        "A",
        "B-",
        "B",
    ]


def test_plot_weighted_note_distribution_accidentals_are_counted():
    """Accidentals should contribute to the expected pitch classes."""
    result = plot_weighted_note_distribution(
        "Bach_BWV_0772.mei",
        pitch_class_order="chromatic",
        limit_to_active=False,
    )
    structured = result.structured_content
    assert structured is not None

    trace = structured["traces"][0]
    value_by_pitch_class = dict(zip(structured["categories"], trace["values"], strict=True))

    assert value_by_pitch_class["F#"] > 0
    assert value_by_pitch_class["B-"] > 0


def test_plot_weighted_note_distribution_invalid_file():
    """Invalid filenames should raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        plot_weighted_note_distribution("nonexistent_file.mei")
