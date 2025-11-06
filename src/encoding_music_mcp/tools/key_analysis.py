"""MEI key analysis tool using music21."""

from typing import Any

from music21 import converter

from .helpers import get_mei_filepath

__all__ = ["analyze_key"]


def analyze_key(filename: str) -> dict[str, Any]:
    """Analyze the key of a piece using music21.

    Returns the key name and a confidence factor based on music21's
    key analysis algorithm.

    Args:
        filename: Name of the MEI file (e.g., "Bach_BWV_0772.mei")

    Returns:
        Dictionary containing:
        - Key Name: The detected key (e.g., "C major", "a minor")
        - Confidence Factor: Correlation coefficient (0.0-1.0)
    """
    filepath = get_mei_filepath(filename)
    score = converter.parse(str(filepath))
    key_analysis = score.analyze("key")

    analysis_dict = {
        "Key Name": str(key_analysis),
        "Confidence Factor": key_analysis.correlationCoefficient,
    }

    return analysis_dict
