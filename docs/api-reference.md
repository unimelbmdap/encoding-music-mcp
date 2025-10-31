# API Reference

Complete reference for all encoding-music-mcp tools.

## Tool Catalog

| Tool | Parameters | Returns | Documentation |
|------|------------|---------|---------------|
| `list_available_mei_files` | None | `dict` with file lists | [Docs](tools/discovery.md) |
| `get_mei_metadata` | `filename: str` | `dict` with metadata | [Docs](tools/metadata.md) |
| `analyze_key` | `filename: str` | `dict` with key info | [Docs](tools/key-analysis.md) |
| `get_notes` | `filename: str` | `dict` with notes | [Docs](tools/intervals/notes.md) |
| `get_melodic_intervals` | `filename: str` | `dict` with intervals | [Docs](tools/intervals/melodic.md) |
| `get_harmonic_intervals` | `filename: str` | `dict` with intervals | [Docs](tools/intervals/harmonic.md) |
| `get_melodic_ngrams` | `filename: str, n: int = 4` | `dict` with n-grams | [Docs](tools/intervals/ngrams.md) |

## Discovery Tools

### list_available_mei_files()

Discover all built-in MEI files.

**Parameters**: None

**Returns**:
```python
{
    "bach_inventions": List[str],      # 15 files
    "bartok_mikrokosmos": List[str],   # 19 files
    "morley_canzonets": List[str],     # 12 files
    "all_files": List[str]             # 46 files
}
```

[Full Documentation →](tools/discovery.md)

## Metadata Tools

### get_mei_metadata(filename)

Extract metadata from MEI file header.

**Parameters**:
- `filename` (str): MEI filename (e.g., "Bach_BWV_0772.mei")

**Returns**:
```python
{
    "title": str,
    "composer": str,
    "mei_editors": List[str],
    "xml_editors": List[str],
    "analysts": List[str],
    "publication_date": str | None,
    "copyright": str | None,
    "application": str | None
}
```

[Full Documentation →](tools/metadata.md)

## Analysis Tools

### analyze_key(filename)

Detect musical key using music21.

**Parameters**:
- `filename` (str): MEI filename

**Returns**:
```python
{
    "Key Name": str,              # e.g., "C major", "a minor"
    "Confidence Factor": float    # 0.0 to 1.0
}
```

[Full Documentation →](tools/key-analysis.md)

### get_notes(filename)

Extract all notes with pitch and octave.

**Parameters**:
- `filename` (str): MEI filename

**Returns**:
```python
{
    "filename": str,
    "notes": str    # Formatted dataframe
}
```

[Full Documentation →](tools/intervals/notes.md)

### get_melodic_intervals(filename)

Calculate melodic intervals within voices.

**Parameters**:
- `filename` (str): MEI filename

**Returns**:
```python
{
    "filename": str,
    "melodic_intervals": str    # Formatted dataframe
}
```

[Full Documentation →](tools/intervals/melodic.md)

### get_harmonic_intervals(filename)

Calculate harmonic intervals between voices.

**Parameters**:
- `filename` (str): MEI filename

**Returns**:
```python
{
    "filename": str,
    "harmonic_intervals": str    # Formatted dataframe
}
```

[Full Documentation →](tools/intervals/harmonic.md)

### get_melodic_ngrams(filename, n=4)

Find recurring melodic patterns.

**Parameters**:
- `filename` (str): MEI filename
- `n` (int, optional): N-gram length (default: 4)

**Returns**:
```python
{
    "filename": str,
    "n": int,
    "melodic_ngrams": str    # Formatted dataframe
}
```

[Full Documentation →](tools/intervals/ngrams.md)

## Common Patterns

### Error Handling

All tools raise `FileNotFoundError` for invalid filenames:

```python
try:
    result = analyze_key("nonexistent.mei")
except FileNotFoundError as e:
    print(f"File not found: {e}")
```

### File Discovery Pattern

```python
# Get all files
files = list_available_mei_files()

# Analyze each file
for filename in files["all_files"]:
    metadata = get_mei_metadata(filename)
    key_info = analyze_key(filename)
    print(f"{filename}: {metadata['title']} in {key_info['Key Name']}")
```

### Interval Analysis Pattern

```python
# Extract notes
notes = get_notes("Bach_BWV_0772.mei")

# Get melodic intervals
melodic = get_melodic_intervals("Bach_BWV_0772.mei")

# Get harmonic intervals
harmonic = get_harmonic_intervals("Bach_BWV_0772.mei")

# Find patterns
patterns = get_melodic_ngrams("Bach_BWV_0772.mei", n=4)
```

## Data Formats

### Dataframe Format

Interval tools return formatted strings representing dataframes:

```
                  1     2
Measure Beat
1.0     1.000  Rest  Rest
        1.250    C4   NaN
        1.500    D4   NaN
```

- **Rows**: Measure.Beat positions
- **Columns**: Voice part numbers
- **Values**: Notes, intervals, or patterns

### Interval Notation

- **Quality**: M (major), m (minor), P (perfect), A (augmented), d (diminished)
- **Number**: Scale degree (2, 3, 4, 5, 6, 7, 8+)
- **Direction**: Positive (ascending), negative (descending)

Examples: `M2`, `-m3`, `P5`, `M13`

## Type Hints

All tools use Python type hints:

```python
from typing import Any

def analyze_key(filename: str) -> dict[str, Any]: ...
def get_melodic_ngrams(filename: str, n: int = 4) -> dict[str, Any]: ...
```

## Related Documentation

- [Tools Overview](tools/index.md)
- [Quick Start Guide](getting-started/quick-start.md)
- [Development Guide](development/structure.md)
