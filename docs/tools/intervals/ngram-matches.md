# get_melodic_ngram_matches

Group melodic n-gram note-ID spans by pattern string.

## Overview

This helper is useful when you already know which pattern or patterns matter and want the exact note IDs for highlighting.

Instead of returning every occurrence as a location-keyed row, it returns a dictionary keyed by pattern string such as `2_2_2_-3`.

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `filename` | `str` | Yes | - | Name of the MEI file |
| `n` | `int` | No | 4 | Length of n-grams to extract |
| `kind` | `str` | No | `'d'` | Interval type: `'d'`, `'c'`, `'q'`, or `'z'` |
| `entries` | `bool` | No | `False` | Restrict to thematic entries only |
| `patterns` | `list[str] \| None` | No | `None` | Optional underscore-separated pattern filters |
| `combine_unisons` | `bool \| None` | No | `None` | Whether to combine unisons when extracting notes |
| `compound` | `bool` | No | `False` | Whether to use compound intervals |

## Returns

| Key | Type | Description |
|-----|------|-------------|
| `filename` | `str` | The input filename |
| `n` | `int` | The n-gram length used |
| `kind` | `str` | The interval type used |
| `entries` | `bool` | Whether entry filtering was applied |
| `patterns` | `list[str]` | The requested filters |
| `combine_unisons` | `bool \| None` | Whether unison combining was explicitly applied |
| `compound` | `bool` | Whether compound intervals were used |
| `matches_by_pattern` | `dict[str, list[dict]]` | Occurrence records grouped by pattern |

## Example Output

```python
{
    "filename": "Bach_BWV_0772.mei",
    "n": 4,
    "kind": "d",
    "entries": False,
    "patterns": ["2_2_2_-3"],
    "matches_by_pattern": {
        "2_2_2_-3": [
            {
                "pattern": ["2", "2", "2", "-3"],
                "column": "1",
                "start_measure": 1.0,
                "start_beat": 1.25,
                "start_offset": 0.25,
                "duration": 1.25,
                "end_offset": 1.5,
                "note_ids": ["nz7y0rb", "n1ecjh8t", "na90xbl", "n67c47", "nqqw2wk"],
            }
        ]
    },
}
```

## Why This Helps

- Highlighting a single pattern no longer requires returning note IDs for every other pattern.
- Pattern-keyed output is easier to pass into notation tools and future multi-colour highlighting workflows.
- Multiple patterns can be requested together, making side-by-side colouring easier later.

## Related Tools

- [`get_melodic_ngrams`](ngrams.md) for the full pattern table
- [`count_melodic_ngrams`](ngram-counts.md) for ranked frequency summaries
