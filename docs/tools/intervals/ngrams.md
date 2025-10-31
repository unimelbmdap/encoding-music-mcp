# get_melodic_ngrams

Find recurring melodic patterns using n-gram analysis.

## Overview

The `get_melodic_ngrams` tool identifies sequences of melodic intervals (n-grams) in each voice. This is useful for finding recurring motifs, sequences, and melodic patterns.

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `filename` | `str` | Yes | - | Name of the MEI file |
| `n` | `int` | No | 4 | Length of n-grams to extract |
| `kind` | `str` | No | 'd' | Interval type: 'd' (diatonic), 'c' (chromatic), 'q' (with quality), 'z' (zero-based) |
| `entries` | `bool` | No | False | Filter to thematic entries only (after rests/breaks) |

## Returns

| Key | Type | Description |
|-----|------|-------------|
| `filename` | `str` | The input filename |
| `n` | `int` | The n-gram length used |
| `kind` | `str` | The interval type used |
| `entries` | `bool` | Whether entry filtering was applied |
| `melodic_ngrams` | `str` | CSV representation of n-grams dataframe |

## Example Output

### With n=4 (default)

```csv
Measure,Beat,1,2
1.0,1.5,2_2_2_-3,
1.0,1.75,2_2_-3_2,
1.0,2.0,2_-3_2_-3,
1.0,2.25,-3_2_-3_5,
1.0,2.5,2_-3_5_4,
1.0,3.5,4_-2_2_2,2_2_2_-3
```

### With n=3

```csv
Measure,Beat,1,2
1.0,1.5,2_2_2,
1.0,1.75,2_2_-3,
1.0,2.0,2_-3_2,
1.0,2.25,-3_2_-3,
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

## Interval Types (`kind` parameter)

The `kind` parameter controls how intervals are calculated:

### Diatonic (`kind='d'`, default)

Basic scale degrees, no quality information:

```python
result = get_melodic_ngrams("Bach_BWV_0772.mei", kind='d')
# Example: 2_-3_2 (up 2nd, down 3rd, up 2nd)
```

### Chromatic (`kind='c'`)

Semitone distances:

```python
result = get_melodic_ngrams("Bach_BWV_0772.mei", kind='c')
# Example: 2_-4_2 (up 2 semitones, down 4 semitones, up 2 semitones)
```

### With Quality (`kind='q'`)

Includes major/minor/perfect quality - ideal for tonal analysis:

```python
result = get_melodic_ngrams("Bach_BWV_0772.mei", kind='q')
# Example: M2_-m3_M2 (major 2nd up, minor 3rd down, major 2nd up)
```

### Zero-based (`kind='z'`)

Zero-indexed diatonic intervals (for computational analysis):

```python
result = get_melodic_ngrams("Bach_BWV_0772.mei", kind='z')
# Example: 1_-2_1 (same as 2_-3_2 but zero-indexed)
```

!!! tip "Which Kind to Use?"
    - **'d'** - General pattern recognition
    - **'c'** - Atonal/twelve-tone analysis
    - **'q'** - Tonal/harmonic analysis (most detailed)
    - **'z'** - Computational/statistical analysis

## Thematic Entries (`entries` parameter)

The `entries` parameter filters ngrams to show only those occurring after:

- Rests
- Section breaks
- Fermatas

This is **extremely useful** for identifying thematic material and primary motives.

### Standard Analysis (all ngrams)

```python
result = get_melodic_ngrams("Morley_1595_01_Go_ye_my_canzonettes.mei", n=4)
# Returns hundreds of ngrams
```

### Thematic Analysis (entries only)

```python
result = get_melodic_ngrams(
    "Morley_1595_01_Go_ye_my_canzonettes.mei",
    n=4,
    entries=True
)
# Returns only ~13 thematic entries - the main motives!
```

Example output with `entries=True`:

```csv
Measure,Beat,Offset,1,2
1.0,1.0,0.0,1_1_2_1,
2.0,1.0,4.0,,1_1_2_1
9.0,1.0,32.0,1_1_2_1,
14.0,2.0,53.0,,1_1_4_-3
21.0,4.0,83.0,-4_2_2_-3,
```

!!! tip "Thematic Analysis Workflow"
    1. Use `entries=True` to find main motives
    2. Use `entries=False` (default) to see all occurrences
    3. Compare entry patterns across pieces to find thematic relationships

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
