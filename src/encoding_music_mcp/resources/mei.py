"""MEI file resources for MCP server."""

import json
from pathlib import Path

from ..tools.helpers import get_mei_collections

__all__ = ["mei_collections_list", "mei_file_content"]


def mei_collections_list() -> str:
    """List all available MEI file collections.

    Returns organised list of MEI files by collection (Bach, Bartók, Morley).
    """
    return json.dumps(get_mei_collections(), indent=2)


def mei_file_content(filename: str) -> str:
    """Get the content of a specific MEI file.

    Args:
        filename: Name of the MEI file (e.g., "Bach_BWV_0772.mei")

    Returns:
        The XML content of the MEI file
    """
    resources_dir = Path(__file__).parent.parent / "resources" / "mei_files"
    filepath = resources_dir / filename

    if not filepath.exists():
        raise FileNotFoundError(f"MEI file not found: {filename}")

    return filepath.read_text(encoding="utf-8")
