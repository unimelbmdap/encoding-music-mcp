"""MEI file discovery tool."""

from pathlib import Path

__all__ = ["list_available_mei_files"]


def list_available_mei_files() -> dict[str, list[str]]:
    """List all built-in MEI files available as resources.

    Returns:
        Dictionary with categorized lists of available MEI files
    """
    resources_dir = Path(__file__).parent.parent / "resources"

    if not resources_dir.exists():
        return {"all_files": []}

    all_files = sorted([f.name for f in resources_dir.glob("*.mei")])

    # Categorize files
    bach = [f for f in all_files if f.startswith("Bach")]
    bartok = [f for f in all_files if f.startswith("Bartok")]
    morley = [f for f in all_files if f.startswith("Morley")]

    return {
        "bach_inventions": bach,
        "bartok_mikrokosmos": bartok,
        "morley_canzonets": morley,
        "all_files": all_files,
    }
