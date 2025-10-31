# get_notes

Extract all notes from an MEI file with pitch and octave information.

## Overview

The `get_notes` tool extracts every note from an MEI file, displaying pitch names and octave numbers organized by measure, beat, and voice part.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `filename` | `str` | Yes | Name of the MEI file (e.g., "Bach_BWV_0772.mei") |

## Returns

| Key | Type | Description |
|-----|------|-------------|
| `filename` | `str` | The input filename |
| `notes` | `str` | Formatted dataframe of notes |

## Example Output

```
                  1     2
Measure Beat
1.0     1.000  Rest  Rest
        1.250    C4   NaN
        1.500    D4   NaN
        1.750    E4   NaN
        2.000    F4   NaN
        2.250    D4   NaN
        2.500    E4   NaN
        2.750    C4   NaN
        3.000    G4   NaN
        3.250   NaN    C3
        3.500    C5    D3
```

## Note Representation

- **Pitch + Octave**: `C4`, `D5`, `B♭3`
- **Rest**: `Rest`
- **No note**: `NaN` (voice is silent at this moment)

### Octave Numbers

Following scientific pitch notation:

- `C4` = Middle C
- `C3` = One octave below middle C
- `C5` = One octave above middle C

## Use Cases

### Basic Note Inventory

See what notes appear in a piece:

```python
notes = get_notes("Bach_BWV_0772.mei")
print(notes["notes"])
```

### Voice Part Analysis

Identify when each voice enters and rests:

- Look for `Rest` to find rests
- Look for `NaN` to find where voices are silent

### Preparation for Interval Analysis

Notes extraction is typically the first step before melodic or harmonic interval analysis.

## Related Tools

- [get_melodic_intervals](melodic.md) - Calculate intervals from these notes
- [get_harmonic_intervals](harmonic.md) - Compare notes between voices
- [Intervals Overview](index.md) - Learn about interval analysis
