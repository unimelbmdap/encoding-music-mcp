"""MEI interval analysis tools using CRIM Intervals."""

from typing import Any

from crim_intervals.main_objs import importScore

from .helpers import get_mei_filepath

__all__ = [
    "get_notes",
    "get_melodic_intervals",
    "get_harmonic_intervals",
    "get_melodic_ngrams",
    "get_cadences",
]


def _load_piece_with_details(filepath) -> tuple[Any, Any]:
    """Load a piece and prepare detailed note dataframe.

    Args:
        filepath: Path to the MEI file

    Returns:
        Tuple of (piece, detailed_notes_dataframe)

    Raises:
        FileNotFoundError: If the file cannot be loaded
    """
    piece = importScore(str(filepath))
    if piece is None:
        raise FileNotFoundError(f"Could not load MEI file: {filepath}")
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
        - notes: CSV representation of the notes dataframe
        - filename: The input filename
    """
    filepath = get_mei_filepath(filename)
    _, nr = _load_piece_with_details(filepath)

    return {
        "filename": filename,
        "notes": nr.to_csv(index=True) if not nr.empty else "No notes found",
    }


def get_melodic_intervals(filename: str, kind: str = "d") -> dict[str, Any]:
    """Extract melodic intervals from an MEI file using CRIM Intervals.

    Returns a dataframe of melodic intervals for the given piece.
    Columns represent individual staves or voice parts.
    Rows represent measure and beat information, expressed as floats.

    Args:
        filename: Name of the MEI file (e.g., "Bach_BWV_0772.mei")
        kind: Type of interval to calculate:
            - 'd' (default): diatonic intervals (e.g., 2, -3, 5)
            - 'c': chromatic intervals (e.g., 0, 2, -4)
            - 'q': diatonic with quality (e.g., 'M2', 'm3', 'P5')
            - 'z': zero-based diatonic intervals

    Returns:
        Dictionary containing:
        - melodic_intervals: CSV representation of the melodic intervals dataframe
        - kind: The interval type used
        - filename: The input filename
    """
    filepath = get_mei_filepath(filename)
    piece, nr = _load_piece_with_details(filepath)
    mel = piece.melodic(df=nr, kind=kind)

    return {
        "filename": filename,
        "kind": kind,
        "melodic_intervals": mel.to_csv(index=True)
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
        - harmonic_intervals: CSV representation of the harmonic intervals dataframe
        - filename: The input filename
    """
    filepath = get_mei_filepath(filename)
    piece, nr = _load_piece_with_details(filepath)
    har = piece.harmonic(df=nr)

    return {
        "filename": filename,
        "harmonic_intervals": har.to_csv(index=True)
        if not har.empty
        else "No harmonic intervals found",
    }


def get_melodic_ngrams(
    filename: str, n: int = 4, kind: str = "d", entries: bool = False
) -> dict[str, Any]:
    """Extract melodic n-grams from an MEI file using CRIM Intervals.

    Returns a dataframe of melodic n-grams for the given piece.
    Columns represent individual staves or voice parts.
    Rows represent measure and beat information, expressed as floats.
    N-grams are tuples of intervals converted to strings with underscore separators.

    Args:
        filename: Name of the MEI file (e.g., "Bach_BWV_0772.mei")
        n: Length of the n-grams (default: 4)
        kind: Type of interval to calculate:
            - 'd' (default): diatonic intervals (e.g., 2, -3, 5)
            - 'c': chromatic intervals (e.g., 0, 2, -4)
            - 'q': diatonic with quality (e.g., 'M2', 'm3', 'P5')
            - 'z': zero-based diatonic intervals
        entries: If True, filter to only show n-grams occurring after rests,
            section breaks, or fermatas. This is useful for identifying thematic
            material and motives. (default: False)

    Returns:
        Dictionary containing:
        - melodic_ngrams: CSV representation of the melodic n-grams dataframe
        - n: The n-gram length used
        - kind: The interval type used
        - entries: Whether entry filtering was applied
        - filename: The input filename
    """
    filepath = get_mei_filepath(filename)
    piece = importScore(str(filepath))
    if piece is None:
        raise FileNotFoundError(f"Could not load MEI file: {filepath}")

    if entries:
        # When filtering to entries, use end=False and offsets='first'
        mel = piece.melodic(kind=kind, end=False)
        mel_ngrams = piece.ngrams(df=mel, n=n, offsets="first")
        mel_ngrams = piece.entries(
            df=mel_ngrams, thematic=False, anywhere=False, fermatas=True, exclude=[]
        ).fillna("")
        mel_ngrams = piece.numberParts(mel_ngrams)
        mel_ngrams = piece.detailIndex(mel_ngrams, offset=True)
    else:
        # Standard n-gram extraction
        mel = piece.melodic(kind=kind, end=False)
        mel_ngrams = piece.ngrams(df=mel, n=n, offsets="first").fillna("")
        mel_ngrams = piece.numberParts(mel_ngrams)
        mel_ngrams = piece.detailIndex(mel_ngrams, offset=True)

    # Convert tuples to strings with underscore separators
    def tuple_to_string(x):
        return "_".join(map(str, x)) if isinstance(x, tuple) else x

    mel_ngrams = mel_ngrams.map(tuple_to_string)

    return {
        "filename": filename,
        "n": n,
        "kind": kind,
        "entries": entries,
        "melodic_ngrams": mel_ngrams.to_csv(index=True)
        if not mel_ngrams.empty
        else "No melodic n-grams found",
    }


def get_cadences(filename: str) -> dict[str, Any]:
    """Extract predicted cadences from an MEI file using CRIM Intervals.

    Returns a dataframe of cadences predicted for Renaissance counterpoint.
    Columns include Composer, Title, Measure, Beat, Progress, CadType (cadence type),
    Tone, and CVFs (Cadential Voice Functions).

    Args:
        filename: Name of the MEI file (e.g., "Morley_1595_01_Go_ye_my_canzonettes.mei")

    Returns:
        Dictionary containing:
        - cadences: CSV representation of the cadences dataframe
        - filename: The input filename
    """
    filepath = get_mei_filepath(filename)
    piece = importScore(str(filepath))
    if piece is None:
        raise FileNotFoundError(f"Could not load MEI file: {filepath}")

    try:
        cads = piece.cadences()
    except (ValueError, KeyError) as e:
        # Cadence detection may fail for non-Renaissance music or unusual textures
        return {
            "filename": filename,
            "cadences": f"Cadence detection not supported for this piece. "
            f"This tool is optimised for Renaissance counterpoint (15th-17th century vocal polyphony). "
            f"Error: {str(e)}",
        }

    # Check if any cadences were found before adding metadata columns
    if cads.empty:
        return {
            "filename": filename,
            "cadences": "No cadences found",
        }

    cads["Composer"] = piece.metadata["composer"]
    cads["Title"] = piece.metadata["title"]
    cads = cads[
        ["Composer", "Title", "Measure", "Beat", "Progress", "CadType", "Tone", "CVFs"]
    ]

    return {
        "filename": filename,
        "cadences": cads.to_csv(index=False),
    }
