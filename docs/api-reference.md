# API Reference

Complete reference for all encoding-music-mcp tools.

## Tool Catalog

| Tool | Parameters | Returns | Documentation |
|------|------------|---------|---------------|
| `list_available_mei_files` | None | `dict` with file lists | [Docs](tools/discovery.md) |
| `register_mei_file_from_path` | `file_path: str | None = None, filename: str | None = None` | `dict` registration status | [Docs](tools/uploads.md) |
| `get_mei_metadata` | `filename: str` | `dict` with metadata | [Docs](tools/metadata.md) |
| `analyze_key` | `filename: str` | `dict` with key info | [Docs](tools/key-analysis.md) |
| `get_notes` | `filename: str` | `dict` with notes | [Docs](tools/intervals/notes.md) |
| `get_melodic_intervals` | `filename: str` | `dict` with intervals | [Docs](tools/intervals/melodic.md) |
| `get_harmonic_intervals` | `filename: str` | `dict` with intervals | [Docs](tools/intervals/harmonic.md) |
| `get_melodic_ngrams` | `filename: str, n: int = 4, kind: str = "d", entries: bool = False, include_note_ids: bool = False` | `dict` with n-grams | [Docs](tools/intervals/ngrams.md) |
| `count_melodic_ngrams` | `filename: str, n: int = 4, kind: str = "d", entries: bool = False, combine_unisons: bool \| None = None, compound: bool = False` | `dict` with ranked n-gram counts | [Docs](tools/intervals/ngram-counts.md) |
| `resolve_note_ids_for_highlight` | `filename: str, spans: list[dict[str, Any]]` | `dict` with resolved note-ID spans | [Docs](tools/intervals/note-id-resolution.md) |
| `get_melodic_ngram_matches` | `filename: str, n: int = 4, kind: str = "d", entries: bool = False, patterns: list[str] \| None = None, combine_unisons: bool \| None = None, compound: bool = False` | `dict` with pattern-keyed note-id matches | [Docs](tools/intervals/ngram-matches.md) |
| `get_first_occur_melodic_ngrams` | `filename: str, n: int = 4, kind: str = "d", combine_unisons: bool = True, compound: bool = False` | `dict` with first-occurrence patterns | [Docs](tools/intervals/first-occur.md) |
| `get_cadences` | `filename: str` | `dict` with predicted cadences | [Docs](tools/intervals/cadences.md) |
| `show_notation` | `filename: str \| None = None, start_measure: int = None, end_measure: int = None, page: int = 1` | SVG notation | [Docs](tools/notation.md) |
| `show_notation_highlight` | `filename: str, highlight_note_ids: list[str], start_measure: int = None, end_measure: int = None, page: int = 1` | Highlighted SVG notation | [Docs](tools/notation.md#show_notation_highlight) |
| `plot_voice_ranges` | `filename: str` | Voice range plot payload | [Docs](tools/visualisation/voice-ranges.md) |
| `plot_weighted_note_distribution` | `filename: str | None = None, filenames: list[str] | None = None, pitch_class_order: str = "fifths", group_by_staff: bool = False, limit_to_active: bool = True` | Radar plot payload | [Docs](tools/visualisation/weighted-note-distribution.md) |
| `plot_melodic_ngram_heatmap` | `filename: str | None = None, filenames: list[str] | None = None, n: int = 4, kind: str = "d", entries: bool = False, top_n: int = 2, combine_unisons: bool \| None = None, compound: bool = False` | Melodic n-gram heatmap payload | [Docs](tools/visualisation/melodic-ngram-heatmap.md) |
| `plot_sonority_ngram_progress` | `filename: str | None = None, filenames: list[str] | None = None, n: int = 4, compound: bool = True, sort: bool = False, minimum_beat_strength: float = 0.0` | Sonority n-gram progress payload | [Docs](tools/visualisation/sonority-ngram-progress.md) |
| `play_excerpt` | `filename: str | None = None, start_q: float = 0.0, end_q: float = None, bpm: int = 60` | Audio player payload | [Docs](tools/play-excerpt.md) |
| `load_audio_resource` | `resource_uri: str` | Base64 audio payload | [Docs](tools/play-excerpt.md#load_audio_resource) |

## Discovery Tools

### list_available_mei_files()

Discover all built-in MEI files and user-registered MEI files.

**Parameters**: None

**Returns**:
```python
{
    "bach_inventions": List[str],      # 15 files
    "bartok_mikrokosmos": List[str],   # 19 files
    "morley_canzonets": List[str],     # 12 files
    "uploaded_mei_files": List[str],   # files registered during this session
    "all_files": List[str]             # built-in plus uploaded filenames
}
```

[Full Documentation ->](tools/discovery.md)

## Uploaded MEI Tools

### register_mei_file_from_path(file_path=None, filename=None)

Register a local MEI file path exposed by the user. If `file_path` is omitted
and the client supports elicitation, the server asks the user to provide a local
path visible to the MCP server process.

**Parameters**:
- `file_path` (str | None): Local path to the MEI file
- `filename` (str | None): Optional session filename. Defaults to the path basename.

**Returns**:
```python
{
    "filename": str,
    "registered": True,
    "source_path": str,
    "message": str
}
```

After registration, use `filename` with tools such as `show_notation`,
`get_notes`, `get_melodic_ngrams`, `analyze_key`, and visualisation tools.

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

[Full Documentation ->](tools/metadata.md)

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

[Full Documentation ->](tools/key-analysis.md)

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

[Full Documentation ->](tools/intervals/notes.md)

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

[Full Documentation ->](tools/intervals/melodic.md)

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

[Full Documentation ->](tools/intervals/harmonic.md)

### get_melodic_ngrams(filename, n=4, kind="d", entries=False, include_note_ids=False)

Find recurring melodic patterns.

**Parameters**:
- `filename` (str): MEI filename
- `n` (int, optional): N-gram length (default: 4)
- `kind` (str, optional): Interval type
- `entries` (bool, optional): Restrict to entry-filtered n-grams
- `include_note_ids` (bool, optional): Include occurrence-level note-ID spans

**Returns**:
```python
{
    "filename": str,
    "n": int,
    "kind": str,
    "entries": bool,
    "include_note_ids": bool,
    "melodic_ngrams": str,   # CSV representation using pattern strings like 2_2_2_-3
    "melodic_ngram_note_ids": list[dict[str, Any]]  # optional
}
```

[Full Documentation ->](tools/intervals/ngrams.md)

### count_melodic_ngrams(filename, n=4, kind="d", entries=False, combine_unisons=None, compound=False)

Count how many times each melodic n-gram occurs.

**Parameters**:
- `filename` (str): MEI filename
- `n` (int, optional): N-gram length (default: 4)
- `kind` (str, optional): Interval type
- `entries` (bool, optional): Restrict to entry-filtered n-grams
- `combine_unisons` (bool | None, optional): Whether to combine unisons when extracting notes
- `compound` (bool, optional): Whether to use compound intervals

**Returns**:
```python
{
    "filename": str,
    "n": int,
    "kind": str,
    "entries": bool,
    "combine_unisons": bool | None,
    "compound": bool,
    "pattern_counts": [
        {
            "pattern": list[str],
            "pattern_string": str,
            "count": int,
        }
    ]
}
```

[Full Documentation ->](tools/intervals/ngram-counts.md)

### resolve_note_ids_for_highlight(filename, spans)

Resolve analysis locations or spans to MEI note IDs for notation highlighting.

**Parameters**:
- `filename` (str): MEI filename
- `spans` (list[dict]): Locations from analysis output. Each span may provide
  `start_measure`/`start_beat`, `start_q`, or `start_offset`; optional
  `staff`, `part`, `column`, or `voice_pair`; optional `duration`, `end_q`,
  `end_offset`, or `note_count`.

**Returns**:
```python
{
    "filename": str,
    "spans": [
        {
            "index": int,
            "matched_parts": list[str],
            "note_ids": list[str],
            # original span fields are preserved
        }
    ]
}
```

[Full Documentation ->](tools/intervals/note-id-resolution.md)

### get_melodic_ngram_matches(filename, n=4, kind="d", entries=False, patterns=None, combine_unisons=None, compound=False)

Group note-id spans by melodic n-gram pattern.

**Parameters**:
- `filename` (str): MEI filename
- `n` (int, optional): N-gram length (default: 4)
- `kind` (str, optional): Interval type
- `entries` (bool, optional): Restrict to entry-filtered n-grams
- `patterns` (list[str] | None, optional): Underscore-separated pattern filters
- `combine_unisons` (bool | None, optional): Whether to combine unisons when extracting notes
- `compound` (bool, optional): Whether to use compound intervals

**Returns**:
```python
{
    "filename": str,
    "n": int,
    "kind": str,
    "entries": bool,
    "patterns": list[str],
    "combine_unisons": bool | None,
    "compound": bool,
    "matches_by_pattern": {
        "2_2_2_-3": [
            {
                "pattern": list[str],
                "column": str,
                "start_measure": float,
                "start_beat": float,
                "start_offset": float,
                "duration": float,
                "end_offset": float,
                "note_ids": list[str],
            }
        ]
    }
}
```

[Full Documentation ->](tools/intervals/ngram-matches.md)

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
    "patterns": [
        {
            "pattern": list[str],
            "pattern_string": str,
            "count": int,
            "start_q": float,
            "duration": float,
            "end_q": float,
            "column": str,
            "note_ids": list[str],
        }
    ]
}
```

[Full Documentation ->](tools/intervals/first-occur.md)

### get_cadences(filename)

Extract predicted cadences from Renaissance counterpoint.

**Parameters**:
- `filename` (str): MEI filename

**Returns**:
```python
{
    "filename": str,
    "cadences": str    # CSV representation or explanatory message
}
```

[Full Documentation ->](tools/intervals/cadences.md)

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

[Full Documentation ->](tools/notation.md)

### show_notation_highlight(filename, highlight_note_ids, start_measure=None, end_measure=None, page=1)

Render MEI notation and highlight selected MEI note IDs.

**Parameters**:
- `filename` (str): MEI filename
- `highlight_note_ids` (list[str]): MEI `xml:id` values to highlight
- `start_measure` (int, optional): First measure to display
- `end_measure` (int, optional): Last measure to display
- `page` (int, optional): Page number (default: 1)

**Returns**:
```python
{
    "filename": str,
    "svg": str,
    "page": int,
    "total_pages": int,
    "highlight_note_ids": list[str],
}
```

[Full Documentation ->](tools/notation.md#show_notation_highlight)

## Visualisation Tools

### plot_voice_ranges(filename)

Plot the lowest and highest pitch reached by each staff in a single score.

**Parameters**:
- `filename` (str): MEI filename

**Returns**:
```python
{
    "filename": str,
    "title": str,
    "composer": str | None,
    "staves": list[dict[str, Any]],
    "pitch_min": int,
    "pitch_max": int,
}
```

[Full Documentation ->](tools/visualisation/voice-ranges.md)

### plot_weighted_note_distribution(filename=None, filenames=None, pitch_class_order="fifths", group_by_staff=False, limit_to_active=True)

Plot a duration-weighted pitch-class radar chart for one or more scores.

**Parameters**:
- `filename` (str | None): One MEI filename
- `filenames` (list[str] | None): Multiple MEI filenames to overlay on one figure
- `pitch_class_order` (str, optional): `"fifths"` or `"chromatic"` (default: `"fifths"`)
- `group_by_staff` (bool, optional): Plot one polygon per staff (default: `False`)
- `limit_to_active` (bool, optional): Hide pitch classes with zero weight (default: `True`)

**Returns**:
```python
{
    "filename": str,
    "filenames": list[str],
    "score_count": int,
    "scores": list[dict[str, Any]],
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

[Full Documentation ->](tools/visualisation/weighted-note-distribution.md)

### plot_melodic_ngram_heatmap(filename=None, filenames=None, n=4, kind="d", entries=False, top_n=2, combine_unisons=None, compound=False)

Plot top melodic n-gram occurrences as timeline rectangles, separated by score
and staff. The tool counts patterns across all selected pieces, keeps the
highest-ranked `top_n` patterns, and draws every matching occurrence from start
offset to end offset.

**Parameters**:
- `filename` (str | None): One MEI filename
- `filenames` (list[str] | None): Multiple MEI filenames
- `n` (int, optional): N-gram length (default: `4`)
- `kind` (str, optional): Interval kind (default: `"d"`)
- `entries` (bool, optional): Restrict to entry-filtered n-grams
- `top_n` (int, optional): Number of top patterns to plot (default: `2`)
- `combine_unisons` (bool | None, optional): Whether to combine unisons
- `compound` (bool, optional): Whether to use compound intervals

**Returns**:
```python
{
    "filenames": list[str],
    "score_count": int,
    "patterns": list[dict[str, Any]],
    "rows": list[dict[str, Any]],
    "occurrences": list[dict[str, Any]],
    "x_min": float,
    "x_max": float,
}
```

!!! note
    Requires the [MCP Apps extension](https://modelcontextprotocol.io/docs/extensions/apps) for inline display.

[Full Documentation ->](tools/visualisation/melodic-ngram-heatmap.md)

### plot_sonority_ngram_progress(filename=None, filenames=None, n=4, compound=True, sort=False, minimum_beat_strength=0.0)

Plot low-line sonority n-gram occurrences by normalized score progress. The
viewer samples dense y-axis rows at low zoom levels and reveals more rows as the
user zooms in.

**Parameters**:
- `filename` (str | None): One MEI filename
- `filenames` (list[str] | None): Multiple MEI filenames
- `n` (int, optional): Sonority n-gram length (default: `4`)
- `compound` (bool, optional): Use compound interval classes (default: `True`)
- `sort` (bool, optional): Sort sonority contents in CRIM analysis (default: `False`)
- `minimum_beat_strength` (float, optional): Minimum CRIM beat strength filter (default: `0.0`)

**Returns**:
```python
{
    "filenames": list[str],
    "score_count": int,
    "scores": list[dict[str, Any]],
    "rows": list[dict[str, Any]],
    "occurrences": list[dict[str, Any]],
    "beat_strength_filter_applied": bool,
    "beat_strength_fallback_filenames": list[str],
    "warnings": list[str],
    "x_min": 0.0,
    "x_max": 1.0,
}
```

!!! note
    Requires the [MCP Apps extension](https://modelcontextprotocol.io/docs/extensions/apps) for inline display.

[Full Documentation ->](tools/visualisation/sonority-ngram-progress.md)

## Playback Tools

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

[Full Documentation ->](tools/play-excerpt.md)

### load_audio_resource(resource_uri)

Load the base64-encoded MP3 bytes for an `audio://` resource prepared by
`play_excerpt`.

**Parameters**:
- `resource_uri` (str): `audio://files/{token}` URI returned by `play_excerpt`

**Returns**:
```python
{
    "resource_uri": str,
    "mime_type": "audio/mpeg",
    "audio_base64": str,
    "duration_sec": float,
}
```

[Full Documentation ->](tools/play-excerpt.md#load_audio_resource)

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
def get_melodic_ngrams(
    filename: str,
    n: int = 4,
    kind: str = "d",
    entries: bool = False,
    include_note_ids: bool = False,
) -> dict[str, Any]: ...
def count_melodic_ngrams(
    filename: str,
    n: int = 4,
    kind: str = "d",
    entries: bool = False,
    combine_unisons: bool | None = None,
    compound: bool = False,
) -> dict[str, Any]: ...
def resolve_note_ids_for_highlight(
    filename: str,
    spans: list[dict[str, Any]],
) -> dict[str, Any]: ...
def get_melodic_ngram_matches(
    filename: str,
    n: int = 4,
    kind: str = "d",
    entries: bool = False,
    patterns: list[str] | None = None,
    combine_unisons: bool | None = None,
    compound: bool = False,
) -> dict[str, Any]: ...
```

## Related Documentation

- [Tools Overview](tools/index.md)
- [Quick Start Guide](getting-started/quick-start.md)
- [Development Guide](development/structure.md)
