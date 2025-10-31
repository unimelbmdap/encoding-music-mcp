"""MEI interval analysis tools using CRIM Intervals."""

from typing import Any

from crim_intervals.main_objs import importScore

from .helpers import get_mei_filepath

__all__ = [
    "get_notes",
    "get_melodic_intervals",
    "get_harmonic_intervals",
    "get_melodic_ngrams",
]


def _load_piece_with_details(filepath) -> tuple[Any, Any]:
    """Load a piece and prepare detailed note dataframe.

    Args:
        filepath: Path to the MEI file

    Returns:
        Tuple of (piece, detailed_notes_dataframe)
    """
    piece = importScore(str(filepath))
    nr = piece.notes()
    nr = piece.numberParts(nr)
    nr = piece.detailIndex(nr)
    return piece, nr


def get_notes(filename: str) -> dict[str, Any]:
    """Extract all notes from an MEI file using CRIM Intervals.

    Returns a dataframe of notes for the given piece, with pitch and octave information.
    Columns represent individual staves or voice parts.
    Rows represent measure and beat information, expressed as floats.

    Args:
        filename: Name of the MEI file (e.g., "Bach_BWV_0772.mei")

    Returns:
        Dictionary containing:
        - notes: String representation of the notes dataframe
        - filename: The input filename
    """
    filepath = get_mei_filepath(filename)
    _, nr = _load_piece_with_details(filepath)

    return {
        "filename": filename,
        "notes": nr.to_string(index=True) if not nr.empty else "No notes found",
    }


def get_melodic_intervals(filename: str) -> dict[str, Any]:
    """Extract melodic intervals from an MEI file using CRIM Intervals.

    Returns a dataframe of melodic intervals for the given piece.
    Columns represent individual staves or voice parts.
    Rows represent measure and beat information, expressed as floats.

    Args:
        filename: Name of the MEI file (e.g., "Bach_BWV_0772.mei")

    Returns:
        Dictionary containing:
        - melodic_intervals: String representation of the melodic intervals dataframe
        - filename: The input filename
    """
    filepath = get_mei_filepath(filename)
    piece, nr = _load_piece_with_details(filepath)
    mel = piece.melodic(df=nr)

    return {
        "filename": filename,
        "melodic_intervals": mel.to_string(index=True)
        if not mel.empty
        else "No melodic intervals found",
    }


def get_harmonic_intervals(filename: str) -> dict[str, Any]:
    """Extract harmonic intervals from an MEI file using CRIM Intervals.

    Returns a dataframe of harmonic intervals for the given piece.
    Columns represent pairs of voice parts.
    Rows represent measure and beat information, expressed as floats.

    Args:
        filename: Name of the MEI file (e.g., "Bach_BWV_0772.mei")

    Returns:
        Dictionary containing:
        - harmonic_intervals: String representation of the harmonic intervals dataframe
        - filename: The input filename
    """
    filepath = get_mei_filepath(filename)
    piece, nr = _load_piece_with_details(filepath)
    har = piece.harmonic(df=nr)

    return {
        "filename": filename,
        "harmonic_intervals": har.to_string(index=True)
        if not har.empty
        else "No harmonic intervals found",
    }


def get_melodic_ngrams(filename: str, n: int = 4) -> dict[str, Any]:
    """Extract melodic n-grams from an MEI file using CRIM Intervals.

    Returns a dataframe of melodic n-grams for the given piece.
    Columns represent individual staves or voice parts.
    Rows represent measure and beat information, expressed as floats.
    N-grams are tuples of intervals converted to strings with underscore separators.

    Args:
        filename: Name of the MEI file (e.g., "Bach_BWV_0772.mei")
        n: Length of the n-grams (default: 4)

    Returns:
        Dictionary containing:
        - melodic_ngrams: String representation of the melodic n-grams dataframe
        - n: The n-gram length used
        - filename: The input filename
    """
    filepath = get_mei_filepath(filename)
    piece, nr = _load_piece_with_details(filepath)
    mel = piece.melodic(df=nr, kind="d")
    ng = piece.ngrams(df=mel, n=n)

    # Convert tuples to strings with underscore separators
    tuple_to_string = lambda x: "_".join(map(str, x)) if isinstance(x, tuple) else x
    ng = ng.map(tuple_to_string)

    return {
        "filename": filename,
        "n": n,
        "melodic_ngrams": ng.to_string(index=True)
        if not ng.empty
        else "No melodic n-grams found",
    }
