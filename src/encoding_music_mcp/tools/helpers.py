"""Shared helper functions for tools."""

import xml.etree.ElementTree as ET
from pathlib import Path
from threading import Lock
from typing import Any

__all__ = [
    "get_mei_filepath",
    "get_mei_collections",
    "register_uploaded_mei_from_path",
    "remove_uploaded_mei",
    "get_uploaded_mei_files",
]

_UPLOADS: dict[str, dict[str, Any]] = {}
_UPLOADS_LOCK = Lock()


def _builtin_mei_dir() -> Path:
    return Path(__file__).parent.parent / "resources" / "mei_files"


def _normalise_uploaded_filename(filename: str) -> str:
    """Return a safe MEI basename for uploaded content."""
    raw_filename = filename.strip()
    if not raw_filename:
        raise ValueError("filename is required")
    if (
        raw_filename in {".", ".."}
        or "/" in raw_filename
        or "\\" in raw_filename
        or Path(raw_filename).name != raw_filename
    ):
        raise ValueError("filename must be a simple basename")
    candidate = Path(raw_filename).name
    if not candidate.lower().endswith(".mei"):
        raise ValueError("filename must end with .mei")
    return candidate


def _validate_mei_file(path: Path) -> ET.Element:
    """Parse and validate that a local path points to an MEI XML document."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"MEI file is not well-formed XML: {exc}") from exc

    local_name = root.tag.rsplit("}", 1)[-1]
    if local_name != "mei":
        raise ValueError("MEI file must have an <mei> root element")
    return root


def register_uploaded_mei_from_path(
    file_path: str,
    filename: str | None = None,
) -> dict[str, Any]:
    """Register a local MEI path exposed by the user."""
    source_path = Path(file_path).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"MEI file not found: {file_path}")
    if not source_path.is_file():
        raise ValueError(f"MEI path is not a file: {file_path}")
    _validate_mei_file(source_path)

    safe_filename = _normalise_uploaded_filename(filename or source_path.name)

    with _UPLOADS_LOCK:
        _UPLOADS[safe_filename] = {
            "filename": safe_filename,
            "path": source_path,
        }

    return {
        "filename": safe_filename,
        "source_path": str(source_path),
    }


def remove_uploaded_mei(filename: str) -> bool:
    """Remove an uploaded MEI registration from this server session."""
    safe_filename = _normalise_uploaded_filename(filename)
    with _UPLOADS_LOCK:
        entry = _UPLOADS.pop(safe_filename, None)

    return entry is not None


def get_uploaded_mei_files() -> list[str]:
    """Return filenames currently registered from user-uploaded MEI content."""
    with _UPLOADS_LOCK:
        return sorted(
            filename
            for filename, entry in _UPLOADS.items()
            if Path(entry["path"]).exists()
        )


def get_mei_filepath(filename: str) -> Path:
    """Convert an MEI filename to a registered upload or built-in file path.

    Args:
        filename: Name of the MEI file (e.g., "Bach_BWV_0772.mei")

    Returns:
        Path object pointing to a registered upload or built-in resource
    """
    safe_filename = Path(filename).name
    with _UPLOADS_LOCK:
        upload_entry = _UPLOADS.get(safe_filename)
        if upload_entry and Path(upload_entry["path"]).exists():
            return Path(upload_entry["path"])

    return _builtin_mei_dir() / safe_filename


def get_mei_collections() -> dict[str, list[str]]:
    """Get categorised MEI collections (shared by tools and resources).

    Returns:
        Dictionary with categorised lists of available MEI files:
        - bach_inventions: List of Bach files
        - bartok_mikrokosmos: List of Bartók files
        - morley_canzonets: List of Morley files
        - all_files: Complete list of all MEI files
    """
    resources_dir = _builtin_mei_dir()

    if not resources_dir.exists():
        return {"all_files": []}

    built_in_files = sorted([f.name for f in resources_dir.glob("*.mei")])
    uploaded_files = get_uploaded_mei_files()
    all_files = sorted(set(built_in_files + uploaded_files))

    # Categorise files
    bach = [f for f in built_in_files if f.startswith("Bach")]
    bartok = [f for f in built_in_files if f.startswith("Bartok")]
    morley = [f for f in built_in_files if f.startswith("Morley")]

    return {
        "bach_inventions": bach,
        "bartok_mikrokosmos": bartok,
        "morley_canzonets": morley,
        "uploaded_mei_files": uploaded_files,
        "all_files": all_files,
    }
