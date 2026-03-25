from typing import Any
from crim_intervals import importScore

from .helpers import get_mei_filepath


def _pattern_to_list(pattern: Any) -> list[Any] | Any:
    """Convert a tuple-based n-gram pattern to a JSON-friendly list.

    Args:
        pattern: Pattern value extracted from the CRIM Intervals dataframe.

    Returns:
        A list if the input is a tuple, otherwise the original value.
    """
    return list(pattern) if isinstance(pattern, tuple) else pattern


def get_first_occurrence_melodic_ngrams(
    filename: str, n: int = 4, kind: str = "d", combine_unisons: bool = True, compound: bool = False,
) -> dict[str, Any]:
    """Extract first-occurrence melodic n-gram patterns from an MEI file.

    This function computes melodic n-grams using CRIM Intervals, identifies the
    first occurrence of each unique pattern across all parts, and returns the
    playback boundaries for each pattern in quarter-note units.

    Args:
        filename: Name of the MEI file (e.g., "Bach_BWV_0772.mei").
        n: Length of the melodic n-grams (Default: 4).
        kind: Type of interval to calculate:
            - 'd' (default): diatonic intervals (e.g., 2, -3, 5)
            - 'c': chromatic intervals (e.g., 0, 2, -4)
            - 'q': diatonic with quality (e.g., 'M2', 'm3', 'P5')
            - 'z': zero-based diatonic intervals
        combine_unisons: Whether to combine unisons when extracting notes (Default: True).
        compound: Whether to use compound intervals (Default: False).

    Returns:
        Dictionary containing:
        - filename: The input filename
        - n: The n-gram length used
        - kind: The interval type used
        - combine_unisons: Whether unisons were combined
        - compound: Whether compound intervals were used
        - patterns: A list of first-occurrence pattern records, each containing:
            - pattern: The melodic n-gram as a list
            - start_q: Start position in quarter-note units
            - duration: Pattern duration in quarter-note units
            - end_q: End position in quarter-note units
            - column: Staff or part label

    Raises:
        FileNotFoundError: If the MEI file cannot be loaded.
    """
    filepath = get_mei_filepath(filename)
    piece = importScore(str(filepath))
    if piece is None:
        raise FileNotFoundError(f"Could not load MEI file: {filepath}")

    nr = piece.notes(combineUnisons=combine_unisons)
    mel = piece.melodic(df=nr, kind=kind, compound=compound, unit=0, end=False)

    entry_ngrams = piece.entries(df=mel, n=n, thematic=True, anywhere=True)
    ngram_durations = piece.durations(df=mel, n=n, mask_df=entry_ngrams)

    first_occurrence: dict[tuple, dict[str, Any]] = {}

    for row in entry_ngrams.index:
        for col in entry_ngrams.columns:
            pattern = entry_ngrams.loc[row, col]

            if isinstance(pattern, tuple) and pattern not in first_occurrence:
                first_occurrence[pattern] = {
                    "start_q": float(row),
                    "column": col,
                    "duration": float(ngram_durations.loc[row, col]),
                }

    pattern_records = [
        {
            "pattern": _pattern_to_list(pattern),
            "start_q": info["start_q"],
            "duration": info["duration"],
            "end_q": info["start_q"] + info["duration"],
            "column": info["column"],
        }
        for pattern, info in first_occurrence.items()
    ]

    return {
        "filename": filename,
        "n": n,
        "kind": kind,
        "combine_unisons": combine_unisons,
        "compound": compound,
        "patterns": pattern_records,
    }