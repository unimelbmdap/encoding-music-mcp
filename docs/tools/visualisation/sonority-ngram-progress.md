# Sonority N-gram Progress

The `plot_sonority_ngram_progress` tool displays sonority n-grams as a scatter
plot against normalized progress through one or more MEI scores.

## Overview

This view uses CRIM Intervals' corpus-level sonority n-gram analysis. Each point
marks where a low-line sonority n-gram begins, with the x-axis scaled from `0%`
to `100%` of the score. The y-axis lists the displayed sonority n-gram patterns.

For dense scores, the viewer samples y-axis rows at lower zoom levels and adds
more rows back as the user zooms in. This keeps the plot readable while still
allowing close inspection of the full pattern set.

The default CRIM corpus helper filters sonorities by beat strength. Some MEI
files import with valid sonorities but no beat-strength values. In that case,
when `minimum_beat_strength` is `0.0`, the tool recomputes sonority n-grams
without beat-strength filtering and returns a warning in the text and structured
payload. If `minimum_beat_strength` is greater than `0.0`, the tool raises a
clear error instead of pretending the filter was applied.

In multi-score mode, each score introduces only sonority n-gram patterns that
have not already appeared in earlier selected scores. This avoids duplicating
the same y-axis row across later score groups.

## Prerequisites

This tool requires an MCP client that supports the MCP Apps extension. Without
the extension, the tool still returns a textual summary with counts, progress
span, score metadata, and recurring displayed patterns.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `filename` | `str` | Conditionally | Name of one MEI file |
| `filenames` | `list[str]` | Conditionally | Two or more MEI files to compare |
| `n` | `int` | No | Sonority n-gram length. Defaults to `4` |
| `compound` | `bool` | No | Use compound interval classes in CRIM sonority analysis. Defaults to `True` |
| `sort` | `bool` | No | Sort sonority contents in CRIM analysis. Defaults to `False` |
| `minimum_beat_strength` | `float` | No | Minimum CRIM beat strength filter. Defaults to `0.0` |

Provide either `filename`, `filenames`, or both.

## Return Value

The tool returns a `ToolResult` with:

- **Text content**: A compact interpretive summary for chat clients
- **Structured content**: Score metadata, y-axis rows, and occurrence points for
  the viewer app

```python
{
    "filename": "Bartok_Mikrokosmos_022.mei",
    "filenames": ["Bartok_Mikrokosmos_022.mei"],
    "score_count": 1,
    "scores": [
        {
            "filename": "Bartok_Mikrokosmos_022.mei",
            "title": "Mikrokosmos No. 22: Imitation and Counterpoint, SZ 107: 22",
            "composer": "Bartok, Bela",
            "label": "Bartok, Bela | Mikrokosmos No. 22: Imitation and Counterpoint, SZ 107: 22",
            "color": "#74c7ec",
            "end_q": 104.0,
            "pattern_count": 44,
        }
    ],
    "n": 4,
    "kind": "low_line",
    "directed": True,
    "compound": True,
    "sort": False,
    "minimum_beat_strength": 0.0,
    "beat_strength_filter_applied": True,
    "beat_strength_fallback_filenames": [],
    "warnings": [],
    "rows": [
        {
            "id": "Bartok_Mikrokosmos_022.mei::M10_P5_M3_P4",
            "filename": "Bartok_Mikrokosmos_022.mei",
            "score_label": "Bartok, Bela | Mikrokosmos No. 22: Imitation and Counterpoint, SZ 107: 22",
            "score_index": 0,
            "pattern": ["M10", "P5", "M3", "P4"],
            "pattern_string": "M10_P5_M3_P4",
            "label": "M10_P5_M3_P4",
            "count": 2,
            "first_progress": 0.34,
            "color": "#74c7ec",
        }
    ],
    "occurrences": [
        {
            "id": "Bartok_Mikrokosmos_022.mei::M10_P5_M3_P4::36.0",
            "filename": "Bartok_Mikrokosmos_022.mei",
            "row_id": "Bartok_Mikrokosmos_022.mei::M10_P5_M3_P4",
            "score_label": "Bartok, Bela | Mikrokosmos No. 22: Imitation and Counterpoint, SZ 107: 22",
            "pattern": ["M10", "P5", "M3", "P4"],
            "pattern_string": "M10_P5_M3_P4",
            "voice_pair": "Low_Sonority",
            "start_measure": 10.0,
            "start_beat": 1.0,
            "start_q": 36.0,
            "progress": 0.34,
            "count_in_score": 2,
            "color": "#74c7ec",
            "score_index": 0,
        }
    ],
    "x_min": 0.0,
    "x_max": 1.0,
}
```

## Usage

!!! example "Try asking:"
    "Plot the sonority n-gram progress for Bartok_Mikrokosmos_022.mei"

!!! example "Compare multiple scores:"
    "Plot sonority n-gram progress for Bartok_Mikrokosmos_022.mei and Morley_1595_01_Go_ye_my_canzonettes.mei"

!!! example "Change n-gram length:"
    "Plot sonority n-gram progress for Bartok_Mikrokosmos_022.mei with n=3"

## How It Works

1. The tool resolves one or more MEI filenames
2. CRIM Intervals computes corpus-level sonority n-grams with offsets and
   normalized progress values
3. If CRIM returns no beat-strength values for a score, the tool can recompute
   sonority n-grams without the beat-strength filter and records that fallback
4. Each score contributes y-axis rows for newly introduced patterns
5. Occurrences are linked to those rows and plotted by normalized progress
6. The viewer samples dense y-axis rows at low zoom and reveals more rows as the
   user zooms in

## Use Cases

- Inspect where particular sonority patterns first appear in a score
- Compare the progress of low-line sonority patterns across related pieces
- Locate clusters of repeated sonority n-grams over the course of a piece
- Generate a text summary that helps an assistant describe the visualization

## Related Tools

- [plot_melodic_ngram_heatmap](melodic-ngram-heatmap.md) - Show melodic n-gram spans as timeline rectangles
- [get_melodic_ngrams](../intervals/ngrams.md) - Extract melodic n-gram tables
- [count_melodic_ngrams](../intervals/ngram-counts.md) - Rank melodic n-gram patterns by count
