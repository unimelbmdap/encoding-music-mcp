"""Tests for MEI metadata extraction tool."""

import pytest

from src.encoding_music_mcp.tools.metadata import get_mei_metadata


def test_get_mei_metadata_bach():
    """Test metadata extraction for Bach BWV 0772."""
    result = get_mei_metadata("Bach_BWV_0772.mei")

    # Check return type
    assert isinstance(result, dict), "Result should be a dictionary"

    # Check expected keys exist
    expected_keys = [
        "title",
        "composer",
        "mei_editors",
        "xml_editors",
        "analysts",
        "publication_date",
    ]
    for key in expected_keys:
        assert key in result, f"Result should contain '{key}' key"

    # Check specific values for this piece
    assert "Invention" in result["title"], "Title should mention 'Invention'"
    assert "Bach" in result["composer"], "Composer should be Bach"

    # Check that lists are actually lists
    assert isinstance(result["mei_editors"], list), "mei_editors should be a list"
    assert isinstance(result["xml_editors"], list), "xml_editors should be a list"
    assert isinstance(result["analysts"], list), "analysts should be a list"


def test_get_mei_metadata_bartok():
    """Test metadata extraction for Bartók piece."""
    result = get_mei_metadata("Bartok_Mikrokosmos_022.mei")

    # Check return type
    assert isinstance(result, dict), "Result should be a dictionary"

    # Check composer
    assert "Bartók" in result["composer"] or "Bartok" in result["composer"], (
        "Composer should be Bartók"
    )

    # Check title exists and is not empty
    assert result["title"], "Title should not be empty"


def test_get_mei_metadata_morley():
    """Test metadata extraction for Morley piece."""
    result = get_mei_metadata("Morley_1595_01_Go_ye_my_canzonettes.mei")

    # Check return type
    assert isinstance(result, dict), "Result should be a dictionary"

    # Check composer
    assert "Morley" in result["composer"], "Composer should be Morley"

    # Check title exists
    assert result["title"], "Title should not be empty"


def test_get_mei_metadata_invalid_file():
    """Test that invalid filename raises appropriate error."""
    with pytest.raises(FileNotFoundError):
        get_mei_metadata("nonexistent_file.mei")


def test_get_mei_metadata_return_structure():
    """Test that all metadata fields are present and have correct types."""
    result = get_mei_metadata("Bach_BWV_0772.mei")

    # Title should be string
    assert isinstance(result["title"], str), "title should be a string"

    # Composer should be string
    assert isinstance(result["composer"], str), "composer should be a string"

    # Lists should be lists (even if empty)
    assert isinstance(result["mei_editors"], list), "mei_editors should be a list"
    assert isinstance(result["xml_editors"], list), "xml_editors should be a list"
    assert isinstance(result["analysts"], list), "analysts should be a list"

    # Publication date should be string or None
    assert isinstance(result["publication_date"], (str, type(None))), (
        "publication_date should be string or None"
    )
