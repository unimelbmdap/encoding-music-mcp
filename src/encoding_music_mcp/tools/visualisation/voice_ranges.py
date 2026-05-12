"""Voice range plotting tool for a single MEI score."""

from __future__ import annotations

import csv
import io
import re
from typing import Any

from fastmcp.tools.tool import ToolResult
from mcp.types import TextContent

from ..intervals import get_notes
from ..metadata import get_mei_metadata

__all__ = ["plot_voice_ranges"]

_NOTE_RE = re.compile(r"^([A-G])([#-]*)(\d+)$")
_PITCH_CLASS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_NOTE_NAMES = ["C", "C#", "D", "E-", "E", "F", "F#", "G", "A-", "A", "B-", "B"]
_STAFF_COLOURS = [
    "#ff6b6b",
    "#4dabf7",
    "#845ef7",
    "#f59f00",
    "#12b886",
    "#e64980",
]


def _note_to_midi(note: str) -> int:
    """Convert a note token such as C#4 or B-3 into a MIDI value."""
    match = _NOTE_RE.fullmatch(note.strip())
    if not match:
        raise ValueError(f"Unsupported pitch token: {note}")

    step, accidental, octave = match.groups()
    return (
        (int(octave) + 1) * 12
        + _PITCH_CLASS[step]
        + accidental.count("#")
        - accidental.count("-")
    )


def _midi_to_note_name(midi: int) -> str:
    """Convert a MIDI note into a display label."""
    octave = (midi // 12) - 1
    return f"{_NOTE_NAMES[midi % 12]}{octave}"


def _extract_staff_ranges(filename: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return score metadata and per-staff pitch-range summaries."""
    notes_payload = get_notes(filename)
    notes_csv = notes_payload["notes"]
    metadata_payload = get_mei_metadata(filename)
    staff_ranges: list[dict[str, Any]] = []

    reader = csv.DictReader(io.StringIO(notes_csv))
    if not reader.fieldnames:
        raise ValueError(f"No notes found in MEI file: {filename}")

    staff_columns = [
        fieldname
        for fieldname in reader.fieldnames
        if fieldname not in {"Measure", "Beat"}
    ]
    pitch_by_staff: dict[str, list[str]] = {column: [] for column in staff_columns}

    for row in reader:
        for column in staff_columns:
            value = (row.get(column) or "").strip()
            if value and value != "Rest":
                pitch_by_staff[column].append(value)

    for index, column in enumerate(staff_columns):
        pitch_tokens = pitch_by_staff[column]
        if not pitch_tokens:
            continue

        midi_values = [_note_to_midi(token) for token in pitch_tokens]
        lowest_midi = min(midi_values)
        highest_midi = max(midi_values)

        staff_ranges.append(
            {
                "staff": str(column),
                "label": f"Staff {column}",
                "colour": _STAFF_COLOURS[index % len(_STAFF_COLOURS)],
                "lowest_midi": lowest_midi,
                "highest_midi": highest_midi,
                "lowest_note": _midi_to_note_name(lowest_midi),
                "highest_note": _midi_to_note_name(highest_midi),
                "range_semitones": highest_midi - lowest_midi,
            }
        )

    if not staff_ranges:
        raise ValueError(f"No notes found in MEI file: {filename}")

    metadata = {
        "filename": filename,
        "title": metadata_payload.get("title") or filename,
        "composer": metadata_payload.get("composer"),
    }
    return metadata, staff_ranges


def plot_voice_ranges(filename: str) -> ToolResult:
    """Plot note ranges for the staves in a single MEI score.

    Derives the lowest and highest sounding pitch in each staff, then packages
    those ranges for the voice-range viewer app.

    Args:
        filename: Name of the MEI file (e.g., ``"Bach_BWV_0772.mei"``).

    Returns:
        ToolResult with text fallback plus structured content containing score
        metadata, axis labels, and per-staff range summaries.
    """
    metadata, staff_ranges = _extract_staff_ranges(filename)
    x_min = min(staff["lowest_midi"] for staff in staff_ranges)
    x_max = max(staff["highest_midi"] for staff in staff_ranges)

    structured = {
        **metadata,
        "x_min_midi": x_min,
        "x_max_midi": x_max,
        "tick_values": list(range(x_min, x_max + 1)),
        "tick_labels": [_midi_to_note_name(value) for value in range(x_min, x_max + 1)],
        "staff_ranges": staff_ranges,
    }
    description = (
        f"Showing voice ranges for {metadata['title']} ({filename}) "
        f"across {len(staff_ranges)} stave(s)."
    )

    return ToolResult(
        content=[TextContent(type="text", text=description)],
        structured_content=structured,
    )

