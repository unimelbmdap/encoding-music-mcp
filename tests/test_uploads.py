"""Tests for user-supplied MEI registration."""

import asyncio
from pathlib import Path

import pytest

from src.encoding_music_mcp.tools.discovery import list_available_mei_files
from src.encoding_music_mcp.tools.helpers import get_mei_filepath, remove_uploaded_mei
from src.encoding_music_mcp.tools.intervals import get_notes
from src.encoding_music_mcp.tools.metadata import get_mei_metadata
from src.encoding_music_mcp.tools.notation import show_notation
from src.encoding_music_mcp.tools.uploads import (
    list_uploaded_mei_files,
    register_mei_file_from_path,
)


def _sample_mei_path() -> Path:
    return (
        Path(__file__).parent.parent
        / "src"
        / "encoding_music_mcp"
        / "resources"
        / "mei_files"
        / "Bach_BWV_0772.mei"
    )


@pytest.fixture
def uploaded_filename():
    filename = "Uploaded_Bach_Copy.mei"
    remove_uploaded_mei(filename)
    yield filename
    remove_uploaded_mei(filename)


def test_register_mei_file_from_path_uses_original_path(uploaded_filename):
    """Registered files resolve to their original path, not a cached copy."""
    source_path = _sample_mei_path()

    registration = asyncio.run(
        register_mei_file_from_path(str(source_path), uploaded_filename)
    )

    assert registration["registered"] is True
    assert registration["filename"] == uploaded_filename
    assert registration["source_path"] == str(source_path.resolve())

    resolved_path = get_mei_filepath(uploaded_filename)
    assert resolved_path == source_path.resolve()


def test_uploaded_files_are_discoverable(uploaded_filename):
    """Discovery should expose registered uploads without recategorising built-ins."""
    asyncio.run(register_mei_file_from_path(str(_sample_mei_path()), uploaded_filename))

    uploads = list_uploaded_mei_files()
    assert uploaded_filename in uploads["uploaded_mei_files"]

    available = list_available_mei_files()
    assert uploaded_filename in available["uploaded_mei_files"]
    assert uploaded_filename in available["all_files"]
    assert len(available["bach_inventions"]) == 15
    assert len(available["bartok_mikrokosmos"]) == 19
    assert len(available["morley_canzonets"]) == 12


def test_register_mei_file_from_path_makes_local_file_available(uploaded_filename):
    """A local path exposed by the user should register without client-side XML."""
    source_path = _sample_mei_path()

    registration = asyncio.run(
        register_mei_file_from_path(str(source_path), uploaded_filename)
    )

    assert registration["registered"] is True
    assert registration["filename"] == uploaded_filename
    assert registration["source_path"] == str(source_path.resolve())

    metadata = get_mei_metadata(uploaded_filename)
    assert "Invention" in metadata["title"]

    notes = get_notes(uploaded_filename)
    assert "Measure" in notes["notes"]

    notation = asyncio.run(show_notation(uploaded_filename))
    assert notation.structured_content["filename"] == uploaded_filename
    assert notation.structured_content["svg"].startswith("<svg")


def test_register_mei_file_from_path_requires_path_or_context():
    """Without an explicit path, elicitation needs MCP context."""
    with pytest.raises(ValueError, match="file_path is required"):
        asyncio.run(register_mei_file_from_path())


def test_register_mei_file_from_path_rejects_missing_file(uploaded_filename):
    """Missing local files should fail before registration."""
    with pytest.raises(FileNotFoundError):
        asyncio.run(register_mei_file_from_path("missing-file.mei", uploaded_filename))


def test_register_mei_file_from_path_rejects_invalid_content(tmp_path, uploaded_filename):
    """Only well-formed MEI XML files should be registered."""
    invalid_xml = tmp_path / "invalid.mei"
    invalid_xml.write_text("not xml", encoding="utf-8")
    wrong_root = tmp_path / "wrong_root.mei"
    wrong_root.write_text("<score></score>", encoding="utf-8")

    with pytest.raises(ValueError, match="well-formed XML"):
        asyncio.run(register_mei_file_from_path(str(invalid_xml), uploaded_filename))

    with pytest.raises(ValueError, match="root element"):
        asyncio.run(register_mei_file_from_path(str(wrong_root), uploaded_filename))


def test_register_mei_file_from_path_rejects_unsafe_filename(uploaded_filename):
    """Uploaded filenames must be simple MEI basenames."""
    with pytest.raises(ValueError, match="simple basename"):
        asyncio.run(register_mei_file_from_path(str(_sample_mei_path()), "../bad.mei"))

    with pytest.raises(ValueError, match="end with .mei"):
        asyncio.run(register_mei_file_from_path(str(_sample_mei_path()), "bad.xml"))


def test_remove_uploaded_mei(uploaded_filename):
    """Registered uploads can be removed from the session registry."""
    asyncio.run(register_mei_file_from_path(str(_sample_mei_path()), uploaded_filename))

    result = remove_uploaded_mei(uploaded_filename)
    assert result is True
    assert uploaded_filename not in list_uploaded_mei_files()["uploaded_mei_files"]
