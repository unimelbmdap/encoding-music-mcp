"""Inspect MEI harmony annotations and return explicit or inferred chords."""

from __future__ import annotations

import copy
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from .helpers import get_mei_filepath

__all__ = [
    "ChordEvent",
    "HarmonyInspection",
    "get_chord_progression",
    "inspect_harmony",
]

_XML_ID = "{http://www.w3.org/XML/1998/namespace}id"


class HarmonyInspection(BaseModel):
    """Summary of the harmony annotations and voice identifiers in an MEI score."""

    harmony_count: int
    staves: list[str]
    layers: list[str]
    has_explicit_labels: bool
    requires_inference: bool


class ChordEvent(BaseModel):
    """One explicit MEI harmony label or one music21-inferred sonority."""

    name: str
    measure_number: int | None
    beat_str: str | None
    elements: list[str]
    staff: str | None
    layer: str | None
    xml_id: str | None
    source: Literal["explicit_harm", "inferred"]


def _local_name(element: ET.Element) -> str:
    """Return an XML element's local name without its namespace."""
    return element.tag.rsplit("}", 1)[-1]


def _elements(root: ET.Element, name: str) -> list[ET.Element]:
    """Return descendants whose namespace-independent tag matches ``name``."""
    return [element for element in root.iter() if _local_name(element) == name]


def _identifier_sort_key(identifier: str) -> tuple[int, int | str]:
    """Sort numeric MEI identifiers naturally before non-numeric identifiers."""
    try:
        return (0, int(identifier))
    except ValueError:
        return (1, identifier)


def _ordered_identifiers(root: ET.Element, element_name: str) -> list[str]:
    """Collect unique, non-empty MEI ``n`` identifiers in a stable order."""
    identifiers = {
        identifier
        for element in _elements(root, element_name)
        if (identifier := element.get("n"))
    }
    return sorted(identifiers, key=_identifier_sort_key)


def _harmony_label(harmony: ET.Element) -> str:
    """Normalize all descendant text in an MEI harmony annotation."""
    return " ".join(" ".join(harmony.itertext()).split())


def _normalized_string(value: object) -> str | None:
    """Return normalized non-empty text for a string-like location value."""
    if value is None:
        return None
    normalized = " ".join(str(value).split())
    return normalized or None


def _load_mei(filename: str) -> tuple[Path, ET.Element]:
    """Resolve and parse an MEI score, preserving the public missing-file error."""
    filepath = get_mei_filepath(filename)
    if not filepath.is_file():
        raise FileNotFoundError(f"MEI file not found: {filename}")
    return filepath, ET.parse(filepath).getroot()


def _score_identifiers(root: ET.Element) -> tuple[list[str], list[str]]:
    """Return the score's available staff and layer ``n`` identifiers."""
    return _ordered_identifiers(root, "staff"), _ordered_identifiers(root, "layer")


def _validate_filters(
    root: ET.Element,
    *,
    start_measure: int | None,
    end_measure: int | None,
    staff: str | None,
    layer: str | None,
) -> tuple[list[str], list[str]]:
    """Validate public range and identifier filters against the MEI structure."""
    if start_measure is not None and start_measure < 1:
        raise ValueError("start_measure must be at least 1")
    if end_measure is not None and end_measure < 1:
        raise ValueError("end_measure must be at least 1")
    if (
        start_measure is not None
        and end_measure is not None
        and start_measure > end_measure
    ):
        raise ValueError("start_measure must be less than or equal to end_measure")

    staves, layers = _score_identifiers(root)
    if staff is not None and staff not in staves:
        raise ValueError(
            f"Unknown staff '{staff}'. Available staves: {', '.join(staves) or 'none'}"
        )
    if layer is not None and layer not in layers:
        raise ValueError(
            f"Unknown layer '{layer}'. Available layers: {', '.join(layers) or 'none'}"
        )
    if staff is not None and layer is not None:
        matching_staff_elements = [
            element for element in _elements(root, "staff") if element.get("n") == staff
        ]
        if not any(
            descendant.get("n") == layer
            for staff_element in matching_staff_elements
            for descendant in staff_element.iter()
            if _local_name(descendant) == "layer"
        ):
            raise ValueError(f"Layer '{layer}' is not available on staff '{staff}'")
    return staves, layers


def _finite_float(value: object) -> float | None:
    """Return a finite float, normalizing missing, invalid, and NaN values."""
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _measure_number(value: object) -> int | None:
    """Return an integer measure number when one can be represented safely."""
    number = _finite_float(value)
    if number is None or not number.is_integer():
        return None
    return int(number)


def _within_measure_range(
    measure: int | None,
    start_measure: int | None,
    end_measure: int | None,
) -> bool:
    """Return whether a known measure satisfies the requested inclusive range."""
    if start_measure is not None and (measure is None or measure < start_measure):
        return False
    if end_measure is not None and (measure is None or measure > end_measure):
        return False
    return True


def _extract_explicit_harmony(
    root: ET.Element,
    *,
    start_measure: int | None,
    end_measure: int | None,
    staff: str | None,
    layer: str | None,
) -> list[ChordEvent]:
    """Extract normalized labels directly from usable MEI ``harm`` elements."""
    parent_by_child = {
        child: parent for parent in root.iter() for child in list(parent)
    }
    events: list[ChordEvent] = []

    for harmony in _elements(root, "harm"):
        ancestor = parent_by_child.get(harmony)
        while ancestor is not None and _local_name(ancestor) != "measure":
            ancestor = parent_by_child.get(ancestor)
        measure_number = _measure_number(
            ancestor.get("n") if ancestor is not None else None
        )
        harmony_staff = harmony.get("staff")
        harmony_layer = harmony.get("layer")

        if not _within_measure_range(measure_number, start_measure, end_measure):
            continue
        if staff is not None and harmony_staff != staff:
            continue
        if layer is not None and harmony_layer != layer:
            continue

        events.append(
            ChordEvent(
                name=_harmony_label(harmony),
                measure_number=measure_number,
                beat_str=_normalized_string(harmony.get("tstamp")),
                elements=[],
                staff=harmony_staff,
                layer=harmony_layer,
                xml_id=harmony.get(_XML_ID),
                source="explicit_harm",
            )
        )

    return sorted(
        events,
        key=lambda event: (
            event.measure_number is None,
            event.measure_number or 0,
            _finite_float(event.beat_str) is None,
            _finite_float(event.beat_str) or 0.0,
            _identifier_sort_key(event.staff or ""),
            _identifier_sort_key(event.layer or ""),
        ),
    )


def _select_music21_material(
    score, staff_ids: list[str], staff: str | None, layer: str | None
):
    """Copy only the requested MEI staff/layer material before chordification."""
    from music21 import stream

    if not score.parts:
        return score

    selected_score = stream.Score()
    for index, part in enumerate(score.parts):
        part_staff = staff_ids[index] if index < len(staff_ids) else None
        if staff is not None and part_staff != staff:
            continue
        selected_part = copy.deepcopy(part)
        if layer is not None:
            for voice in list(selected_part.recurse().getElementsByClass(stream.Voice)):
                if str(voice.id) != layer and voice.activeSite is not None:
                    voice.activeSite.remove(voice)
        selected_score.insert(0, selected_part)
    return selected_score


def _infer_with_music21(
    filepath: Path,
    *,
    staff_ids: list[str],
    start_measure: int | None,
    end_measure: int | None,
    staff: str | None,
    layer: str | None,
) -> list[ChordEvent]:
    """Infer multi-pitch sonorities with music21 from selected score material."""
    from music21 import chord, converter

    score = converter.parse(str(filepath))
    material = _select_music21_material(score, staff_ids, staff, layer)
    events: list[tuple[float, ChordEvent]] = []

    for sonority in material.chordify().flatten().getElementsByClass(chord.Chord):
        elements = [pitch.nameWithOctave for pitch in sonority.pitches]
        if len(set(elements)) < 2:
            continue
        measure = _measure_number(sonority.measureNumber)
        if not _within_measure_range(measure, start_measure, end_measure):
            continue
        events.append(
            (
                float(sonority.offset),
                ChordEvent(
                    name=sonority.pitchedCommonName,
                    measure_number=measure,
                    beat_str=_normalized_string(sonority.beatStr),
                    elements=elements,
                    staff=staff,
                    layer=layer,
                    xml_id=None,
                    source="inferred",
                ),
            )
        )

    return [event for _, event in sorted(events, key=lambda item: item[0])]


def inspect_harmony(filename: str) -> HarmonyInspection:
    """Inspect MEI harmony labels and available staff/layer identifiers."""
    _, root = _load_mei(filename)
    harmonies = _elements(root, "harm")
    labels = [_harmony_label(harmony) for harmony in harmonies]
    has_explicit_labels = bool(harmonies) and all(labels)
    staves, layers = _score_identifiers(root)
    return HarmonyInspection(
        harmony_count=len(harmonies),
        staves=staves,
        layers=layers,
        has_explicit_labels=has_explicit_labels,
        requires_inference=not has_explicit_labels,
    )


def get_chord_progression(
    filename: str,
    start_measure: int | None = None,
    end_measure: int | None = None,
    staff: str | None = None,
    layer: str | None = None,
) -> list[ChordEvent]:
    """Return explicit MEI harmony labels or inferred multi-pitch sonorities."""
    filepath, root = _load_mei(filename)
    staves, _ = _validate_filters(
        root,
        start_measure=start_measure,
        end_measure=end_measure,
        staff=staff,
        layer=layer,
    )
    harmonies = _elements(root, "harm")
    if harmonies and all(_harmony_label(harmony) for harmony in harmonies):
        return _extract_explicit_harmony(
            root,
            start_measure=start_measure,
            end_measure=end_measure,
            staff=staff,
            layer=layer,
        )
    return _infer_with_music21(
        filepath,
        staff_ids=staves,
        start_measure=start_measure,
        end_measure=end_measure,
        staff=staff,
        layer=layer,
    )
