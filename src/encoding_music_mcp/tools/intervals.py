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
    "count_melodic_ngrams",
    "resolve_note_ids_for_highlight",
    "get_melodic_ngram_matches",
    "get_first_occur_melodic_ngrams",
    "get_cadences",
]

_MEI_NS = {"mei": "http://www.music-encoding.org/ns/mei"}
_XML_ID = "{http://www.w3.org/XML/1998/namespace}id"


def _get_staff_ppq(root: ET.Element) -> dict[str, int]:
    """Return ppq values for each staff number, inheriting score-level ppq."""
    score_def = root.find(".//mei:scoreDef", _MEI_NS)
    default_ppq = int(score_def.get("ppq", "480")) if score_def is not None else 480
    staff_ppq: dict[str, int] = {}
    for staff_def in root.findall(".//mei:staffDef", _MEI_NS):
        staff_n = staff_def.get("n")
        if staff_n:
            staff_ppq[staff_n] = int(staff_def.get("ppq", default_ppq))
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
                                "duration": dur_ppq / current_ppq,
                                "note_ids": event["note_ids"],
                            }
                        )

                    measure_offset_ppq += dur_ppq
                    global_offsets_ppq[part_label] += dur_ppq

                measure_offsets_ppq[part_label] = measure_offset_ppq

    return part_events


def _build_note_event_lookup(
    part_events: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[tuple[float, float, float], int]]:
    """Index note events by measure, beat, and offset for each part."""
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
    return note_lookup


def _normalise_part_labels(value: Any) -> list[str]:
    """Convert a staff/part/voice-pair field into CRIM part labels."""
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        labels: list[str] = []
        for item in value:
            labels.extend(_normalise_part_labels(item))
        return labels

    text = str(value).strip()
    if not text:
        return []
    for separator in ("::", "-", ",", "/"):
        if separator in text:
            return [
                label
                for chunk in text.split(separator)
                for label in _normalise_part_labels(chunk)
            ]
    return [text]


def _span_location_key(span: dict[str, Any]) -> tuple[float, float, float] | None:
    """Return a rounded MEI/CRIM location key from a requested span."""
    if "start_measure" in span and "start_beat" in span:
        offset = span.get("start_offset", span.get("start_q"))
        if offset is None:
            return None
        return (
            round(float(span["start_measure"]), 5),
            round(float(span["start_beat"]), 5),
            round(float(offset), 5),
        )
    return None


def _event_starts_in_span(
    event: dict[str, Any],
    span: dict[str, Any],
    start_q: float | None,
) -> bool:
    """Return True when an event onset belongs to a requested highlight span."""
    event_offset = float(event["offset"])
    if start_q is not None:
        if round(event_offset, 5) < round(start_q, 5):
            return False
        end_q = span.get("end_q", span.get("end_offset"))
        if end_q is None and "duration" in span:
            end_q = start_q + float(span["duration"])
        if end_q is None:
            return round(event_offset, 5) == round(start_q, 5)
        return round(event_offset, 5) < round(float(end_q), 5)

    if "start_measure" in span and "start_beat" in span:
        return (
            round(float(event["measure"]), 5) == round(float(span["start_measure"]), 5)
            and round(float(event["beat"]), 5) == round(float(span["start_beat"]), 5)
        )

    return False


def _resolve_note_id_spans(
    filepath: Path,
    spans: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve generic measure/beat/offset spans to MEI note IDs."""
    part_events = _build_part_note_events(filepath)
    note_lookup = _build_note_event_lookup(part_events)

    resolved_spans: list[dict[str, Any]] = []
    for index, span in enumerate(spans):
        requested_parts = _normalise_part_labels(
            span.get("column", span.get("staff", span.get("part", span.get("voice_pair"))))
        )
        part_labels = requested_parts or list(part_events.keys())
        note_count = span.get("note_count")
        location_key = _span_location_key(span)
        start_q = span.get("start_q", span.get("start_offset"))
        start_q_float = float(start_q) if start_q is not None else None

        note_ids: list[str] = []
        matched_parts: list[str] = []
        for part_label in part_labels:
            events = part_events.get(str(part_label), [])
            if not events:
                continue

            part_note_ids: list[str] = []
            if note_count is not None:
                start_idx = (
                    note_lookup.get(str(part_label), {}).get(location_key)
                    if location_key is not None
                    else None
                )
                if start_idx is None and start_q_float is not None:
                    start_idx = next(
                        (
                            event_index
                            for event_index, event in enumerate(events)
                            if round(float(event["offset"]), 5)
                            == round(start_q_float, 5)
                        ),
                        None,
                    )
                if (
                    start_idx is None
                    and "start_measure" in span
                    and "start_beat" in span
                ):
                    start_idx = next(
                        (
                            event_index
                            for event_index, event in enumerate(events)
                            if round(float(event["measure"]), 5)
                            == round(float(span["start_measure"]), 5)
                            and round(float(event["beat"]), 5)
                            == round(float(span["start_beat"]), 5)
                        ),
                        None,
                    )
                if start_idx is not None:
                    for event in events[start_idx : start_idx + int(note_count)]:
                        part_note_ids.extend(event["note_ids"])
            else:
                for event in events:
                    if _event_starts_in_span(event, span, start_q_float):
                        part_note_ids.extend(event["note_ids"])

            if part_note_ids:
                matched_parts.append(str(part_label))
                note_ids.extend(part_note_ids)

        resolved_spans.append(
            {
                **span,
                "index": index,
                "matched_parts": matched_parts,
                "note_ids": note_ids,
            }
        )

    return resolved_spans


def _build_note_id_matches(
    filepath: Path, mel_ngrams: Any, n: int
) -> list[dict[str, Any]]:
    """Build structured note-id spans for each melodic n-gram match."""
    matches: list[dict[str, Any]] = []

    for row in mel_ngrams.index:
        measure, beat, offset = (float(row[0]), float(row[1]), float(row[2]))

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
            matches.append(
                {
                    "pattern": pattern_values,
                    "pattern_string": pattern_string,
                    "column": part_label,
                    "start_measure": measure,
                    "start_beat": beat,
                    "start_offset": offset,
                    "note_count": n + 1,
                }
            )

    resolved_matches = _resolve_note_id_spans(filepath, matches)
    part_events = _build_part_note_events(filepath)
    events_by_part_and_note_id = {
        part_label: {
            note_id: event
            for event in events
            for note_id in event["note_ids"]
        }
        for part_label, events in part_events.items()
    }
    for match in resolved_matches:
        match.pop("index", None)
        match.pop("matched_parts", None)
        match.pop("note_count", None)
        note_ids = match["note_ids"]
        duration = 0.0
        if note_ids:
            event_by_note_id = events_by_part_and_note_id.get(match["column"], {})
            span_events = [event_by_note_id[note_id] for note_id in note_ids if note_id in event_by_note_id]
            if span_events:
                first_event = span_events[0]
                last_event = span_events[-1]
                duration = (
                    float(last_event["offset"])
                    + float(last_event["duration"])
                    - float(first_event["offset"])
                )
        match["duration"] = duration
        match["end_offset"] = float(match["start_offset"]) + duration

    return resolved_matches


def _normalise_pattern(pattern: Any) -> tuple[list[str], str]:
    """Convert a CRIM n-gram cell value into list and underscore-string forms."""
    if isinstance(pattern, tuple):
        pattern_values = [str(value) for value in pattern]
    elif isinstance(pattern, str):
        cleaned = pattern.strip()
        if not cleaned:
            return [], ""
        if "_" in cleaned:
            pattern_values = [value.strip() for value in cleaned.split("_")]
        else:
            pattern_values = [value.strip() for value in cleaned.split(",")]
    else:
        return [], ""

    pattern_values = [value for value in pattern_values if value]
    return pattern_values, "_".join(pattern_values)


def _pattern_to_string(pattern: Any) -> str:
    """Render a pattern cell as a stable underscore-separated string."""
    _, pattern_string = _normalise_pattern(pattern)
    return pattern_string


def _load_melodic_ngram_dataframe(
    filepath: Path,
    n: int,
    kind: str,
    entries: bool,
    combine_unisons: bool | None = None,
    compound: bool = False,
) -> Any:
    """Load and normalise a melodic n-gram dataframe."""
    piece = importScore(str(filepath))
    if piece is None:
        raise FileNotFoundError(f"Could not load MEI file: {filepath}")

    if combine_unisons is None:
        mel = piece.melodic(kind=kind, end=False)
    else:
        nr = piece.notes(combineUnisons=combine_unisons)
        mel = piece.melodic(
            df=nr,
            kind=kind,
            compound=compound,
            unit=0,
            end=False,
        )

    mel_ngrams = piece.ngrams(df=mel, n=n, offsets="first")

    if entries:
        mel_ngrams = piece.entries(
            df=mel_ngrams, thematic=False, anywhere=False, fermatas=True, exclude=[]
        )

    mel_ngrams = mel_ngrams.fillna("")
    mel_ngrams = piece.numberParts(mel_ngrams)
    mel_ngrams = piece.detailIndex(mel_ngrams, offset=True)

    return mel_ngrams


def _group_matches_by_pattern(
    matches: list[dict[str, Any]], patterns: list[str] | None = None
) -> dict[str, list[dict[str, Any]]]:
    """Group note-id matches by underscore-separated pattern string."""
    pattern_filter = {pattern.strip() for pattern in patterns or [] if pattern.strip()}
    grouped: dict[str, list[dict[str, Any]]] = {}

    for match in matches:
        pattern_string = match["pattern_string"]
        if pattern_filter and pattern_string not in pattern_filter:
            continue

        grouped.setdefault(pattern_string, []).append(
            {
                "pattern": match["pattern"],
                "column": match["column"],
                "start_measure": match["start_measure"],
                "start_beat": match["start_beat"],
                "start_offset": match["start_offset"],
                "duration": match["duration"],
                "end_offset": match["end_offset"],
                "note_ids": match["note_ids"],
            }
        )

    return dict(sorted(grouped.items()))


def _count_patterns(mel_ngrams: Any) -> list[dict[str, Any]]:
    """Count how often each melodic n-gram pattern occurs."""
    counts: dict[str, int] = {}
    patterns_by_string: dict[str, list[str]] = {}

    for row in mel_ngrams.index:
        for column in mel_ngrams.columns:
            pattern_values, pattern_string = _normalise_pattern(mel_ngrams.loc[row, column])
            if not pattern_string:
                continue

            counts[pattern_string] = counts.get(pattern_string, 0) + 1
            patterns_by_string.setdefault(pattern_string, pattern_values)

    sorted_patterns = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [
        {
            "pattern": patterns_by_string[pattern_string],
            "pattern_string": pattern_string,
            "count": count,
        }
        for pattern_string, count in sorted_patterns
    ]


def _load_piece_with_details(filepath: Path) -> tuple[Any, Any]:
    """Load a score and its detailed note dataframe."""
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
    filename: str,
    n: int = 4,
    kind: str = "d",
    entries: bool = False,
    include_note_ids: bool = False,
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
        include_note_ids: If True, also include occurrence-level note-ID spans.
            This is more expensive than returning the pattern table alone and is
            best reserved for targeted highlighting workflows. (default: False)

    Returns:
        Dictionary containing:
        - melodic_ngrams: CSV representation of the melodic n-grams dataframe
        - n: The n-gram length used
        - kind: The interval type used
        - entries: Whether entry filtering was applied
        - include_note_ids: Whether note-ID matches were included
        - filename: The input filename
    """
    filepath = get_mei_filepath(filename)
    mel_ngrams = _load_melodic_ngram_dataframe(filepath, n=n, kind=kind, entries=entries)
    mel_ngrams_as_strings = mel_ngrams.map(_pattern_to_string)

    result = {
        "filename": filename,
        "n": n,
        "kind": kind,
        "entries": entries,
        "include_note_ids": include_note_ids,
        "melodic_ngrams": mel_ngrams_as_strings.to_csv(index=True)
        if not mel_ngrams_as_strings.empty
        else "No melodic n-grams found",
    }

    if include_note_ids:
        result["melodic_ngram_note_ids"] = _build_note_id_matches(filepath, mel_ngrams, n)

    return result


def count_melodic_ngrams(
    filename: str,
    n: int = 4,
    kind: str = "d",
    entries: bool = False,
    combine_unisons: bool | None = None,
    compound: bool = False,
) -> dict[str, Any]:
    """Count melodic n-gram occurrences and rank patterns by frequency.

    Computes melodic n-grams with CRIM Intervals, normalises each pattern into
    a stable underscore-separated key, and returns counts sorted by descending
    frequency.

    Args:
        filename: Name of the MEI file (e.g., "Bach_BWV_0772.mei").
        n: Length of the n-grams.
        kind: Interval representation used for melodic intervals.
        entries: Whether to restrict results to entry-filtered n-grams.
        combine_unisons: Whether CRIM should combine repeated unisons before
            melodic interval extraction. ``None`` uses the default CRIM path.
        compound: Whether to use compound intervals.

    Returns:
        Dictionary containing:
        - filename: The input filename
        - n: The n-gram length used
        - kind: The interval type used
        - entries: Whether entry filtering was applied
        - combine_unisons: Whether unisons were combined
        - compound: Whether compound intervals were used
        - pattern_counts: Ranked list of pattern/count records
    """
    filepath = get_mei_filepath(filename)
    mel_ngrams = _load_melodic_ngram_dataframe(
        filepath,
        n=n,
        kind=kind,
        entries=entries,
        combine_unisons=combine_unisons,
        compound=compound,
    )

    return {
        "filename": filename,
        "n": n,
        "kind": kind,
        "entries": entries,
        "combine_unisons": combine_unisons,
        "compound": compound,
        "pattern_counts": _count_patterns(mel_ngrams),
    }


def resolve_note_ids_for_highlight(
    filename: str,
    spans: list[dict[str, Any]],
) -> dict[str, Any]:
    """Resolve analysis locations or spans to MEI note IDs for highlighting.

    This helper decouples note-ID retrieval from any one analysis tool. A span
    can come from melodic n-grams, harmonic intervals, cadence rows, or
    visualisation payloads.

    Inputs:
        filename: Name of the MEI file, for example ``"Bach_BWV_0772.mei"``.
        spans: Analysis locations or ranges to resolve. Each span should provide
            one of these location shapes:

            - ``start_measure`` and ``start_beat`` for measure/beat rows
            - ``start_q`` or ``start_offset`` for quarter-note offsets

            Optional fields narrow or widen the result:

            - ``staff``, ``part``, ``column``, or ``voice_pair`` restricts
              matching to one or more CRIM part labels. Voice pairs such as
              ``"1,2"`` match both parts.
            - ``duration``, ``end_q``, or ``end_offset`` returns note IDs whose
              onsets fall inside a span.
            - ``note_count`` returns a fixed number of consecutive note events
              from the starting location, which is useful for melodic n-grams
              where ``n`` intervals correspond to ``n + 1`` notes.

    Returns:
        Dictionary containing:
        - filename: The input filename.
        - spans: Resolved span dictionaries. Each resolved span preserves the
          original input span fields and adds:
            - index: Zero-based index of the requested span.
            - matched_parts: CRIM part labels that contributed note IDs.
            - note_ids: MEI ``xml:id`` values for notes matched by the span.
    """
    filepath = get_mei_filepath(filename)
    return {
        "filename": filename,
        "spans": _resolve_note_id_spans(filepath, spans),
    }


def get_melodic_ngram_matches(
    filename: str,
    n: int = 4,
    kind: str = "d",
    entries: bool = False,
    patterns: list[str] | None = None,
    combine_unisons: bool | None = None,
    compound: bool = False,
) -> dict[str, Any]:
    """Return note-ID matches grouped by melodic n-gram pattern.

    Computes melodic n-grams, resolves each occurrence to MEI note IDs, and
    groups the results by pattern string. This is the main data source for
    notation-highlighting workflows that need every occurrence of one or more
    melodic patterns.

    Args:
        filename: Name of the MEI file (e.g., "Bach_BWV_0772.mei").
        n: Length of the n-grams.
        kind: Interval representation used for melodic intervals.
        entries: Whether to restrict results to entry-filtered n-grams.
        patterns: Optional list of underscore-separated pattern strings to keep.
        combine_unisons: Whether CRIM should combine repeated unisons before
            melodic interval extraction. ``None`` uses the default CRIM path.
        compound: Whether to use compound intervals.

    Returns:
        Dictionary containing:
        - filename: The input filename
        - n: The n-gram length used
        - kind: The interval type used
        - entries: Whether entry filtering was applied
        - patterns: Pattern filters that were applied
        - combine_unisons: Whether unisons were combined
        - compound: Whether compound intervals were used
        - matches_by_pattern: Mapping of pattern strings to occurrence records
    """
    filepath = get_mei_filepath(filename)
    mel_ngrams = _load_melodic_ngram_dataframe(
        filepath,
        n=n,
        kind=kind,
        entries=entries,
        combine_unisons=combine_unisons,
        compound=compound,
    )
    grouped_matches = _group_matches_by_pattern(
        _build_note_id_matches(filepath, mel_ngrams, n),
        patterns=patterns,
    )

    return {
        "filename": filename,
        "n": n,
        "kind": kind,
        "entries": entries,
        "patterns": patterns or [],
        "combine_unisons": combine_unisons,
        "compound": compound,
        "matches_by_pattern": grouped_matches,
    }


def get_first_occur_melodic_ngrams(
    filename: str,
    n: int = 4,
    kind: str = "d",
    combine_unisons: bool = True,
    compound: bool = False,
) -> dict[str, Any]:
    """Extract first-occurrence melodic n-gram patterns from an MEI file.

    This computes melodic n-gram counts, groups note-id matches by pattern,
    then keeps the first occurrence of each unique pattern across all parts.

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
            - pattern_string: The underscore-separated pattern key
            - count: Total number of occurrences
            - start_q: Start position in quarter-note units
            - duration: Pattern duration in quarter-note units
            - end_q: End position in quarter-note units
            - column: Staff or part label
            - note_ids: MEI note IDs for the matched n-gram span

    Raises:
        FileNotFoundError: If the MEI file cannot be loaded.
    """
    counts_result = count_melodic_ngrams(
        filename=filename,
        n=n,
        kind=kind,
        combine_unisons=combine_unisons,
        compound=compound,
    )
    pattern_counts = counts_result["pattern_counts"]
    count_by_pattern = {
        record["pattern_string"]: record["count"] for record in pattern_counts
    }

    matches_result = get_melodic_ngram_matches(
        filename=filename,
        n=n,
        kind=kind,
        patterns=[record["pattern_string"] for record in pattern_counts],
        combine_unisons=combine_unisons,
        compound=compound,
    )

    pattern_records: list[dict[str, Any]] = []
    for pattern_string, matches in matches_result["matches_by_pattern"].items():
        if not matches:
            continue

        first_match = matches[0]
        start_q = float(first_match["start_offset"])
        duration = float(first_match["duration"])
        pattern_records.append(
            {
                "pattern": first_match["pattern"],
                "pattern_string": pattern_string,
                "count": count_by_pattern.get(pattern_string, len(matches)),
                "start_q": start_q,
                "duration": duration,
                "end_q": start_q + duration,
                "column": first_match["column"],
                "note_ids": first_match["note_ids"],
            }
        )

    pattern_records.sort(
        key=lambda record: (record["start_q"], str(record["column"]), record["pattern_string"])
    )

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
