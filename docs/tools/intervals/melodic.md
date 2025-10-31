# get_melodic_intervals

Calculate melodic intervals within each voice part.

## Overview

The `get_melodic_intervals` tool analyzes the melodic motion within each voice, calculating the interval between each consecutive pair of notes.

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `filename` | `str` | Yes | - | Name of the MEI file (e.g., "Bach_BWV_0772.mei") |
| `kind` | `str` | No | 'd' | Interval type: 'd' (diatonic), 'c' (chromatic), 'q' (with quality), 'z' (zero-based) |

## Returns

| Key | Type | Description |
|-----|------|-------------|
| `filename` | `str` | The input filename |
| `kind` | `str` | The interval type used |
| `melodic_intervals` | `str` | CSV representation of intervals dataframe |

## Example Output

```csv
Measure,Beat,1,2
1.0,1.0,Rest,Rest
1.0,1.5,M2,
1.0,1.75,M2,
1.0,2.0,m2,
1.0,2.25,-m3,
1.0,2.5,M2,
1.0,2.75,-M3,
1.0,3.0,P5,
1.0,3.5,P4,M2
```

## Understanding the Output

- **Positive intervals**: Ascending motion (e.g., `M2` = up a major second)
- **Negative intervals**: Descending motion (e.g., `-M3` = down a major third)
- **Rest**: Beginning of melodic line
- **NaN**: Voice is silent

## Interval Types (`kind` parameter)

The `kind` parameter controls how intervals are calculated:

### Diatonic (`kind='d'`, default)

Basic scale degrees without quality information:

```python
result = get_melodic_intervals("Bach_BWV_0772.mei", kind='d')
# Example: 2, -3, 5 (up 2nd, down 3rd, up 5th)
```

### Chromatic (`kind='c'`)

Semitone distances - useful for atonal/twelve-tone analysis:

```python
result = get_melodic_intervals("Bach_BWV_0772.mei", kind='c')
# Example: 2, -4, 7 (up 2 semitones, down 4 semitones, up 7 semitones)
```

### With Quality (`kind='q'`)

Includes major/minor/perfect quality - ideal for detailed tonal analysis:

```python
result = get_melodic_intervals("Bach_BWV_0772.mei", kind='q')
# Example: M2, -m3, P5 (major 2nd up, minor 3rd down, perfect 5th up)
```

This is the most detailed option and is shown in the example output above.

### Zero-based (`kind='z'`)

Zero-indexed diatonic intervals for computational analysis:

```python
result = get_melodic_intervals("Bach_BWV_0772.mei", kind='z')
# Example: 1, -2, 4 (same as 2, -3, 5 but zero-indexed)
```

!!! tip "Which Kind to Use?"
    - **'d'** - Quick overview of melodic motion
    - **'c'** - Analyzing chromatic or atonal music
    - **'q'** - Detailed tonal analysis (most common)
    - **'z'** - Statistical or computational work

## Common Melodic Intervals

| Interval | Semitones | Musical Distance |
|----------|-----------|-----------------|
| `M2` | 2 | Whole step up |
| `m2` | 1 | Half step up |
| `M3` | 4 | Major third up |
| `m3` | 3 | Minor third up |
| `P4` | 5 | Perfect fourth up |
| `P5` | 7 | Perfect fifth up |
| `P8` | 12 | Octave up |

## Use Cases

### Melodic Contour Analysis

Identify stepwise vs. leaping motion:

- Steps: `M2`, `m2`, `-M2`, `-m2`
- Leaps: `M3`, `P4`, `P5`, etc.

### Identify Melodic Patterns

Look for recurring interval sequences:

```
M2, M2, m2 (ascending major scale fragment)
-m3, M2, -m3 (zig-zag pattern)
```

### Voice Leading Study

Analyze how each voice moves independently:

- Mostly stepwise = smooth voice leading
- Many leaps = more disjunct motion

### Stylistic Analysis

Compare interval usage across composers or periods:

- Renaissance: Mostly stepwise
- Baroque: Mix of steps and leaps
- Romantic: Larger leaps more common

## Related Tools

- [get_notes](notes.md) - See the actual notes
- [get_melodic_ngrams](ngrams.md) - Find recurring patterns
- [get_harmonic_intervals](harmonic.md) - Analyze intervals between voices
