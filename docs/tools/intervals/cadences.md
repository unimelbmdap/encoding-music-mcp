# Cadence Detection

Extract and analyze predicted cadences in Renaissance counterpoint using CRIM Intervals.

## Overview

The `get_cadences` tool uses machine learning to identify and classify cadences in Renaissance polyphonic music. It analyzes voice leading patterns and harmonic progressions to predict cadence locations and types.

## Usage

```python
from encoding_music_mcp.tools import get_cadences

result = get_cadences("Morley_1595_01_Go_ye_my_canzonettes.mei")
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `filename` | `str` | Yes | Name of the MEI file to analyze |

## Returns

Returns a dictionary with the following keys:

| Key | Type | Description |
|-----|------|-------------|
| `filename` | `str` | The input filename |
| `cadences` | `str` | CSV representation of the cadences dataframe |

## Output Format

The cadences dataframe includes the following columns:

| Column | Description |
|--------|-------------|
| `Composer` | Composer name from MEI metadata |
| `Title` | Work title from MEI metadata |
| `Measure` | Measure number where cadence occurs |
| `Beat` | Beat position within the measure |
| `Progress` | Progress through the piece (0.0-1.0) |
| `CadType` | Cadence type (Authentic, Plagal, etc.) |
| `Tone` | The tonal centre of the cadence |
| `CVFs` | Cadential Voice Functions for each voice |

### Example Output

```
Composer,Title,Measure,Beat,Progress,CadType,Tone,CVFs
"Morley, Thomas",Go ye my canzonettes,14,2.0,0.186,Authentic,G,"['Ct', 'T']"
"Morley, Thomas",Go ye my canzonettes,21,4.0,0.298,Plagal,D,"['Ct', 'T']"
"Morley, Thomas",Go ye my canzonettes,30,4.0,0.421,Authentic,C,"['Ct', 'T']"
```

## Cadence Types

The tool identifies several cadence types common in Renaissance music:

### Authentic Cadence
- Strongest conclusive cadence
- Typically involves dominant-to-tonic motion
- Features characteristic voice leading patterns

### Plagal Cadence
- Subdominant-to-tonic motion
- Often called the "Amen" cadence
- Provides a sense of resolution

### Phrygian Cadence
- Half cadence with distinctive semitone motion in the bass
- Common in Renaissance music
- Often signals a temporary resting point

### Evaded Cadence
- Expected cadence is avoided or interrupted
- Creates harmonic surprise or continuation

## Cadential Voice Functions (CVFs)

The CVFs column describes the role each voice plays in the cadence:

| Function | Description |
|----------|-------------|
| `T` | Tenor (structural voice) |
| `Ct` | Cantus (often the highest voice) |
| `B` | Bassus (lowest voice) |
| `A` | Altus (middle voice) |

## Best Practices

### Suitable Repertoire

This tool is optimised for:
- Renaissance polyphony (15th-17th century)
- Sacred and secular vocal music
- Italian, English, and Franco-Flemish styles
- Works with clear voice leading

### Interpretation

Remember that:
- Cadence detection uses machine learning predictions
- Results may vary based on texture and style
- Some cadences may be more clearly defined than others
- Context and musical judgment are still important

### Analysis Workflow

1. **Initial Detection**: Run `get_cadences` to identify potential cadences
2. **Review Locations**: Check measure and beat positions
3. **Verify Types**: Confirm cadence types match musical context
4. **Analyse Patterns**: Look for recurring cadential formulas
5. **Compare Pieces**: Study cadence usage across works

## Example Analysis

```python
# Analyse cadences in a Morley canzonet
result = get_cadences("Morley_1595_01_Go_ye_my_canzonettes.mei")

# The output shows:
# - 8 cadences throughout the piece
# - Mix of Authentic and Plagal types
# - Cadences at structural points (measures 14, 21, 30, etc.)
# - Consistent voice functions in two-part texture
```

## Use Cases

### Form Analysis
- Identify section boundaries
- Map large-scale structure
- Study phrase lengths

### Style Comparison
- Compare cadential practices between composers
- Analyse historical trends
- Study regional differences

### Voice Leading
- Examine cadential formulas
- Study approach patterns
- Analyse resolution types

### Structural Analysis
- Identify important arrival points
- Understand tonal hierarchy
- Map harmonic rhythm

## Related Tools

- [`get_notes`](notes.md) - View the actual notes at cadence points
- [`get_harmonic_intervals`](harmonic.md) - Analyse voice leading at cadences
- [`get_melodic_intervals`](melodic.md) - Study melodic approach to cadences

## Technical Details

The cadence detection algorithm:
- Analyses simultaneous intervals between voices
- Identifies characteristic voice-leading patterns
- Considers melodic motion in approach to cadence
- Classifies cadence type based on learned patterns
- Extracts tonal centre from harmonic context

## Limitations

- Optimised for Renaissance counterpoint
- May be less accurate for:
  - Highly chromatic passages
  - Unusual textures
  - Non-Western music
  - Instrumental music with different conventions
- Predictions should be verified musically

## See Also

- [CRIM Intervals Documentation](https://github.com/HCDigitalScholarship/intervals)
- [Renaissance Cadence Types](https://www.britannica.com/art/cadence-music)
- [Voice Leading in Renaissance Music](https://en.wikipedia.org/wiki/Voice_leading)
