# get_harmonic_intervals

Calculate harmonic intervals between voice parts.

## Overview

The `get_harmonic_intervals` tool analyzes the vertical (harmonic) relationships between voices, calculating the interval between simultaneously sounding notes.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `filename` | `str` | Yes | Name of the MEI file (e.g., "Bach_BWV_0772.mei") |

## Returns

| Key | Type | Description |
|-----|------|-------------|
| `filename` | `str` | The input filename |
| `harmonic_intervals` | `str` | Formatted dataframe of intervals |

## Example Output

```
                2_1
Measure Beat
1.0     1.000  Rest
        1.250  Rest
        3.250   P12
        3.500   m14
        3.750   m13
        4.000   A11
        4.250   M13
        4.500   m13
        4.750   P15
2.0     1.000   P12
```

## Understanding the Output

### Column Names

- `2_1`: Interval from voice 2 to voice 1 (lower to upper)
- `3_2`: Interval from voice 3 to voice 2
- Multi-voice pieces will have multiple columns

### Interval Values

- **Compound intervals**: Numbers > 8 (e.g., `P12` = octave + perfect 5th)
- **Simple intervals**: Numbers ≤ 8 (e.g., `P5`, `M3`)
- **Rest**: One or both voices resting
- **NaN**: Not applicable (voices not sounding together)

## Common Harmonic Intervals

| Interval | Quality | Example |
|----------|---------|---------|
| `P1` | Perfect unison | Same pitch |
| `M3` | Major third | Consonant |
| `m3` | Minor third | Consonant |
| `P5` | Perfect fifth | Consonant |
| `M6` | Major sixth | Consonant |
| `m7` | Minor seventh | Dissonant |
| `M7` | Major seventh | Dissonant |
| `P8` | Perfect octave | Consonant |
| `P12` | Perfect 12th | Compound 5th |
| `M13` | Major 13th | Compound 6th |

## Use Cases

### Consonance and Dissonance Analysis

Identify harmonic stability:

- **Consonant**: `P1`, `m3`, `M3`, `P5`, `m6`, `M6`, `P8`
- **Dissonant**: `m2`, `M2`, `A4`, `d5`, `m7`, `M7`

### Voice Leading Study

Track how harmonic intervals change over time:

```
P8 → M10 → P12 (expanding motion)
P12 → M10 → P8 (contracting motion)
```

### Parallel Motion Detection

Look for sequences of the same interval:

```
M3, M3, M3 (parallel thirds)
P5, P5, P5 (parallel fifths - often avoided in counterpoint)
```

### Harmonic Rhythm

Analyze how often harmonies change by looking at interval changes.

## Related Tools

- [get_melodic_intervals](melodic.md) - Analyze melodic motion
- [get_notes](notes.md) - See the actual notes
- [analyze_key](../key-analysis.md) - Determine overall tonality
