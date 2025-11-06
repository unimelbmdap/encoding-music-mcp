"""Tests for MEI file discovery tool."""

from src.encoding_music_mcp.tools.discovery import list_available_mei_files


def test_list_available_mei_files():
    """Test that list_available_mei_files returns expected structure."""
    result = list_available_mei_files()

    # Check return type
    assert isinstance(result, dict), "Result should be a dictionary"

    # Check required keys
    assert "bach_inventions" in result, "Should include bach_inventions"
    assert "bartok_mikrokosmos" in result, "Should include bartok_mikrokosmos"
    assert "morley_canzonets" in result, "Should include morley_canzonets"
    assert "all_files" in result, "Should include all_files"

    # Check that each category is a list
    assert isinstance(result["bach_inventions"], list), (
        "bach_inventions should be a list"
    )
    assert isinstance(result["bartok_mikrokosmos"], list), (
        "bartok_mikrokosmos should be a list"
    )
    assert isinstance(result["morley_canzonets"], list), (
        "morley_canzonets should be a list"
    )
    assert isinstance(result["all_files"], list), "all_files should be a list"

    # Check expected counts
    assert len(result["bach_inventions"]) == 15, "Should have 15 Bach inventions"
    assert len(result["bartok_mikrokosmos"]) == 19, "Should have 19 Bartók pieces"
    assert len(result["morley_canzonets"]) == 12, "Should have 12 Morley canzonets"
    assert len(result["all_files"]) == 46, "Should have 46 total files"

    # Check that all_files contains all individual files
    all_combined = (
        result["bach_inventions"]
        + result["bartok_mikrokosmos"]
        + result["morley_canzonets"]
    )
    assert set(all_combined) == set(result["all_files"]), (
        "all_files should match combined list"
    )


def test_bach_inventions_naming():
    """Test that Bach inventions follow expected naming convention."""
    result = list_available_mei_files()

    for filename in result["bach_inventions"]:
        assert filename.startswith("Bach_BWV_"), (
            f"{filename} should start with 'Bach_BWV_'"
        )
        assert filename.endswith(".mei"), f"{filename} should end with '.mei'"


def test_bartok_naming():
    """Test that Bartók files follow expected naming convention."""
    result = list_available_mei_files()

    for filename in result["bartok_mikrokosmos"]:
        assert filename.startswith("Bartok_Mikrokosmos_"), (
            f"{filename} should start with 'Bartok_Mikrokosmos_'"
        )
        assert filename.endswith(".mei"), f"{filename} should end with '.mei'"


def test_morley_naming():
    """Test that Morley files follow expected naming convention."""
    result = list_available_mei_files()

    for filename in result["morley_canzonets"]:
        assert filename.startswith("Morley_"), f"{filename} should start with 'Morley_'"
        assert filename.endswith(".mei"), f"{filename} should end with '.mei'"
