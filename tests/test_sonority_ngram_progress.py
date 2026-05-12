"""Tests for sonority n-gram progress visualisation."""

import pytest

from src.encoding_music_mcp.tools.visualisation.sonority_ngram_progress import (
    plot_sonority_ngram_progress,
)


def test_plot_sonority_ngram_progress_single_score():
    """Single-score view should expose rows, occurrences, and score metadata."""
    result = plot_sonority_ngram_progress("Bartok_Mikrokosmos_022.mei", n=4)
    structured = result.structured_content

    assert structured is not None
    assert structured["filename"] == "Bartok_Mikrokosmos_022.mei"
    assert structured["filenames"] == ["Bartok_Mikrokosmos_022.mei"]
    assert structured["score_count"] == 1
    assert structured["n"] == 4
    assert structured["kind"] == "low_line"
    assert structured["directed"] is True
    assert structured["compound"] is True
    assert structured["sort"] is False
    assert structured["x_min"] == 0.0
    assert structured["x_max"] == 1.0
    assert len(structured["scores"]) == 1
    assert len(structured["rows"]) > 0
    assert len(structured["occurrences"]) > 0


def test_plot_sonority_ngram_progress_occurrence_shape():
    """Occurrence records should link back to rendered rows and normalized progress."""
    result = plot_sonority_ngram_progress("Bartok_Mikrokosmos_022.mei", n=4)
    structured = result.structured_content
    row_ids = {row["id"] for row in structured["rows"]}
    occurrence = structured["occurrences"][0]

    assert occurrence["row_id"] in row_ids
    assert occurrence["filename"] == "Bartok_Mikrokosmos_022.mei"
    assert occurrence["voice_pair"] == "Low_Sonority"
    assert isinstance(occurrence["pattern"], list)
    assert occurrence["pattern_string"]
    assert isinstance(occurrence["start_q"], float)
    assert 0.0 <= occurrence["progress"] <= 1.0
    assert occurrence["count_in_score"] >= 1
    assert occurrence["color"].startswith("#")


def test_plot_sonority_ngram_progress_multiple_scores():
    """Multiple-score view should keep first-introduced rows by score group."""
    result = plot_sonority_ngram_progress(
        filenames=["Bartok_Mikrokosmos_022.mei", "Morley_1595_01_Go_ye_my_canzonettes.mei"],
        n=4,
    )
    structured = result.structured_content

    assert structured["filenames"] == [
        "Bartok_Mikrokosmos_022.mei",
        "Morley_1595_01_Go_ye_my_canzonettes.mei",
    ]
    assert structured["score_count"] == 2
    assert len(structured["scores"]) == 2
    assert len(structured["rows"]) > 0
    assert len(structured["occurrences"]) > 0
    assert {row["score_index"] for row in structured["rows"]}.issubset({0, 1})
    assert {occurrence["score_index"] for occurrence in structured["occurrences"]}.issubset(
        {0, 1}
    )
    assert structured["scores"][0]["color"] != structured["scores"][1]["color"]


def test_plot_sonority_ngram_progress_text_summary():
    """Text fallback should give assistants enough detail to discuss the plot."""
    result = plot_sonority_ngram_progress("Bartok_Mikrokosmos_022.mei", n=4)
    text = result.content[0].text

    assert "Sonority n-gram progress scatter" in text
    assert "Occurrences span roughly" in text
    assert "Scores:" in text
    assert "Most recurring displayed patterns:" in text


def test_plot_sonority_ngram_progress_skips_missing_beat_strength_filter():
    """Scores with sonorities but no beat strengths should fall back explicitly."""
    result = plot_sonority_ngram_progress("Bach_BWV_0772.mei", n=4)
    structured = result.structured_content
    text = result.content[0].text

    assert len(structured["rows"]) > 0
    assert len(structured["occurrences"]) > 0
    assert structured["beat_strength_filter_applied"] is False
    assert structured["beat_strength_fallback_filenames"] == ["Bach_BWV_0772.mei"]
    assert "Beat-strength filtering was skipped" in structured["warnings"][0]
    assert "Warnings:" in text
    assert "Beat-strength filtering was skipped" in text


def test_plot_sonority_ngram_progress_rejects_unavailable_beat_strength_filter():
    """Explicit beat-strength filtering should fail when CRIM has no values."""
    with pytest.raises(ValueError, match="Cannot apply minimum_beat_strength"):
        plot_sonority_ngram_progress(
            "Bach_BWV_0772.mei",
            n=4,
            minimum_beat_strength=0.25,
        )


def test_plot_sonority_ngram_progress_invalid_n():
    """Invalid n-gram lengths should be rejected before analysis."""
    with pytest.raises(ValueError, match="n must be at least 1"):
        plot_sonority_ngram_progress("Bartok_Mikrokosmos_022.mei", n=0)


def test_plot_sonority_ngram_progress_invalid_file():
    """Invalid filenames should raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        plot_sonority_ngram_progress("nonexistent_file.mei")
