"""Sonority n-gram progress scatter plotting for one or more MEI scores."""

from __future__ import annotations

import warnings
from typing import Any

from crim_intervals.corpus_tools import corpus_sonority_ngrams
from crim_intervals.main_objs import CorpusBase
from fastmcp.tools.tool import ToolResult
from mcp.types import TextContent

from ..helpers import get_mei_filepath
from ..intervals import _normalise_pattern
from ..metadata import get_mei_metadata
from .melodic_ngram_heatmap import _resolve_filenames, _score_label

__all__ = ["plot_sonority_ngram_progress"]

_SCORE_COLOURS = [
    "#74c7ec",
    "#2f72df",
    "#f2c230",
    "#2fd05f",
    "#d92b8a",
    "#f46a4e",
    "#8d5cf6",
    "#2bbbd0",
]


def _normalise_module_pattern(pattern: Any) -> tuple[list[str], str]:
    """Preserve CRIM module n-gram items while making a stable row key."""
    if isinstance(pattern, str) and "," in pattern:
        pattern_values = [value.strip() for value in pattern.split(",") if value.strip()]
        return pattern_values, "_".join(pattern_values)
    return _normalise_pattern(pattern)


def _load_corpus_sonority_ngrams(
    filenames: list[str],
    n: int,
    compound: bool,
    sort: bool,
    minimum_beat_strength: float,
) -> Any:
    """Load CRIM's corpus-level sonority n-gram dataframe."""
    filepaths = [get_mei_filepath(filename) for filename in filenames]
    for filename, path in zip(filenames, filepaths, strict=True):
        if not path.exists():
            raise FileNotFoundError(f"MEI file not found: {filename}")
    paths = [str(path) for path in filepaths]
    corpus = CorpusBase(paths)
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=".*A value is trying to be set on a copy.*",
            category=FutureWarning,
        )
        return corpus_sonority_ngrams(
            corpus,
            ngram_length=n,
            metadata_choice=True,
            include_offset=True,
            include_progress=True,
            compound=compound,
            sort=sort,
            minimum_beat_strength=minimum_beat_strength,
        )


def _build_score_payload(
    filename: str,
    corpus_ngrams: Any,
    n: int,
    compound: bool,
    sort: bool,
    color: str,
) -> dict[str, Any]:
    """Build sonority n-gram occurrences for one score."""
    metadata = get_mei_metadata(filename)
    title = metadata.get("title") or filename
    score_rows = corpus_ngrams[
        corpus_ngrams["Title"].fillna("").astype(str).eq(str(title))
    ]
    if score_rows.empty:
        score_rows = corpus_ngrams[
            corpus_ngrams["Title"].fillna("").astype(str).str.contains(
                str(title),
                regex=False,
            )
        ]

    occurrences: list[dict[str, Any]] = []
    count_by_pattern: dict[str, int] = {}
    first_progress_by_pattern: dict[str, float] = {}
    pattern_values_by_string: dict[str, list[str]] = {}

    for _, row in score_rows.iterrows():
        pattern_values, pattern_string = _normalise_module_pattern(row["Low_Sonority"])
        if not pattern_string:
            continue

        start_q = float(row["Offset"]) if "Offset" in row else 0.0
        progress = max(0.0, min(1.0, float(row["Progress"])))

        count_by_pattern[pattern_string] = count_by_pattern.get(pattern_string, 0) + 1
        first_progress_by_pattern.setdefault(pattern_string, progress)
        pattern_values_by_string.setdefault(pattern_string, pattern_values)
        occurrences.append(
            {
                "id": f"{filename}::{pattern_string}::{start_q}",
                "filename": filename,
                "score_label": _score_label(filename, metadata),
                "pattern": pattern_values,
                "pattern_string": pattern_string,
                "voice_pair": "Low_Sonority",
                "start_measure": float(row["Measure"]) if "Measure" in row else None,
                "start_beat": float(row["Beat"]) if "Beat" in row else None,
                "start_q": start_q,
                "progress": progress,
                "count_in_score": 0,
                "color": color,
            }
        )

    for occurrence in occurrences:
        occurrence["count_in_score"] = count_by_pattern[occurrence["pattern_string"]]

    patterns = [
        {
            "pattern": pattern_values_by_string[pattern_string],
            "pattern_string": pattern_string,
            "count": count,
            "first_progress": first_progress_by_pattern[pattern_string],
        }
        for pattern_string, count in count_by_pattern.items()
    ]
    patterns.sort(key=lambda item: (item["first_progress"], item["pattern_string"]))

    return {
        "filename": filename,
        "title": title,
        "composer": metadata.get("composer"),
        "label": _score_label(filename, metadata),
        "color": color,
        "end_q": max((occurrence["start_q"] for occurrence in occurrences), default=0.0),
        "patterns": patterns,
        "occurrences": occurrences,
    }


def _build_progress_payload(
    filename: str | None,
    filenames: list[str] | None,
    n: int,
    compound: bool,
    sort: bool,
    minimum_beat_strength: float,
) -> dict[str, Any]:
    """Build the structured payload consumed by the progress scatter app."""
    if n < 1:
        raise ValueError("n must be at least 1")

    resolved_filenames = _resolve_filenames(filename, filenames)
    corpus_ngrams = _load_corpus_sonority_ngrams(
        filenames=resolved_filenames,
        n=n,
        compound=compound,
        sort=sort,
        minimum_beat_strength=minimum_beat_strength,
    )
    score_payloads = [
        _build_score_payload(
            filename=score_filename,
            corpus_ngrams=corpus_ngrams,
            n=n,
            compound=compound,
            sort=sort,
            color=_SCORE_COLOURS[index % len(_SCORE_COLOURS)],
        )
        for index, score_filename in enumerate(resolved_filenames)
    ]

    rows: list[dict[str, Any]] = []
    occurrences: list[dict[str, Any]] = []
    seen_patterns: set[str] = set()

    for score_index, score in enumerate(score_payloads):
        introduced_patterns = [
            pattern
            for pattern in score["patterns"]
            if pattern["pattern_string"] not in seen_patterns
        ]
        introduced_pattern_strings = {
            pattern["pattern_string"] for pattern in introduced_patterns
        }

        for pattern in introduced_patterns:
            rows.append(
                {
                    "id": f"{score['filename']}::{pattern['pattern_string']}",
                    "filename": score["filename"],
                    "score_label": score["label"],
                    "score_index": score_index,
                    "pattern": pattern["pattern"],
                    "pattern_string": pattern["pattern_string"],
                    "label": pattern["pattern_string"],
                    "count": pattern["count"],
                    "first_progress": pattern["first_progress"],
                    "color": score["color"],
                }
            )

        for occurrence in score["occurrences"]:
            pattern_string = occurrence["pattern_string"]
            if pattern_string not in introduced_pattern_strings:
                continue
            occurrences.append(
                {
                    **occurrence,
                    "row_id": f"{score['filename']}::{pattern_string}",
                    "score_index": score_index,
                }
            )

        seen_patterns.update(pattern["pattern_string"] for pattern in score["patterns"])

    return {
        "filename": resolved_filenames[0],
        "filenames": resolved_filenames,
        "score_count": len(score_payloads),
        "scores": [
            {
                "filename": score["filename"],
                "title": score["title"],
                "composer": score["composer"],
                "label": score["label"],
                "color": score["color"],
                "end_q": score["end_q"],
                "pattern_count": len(score["patterns"]),
            }
            for score in score_payloads
        ],
        "n": n,
        "kind": "low_line",
        "directed": True,
        "compound": compound,
        "sort": sort,
        "minimum_beat_strength": minimum_beat_strength,
        "rows": rows,
        "occurrences": occurrences,
        "x_min": 0.0,
        "x_max": 1.0,
    }


def _format_score_name(score: dict[str, Any]) -> str:
    composer = score.get("composer")
    title = score.get("title") or score.get("filename")
    return f"{composer} | {title}" if composer else str(title)


def _progress_percent(value: float) -> str:
    return f"{round(value * 100)}%"


def _build_text_summary(structured: dict[str, Any]) -> str:
    """Build a compact natural-language summary for chat clients."""
    rows = structured["rows"]
    occurrences = structured["occurrences"]
    score_lines = [
        (
            f"- {_format_score_name(score)}: {score['pattern_count']} distinct "
            f"sonority n-gram pattern{'' if score['pattern_count'] == 1 else 's'}"
        )
        for score in structured["scores"]
    ]

    description = (
        f"Sonority n-gram progress scatter for {structured['score_count']} "
        f"score{'' if structured['score_count'] == 1 else 's'}.\n"
        f"The plot contains {len(rows)} displayed pattern"
        f"{'' if len(rows) == 1 else 's'} and {len(occurrences)} occurrence"
        f"{'' if len(occurrences) == 1 else 's'}. Each point marks where a "
        "low-line sonority n-gram begins, measured as progress from the start "
        "to the end of the score."
    )

    if not rows or not occurrences:
        return description

    progress_values = [float(occurrence["progress"]) for occurrence in occurrences]
    first_progress = min(progress_values)
    last_progress = max(progress_values)

    pattern_counts = sorted(
        (
            (row["count"], row["pattern_string"], float(row["first_progress"]))
            for row in rows
        ),
        key=lambda item: (-item[0], item[2], item[1]),
    )
    top_patterns = [
        (
            f"- {pattern}: {count} occurrence{'' if count == 1 else 's'}, "
            f"first appearing around {_progress_percent(first)}"
        )
        for count, pattern, first in pattern_counts[:5]
    ]

    return "\n".join(
        [
            description,
            (
                f"Occurrences span roughly {_progress_percent(first_progress)} to "
                f"{_progress_percent(last_progress)} of the score timeline."
            ),
            "Scores:",
            *score_lines,
            "Most recurring displayed patterns:",
            *top_patterns,
        ]
    )


def plot_sonority_ngram_progress(
    filename: str | None = None,
    filenames: list[str] | None = None,
    n: int = 4,
    compound: bool = True,
    sort: bool = False,
    minimum_beat_strength: float = 0.0,
) -> ToolResult:
    """Plot sonority n-grams by normalized progress through each score.

    Each score is scanned from start to finish with n-gram items that combine
    melodic motion with the full vertical sonority context. Occurrences are
    plotted at their start progress from 0 to 1. In multi-score mode, each score
    introduces only patterns that have not appeared in earlier scores, so
    repeated ideas are not duplicated in later score groups.
    """
    structured = _build_progress_payload(
        filename=filename,
        filenames=filenames,
        n=n,
        compound=compound,
        sort=sort,
        minimum_beat_strength=minimum_beat_strength,
    )

    return ToolResult(
        content=[TextContent(type="text", text=_build_text_summary(structured))],
        structured_content=structured,
    )
