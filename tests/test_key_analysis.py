"""Tests for MEI key analysis tool."""

import pytest

from src.encoding_music_mcp.tools.key_analysis import analyze_key


def test_analyze_key_bach():
    """Test key analysis for Bach BWV 0772 (known to be in C major)."""
    result = analyze_key("Bach_BWV_0772.mei")

    # Check return type
    assert isinstance(result, dict), "Result should be a dictionary"

    # Check expected keys
    assert "Key Name" in result, "Result should contain 'Key Name'"
    assert "Confidence Factor" in result, "Result should contain 'Confidence Factor'"

    # Check key name type
    assert isinstance(result["Key Name"], str), "Key Name should be a string"

    # Check confidence factor
    assert isinstance(result["Confidence Factor"], (int, float)), (
        "Confidence Factor should be numeric"
    )
    assert 0.0 <= result["Confidence Factor"] <= 1.0, (
        "Confidence Factor should be between 0 and 1"
    )

    # For BWV 772, we expect C major
    assert "C" in result["Key Name"], "BWV 772 should be in C major"
    assert "major" in result["Key Name"], "BWV 772 should be in major key"


def test_analyze_key_confidence():
    """Test that confidence factor is reasonable for well-defined keys."""
    result = analyze_key("Bach_BWV_0772.mei")

    # Bach's inventions are tonal pieces, should have high confidence
    assert result["Confidence Factor"] > 0.5, (
        "Well-defined tonal piece should have confidence > 0.5"
    )


def test_analyze_key_bartok():
    """Test key analysis for Bartók piece."""
    result = analyze_key("Bartok_Mikrokosmos_022.mei")

    # Check return structure
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "Key Name" in result, "Result should contain 'Key Name'"
    assert "Confidence Factor" in result, "Result should contain 'Confidence Factor'"

    # Check types
    assert isinstance(result["Key Name"], str), "Key Name should be a string"
    assert isinstance(result["Confidence Factor"], (int, float)), (
        "Confidence Factor should be numeric"
    )


def test_analyze_key_morley():
    """Test key analysis for Morley piece."""
    result = analyze_key("Morley_1595_01_Go_ye_my_canzonettes.mei")

    # Check return structure
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "Key Name" in result, "Result should contain 'Key Name'"
    assert "Confidence Factor" in result, "Result should contain 'Confidence Factor'"

    # Check types
    assert isinstance(result["Key Name"], str), "Key Name should be a string"
    assert isinstance(result["Confidence Factor"], (int, float)), (
        "Confidence Factor should be numeric"
    )


def test_analyze_key_invalid_file():
    """Test that invalid filename raises appropriate error."""
    with pytest.raises(FileNotFoundError):
        analyze_key("nonexistent_file.mei")


def test_analyze_key_format():
    """Test that key name follows expected format."""
    result = analyze_key("Bach_BWV_0772.mei")

    key_name = result["Key Name"]

    # Should contain either "major" or "minor"
    assert "major" in key_name or "minor" in key_name, (
        "Key name should specify major or minor"
    )

    # Should start with a letter (the tonic)
    assert key_name[0].isalpha(), "Key name should start with a letter"
