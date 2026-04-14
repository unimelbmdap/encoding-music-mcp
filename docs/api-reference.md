# API Reference

Complete reference for all encoding-music-mcp tools.

## Tool Catalog

| Tool | Parameters | Returns | Documentation |
|------|------------|---------|---------------|
| `run_comprehensive_analysis` | `filename: str` | `str` comprehensive analysis text | N/A |
| `diagnose_sampling` | None | `dict` sampling diagnostic status | N/A |
| `list_available_mei_files` | None | `dict` with file lists | [Docs](tools/discovery.md) |
| `get_mei_metadata` | `filename: str` | `dict` with metadata | [Docs](tools/metadata.md) |
| `analyze_key` | `filename: str` | `dict` with key info | [Docs](tools/key-analysis.md) |
| `get_notes` | `filename: str` | `dict` with notes | [Docs](tools/intervals/notes.md) |
| `get_melodic_intervals` | `filename: str` | `dict` with intervals | [Docs](tools/intervals/melodic.md) |
| `get_harmonic_intervals` | `filename: str` | `dict` with intervals | [Docs](tools/intervals/harmonic.md) |
| `get_melodic_ngrams` | `filename: str, n: int = 4` | `dict` with n-grams | [Docs](tools/intervals/ngrams.md) |
| `get_first_occur_melodic_ngrams` | `filename: str, n: int = 4, kind: str = "d", combine_unisons: bool = True, compound: bool = False` | `dict` with first-occurrence patterns | [Docs](tools/intervals/first-occur.md) |
| `show_notation` | `filename: str, start_measure: int = None, end_measure: int = None, page: int = 1` | SVG notation | [Docs](tools/notation.md) |
| `plot_weighted_note_distribution` | `filename: str, pitch_class_order: str = "fifths", group_by_staff: bool = False, limit_to_active: bool = True` | Radar plot payload | [Docs](tools/weighted-note-distribution.md) |
| `play_excerpt` | `filename: str | None = None, start_q: float = 0.0, end_q: float = None, bpm: int = 60` | Audio player payload | [Docs](tools/play-excerpt.md) |

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

### run_comprehensive_analysis(filename)

Run the comprehensive analysis workflow and return the final analysis text.

**Parameters**:
- `filename` (str): MEI filename

**Returns**:
```python
"[sampled path]\\n..." | "[legacy fallback]\\n..."
```

### diagnose_sampling()

Run a tiny sampling diagnostic to determine whether this tool call has
usable MCP sampling support.

**Parameters**: None

**Returns**:
```python
{
    "status": "no_context" | "sampling_unsupported" | "sampling_ok",
    "has_context": bool,
    "supports_sampling_tools": bool,
    "sampling_attempted": bool,
    "error": str,          # present when unsupported
    "sample_text": str,    # present when successful
}
```

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
    "notes": str    # CSV representation
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
    "melodic_intervals": str    # CSV representation
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
    "harmonic_intervals": str    # CSV representation
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
    "melodic_ngrams": str    # CSV representation
}
```

[Full Documentation →](tools/intervals/ngrams.md)

### get_first_occur_melodic_ngrams(filename, n=4, kind="d", combine_unisons=True, compound=False)

Find the first occurrence of each unique melodic n-gram in a score.

**Parameters**:
- `filename` (str): MEI filename
- `n` (int, optional): N-gram length (default: 4)
- `kind` (str, optional): Interval type
- `combine_unisons` (bool, optional): Whether to combine unisons when extracting notes
- `compound` (bool, optional): Whether to use compound intervals

**Returns**:
```python
{
    "filename": str,
    "n": int,
    "kind": str,
    "combine_unisons": bool,
    "compound": bool,
    "patterns": list[dict[str, Any]]
}
```

[Full Documentation â†’](tools/intervals/first-occur.md)

## Notation Tools

### show_notation(filename, start_measure=None, end_measure=None, page=1)

Render MEI file as sheet music notation using Verovio.

**Parameters**:
- `filename` (str): MEI filename
- `start_measure` (int, optional): First measure to display
- `end_measure` (int, optional): Last measure to display
- `page` (int, optional): Page number (default: 1)

**Returns**:
```python
{
    "filename": str,
    "svg": str,          # SVG markup
    "page": int,
    "total_pages": int,
    "start_measure": int | None,
    "end_measure": int | None
}
```

!!! note
    Requires the [MCP Apps extension](https://modelcontextprotocol.io/docs/extensions/apps) for inline display.

[Full Documentation →](tools/notation.md)

### plot_weighted_note_distribution(filename, pitch_class_order="fifths", group_by_staff=False, limit_to_active=True)

Plot a duration-weighted pitch-class radar chart for one score.

**Parameters**:
- `filename` (str): MEI filename
- `pitch_class_order` (str, optional): `"fifths"` or `"chromatic"` (default: `"fifths"`)
- `group_by_staff` (bool, optional): Plot one polygon per staff (default: `False`)
- `limit_to_active` (bool, optional): Hide pitch classes with zero weight (default: `True`)

**Returns**:
```python
{
    "filename": str,
    "title": str,
    "composer": str | None,
    "pitch_class_order": str,
    "group_by_staff": bool,
    "limit_to_active": bool,
    "categories": list[str],
    "radial_max": float,
    "traces": [
        {
            "label": str,
            "color": str,
            "values": list[float],
            "raw_weights_ppq": list[float],
            "total_weight_ppq": float,
            "note_count": int,
        }
    ],
}
```

!!! note
    Requires the [MCP Apps extension](https://modelcontextprotocol.io/docs/extensions/apps) for inline display.

[Full Documentation →](tools/weighted-note-distribution.md)

### play_excerpt(filename=None, start_q=0.0, end_q=None, bpm=60)

Render an MEI file or excerpt to streamed MP3 audio.

**Parameters**:
- `filename` (str | None): MEI filename. If omitted, the server can elicit it from the user.
- `start_q` (float, optional): Start offset in quarter-note units
- `end_q` (float | None, optional): End offset in quarter-note units
- `bpm` (int, optional): Playback tempo in beats per minute

**Returns**:
```python
{
    "filename": str,
    "audio_resource_uri": str,
    "mime_type": "audio/mpeg",
    "start_q": float,
    "end_q": float | None,
    "bpm": int,
    "duration_sec": float,
}
```

[Full Documentation â†’](tools/play-excerpt.md)

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

### CSV Format

Interval tools return data in CSV format for efficient token usage:

```csv
Measure,Beat,1,2
1.0,1.0,Rest,Rest
1.0,1.25,C4,
1.0,1.5,D4,
```

- **Rows**: Measure and beat positions (indexed)
- **Columns**: Voice part numbers
- **Values**: Notes, intervals, or patterns
- **Empty cells**: Represented as blank (no NaN in CSV)

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
