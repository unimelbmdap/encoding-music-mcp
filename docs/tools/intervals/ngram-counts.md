# count_melodic_ngrams

Count and rank melodic n-gram patterns by frequency.

## Overview

This helper is designed for questions like:

- "How many times does each pattern occur?"
- "What are the top 2 melodic n-grams?"
- "Which motive is most common in this piece?"

Instead of returning one row per location, it groups occurrences by pattern string and returns counts sorted from most frequent to least frequent.

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `filename` | `str` | Yes | - | Name of the MEI file |
| `n` | `int` | No | 4 | Length of n-grams to extract |
| `kind` | `str` | No | `'d'` | Interval type: `'d'`, `'c'`, `'q'`, or `'z'` |
| `entries` | `bool` | No | `False` | Restrict to thematic entries only |

## Returns

| Key | Type | Description |
|-----|------|-------------|
| `filename` | `str` | The input filename |
| `n` | `int` | The n-gram length used |
| `kind` | `str` | The interval type used |
| `entries` | `bool` | Whether entry filtering was applied |
| `pattern_counts` | `list[dict]` | Ranked pattern counts |

## Example Output

```python
{
    "filename": "Bach_BWV_0772.mei",
    "n": 4,
    "kind": "d",
    "entries": False,
    "pattern_counts": [
        {"pattern": ["2", "2", "2", "-3"], "pattern_string": "2_2_2_-3", "count": 6},
        {"pattern": ["2", "2", "-3", "2"], "pattern_string": "2_2_-3_2", "count": 5},
    ],
}
```

## Typical Workflow

1. Use [`get_melodic_ngrams`](ngrams.md) to inspect the full location table.
2. Use `count_melodic_ngrams` to answer frequency and ranking questions.
3. Use [`get_melodic_ngram_matches`](ngram-matches.md) only for the patterns you want to highlight.
