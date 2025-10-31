# get_melodic_intervals

Calculate melodic intervals within each voice part.

## Overview

The `get_melodic_intervals` tool analyzes the melodic motion within each voice, calculating the interval between each consecutive pair of notes.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `filename` | `str` | Yes | Name of the MEI file (e.g., "Bach_BWV_0772.mei") |

## Returns

| Key | Type | Description |
|-----|------|-------------|
| `filename` | `str` | The input filename |
| `melodic_intervals` | `str` | Formatted dataframe of intervals |

## Example Output

```
                  1     2
Measure Beat
1.0     1.000  Rest  Rest
        1.500    M2   NaN
        1.750    M2   NaN
        2.000    m2   NaN
        2.250   -m3   NaN
        2.500    M2   NaN
        2.750   -M3   NaN
        3.000    P5   NaN
        3.500    P4    M2
```

## Understanding the Output

- **Positive intervals**: Ascending motion (e.g., `M2` = up a major second)
- **Negative intervals**: Descending motion (e.g., `-M3` = down a major third)
- **Rest**: Beginning of melodic line
- **NaN**: Voice is silent

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
