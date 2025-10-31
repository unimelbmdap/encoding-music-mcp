# Interval Analysis Tools

Comprehensive interval analysis using the CRIM Intervals library.

## Overview

The interval analysis tools provide detailed melodic and harmonic analysis of MEI files. Built on the [CRIM Intervals](https://github.com/HCDigitalScholarship/intervals) library, these tools extract notes, calculate intervals, and identify recurring patterns.

## Available Tools

| Tool | Purpose | Learn More |
|------|---------|------------|
| [`get_notes`](notes.md) | Extract all notes with pitch and octave information | [Documentation](notes.md) |
| [`get_melodic_intervals`](melodic.md) | Calculate melodic intervals within each voice | [Documentation](melodic.md) |
| [`get_harmonic_intervals`](harmonic.md) | Calculate harmonic intervals between voices | [Documentation](harmonic.md) |
| [`get_melodic_ngrams`](ngrams.md) | Find recurring melodic patterns (n-grams) | [Documentation](ngrams.md) |

## Common Features

All interval tools share these characteristics:

### Dataframe Format

Results are returned as formatted strings representing dataframes:

- **Rows**: Measure and beat positions (e.g., `1.0 1.500` = measure 1, beat 1.5)
- **Columns**: Voice parts numbered sequentially (1, 2, 3, ...)
- **Values**: Notes, intervals, or patterns

### Example Structure

```
                  1     2
Measure Beat
1.0     1.000  Rest  Rest
        1.250    C4   NaN
        1.500    D4   NaN
        1.750    E4   NaN
```

### Return Format

All tools return dictionaries with consistent keys:

```python
{
    "filename": "Bach_BWV_0772.mei",
    "notes": "...",        # Or melodic_intervals, harmonic_intervals, melodic_ngrams
    # Additional keys depending on tool
}
```

## Understanding Intervals

### Interval Notation

Intervals use standard music theory abbreviations:

| Notation | Meaning | Semitones |
|----------|---------|-----------|
| `P1` | Perfect unison | 0 |
| `m2` | Minor 2nd | 1 |
| `M2` | Major 2nd | 2 |
| `m3` | Minor 3rd | 3 |
| `M3` | Major 3rd | 4 |
| `P4` | Perfect 4th | 5 |
| `A4` | Augmented 4th | 6 |
| `d5` | Diminished 5th | 6 |
| `P5` | Perfect 5th | 7 |
| `m6` | Minor 6th | 8 |
| `M6` | Major 6th | 9 |
| `m7` | Minor 7th | 10 |
| `M7` | Major 7th | 11 |
| `P8` | Perfect octave | 12 |

### Direction

- **Positive intervals**: Ascending motion (e.g., `M3`)
- **Negative intervals**: Descending motion (e.g., `-M3`)

### Compound Intervals

Intervals larger than an octave use numbers above 8:

- `M9` = Major 9th (octave + major 2nd)
- `P11` = Perfect 11th (octave + perfect 4th)
- `M13` = Major 13th (octave + major 6th)

## Workflow

A typical analysis workflow might be:

1. **Extract Notes** with [`get_notes`](notes.md)
2. **Analyze Melody** with [`get_melodic_intervals`](melodic.md)
3. **Analyze Harmony** with [`get_harmonic_intervals`](harmonic.md)
4. **Find Patterns** with [`get_melodic_ngrams`](ngrams.md)

## Use Cases

### Melodic Analysis
- Identify stepwise vs. leaping motion
- Analyze melodic contour
- Find recurring motivic patterns

### Harmonic Analysis
- Study voice leading
- Identify consonance and dissonance
- Analyze harmonic rhythm

### Pattern Recognition
- Find recurring melodic figures
- Compare motivic usage across pieces
- Identify sequences and imitations

### Comparative Studies
- Compare interval usage across composers
- Analyze stylistic differences
- Study historical trends

## About CRIM Intervals

[CRIM Intervals](https://github.com/HCDigitalScholarship/intervals) is a Python library developed by the CRIM (Citations: The Renaissance Imitation Mass) Project for analyzing Renaissance polyphony. It provides:

- Robust interval calculation
- N-gram pattern matching
- Support for various music encoding formats
- Integration with music21

## Next Steps

Explore the individual tool documentation:

- [Notes Extraction](notes.md)
- [Melodic Intervals](melodic.md)
- [Harmonic Intervals](harmonic.md)
- [Melodic N-grams](ngrams.md)
