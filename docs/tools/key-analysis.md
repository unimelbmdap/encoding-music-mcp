# analyze_key

Detect the musical key of a piece using music21's key detection algorithm.

## Overview

The `analyze_key` tool analyzes the pitch content of an MEI file to determine its musical key. It returns both the key name and a confidence factor indicating how certain the analysis is.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `filename` | `str` | Yes | Name of the MEI file (e.g., "Bach_BWV_0772.mei") |

## Returns

Returns a dictionary with two keys:

| Key | Type | Description |
|-----|------|-------------|
| `Key Name` | `str` | Detected key (e.g., "C major", "a minor") |
| `Confidence Factor` | `float` | Correlation coefficient between 0.0 and 1.0 |

## Example Usage

### With Claude Desktop

!!! example "Natural language queries"
    - "What key is Bach_BWV_0772.mei in?"
    - "Analyze the key of Morley_1595_01_Go_ye_my_canzonettes.mei"
    - "Compare the keys of all Bach inventions"

### Example Output

```json
{
  "Key Name": "C major",
  "Confidence Factor": 0.9451
}
```

## Understanding Confidence Factors

The confidence factor indicates how strongly the pitch content matches the detected key:

| Range | Interpretation | Example |
|-------|----------------|---------|
| **0.8 - 1.0** | Very confident - clear tonal center | Bach inventions, typical Classical/Romantic works |
| **0.5 - 0.8** | Moderate confidence - some ambiguity | Modal pieces, early music, chromatic passages |
| **0.0 - 0.5** | Low confidence - weak or ambiguous tonality | Atonal music, highly chromatic music |

!!! tip "Interpreting Results"
    High confidence doesn't always mean the analysis is "correct" - it means the pitch content strongly correlates with a particular key profile. Some pieces may be:

    - **Modal**: May report as major/minor with lower confidence
    - **Modulating**: Reports the overall or most prominent key
    - **Chromatic**: May have lower confidence even if clearly tonal

## Use Cases

### Single Piece Analysis

Determine the key of a specific piece:

```python
result = analyze_key("Bach_BWV_0772.mei")
print(f"Key: {result['Key Name']}")
print(f"Confidence: {result['Confidence Factor']:.2%}")
```

### Batch Analysis

Compare keys across a collection:

```python
files = list_available_mei_files()
for filename in files["bach_inventions"]:
    key_info = analyze_key(filename)
    print(f"{filename}: {key_info['Key Name']} "
          f"({key_info['Confidence Factor']:.2f})")
```

### Key Distribution Study

Analyze key usage in a corpus:

```python
from collections import Counter

keys = []
for filename in all_files:
    result = analyze_key(filename)
    keys.append(result['Key Name'])

key_counts = Counter(keys)
print(f"Most common keys: {key_counts.most_common(5)}")
```

## Algorithm

The tool uses music21's Krumhansl-Schmuckler key-finding algorithm, which:

1. Extracts all pitches from the score
2. Calculates a pitch-class distribution
3. Correlates with major and minor key profiles
4. Returns the key with the highest correlation

## Key Name Format

Keys are formatted as:

- **Major keys**: Capital letter + "major" (e.g., "C major", "F major")
- **Minor keys**: Lowercase letter + "minor" (e.g., "a minor", "d minor")
- **Accidentals**: Sharps (#) or flats (b) as needed (e.g., "F# major", "B♭ major")

## Limitations

### What This Tool Can't Do

- **Detect modulations**: Reports overall key, not key changes
- **Handle polytonality**: Reports single dominant key
- **Distinguish modes**: Reports as major or minor
- **Detect ambiguous cases**: Will still return highest correlation

!!! warning "Non-tonal Music"
    For atonal, serial, or highly experimental music, the confidence factor will be low and the reported key may not be meaningful.

## Related Tools

- [get_melodic_intervals](intervals/melodic.md) - Analyze melodic content
- [get_harmonic_intervals](intervals/harmonic.md) - Analyze harmonic content
- [list_available_mei_files](discovery.md) - Find files to analyze

## Error Handling

If a file doesn't exist:

```python
FileNotFoundError: [Errno 2] No such file or directory:
  'src/encoding_music_mcp/resources/nonexistent.mei'
```

## Implementation

Uses the music21 library:

```python
score = converter.parse(filepath)
key_analysis = score.analyze('key')
```
