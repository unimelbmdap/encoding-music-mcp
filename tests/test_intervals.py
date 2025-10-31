"""Tests for MEI interval analysis tools."""

import pytest

from src.encoding_music_mcp.tools.intervals import (
    get_notes,
    get_melodic_intervals,
    get_harmonic_intervals,
    get_melodic_ngrams,
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
    assert isinstance(result["melodic_intervals"], str), "Melodic intervals should be a string"
    assert len(result["melodic_intervals"]) > 0, "Melodic intervals should not be empty"
    assert "Measure" in result["melodic_intervals"], "Should contain measure information"


def test_get_melodic_intervals_contains_intervals():
    """Test that melodic intervals contain expected interval notation."""
    result = get_melodic_intervals("Bach_BWV_0772.mei", kind="q")

    intervals_str = result["melodic_intervals"]

    # Should contain standard interval notation (P = Perfect, M = Major, m = minor)
    has_intervals = any(x in intervals_str for x in ["M2", "m2", "P4", "P5", "M3", "m3"])
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
    assert isinstance(result["harmonic_intervals"], str), "Harmonic intervals should be a string"
    assert len(result["harmonic_intervals"]) > 0, "Harmonic intervals should not be empty"


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

    # Check values
    assert result["filename"] == "Bach_BWV_0772.mei", "Filename should match input"
    assert result["n"] == 4, "Default n should be 4"

    # Check n-grams content
    assert isinstance(result["melodic_ngrams"], str), "Melodic n-grams should be a string"
    assert len(result["melodic_ngrams"]) > 0, "Melodic n-grams should not be empty"


def test_get_melodic_ngrams_custom_n():
    """Test melodic n-gram extraction with custom n value."""
    result = get_melodic_ngrams("Bach_BWV_0772.mei", n=3)

    # Check n value
    assert result["n"] == 3, "n should match input parameter"

    # Check n-grams content
    assert isinstance(result["melodic_ngrams"], str), "Melodic n-grams should be a string"
    assert len(result["melodic_ngrams"]) > 0, "Melodic n-grams should not be empty"


def test_get_melodic_ngrams_format():
    """Test that n-grams are formatted with underscore separators."""
    result = get_melodic_ngrams("Bach_BWV_0772.mei", n=4)

    ngrams_str = result["melodic_ngrams"]

    # Should contain underscore-separated patterns
    assert "_" in ngrams_str, "N-grams should use underscore separators"


def test_get_melodic_ngrams_different_n_values():
    """Test that different n values produce different results."""
    result_n3 = get_melodic_ngrams("Bach_BWV_0772.mei", n=3)
    result_n5 = get_melodic_ngrams("Bach_BWV_0772.mei", n=5)

    # Both should succeed
    assert result_n3["n"] == 3, "n=3 should be recorded"
    assert result_n5["n"] == 5, "n=5 should be recorded"

    # Results should be different (different n values produce different patterns)
    assert result_n3["melodic_ngrams"] != result_n5["melodic_ngrams"], \
        "Different n values should produce different results"


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
    assert len(result_melodic["melodic_intervals"]) > 0, "Melodic intervals should not be empty"
    assert len(result_harmonic["harmonic_intervals"]) > 0, "Harmonic intervals should not be empty"
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
    assert len(result_melodic["melodic_intervals"]) > 0, "Melodic intervals should not be empty"
    assert len(result_harmonic["harmonic_intervals"]) > 0, "Harmonic intervals should not be empty"
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
    assert result["filename"] == "Morley_1595_01_Go_ye_my_canzonettes.mei", "Filename should match input"

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
    assert "Morley" in cadences_str or "Thomas" in cadences_str, "Should contain composer name"


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
