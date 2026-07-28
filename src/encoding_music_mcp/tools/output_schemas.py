"""JSON Schemas for tools that return explicit ``ToolResult`` payloads.

FastMCP infers output schemas for ordinary dictionary return values. Tools that
return ``ToolResult`` need an explicit schema so MCP hosts know that
``structuredContent`` is part of the public result contract.
"""

from typing import Any

_NULLABLE_STRING = {
    "anyOf": [
        {"type": "string"},
        {"type": "null"},
    ]
}
_NULLABLE_NUMBER = {
    "anyOf": [
        {"type": "number"},
        {"type": "null"},
    ]
}
_STRING_ARRAY = {"type": "array", "items": {"type": "string"}}
_OBJECT_ARRAY = {"type": "array", "items": {"type": "object"}}

SHOW_NOTATION_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "filename": {"type": "string"},
        "svg": {"type": "string"},
        "page": {"type": "integer"},
        "total_pages": {"type": "integer"},
        "start_measure": {"type": "integer"},
        "end_measure": {"type": "integer"},
    },
    "required": ["filename", "svg", "page", "total_pages"],
}

SHOW_NOTATION_HIGHLIGHT_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        **SHOW_NOTATION_OUTPUT_SCHEMA["properties"],
        "highlight_note_ids": _STRING_ARRAY,
    },
    "required": [
        *SHOW_NOTATION_OUTPUT_SCHEMA["required"],
        "highlight_note_ids",
    ],
}

VOICE_RANGES_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "filename": {"type": "string"},
        "title": {"type": "string"},
        "composer": _NULLABLE_STRING,
        "x_min_midi": {"type": "integer"},
        "x_max_midi": {"type": "integer"},
        "tick_values": {"type": "array", "items": {"type": "integer"}},
        "tick_labels": _STRING_ARRAY,
        "staff_ranges": _OBJECT_ARRAY,
    },
    "required": [
        "filename",
        "title",
        "composer",
        "x_min_midi",
        "x_max_midi",
        "tick_values",
        "tick_labels",
        "staff_ranges",
    ],
}

WEIGHTED_NOTE_DISTRIBUTION_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "filename": {"type": "string"},
        "filenames": _STRING_ARRAY,
        "score_count": {"type": "integer"},
        "scores": _OBJECT_ARRAY,
        "title": {"type": "string"},
        "composer": _NULLABLE_STRING,
        "pitch_class_order": {"type": "string"},
        "group_by_staff": {"type": "boolean"},
        "limit_to_active": {"type": "boolean"},
        "categories": _STRING_ARRAY,
        "radial_max": {"type": "number"},
        "traces": _OBJECT_ARRAY,
    },
    "required": [
        "filename",
        "filenames",
        "score_count",
        "scores",
        "title",
        "composer",
        "pitch_class_order",
        "group_by_staff",
        "limit_to_active",
        "categories",
        "radial_max",
        "traces",
    ],
}

MELODIC_NGRAM_HEATMAP_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "filename": {"type": "string"},
        "filenames": _STRING_ARRAY,
        "score_count": {"type": "integer"},
        "scores": _OBJECT_ARRAY,
        "n": {"type": "integer"},
        "kind": {"type": "string"},
        "entries": {"type": "boolean"},
        "top_n": {"type": "integer"},
        "combine_unisons": {
            "anyOf": [
                {"type": "boolean"},
                {"type": "null"},
            ]
        },
        "compound": {"type": "boolean"},
        "patterns": _OBJECT_ARRAY,
        "rows": _OBJECT_ARRAY,
        "occurrences": _OBJECT_ARRAY,
        "x_min": {"type": "number"},
        "x_max": {"type": "number"},
    },
    "required": [
        "filename",
        "filenames",
        "score_count",
        "scores",
        "n",
        "kind",
        "entries",
        "top_n",
        "combine_unisons",
        "compound",
        "patterns",
        "rows",
        "occurrences",
        "x_min",
        "x_max",
    ],
}

SONORITY_NGRAM_PROGRESS_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "filename": {"type": "string"},
        "filenames": _STRING_ARRAY,
        "score_count": {"type": "integer"},
        "scores": _OBJECT_ARRAY,
        "n": {"type": "integer"},
        "kind": {"type": "string"},
        "directed": {"type": "boolean"},
        "compound": {"type": "boolean"},
        "sort": {"type": "boolean"},
        "minimum_beat_strength": {"type": "number"},
        "beat_strength_filter_applied": {"type": "boolean"},
        "beat_strength_fallback_filenames": _STRING_ARRAY,
        "warnings": _STRING_ARRAY,
        "rows": _OBJECT_ARRAY,
        "occurrences": _OBJECT_ARRAY,
        "x_min": {"type": "number"},
        "x_max": {"type": "number"},
    },
    "required": [
        "filename",
        "filenames",
        "score_count",
        "scores",
        "n",
        "kind",
        "directed",
        "compound",
        "sort",
        "minimum_beat_strength",
        "beat_strength_filter_applied",
        "beat_strength_fallback_filenames",
        "warnings",
        "rows",
        "occurrences",
        "x_min",
        "x_max",
    ],
}

PLAY_EXCERPT_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "filename": {"type": "string"},
        "audio_resource_uri": {"type": "string"},
        "mime_type": {"type": "string"},
        "start_q": {"type": "number"},
        "end_q": _NULLABLE_NUMBER,
        "bpm": {"type": "integer"},
        "duration_sec": {"type": "number"},
    },
    "required": [
        "filename",
        "audio_resource_uri",
        "mime_type",
        "start_q",
        "end_q",
        "bpm",
        "duration_sec",
    ],
}

LOAD_AUDIO_RESOURCE_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "resource_uri": {"type": "string"},
        "mime_type": {"type": "string"},
        "audio_base64": {"type": "string"},
        "duration_sec": {"type": "number"},
    },
    "required": [
        "resource_uri",
        "mime_type",
        "audio_base64",
        "duration_sec",
    ],
}
