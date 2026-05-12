"""Weighted note-distribution radar plot for one or more MEI scores."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from fastmcp.tools.tool import ToolResult
from mcp.types import TextContent

from ..helpers import get_mei_filepath
from ..metadata import get_mei_metadata

__all__ = ["plot_weighted_note_distribution"]

_MEI_NS = {"mei": "http://www.music-encoding.org/ns/mei"}
_PITCH_CLASS_ORDER_CHROMATIC = [
    "C",
    "C#",
    "D",
    "E-",
    "E",
    "F",
    "F#",
    "G",
    "A-",
    "A",
    "B-",
    "B",
]
_PITCH_CLASS_ORDER_FIFTHS = [
    "C",
    "G",
    "D",
    "A",
    "E",
    "B",
    "F#",
    "C#",
    "A-",
    "E-",
    "B-",
    "F",
]
_PITCH_CLASS_LABELS = {
    0: "C",
    1: "C#",
    2: "D",
    3: "E-",
    4: "E",
    5: "F",
    6: "F#",
    7: "G",
    8: "A-",
    9: "A",
    10: "B-",
    11: "B",
}
_PITCH_CLASS_BASES = {
    "c": 0,
    "d": 2,
    "e": 4,
    "f": 5,
    "g": 7,
    "a": 9,
    "b": 11,
}
_TRACE_COLOURS = [
    "#d9485f",
    "#2b6cb0",
    "#d97706",
    "#1f8a70",
    "#7c3aed",
    "#475569",
]


def _accidental_offset(value: str | None) -> int:
    """Translate MEI accidental tokens into semitone offsets."""
    if not value:
        return 0

    token = value.strip().lower()
    mapping = {
        "n": 0,
        "s": 1,
        "ss": 2,
        "x": 2,
        "xs": 3,
        "f": -1,
        "ff": -2,
        "tf": -3,
    }
    if token in mapping:
        return mapping[token]

    if set(token) <= {"s"}:
        return len(token)
    if set(token) <= {"f"}:
        return -len(token)
    return 0


def _note_pitch_class(note: ET.Element) -> str | None:
    """Return the note's canonical pitch-class label."""
    pname = note.get("pname")
    if not pname:
        return None

    accidental = note.get("accid.ges") or note.get("accid")
    if not accidental:
        accid_element = note.find("mei:accid", _MEI_NS)
        accidental = accid_element.get("accid") if accid_element is not None else None

    semitone = (_PITCH_CLASS_BASES[pname.lower()] + _accidental_offset(accidental)) % 12
    return _PITCH_CLASS_LABELS[semitone]


def _iter_weighted_events(element: ET.Element) -> list[tuple[int, list[str]]]:
    """Flatten one MEI layer subtree into duration/pitch-class events."""
    tag = element.tag.rsplit("}", 1)[-1]

    if tag in {"beam", "tuplet", "bTrem", "fTrem"}:
        events: list[tuple[int, list[str]]] = []
        for child in list(element):
            events.extend(_iter_weighted_events(child))
        return events

    if tag == "chord":
        dur_ppq = element.get("dur.ppq")
        if dur_ppq is None:
            return []

        pitch_classes = [
            pitch_class
            for note in element.findall("mei:note", _MEI_NS)
            if (pitch_class := _note_pitch_class(note)) is not None
        ]
        if not pitch_classes:
            return []
        return [(int(dur_ppq), pitch_classes)]

    if tag == "note":
        dur_ppq = element.get("dur.ppq")
        pitch_class = _note_pitch_class(element)
        if dur_ppq is None or pitch_class is None:
            return []
        return [(int(dur_ppq), [pitch_class])]

    return []


def _order_for_name(pitch_class_order: str) -> list[str]:
    """Resolve the requested pitch-class order."""
    order_name = pitch_class_order.strip().lower()
    if order_name == "chromatic":
        return _PITCH_CLASS_ORDER_CHROMATIC
    if order_name == "fifths":
        return _PITCH_CLASS_ORDER_FIFTHS
    raise ValueError("pitch_class_order must be either 'chromatic' or 'fifths'")


def _resolve_filenames(
    filename: str | None,
    filenames: list[str] | None,
) -> list[str]:
    """Normalise single-file and multi-file inputs."""
    resolved: list[str] = []
    if filename:
        resolved.append(filename)
    if filenames:
        resolved.extend(name for name in filenames if name)

    deduped: list[str] = []
    for name in resolved:
        if name not in deduped:
            deduped.append(name)

    if not deduped:
        raise ValueError("Provide filename or filenames")
    return deduped


def _build_score_groups(
    filename: str,
    group_by_staff: bool,
) -> tuple[dict[str, Any], dict[str, dict[str, float]], dict[str, int]]:
    """Compute weighted pitch-class totals for one score."""
    filepath = get_mei_filepath(filename)
    if not filepath.exists():
        raise FileNotFoundError(f"MEI file not found: {filename}")

    metadata = get_mei_metadata(filename)
    root = ET.parse(filepath).getroot()

    group_totals: dict[str, dict[str, float]] = {}
    note_counts: dict[str, int] = {}
    for measure in root.findall(".//mei:measure", _MEI_NS):
        for staff in measure.findall("mei:staff", _MEI_NS):
            staff_n = staff.get("n", "?")
            if group_by_staff:
                group_label = f"{metadata.get('title') or filename} - Staff {staff_n}"
            else:
                group_label = metadata.get("title") or filename
            totals = group_totals.setdefault(
                group_label,
                {pitch_class: 0.0 for pitch_class in _PITCH_CLASS_LABELS.values()},
            )
            note_counts.setdefault(group_label, 0)

            for layer in staff.findall("mei:layer", _MEI_NS):
                for child in list(layer):
                    for dur_ppq, pitch_classes in _iter_weighted_events(child):
                        for pitch_class in pitch_classes:
                            totals[pitch_class] += float(dur_ppq)
                            note_counts[group_label] += 1

    if not group_totals or all(sum(values.values()) == 0 for values in group_totals.values()):
        raise ValueError(f"No sounding notes found in MEI file: {filename}")

    metadata_payload = {
        "filename": filename,
        "title": metadata.get("title") or filename,
        "composer": metadata.get("composer"),
    }
    return metadata_payload, group_totals, note_counts


def _build_weighted_note_payload(
    filename: str | None,
    filenames: list[str] | None,
    pitch_class_order: str,
    group_by_staff: bool,
    limit_to_active: bool,
) -> dict[str, Any]:
    """Compute score-level or staff-level weighted pitch-class summaries."""
    resolved_filenames = _resolve_filenames(filename, filenames)
    order = _order_for_name(pitch_class_order)

    score_metadata: list[dict[str, Any]] = []
    group_totals: dict[str, dict[str, float]] = {}
    note_counts: dict[str, int] = {}

    for score_filename in resolved_filenames:
        metadata_payload, score_groups, score_counts = _build_score_groups(
            filename=score_filename,
            group_by_staff=group_by_staff,
        )
        score_metadata.append(metadata_payload)
        group_totals.update(score_groups)
        note_counts.update(score_counts)

    active_pitch_classes = [
        pitch_class
        for pitch_class in order
        if any(group_totals[label][pitch_class] > 0 for label in group_totals)
    ]
    categories = active_pitch_classes if limit_to_active else order[:]

    traces: list[dict[str, Any]] = []
    radial_max = 0.0
    for index, label in enumerate(group_totals.keys()):
        totals = group_totals[label]
        total_weight = sum(totals.values())
        values = [
            (totals[pitch_class] / total_weight) if total_weight else 0.0
            for pitch_class in categories
        ]
        radial_max = max(radial_max, max(values, default=0.0))
        traces.append(
            {
                "id": label.lower().replace(" ", "-"),
                "label": label,
                "color": _TRACE_COLOURS[index % len(_TRACE_COLOURS)],
                "values": values,
                "raw_weights_ppq": [totals[pitch_class] for pitch_class in categories],
                "total_weight_ppq": total_weight,
                "note_count": note_counts[label],
            }
        )

    if len(score_metadata) == 1:
        title = score_metadata[0]["title"]
        composer = score_metadata[0]["composer"]
    else:
        title = f"{len(score_metadata)} scores"
        composers = {
            metadata["composer"]
            for metadata in score_metadata
            if metadata.get("composer")
        }
        composer = ", ".join(sorted(composers)) if composers else None

    return {
        "filename": resolved_filenames[0],
        "filenames": resolved_filenames,
        "score_count": len(score_metadata),
        "scores": score_metadata,
        "title": title,
        "composer": composer,
        "pitch_class_order": pitch_class_order.lower(),
        "group_by_staff": group_by_staff,
        "limit_to_active": limit_to_active,
        "categories": categories,
        "radial_max": radial_max,
        "traces": traces,
    }


def plot_weighted_note_distribution(
    filename: str | None = None,
    filenames: list[str] | None = None,
    pitch_class_order: str = "fifths",
    group_by_staff: bool = False,
    limit_to_active: bool = True,
) -> ToolResult:
    """Plot a duration-weighted pitch-class radar chart for one or more MEI scores.

    Each note contributes its duration weight (``dur.ppq``) to its pitch class,
    so sustained tones count more than brief passing notes. By default the tool
    combines each score into one polygon and orders pitch classes by the circle
    of fifths, mirroring the notebook example shared by the user.
    """
    structured = _build_weighted_note_payload(
        filename=filename,
        filenames=filenames,
        pitch_class_order=pitch_class_order,
        group_by_staff=group_by_staff,
        limit_to_active=limit_to_active,
    )

    trace_count = len(structured["traces"])
    score_count = structured["score_count"]
    description = (
        f"Showing weighted note distribution for {score_count} score"
        f"{'' if score_count == 1 else 's'} with {trace_count} trace"
        f"{'' if trace_count == 1 else 's'} in {structured['pitch_class_order']} order."
    )

    return ToolResult(
        content=[TextContent(type="text", text=description)],
        structured_content=structured,
    )
