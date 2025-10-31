# get_melodic_ngrams

Find recurring melodic patterns using n-gram analysis.

## Overview

The `get_melodic_ngrams` tool identifies sequences of melodic intervals (n-grams) in each voice. This is useful for finding recurring motifs, sequences, and melodic patterns.

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `filename` | `str` | Yes | - | Name of the MEI file |
| `n` | `int` | No | 4 | Length of n-grams to extract |

## Returns

| Key | Type | Description |
|-----|------|-------------|
| `filename` | `str` | The input filename |
| `n` | `int` | The n-gram length used |
| `melodic_ngrams` | `str` | Formatted dataframe of n-grams |

## Example Output

### With n=4 (default)

```
                         1            2
Measure Beat
1.0     1.500     2_2_2_-3          NaN
        1.750     2_2_-3_2          NaN
        2.000    2_-3_2_-3          NaN
        2.250    -3_2_-3_5          NaN
        2.500     2_-3_5_4          NaN
        3.500     4_-2_2_2     2_2_2_-3
```

### With n=3

```
                      1         2
Measure Beat
1.0     1.500     2_2_2       NaN
        1.750    2_2_-3       NaN
        2.000    2_-3_2       NaN
        2.250   -3_2_-3       NaN
```

## Understanding N-grams

### Format

N-grams are represented as underscore-separated interval sequences:

- `2_2_2_-3` = M2, M2, M2, -m3 (three major seconds up, then minor third down)
- `5_4_-2` = P5, P4, -M2 (fifth up, fourth up, major second down)

### Choosing N

- **n=2**: Very short patterns, many matches
- **n=3**: Short motifs
- **n=4**: Standard motif length (default)
- **n=5-6**: Longer phrases
- **n=7+**: Extended melodic ideas

!!! tip "Finding the Right N"
    Start with n=4. If patterns are too common, increase n. If too few matches, decrease n.

## Use Cases

### Find Recurring Motifs

Identify melodic ideas that repeat:

```python
result = get_melodic_ngrams("Bach_BWV_0772.mei", n=4)
# Look for the same pattern appearing multiple times
```

### Sequence Detection

Find sequences (patterns that repeat at different pitch levels):

```
2_2_2 appearing multiple times = ascending major scale fragments
```

### Motivic Analysis

Compare motifs across pieces:

```python
bach_ngrams = get_melodic_ngrams("Bach_BWV_0772.mei")
bartok_ngrams = get_melodic_ngrams("Bartok_Mikrokosmos_022.mei")
# Compare common patterns
```

### Imitation Study

Find where voices imitate each other's melodies:

```
Voice 1: 2_2_2_-3 at measure 1
Voice 2: 2_2_2_-3 at measure 3 (imitation!)
```

## Pattern Interpretation

### Reading Interval Sequences

Example: `2_-3_2_-3`

1. M2 up (major second ascending)
2. -m3 down (minor third descending)
3. M2 up (major second ascending)
4. -m3 down (minor third descending)

This creates a zig-zag pattern.

### Common Patterns

| Pattern | Meaning |
|---------|---------|
| `2_2_2` | Ascending major scale fragment |
| `-2_-2_-2` | Descending major scale fragment |
| `3_4` | Minor triad outline |
| `4_3` | Major triad outline |
| `7_0_-7` | Octave leap and return |

## Adjusting Analysis

### For Short Motifs

Use smaller n:

```python
result = get_melodic_ngrams("Bach_BWV_0772.mei", n=3)
```

### For Extended Phrases

Use larger n:

```python
result = get_melodic_ngrams("Bach_BWV_0772.mei", n=6)
```

## Related Tools

- [get_melodic_intervals](melodic.md) - See the underlying intervals
- [get_notes](notes.md) - See the actual notes
- [Intervals Overview](index.md) - Learn about interval analysis
