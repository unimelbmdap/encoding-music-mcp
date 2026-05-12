"""Tests for melodic n-gram heatmap visualisation."""

import pytest

from src.encoding_music_mcp.tools.visualisation.melodic_ngram_heatmap import (
    plot_melodic_ngram_heatmap,
)


def test_plot_melodic_ngram_heatmap_multiple_scores():
    """Heatmap should rank patterns across pieces and separate staff rows."""
    result = plot_melodic_ngram_heatmap(
        filenames=["Bach_BWV_0772.mei", "Bartok_Mikrokosmos_022.mei"],
        n=4,
        top_n=2,
    )
    structured = result.structured_content

    assert structured is not None
    assert structured["filenames"] == [
        "Bach_BWV_0772.mei",
        "Bartok_Mikrokosmos_022.mei",
    ]
    assert structured["score_count"] == 2
    assert structured["n"] == 4
    assert structured["top_n"] == 2
    assert len(structured["patterns"]) == 2
    assert len(structured["rows"]) >= 4
    assert len(structured["occurrences"]) > 0

    filenames_by_row = {row["filename"] for row in structured["rows"]}
    assert filenames_by_row == {"Bach_BWV_0772.mei", "Bartok_Mikrokosmos_022.mei"}
    assert all("Staff" in row["label"] for row in structured["rows"])


def test_plot_melodic_ngram_heatmap_occurrence_shape():
    """Occurrence records should contain rectangle coordinates and colours."""
    result = plot_melodic_ngram_heatmap("Bach_BWV_0772.mei", top_n=2)
    structured = result.structured_content
    occurrence = structured["occurrences"][0]

    assert "row_id" in occurrence
    assert "pattern_string" in occurrence
    assert "start_q" in occurrence
    assert "end_q" in occurrence
    assert "duration" in occurrence
    assert "color" in occurrence
    assert isinstance(occurrence["pattern"], list)
    assert occurrence["end_q"] > occurrence["start_q"]
    assert occurrence["duration"] > 0
    assert occurrence["color"].startswith("#")


def test_plot_melodic_ngram_heatmap_custom_top_n():
    """The selected pattern count should follow the requested top_n."""
    result = plot_melodic_ngram_heatmap("Bach_BWV_0772.mei", top_n=3)
    structured = result.structured_content

    assert len(structured["patterns"]) == 3
    assert structured["patterns"][0]["count"] >= structured["patterns"][-1]["count"]


def test_plot_melodic_ngram_heatmap_invalid_file():
    """Invalid filenames should raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        plot_melodic_ngram_heatmap("nonexistent_file.mei")
