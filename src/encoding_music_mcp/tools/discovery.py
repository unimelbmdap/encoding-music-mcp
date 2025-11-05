"""MEI file discovery tool."""

from .helpers import get_mei_collections

__all__ = ["list_available_mei_files"]


def list_available_mei_files() -> dict[str, list[str]]:
    """List all built-in MEI files available as resources.

    Returns:
        Dictionary with categorised lists of available MEI files
    """
    return get_mei_collections()
