"""Shared helper functions for tools."""

from pathlib import Path

__all__ = ["get_mei_filepath", "get_mei_collections"]


def get_mei_filepath(filename: str) -> Path:
    """Convert an MEI filename to its full filepath in the resources directory.

    Args:
        filename: Name of the MEI file (e.g., "Bach_BWV_0772.mei")

    Returns:
        Path object pointing to the file in the resources directory
    """
    resources_dir = Path(__file__).parent.parent / "resources" / "mei_files"
    return resources_dir / filename


def get_mei_collections() -> dict[str, list[str]]:
    """Get categorised MEI collections (shared by tools and resources).

    Returns:
        Dictionary with categorised lists of available MEI files:
        - bach_inventions: List of Bach files
        - bartok_mikrokosmos: List of Bartók files
        - morley_canzonets: List of Morley files
        - all_files: Complete list of all MEI files
    """
    resources_dir = Path(__file__).parent.parent / "resources" / "mei_files"

    if not resources_dir.exists():
        return {"all_files": []}

    all_files = sorted([f.name for f in resources_dir.glob("*.mei")])

    # Categorise files
    bach = [f for f in all_files if f.startswith("Bach")]
    bartok = [f for f in all_files if f.startswith("Bartok")]
    morley = [f for f in all_files if f.startswith("Morley")]

    return {
        "bach_inventions": bach,
        "bartok_mikrokosmos": bartok,
        "morley_canzonets": morley,
        "all_files": all_files,
    }
