# get_first_occur_melodic_ngrams

Find the first occurrence of each unique melodic n-gram in a score.

## Overview

The `get_first_occur_melodic_ngrams` tool counts melodic n-grams, groups note-ID matches by pattern, then keeps only the earliest occurrence of each distinct pattern across all parts. This is useful when you want a compact catalogue of melodic ideas with playback locations and highlightable note IDs.

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `filename` | `str` | Yes | - | Name of the MEI file |
| `n` | `int` | No | 4 | Length of melodic n-grams to extract |
| `kind` | `str` | No | `'d'` | Interval type: `'d'`, `'c'`, `'q'`, or `'z'` |
| `combine_unisons` | `bool` | No | `True` | Whether to combine unisons when extracting notes |
| `compound` | `bool` | No | `False` | Whether to use compound intervals |

## Returns

| Key | Type | Description |
|-----|------|-------------|
| `filename` | `str` | The input filename |
| `n` | `int` | The n-gram length used |
| `kind` | `str` | The interval type used |
| `combine_unisons` | `bool` | Whether unisons were combined |
| `compound` | `bool` | Whether compound intervals were used |
| `patterns` | `list[dict]` | First-occurrence pattern records |

Each entry in `patterns` contains:

```python
{
    "pattern": ["2", "2", "-3", "2"],
    "pattern_string": "2_2_-3_2",
    "count": 5,
    "start_q": 1.5,
    "duration": 2.0,
    "end_q": 3.5,
    "column": "1",
    "note_ids": ["n1", "n2", "n3", "n4", "n5"],
}
```

## Use Cases

- Build a compact inventory of melodic ideas in a piece
- Jump directly to the first appearance of a pattern for playback
- Feed `start_q` and `end_q` into `play_excerpt` to hear what a returned n-gram sounds like
- Feed `note_ids` into notation highlighting tools
- Compare which motives appear earliest in different voices

## Related Tools

- [get_melodic_ngrams](ngrams.md) - Return all melodic n-gram occurrences
- [count_melodic_ngrams](ngram-counts.md) - Count and rank all melodic n-gram patterns
- [get_melodic_ngram_matches](ngram-matches.md) - Return pattern-keyed note-ID spans
- [get_melodic_intervals](melodic.md) - Inspect the interval stream that the patterns come from
- [play_excerpt](../play-excerpt.md) - Listen to the returned `start_q` / `end_q` pattern windows
