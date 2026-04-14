"""MEI interval analysis tools using CRIM Intervals."""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from crim_intervals.main_objs import importScore

from .helpers import get_mei_filepath

__all__ = [
    "get_notes",
    "get_melodic_intervals",
    "get_harmonic_intervals",
    "get_melodic_ngrams",
    "get_first_occur_melodic_ngrams",
    "get_cadences",
]

_MEI_NS = {"mei": "http://www.music-encoding.org/ns/mei"}
_XML_ID = "{http://www.w3.org/XML/1998/namespace}id"


def _get_staff_ppq(root: ET.Element) -> dict[str, int]:
    """Return ppq values for each staff number, defaulting to 480."""
    staff_ppq: dict[str, int] = {}
    for staff_def in root.findall(".//mei:staffDef", _MEI_NS):
        staff_n = staff_def.get("n")
        ppq = staff_def.get("ppq")
        if staff_n and ppq:
            staff_ppq[staff_n] = int(ppq)
    return staff_ppq


def _iter_layer_events(
    element: ET.Element,
    current_ppq: int,
) -> list[dict[str, Any]]:
    """Flatten a layer subtree into timed events in document order."""
    events: list[dict[str, Any]] = []

    tag = element.tag.rsplit("}", 1)[-1]

    if tag in {"beam", "tuplet", "bTrem", "fTrem"}:
        for child in list(element):
            events.extend(_iter_layer_events(child, current_ppq))
        return events

    if tag == "chord":
        note_ids = [
            note.get(_XML_ID)
            for note in element.findall("mei:note", _MEI_NS)
            if note.get(_XML_ID)
        ]
        dur_ppq = element.get("dur.ppq")
        if dur_ppq is None:
            return events
        events.append(
            {
                "kind": "note",
                "dur_ppq": int(dur_ppq),
                "note_ids": note_ids,
            }
        )
        return events

    if tag == "note":
        dur_ppq = element.get("dur.ppq")
        if dur_ppq is None:
            return events
        xml_id = element.get(_XML_ID)
        events.append(
            {
                "kind": "note",
                "dur_ppq": int(dur_ppq),
                "note_ids": [xml_id] if xml_id else [],
            }
        )
        return events

    if tag in {"rest", "mRest", "space", "mSpace"}:
        dur_ppq = element.get("dur.ppq")
        if dur_ppq is None:
            if tag in {"mRest", "mSpace"}:
                dur_ppq = str(current_ppq * 4)
            else:
                return events
        events.append({"kind": "rest", "dur_ppq": int(dur_ppq)})
        return events

    return events


def _build_part_note_events(filepath: Path) -> dict[str, list[dict[str, Any]]]:
    """Parse MEI and return sounded-note events for each CRIM part number."""
    root = ET.parse(filepath).getroot()
    staff_ppq = _get_staff_ppq(root)

    part_key_to_label: dict[tuple[str, str], str] = {}
    part_events: dict[str, list[dict[str, Any]]] = {}
    global_offsets_ppq: dict[str, int] = {}

    for measure in root.findall(".//mei:measure", _MEI_NS):
        measure_n = float(measure.get("n", "0"))
        measure_offsets_ppq: dict[str, int] = {}

        for staff in measure.findall("mei:staff", _MEI_NS):
            staff_n = staff.get("n", "")
            current_ppq = staff_ppq.get(staff_n, 480)

            for layer in staff.findall("mei:layer", _MEI_NS):
                layer_n = layer.get("n", "1")
                part_key = (staff_n, layer_n)
                if part_key not in part_key_to_label:
                    part_label = str(len(part_key_to_label) + 1)
                    part_key_to_label[part_key] = part_label
                    part_events[part_label] = []
                    global_offsets_ppq[part_label] = 0

                part_label = part_key_to_label[part_key]
                measure_offset_ppq = measure_offsets_ppq.get(part_label, 0)
                layer_events: list[dict[str, Any]] = []

                for child in list(layer):
                    layer_events.extend(_iter_layer_events(child, current_ppq))

                for event in layer_events:
                    dur_ppq = event["dur_ppq"]
                    if event["kind"] == "note" and event["note_ids"]:
                        onset_q = global_offsets_ppq[part_label] / current_ppq
                        beat = 1 + (measure_offset_ppq / current_ppq)
                        part_events[part_label].append(
                            {
                                "measure": measure_n,
                                "beat": beat,
                                "offset": onset_q,
                                "note_ids": event["note_ids"],
                            }
                        )

                    measure_offset_ppq += dur_ppq
                    global_offsets_ppq[part_label] += dur_ppq

                measure_offsets_ppq[part_label] = measure_offset_ppq

    return part_events


def _build_note_id_matches(
    filepath: Path, mel_ngrams: Any, n: int
) -> list[dict[str, Any]]:
    """Build structured note-id spans for each melodic n-gram match."""
    part_events = _build_part_note_events(filepath)

    note_lookup: dict[str, dict[tuple[float, float, float], int]] = {}
    for part_label, events in part_events.items():
        part_lookup: dict[tuple[float, float, float], int] = {}
        for idx, event in enumerate(events):
            key = (
                round(float(event["measure"]), 5),
                round(float(event["beat"]), 5),
                round(float(event["offset"]), 5),
            )
            part_lookup[key] = idx
        note_lookup[part_label] = part_lookup

    matches: list[dict[str, Any]] = []

    for row in mel_ngrams.index:
        measure, beat, offset = (float(row[0]), float(row[1]), float(row[2]))
        row_key = (round(measure, 5), round(beat, 5), round(offset, 5))

        for column in mel_ngrams.columns:
            pattern = mel_ngrams.loc[row, column]
            if isinstance(pattern, tuple):
                pattern_values = list(pattern)
                pattern_string = "_".join(map(str, pattern))
            elif isinstance(pattern, str) and pattern.strip():
                pattern_values = [value.strip() for value in pattern.split(",")]
                pattern_string = "_".join(pattern_values)
            else:
                continue

            part_label = str(column)
            part_lookup = note_lookup.get(part_label, {})
            start_idx = part_lookup.get(row_key)
            events = part_events.get(part_label, [])

            note_ids: list[str] = []
            if start_idx is not None:
                span = events[start_idx : start_idx + n + 1]
                for event in span:
                    note_ids.extend(event["note_ids"])

            matches.append(
                {
                    "pattern": pattern_values,
                    "pattern_string": pattern_string,
                    "column": part_label,
                    "start_measure": measure,
                    "start_beat": beat,
                    "start_offset": offset,
                    "note_ids": note_ids,
                }
            )

    return matches


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
        - melodic_ngram_note_ids: Structured list of n-gram matches with note IDs
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

    melodic_ngram_note_ids = _build_note_id_matches(filepath, mel_ngrams, n)
    mel_ngrams = mel_ngrams.map(tuple_to_string)

    return {
        "filename": filename,
        "n": n,
        "kind": kind,
        "entries": entries,
        "melodic_ngram_note_ids": melodic_ngram_note_ids,
        "melodic_ngrams": mel_ngrams.to_csv(index=True)
        if not mel_ngrams.empty
        else "No melodic n-grams found",
    }


def _pattern_to_list(pattern: Any) -> list[Any] | Any:
    """Convert a tuple-based n-gram pattern to a JSON-friendly list."""
    return list(pattern) if isinstance(pattern, tuple) else pattern


def get_first_occur_melodic_ngrams(
    filename: str,
    n: int = 4,
    kind: str = "d",
    combine_unisons: bool = True,
    compound: bool = False,
) -> dict[str, Any]:
    """Extract first-occurrence melodic n-gram patterns from an MEI file.

    This computes melodic n-grams using CRIM Intervals, identifies the first
    occurrence of each unique pattern across all parts, and returns quarter-note
    playback boundaries for each pattern.

    Args:
        filename: Name of the MEI file (e.g., "Bach_BWV_0772.mei").
        n: Length of the melodic n-grams.
        kind: Type of interval to calculate:
            - 'd' (default): diatonic intervals (e.g., 2, -3, 5)
            - 'c': chromatic intervals (e.g., 0, 2, -4)
            - 'q': diatonic with quality (e.g., 'M2', 'm3', 'P5')
            - 'z': zero-based diatonic intervals
        combine_unisons: Whether to combine unisons when extracting notes.
        compound: Whether to use compound intervals.

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
