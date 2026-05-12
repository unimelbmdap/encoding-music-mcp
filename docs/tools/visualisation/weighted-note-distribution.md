# Weighted Note Distribution

The `plot_weighted_note_distribution` tool displays a radar chart of pitch-class usage for one or more MEI scores, weighted by note duration.

## Overview

This tool is designed for the kind of "weighted note distribution" view shown in the notebook example. Instead of counting each note event equally, it weights each pitch class by `dur.ppq`, so longer notes contribute more strongly than short passing notes.

By default the chart:

- combines each score into one trace
- orders pitch classes by the circle of fifths
- hides pitch classes that never occur

## Prerequisites

This tool requires an MCP client that supports the MCP Apps extension. Without the extension, the tool still returns a short text description.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `filename` | `str` | Conditionally | Name of one MEI file |
| `filenames` | `list[str]` | Conditionally | Two or more MEI files to overlay on one figure |
| `pitch_class_order` | `str` | No | `"fifths"` (default) or `"chromatic"` |
| `group_by_staff` | `bool` | No | When `True`, show one polygon per staff instead of one combined score trace |
| `limit_to_active` | `bool` | No | When `True` (default), omit pitch classes with zero weight |

Provide either `filename`, `filenames`, or both.

## Return Value

The tool returns a `ToolResult` with:

- **Text content**: A short description of the rendered chart
- **Structured content**: Score metadata, ordered pitch-class labels, and one or more weighted traces for the viewer app

```python
{
    "filename": "Bach_BWV_0772.mei",
    "filenames": ["Bach_BWV_0772.mei", "Bach_BWV_0773.mei"],
    "score_count": 2,
    "scores": [
        {"filename": "Bach_BWV_0772.mei", "title": "...", "composer": "..."},
        {"filename": "Bach_BWV_0773.mei", "title": "...", "composer": "..."},
    ],
    "title": "Invention No. 1 in C major, BWV 772",
    "composer": "Bach, Johann Sebastian",
    "pitch_class_order": "fifths",
    "group_by_staff": False,
    "limit_to_active": True,
    "categories": ["C", "G", "D", "A", "E", "B", "F"],
    "radial_max": 0.21,
    "traces": [
        {
            "label": "Score",
            "color": "#d9485f",
            "values": [0.18, 0.16, 0.14, 0.09, 0.08, 0.03, 0.04],
            "raw_weights_ppq": [9600.0, 8400.0, 7200.0, 4800.0, 4200.0, 1800.0, 2100.0],
            "total_weight_ppq": 52080.0,
            "note_count": 312,
        }
    ],
}
```

## Usage

!!! example "Try asking:"
    "Plot the weighted note distribution for Bach_BWV_0772.mei"

!!! example "Overlay multiple scores:"
    "Plot the weighted note distribution for Bach_BWV_0772.mei and Bach_BWV_0773.mei on one chart"

!!! example "Or per staff:"
    "Plot the weighted note distribution for Bach_BWV_0772.mei by staff"

## How It Works

1. The tool parses each staff and layer in the MEI score
2. Every sounding note contributes its `dur.ppq` value to its pitch class
3. Chords contribute the same duration to each contained pitch class
4. The totals are scaled to proportions and arranged in the requested pitch-class order
5. The viewer renders those values as one or more radar polygons

## Use Cases

- Compare tonal emphasis across staves in a polyphonic score
- See which pitch classes dominate a single piece
- Compare two or more pieces as translucent polygons on the same radar chart
- Mirror the weighted-note radar plot shown in exploratory notebooks

## Related Tools

- [get_notes](../intervals/notes.md) - Extract unweighted note-event tables
- [plot_voice_ranges](voice-ranges.md) - Compare staff pitch spans instead of pitch-class emphasis
