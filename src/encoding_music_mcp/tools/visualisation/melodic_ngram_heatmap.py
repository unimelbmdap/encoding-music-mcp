"""Melodic n-gram heatmap plotting for one or more MEI scores."""

from __future__ import annotations

from typing import Any

from fastmcp.tools.tool import ToolResult
from mcp.types import TextContent

from ..helpers import get_mei_filepath
from ..intervals import (
    _build_note_id_matches,
    _build_part_note_events,
    _count_patterns,
    _load_melodic_ngram_dataframe,
)
from ..metadata import get_mei_metadata

__all__ = ["plot_melodic_ngram_heatmap"]

_PATTERN_COLOURS = [
    "#d92b8a",
    "#2bbbd0",
    "#f2c230",
    "#8d5cf6",
    "#2fd05f",
    "#f46a4e",
    "#2f72df",
    "#b6e36a",
]


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


def _score_label(filename: str, metadata: dict[str, Any]) -> str:
    """Return a concise score label for row headings."""
    title = metadata.get("title")
    if title and title != "Unknown":
        return str(title)
    return filename


def _build_score_payload(
    filename: str,
    n: int,
    kind: str,
    entries: bool,
    combine_unisons: bool | None,
    compound: bool,
) -> dict[str, Any]:
    """Build n-gram counts, matches, and staff rows for one score."""
    filepath = get_mei_filepath(filename)
    metadata = get_mei_metadata(filename)
    mel_ngrams = _load_melodic_ngram_dataframe(
        filepath,
        n=n,
        kind=kind,
        entries=entries,
        combine_unisons=combine_unisons,
        compound=compound,
    )
    part_events = _build_part_note_events(filepath)

    rows: list[dict[str, Any]] = []
    for staff in sorted(part_events.keys(), key=lambda value: int(value) if value.isdigit() else value):
        events = part_events[staff]
        end_q = max(
            (float(event["offset"]) + float(event["duration"]) for event in events),
            default=0.0,
        )
        rows.append(
            {
                "id": f"{filename}::{staff}",
                "filename": filename,
                "score_label": _score_label(filename, metadata),
                "staff": staff,
                "label": f"{_score_label(filename, metadata)} - Staff {staff}",
                "end_q": end_q,
            }
        )

    return {
        "filename": filename,
        "title": metadata.get("title") or filename,
        "composer": metadata.get("composer"),
        "rows": rows,
        "pattern_counts": _count_patterns(mel_ngrams),
        "matches": _build_note_id_matches(filepath, mel_ngrams, n),
    }


def _build_heatmap_payload(
    filename: str | None,
    filenames: list[str] | None,
    n: int,
    kind: str,
    entries: bool,
    top_n: int,
    combine_unisons: bool | None,
    compound: bool,
) -> dict[str, Any]:
    """Build the structured payload consumed by the heatmap app."""
    if n < 1:
        raise ValueError("n must be at least 1")
    if top_n < 1:
        raise ValueError("top_n must be at least 1")

    resolved_filenames = _resolve_filenames(filename, filenames)
    score_payloads = [
        _build_score_payload(
            filename=score_filename,
            n=n,
            kind=kind,
            entries=entries,
            combine_unisons=combine_unisons,
            compound=compound,
        )
        for score_filename in resolved_filenames
    ]

    count_by_pattern: dict[str, int] = {}
    pattern_values: dict[str, list[str]] = {}
    for score in score_payloads:
        for record in score["pattern_counts"]:
            pattern_string = record["pattern_string"]
            count_by_pattern[pattern_string] = (
                count_by_pattern.get(pattern_string, 0) + int(record["count"])
            )
            pattern_values.setdefault(pattern_string, record["pattern"])

    top_patterns = sorted(
        count_by_pattern.items(),
        key=lambda item: (-item[1], item[0]),
    )[:top_n]
    selected_patterns = {pattern for pattern, _ in top_patterns}
    colour_by_pattern = {
        pattern: _PATTERN_COLOURS[index % len(_PATTERN_COLOURS)]
        for index, (pattern, _) in enumerate(top_patterns)
    }

    rows: list[dict[str, Any]] = []
    occurrences: list[dict[str, Any]] = []
    max_offset = 0.0
    for score in score_payloads:
        rows.extend(score["rows"])
        max_offset = max(max_offset, *(row["end_q"] for row in score["rows"]))
        score_matches = [
            match
            for match in score["matches"]
            if match["pattern_string"] in selected_patterns and float(match["duration"]) > 0
        ]
        for match in score_matches:
            pattern_string = match["pattern_string"]
            start_q = float(match["start_offset"])
            end_q = float(match["end_offset"])
            max_offset = max(max_offset, end_q)
            occurrences.append(
                {
                    "id": (
                        f"{score['filename']}::{match['column']}::"
                        f"{pattern_string}::{start_q}"
                    ),
                    "filename": score["filename"],
                    "row_id": f"{score['filename']}::{match['column']}",
                    "staff": str(match["column"]),
                    "pattern": match["pattern"],
                    "pattern_string": pattern_string,
                    "start_q": start_q,
                    "end_q": end_q,
                    "duration": float(match["duration"]),
                    "start_measure": float(match["start_measure"]),
                    "start_beat": float(match["start_beat"]),
                    "note_ids": match["note_ids"],
                    "color": colour_by_pattern[pattern_string],
                }
            )

    patterns = [
        {
            "pattern": pattern_values[pattern],
            "pattern_string": pattern,
            "count": count,
            "color": colour_by_pattern[pattern],
        }
        for pattern, count in top_patterns
    ]

    return {
        "filename": resolved_filenames[0],
        "filenames": resolved_filenames,
        "score_count": len(score_payloads),
        "scores": [
            {
                "filename": score["filename"],
                "title": score["title"],
                "composer": score["composer"],
            }
            for score in score_payloads
        ],
        "n": n,
        "kind": kind,
        "entries": entries,
        "top_n": top_n,
        "combine_unisons": combine_unisons,
        "compound": compound,
        "patterns": patterns,
        "rows": rows,
        "occurrences": occurrences,
        "x_min": 0.0,
        "x_max": max_offset,
    }


def plot_melodic_ngram_heatmap(
    filename: str | None = None,
    filenames: list[str] | None = None,
    n: int = 4,
    kind: str = "d",
    entries: bool = False,
    top_n: int = 2,
    combine_unisons: bool | None = None,
    compound: bool = False,
) -> ToolResult:
    """Plot top melodic n-gram occurrences as per-staff timeline rectangles.

    The tool ranks melodic n-gram patterns by total occurrence count across all
    supplied scores, keeps the top ``top_n`` patterns, and returns one heatmap
    row for every staff/part in every score. Each occurrence is drawn from its
    start offset to the end offset of the matched pattern.
    """
    structured = _build_heatmap_payload(
        filename=filename,
        filenames=filenames,
        n=n,
        kind=kind,
        entries=entries,
        top_n=top_n,
        combine_unisons=combine_unisons,
        compound=compound,
    )

    description = (
        f"Showing melodic n-gram heatmap for {structured['score_count']} score"
        f"{'' if structured['score_count'] == 1 else 's'} with top "
        f"{len(structured['patterns'])} pattern"
        f"{'' if len(structured['patterns']) == 1 else 's'}."
    )
    return ToolResult(
        content=[TextContent(type="text", text=description)],
        structured_content=structured,
    )
