"""Shared helper functions for tools."""

from pathlib import Path

__all__ = ["get_mei_filepath"]


def get_mei_filepath(filename: str) -> Path:
    """Convert an MEI filename to its full filepath in the resources directory.

    Args:
        filename: Name of the MEI file (e.g., "Bach_BWV_0772.mei")

    Returns:
        Path object pointing to the file in the resources directory
    """
    resources_dir = Path(__file__).parent.parent / "resources"
    return resources_dir / filename
