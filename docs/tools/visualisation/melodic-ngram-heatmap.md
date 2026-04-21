# Melodic N-gram Heatmap

`plot_melodic_ngram_heatmap` plots repeated melodic n-gram patterns as
timeline rectangles for one or more MEI scores. Rows are separated by score and
staff, and colours identify the most frequent patterns across the selected
pieces.

## Parameters

- `filename` (`str | None`): One MEI filename.
- `filenames` (`list[str] | None`): Multiple MEI filenames.
- `n` (`int`, optional): N-gram length. Defaults to `4`.
- `kind` (`str`, optional): CRIM interval kind. Defaults to `"d"`.
- `entries` (`bool`, optional): Restrict to entry-filtered n-grams. Defaults to
  `False`.
- `top_n` (`int`, optional): Number of top patterns to colour and plot. Defaults
  to `2`.
- `combine_unisons` (`bool | None`, optional): Passed through to CRIM note
  extraction.
- `compound` (`bool`, optional): Whether to use compound intervals. Defaults to
  `False`.

## Returns

The tool returns an MCP App payload with:

```python
{
    "filenames": list[str],
    "score_count": int,
    "n": int,
    "kind": str,
    "top_n": int,
    "patterns": [
        {
            "pattern": list[str],
            "pattern_string": str,
            "count": int,
            "color": str,
        }
    ],
    "rows": [
        {
            "id": str,
            "filename": str,
            "score_label": str,
            "staff": str,
            "label": str,
            "end_q": float,
        }
    ],
    "occurrences": [
        {
            "row_id": str,
            "pattern_string": str,
            "start_q": float,
            "end_q": float,
            "duration": float,
            "start_measure": float,
            "start_beat": float,
            "note_ids": list[str],
            "color": str,
        }
    ],
}
```

!!! note
    Requires the MCP Apps extension for inline display.

## Payload Sent To The App

The Python tool returns a `ToolResult` with a short text fallback plus
`structured_content`. The HTML app reads that payload from
`result.structuredContent`:

```javascript
app.ontoolresult = (result) => {
    const structured = result.structuredContent;
    render(structured);
};
```

Example `structured_content`:

```python
{
    "filename": "Bach_BWV_0772.mei",
    "filenames": ["Bach_BWV_0772.mei", "Bartok_Mikrokosmos_022.mei"],
    "score_count": 2,
    "scores": [
        {
            "filename": "Bach_BWV_0772.mei",
            "title": "...",
            "composer": "...",
        },
        {
            "filename": "Bartok_Mikrokosmos_022.mei",
            "title": "...",
            "composer": "...",
        },
    ],
    "n": 4,
    "kind": "d",
    "entries": False,
    "top_n": 2,
    "combine_unisons": None,
    "compound": False,
    "patterns": [
        {
            "pattern": ["2", "2", "2", "-3"],
            "pattern_string": "2_2_2_-3",
            "count": 12,
            "color": "#d92b8a",
        }
    ],
    "rows": [
        {
            "id": "Bach_BWV_0772.mei::1",
            "filename": "Bach_BWV_0772.mei",
            "score_label": "...",
            "staff": "1",
            "label": "... - Staff 1",
            "end_q": 104.0,
        }
    ],
    "occurrences": [
        {
            "id": "Bach_BWV_0772.mei::1::2_2_2_-3::0.0",
            "filename": "Bach_BWV_0772.mei",
            "row_id": "Bach_BWV_0772.mei::1",
            "staff": "1",
            "pattern": ["2", "2", "2", "-3"],
            "pattern_string": "2_2_2_-3",
            "start_q": 0.0,
            "end_q": 2.5,
            "duration": 2.5,
            "start_measure": 1.0,
            "start_beat": 1.0,
            "note_ids": ["..."],
            "color": "#d92b8a",
        }
    ],
    "x_min": 0.0,
    "x_max": 104.0,
}
```

The app mainly uses:

- `scores` for the header metadata
- `n`, `kind`, `entries`, and `patterns.length` for the summary line
- `patterns` for the legend
- `rows` for the y-axis score/staff rows
- `occurrences` for coloured rectangles
- `x_max` for scaling the timeline axis
