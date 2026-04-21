"""Tests for MEI interval analysis tools."""

import pytest

from src.encoding_music_mcp.tools.intervals import (
    get_notes,
    get_melodic_intervals,
    get_harmonic_intervals,
    get_melodic_ngrams,
    count_melodic_ngrams,
    get_melodic_ngram_matches,
    get_first_occur_melodic_ngrams,
    get_cadences,
)


def test_get_notes_bach():
    """Test note extraction for Bach BWV 0772."""
    result = get_notes("Bach_BWV_0772.mei")

    # Check return type
    assert isinstance(result, dict), "Result should be a dictionary"

    # Check expected keys
    assert "filename" in result, "Result should contain 'filename'"
    assert "notes" in result, "Result should contain 'notes'"

    # Check filename matches
    assert result["filename"] == "Bach_BWV_0772.mei", "Filename should match input"

    # Check notes content
    assert isinstance(result["notes"], str), "Notes should be a string"
    assert len(result["notes"]) > 0, "Notes should not be empty"
    assert "Measure" in result["notes"], "Notes should contain measure information"
    assert "Beat" in result["notes"], "Notes should contain beat information"


def test_get_notes_contains_pitches():
    """Test that notes contain expected pitch names."""
    result = get_notes("Bach_BWV_0772.mei")

    notes_str = result["notes"]

    # Should contain some common note names
    # Bach BWV 772 starts with C, D, E, F...
    assert "C" in notes_str or "D" in notes_str, "Should contain note names"


def test_get_melodic_intervals_bach():
    """Test melodic interval extraction for Bach BWV 0772."""
    result = get_melodic_intervals("Bach_BWV_0772.mei")

    # Check return type
    assert isinstance(result, dict), "Result should be a dictionary"

    # Check expected keys
    assert "filename" in result, "Result should contain 'filename'"
    assert "melodic_intervals" in result, "Result should contain 'melodic_intervals'"

    # Check filename matches
    assert result["filename"] == "Bach_BWV_0772.mei", "Filename should match input"

    # Check intervals content
    assert isinstance(result["melodic_intervals"], str), (
        "Melodic intervals should be a string"
    )
    assert len(result["melodic_intervals"]) > 0, "Melodic intervals should not be empty"
    assert "Measure" in result["melodic_intervals"], (
        "Should contain measure information"
    )


def test_get_melodic_intervals_contains_intervals():
    """Test that melodic intervals contain expected interval notation."""
    result = get_melodic_intervals("Bach_BWV_0772.mei", kind="q")

    intervals_str = result["melodic_intervals"]

    # Should contain standard interval notation (P = Perfect, M = Major, m = minor)
    has_intervals = any(
        x in intervals_str for x in ["M2", "m2", "P4", "P5", "M3", "m3"]
    )
    assert has_intervals, "Should contain standard interval notation"


def test_get_harmonic_intervals_bach():
    """Test harmonic interval extraction for Bach BWV 0772."""
    result = get_harmonic_intervals("Bach_BWV_0772.mei")

    # Check return type
    assert isinstance(result, dict), "Result should be a dictionary"

    # Check expected keys
    assert "filename" in result, "Result should contain 'filename'"
    assert "harmonic_intervals" in result, "Result should contain 'harmonic_intervals'"

    # Check filename matches
    assert result["filename"] == "Bach_BWV_0772.mei", "Filename should match input"

    # Check intervals content
    assert isinstance(result["harmonic_intervals"], str), (
        "Harmonic intervals should be a string"
    )
    assert len(result["harmonic_intervals"]) > 0, (
        "Harmonic intervals should not be empty"
    )


def test_get_harmonic_intervals_contains_intervals():
    """Test that harmonic intervals contain expected interval notation."""
    result = get_harmonic_intervals("Bach_BWV_0772.mei")

    intervals_str = result["harmonic_intervals"]

    # Should contain interval notation or voice pair indicators
    assert "Measure" in intervals_str, "Should contain measure information"
    # Harmonic intervals for two-part invention should show intervals between parts


def test_get_melodic_ngrams_default():
    """Test melodic n-gram extraction with default n=4."""
    result = get_melodic_ngrams("Bach_BWV_0772.mei")

    # Check return type
    assert isinstance(result, dict), "Result should be a dictionary"

    # Check expected keys
    assert "filename" in result, "Result should contain 'filename'"
    assert "n" in result, "Result should contain 'n'"
    assert "melodic_ngrams" in result, "Result should contain 'melodic_ngrams'"
    assert "include_note_ids" in result, "Result should record note-id inclusion mode"

    # Check values
    assert result["filename"] == "Bach_BWV_0772.mei", "Filename should match input"
    assert result["n"] == 4, "Default n should be 4"
    assert result["include_note_ids"] is False, "Note IDs should be omitted by default"

    # Check n-grams content
    assert isinstance(result["melodic_ngrams"], str), (
        "Melodic n-grams should be a string"
    )
    assert len(result["melodic_ngrams"]) > 0, "Melodic n-grams should not be empty"
    assert "melodic_ngram_note_ids" not in result, (
        "Default result should not eagerly include note IDs"
    )


def test_get_melodic_ngrams_include_note_ids():
    """Test that melodic n-grams can optionally expose note-id matches."""
    result = get_melodic_ngrams("Bach_BWV_0772.mei", n=4, include_note_ids=True)

    matches = result["melodic_ngram_note_ids"]
    assert len(matches) > 0, "Should include note-id matches"

    match = matches[0]
    assert "pattern" in match
    assert "pattern_string" in match
    assert "column" in match
    assert "start_measure" in match
    assert "start_beat" in match
    assert "start_offset" in match
    assert "note_ids" in match

    assert isinstance(match["pattern"], list)
    assert len(match["pattern"]) == 4
    assert isinstance(match["pattern_string"], str)
    assert isinstance(match["column"], str)
    assert isinstance(match["start_measure"], float)
    assert isinstance(match["start_beat"], float)
    assert isinstance(match["start_offset"], float)
    assert isinstance(match["note_ids"], list)
    assert len(match["note_ids"]) == 5
    assert all(isinstance(note_id, str) for note_id in match["note_ids"])


def test_get_melodic_ngrams_format():
    """Test that n-grams are formatted with underscore separators."""
    result = get_melodic_ngrams("Bach_BWV_0772.mei", n=4)

    ngrams_str = result["melodic_ngrams"]

    assert "2_2_2_-3" in ngrams_str, "N-grams should use underscore separators"
    assert "2, 2, 2, -3" not in ngrams_str, "CSV should not keep comma-separated tuples"


def test_get_melodic_ngrams_custom_n():
    """Test melodic n-gram extraction with custom n value."""
    result = get_melodic_ngrams("Bach_BWV_0772.mei", n=3)

    # Check n value
    assert result["n"] == 3, "n should match input parameter"

    # Check n-grams content
    assert isinstance(result["melodic_ngrams"], str), (
        "Melodic n-grams should be a string"
    )
    assert len(result["melodic_ngrams"]) > 0, "Melodic n-grams should not be empty"


def test_get_melodic_ngrams_different_n_values():
    """Test that different n values produce different results."""
    result_n3 = get_melodic_ngrams("Bach_BWV_0772.mei", n=3)
    result_n5 = get_melodic_ngrams("Bach_BWV_0772.mei", n=5)

    # Both should succeed
    assert result_n3["n"] == 3, "n=3 should be recorded"
    assert result_n5["n"] == 5, "n=5 should be recorded"

    # Results should be different (different n values produce different patterns)
    assert result_n3["melodic_ngrams"] != result_n5["melodic_ngrams"], (
        "Different n values should produce different results"
    )


def test_count_melodic_ngrams_returns_ranked_counts():
    """Test that melodic n-gram counts are grouped and ranked by frequency."""
    result = count_melodic_ngrams("Bach_BWV_0772.mei", n=4)

    assert result["filename"] == "Bach_BWV_0772.mei"
    assert result["n"] == 4
    assert "pattern_counts" in result
    assert isinstance(result["pattern_counts"], list)
    assert len(result["pattern_counts"]) > 0

    first_pattern = result["pattern_counts"][0]
    assert "pattern" in first_pattern
    assert "pattern_string" in first_pattern
    assert "count" in first_pattern
    assert isinstance(first_pattern["pattern"], list)
    assert isinstance(first_pattern["pattern_string"], str)
    assert isinstance(first_pattern["count"], int)
    assert first_pattern["count"] >= result["pattern_counts"][-1]["count"]


def test_get_melodic_ngram_matches_groups_occurrences_by_pattern():
    """Test that melodic n-gram matches are keyed by pattern string."""
    result = get_melodic_ngram_matches("Bach_BWV_0772.mei", n=4, patterns=["2_2_2_-3"])

    assert result["filename"] == "Bach_BWV_0772.mei"
    assert result["patterns"] == ["2_2_2_-3"]
    assert "matches_by_pattern" in result
    assert list(result["matches_by_pattern"].keys()) == ["2_2_2_-3"]

    matches = result["matches_by_pattern"]["2_2_2_-3"]
    assert len(matches) > 0

    match = matches[0]
    assert "pattern" in match
    assert "column" in match
    assert "start_measure" in match
    assert "start_beat" in match
    assert "start_offset" in match
    assert "note_ids" in match
    assert match["pattern"] == ["2", "2", "2", "-3"]
    assert isinstance(match["note_ids"], list)


def test_get_first_occur_melodic_ngrams_bach():
    """Test first-occurrence melodic n-gram extraction for Bach BWV 0772."""
    result = get_first_occur_melodic_ngrams("Bach_BWV_0772.mei")

    assert isinstance(result, dict), "Result should be a dictionary"
    assert result["filename"] == "Bach_BWV_0772.mei"
    assert result["n"] == 4
    assert result["kind"] == "d"
    assert result["combine_unisons"] is True
    assert result["compound"] is False
    assert "patterns" in result, "Result should contain 'patterns'"
    assert isinstance(result["patterns"], list), "Patterns should be a list"
    assert len(result["patterns"]) > 0, "Patterns should not be empty"


def test_get_first_occur_melodic_ngrams_pattern_record_shape():
    """Test that pattern records contain the expected fields and value types."""
    result = get_first_occur_melodic_ngrams("Bach_BWV_0772.mei")
    pattern = result["patterns"][0]

    assert "pattern" in pattern
    assert "start_q" in pattern
    assert "duration" in pattern
    assert "end_q" in pattern
    assert "column" in pattern

    assert isinstance(pattern["pattern"], list), "Pattern should be a list"
    assert len(pattern["pattern"]) == result["n"], "Pattern length should match n"
    assert isinstance(pattern["start_q"], float), "start_q should be a float"
    assert isinstance(pattern["duration"], float), "duration should be a float"
    assert isinstance(pattern["end_q"], float), "end_q should be a float"
    assert isinstance(pattern["column"], str), "column should be a string"
    assert pattern["end_q"] > pattern["start_q"], "end_q should be greater than start_q"


def test_get_first_occur_melodic_ngrams_custom_options():
    """Test that custom parameters are recorded in the result."""
    result = get_first_occur_melodic_ngrams(
        "Bach_BWV_0772.mei",
        n=3,
        kind="q",
        combine_unisons=False,
        compound=True,
    )

    assert result["n"] == 3
    assert result["kind"] == "q"
    assert result["combine_unisons"] is False
    assert result["compound"] is True
    assert len(result["patterns"]) > 0, "Custom configuration should still return patterns"


def test_intervals_invalid_file():
    """Test that all interval tools handle invalid filenames appropriately."""
    with pytest.raises(FileNotFoundError):
        get_notes("nonexistent_file.mei")

    with pytest.raises(FileNotFoundError):
        get_melodic_intervals("nonexistent_file.mei")

    with pytest.raises(FileNotFoundError):
        get_harmonic_intervals("nonexistent_file.mei")

    with pytest.raises(FileNotFoundError):
        get_melodic_ngrams("nonexistent_file.mei")

    with pytest.raises(FileNotFoundError):
        get_first_occur_melodic_ngrams("nonexistent_file.mei")

    with pytest.raises(FileNotFoundError):
        get_cadences("nonexistent_file.mei")


def test_intervals_bartok():
    """Test that interval tools work with Bartók pieces."""
    result_notes = get_notes("Bartok_Mikrokosmos_022.mei")
    result_melodic = get_melodic_intervals("Bartok_Mikrokosmos_022.mei")
    result_harmonic = get_harmonic_intervals("Bartok_Mikrokosmos_022.mei")
    result_ngrams = get_melodic_ngrams("Bartok_Mikrokosmos_022.mei")

    # All should return valid dictionaries
    assert isinstance(result_notes, dict), "Notes result should be a dictionary"
    assert isinstance(result_melodic, dict), "Melodic result should be a dictionary"
    assert isinstance(result_harmonic, dict), "Harmonic result should be a dictionary"
    assert isinstance(result_ngrams, dict), "N-grams result should be a dictionary"

    # All should have content
    assert len(result_notes["notes"]) > 0, "Notes should not be empty"
    assert len(result_melodic["melodic_intervals"]) > 0, (
        "Melodic intervals should not be empty"
    )
    assert len(result_harmonic["harmonic_intervals"]) > 0, (
        "Harmonic intervals should not be empty"
    )
    assert len(result_ngrams["melodic_ngrams"]) > 0, "N-grams should not be empty"


def test_intervals_morley():
    """Test that interval tools work with Morley pieces."""
    result_notes = get_notes("Morley_1595_01_Go_ye_my_canzonettes.mei")
    result_melodic = get_melodic_intervals("Morley_1595_01_Go_ye_my_canzonettes.mei")
    result_harmonic = get_harmonic_intervals("Morley_1595_01_Go_ye_my_canzonettes.mei")
    result_ngrams = get_melodic_ngrams("Morley_1595_01_Go_ye_my_canzonettes.mei")

    # All should return valid dictionaries
    assert isinstance(result_notes, dict), "Notes result should be a dictionary"
    assert isinstance(result_melodic, dict), "Melodic result should be a dictionary"
    assert isinstance(result_harmonic, dict), "Harmonic result should be a dictionary"
    assert isinstance(result_ngrams, dict), "N-grams result should be a dictionary"

    # All should have content
    assert len(result_notes["notes"]) > 0, "Notes should not be empty"
    assert len(result_melodic["melodic_intervals"]) > 0, (
        "Melodic intervals should not be empty"
    )
    assert len(result_harmonic["harmonic_intervals"]) > 0, (
        "Harmonic intervals should not be empty"
    )
    assert len(result_ngrams["melodic_ngrams"]) > 0, "N-grams should not be empty"


def test_get_cadences_morley():
    """Test cadence extraction for Morley Go ye my canzonettes."""
    result = get_cadences("Morley_1595_01_Go_ye_my_canzonettes.mei")

    # Check return type
    assert isinstance(result, dict), "Result should be a dictionary"

    # Check expected keys
    assert "filename" in result, "Result should contain 'filename'"
    assert "cadences" in result, "Result should contain 'cadences'"

    # Check filename matches
    assert result["filename"] == "Morley_1595_01_Go_ye_my_canzonettes.mei", (
        "Filename should match input"
    )

    # Check cadences content
    assert isinstance(result["cadences"], str), "Cadences should be a string"
    assert len(result["cadences"]) > 0, "Cadences should not be empty"


def test_get_cadences_contains_expected_columns():
    """Test that cadences contain expected column names."""
    result = get_cadences("Morley_1595_01_Go_ye_my_canzonettes.mei")

    cadences_str = result["cadences"]

    # Should contain expected column names
    assert "Composer" in cadences_str, "Should contain Composer column"
    assert "Title" in cadences_str, "Should contain Title column"
    assert "Measure" in cadences_str, "Should contain Measure column"
    assert "Beat" in cadences_str, "Should contain Beat column"
    assert "Progress" in cadences_str, "Should contain Progress column"
    assert "CadType" in cadences_str, "Should contain CadType column"
    assert "Tone" in cadences_str, "Should contain Tone column"
    assert "CVFs" in cadences_str, "Should contain CVFs column"


def test_get_cadences_contains_metadata():
    """Test that cadences contain composer and title metadata."""
    result = get_cadences("Morley_1595_01_Go_ye_my_canzonettes.mei")

    cadences_str = result["cadences"]

    # Should contain composer and title information
    assert "Morley" in cadences_str or "Thomas" in cadences_str, (
        "Should contain composer name"
    )


def test_get_cadences_invalid_file():
    """Test that get_cadences handles invalid filenames appropriately."""
    with pytest.raises(FileNotFoundError):
        get_cadences("nonexistent_file.mei")


def test_get_cadences_multiple_pieces():
    """Test that cadence extraction works with multiple Renaissance pieces."""
    result1 = get_cadences("Morley_1595_01_Go_ye_my_canzonettes.mei")
    result2 = get_cadences("Morley_1595_07_Leave_now_mine_eyes.mei")

    # Both should return valid dictionaries
    assert isinstance(result1, dict), "First result should be a dictionary"
    assert isinstance(result2, dict), "Second result should be a dictionary"

    # Both should have content
    assert len(result1["cadences"]) > 0, "First piece should have cadences"
    assert len(result2["cadences"]) > 0, "Second piece should have cadences"

    # Filenames should match
    assert result1["filename"] == "Morley_1595_01_Go_ye_my_canzonettes.mei"
    assert result2["filename"] == "Morley_1595_07_Leave_now_mine_eyes.mei"


def test_get_cadences_non_renaissance_music():
    """Test that cadence detection handles non-Renaissance music gracefully."""
    # Bach is Baroque, not Renaissance - cadence detection may not work
    result = get_cadences("Bach_BWV_0772.mei")

    # Should return valid dictionary
    assert isinstance(result, dict), "Result should be a dictionary"

    # Should have expected keys
    assert "filename" in result, "Result should contain 'filename'"
    assert "cadences" in result, "Result should contain 'cadences'"

    # Filename should match
    assert result["filename"] == "Bach_BWV_0772.mei"

    # Should contain an error message or "No cadences found"
    cadences_str = result["cadences"]
    assert isinstance(cadences_str, str), "Cadences should be a string"
    # Should indicate the tool is optimised for Renaissance music or no cadences found
    is_valid_response = (
        "not supported" in cadences_str.lower()
        or "no cadences" in cadences_str.lower()
        or "renaissance" in cadences_str.lower()
    )
    assert is_valid_response, (
        "Should indicate limitation or no cadences for non-Renaissance music"
    )
