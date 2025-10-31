# render_notation

Render musical excerpts as SVG notation for visual display.

## Overview

The `render_notation` tool combines music21's measure selection with verovio's rendering capabilities to create small, focused musical examples. This allows you to display notation directly without requiring external dependencies like LilyPond or MuseScore.

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `filename` | `str` | Yes | - | Name of the MEI file |
| `start_measure` | `int` | No | 1 | First measure to render |
| `end_measure` | `int` | No | 4 | Last measure to render |
| `page_width` | `int` | No | 1200 | Width of rendered page in pixels |

## Returns

| Key | Type | Description |
|-----|------|-------------|
| `filename` | `str` | The input filename |
| `measures` | `str` | Measure range rendered (e.g., "1-4") |
| `svg` | `str` | SVG markup as a string |
| `format` | `str` | Always "svg" |

## Example Usage

### Basic Example

Render the first 4 measures:

```python
result = render_notation("Bach_BWV_0772.mei")
# Returns SVG of measures 1-4
```

### Custom Range

Render a specific section:

```python
result = render_notation("Bach_BWV_0772.mei", start_measure=5, end_measure=8)
# Returns SVG of measures 5-8
```

### Wider Display

Render with more horizontal space:

```python
result = render_notation("Bach_BWV_0772.mei", page_width=1600)
# Returns wider SVG rendering
```

## Use Cases

### Illustrate Analysis

Show the actual notation when discussing musical features:

```python
# Analyze intervals
intervals = get_melodic_intervals("Bach_BWV_0772.mei")

# Show the notation being analyzed
notation = render_notation("Bach_BWV_0772.mei", start_measure=1, end_measure=2)
```

### Compare Sections

Render different sections for comparison:

```python
opening = render_notation("Bach_BWV_0772.mei", start_measure=1, end_measure=4)
closing = render_notation("Bach_BWV_0772.mei", start_measure=20, end_measure=23)
```

### Focus on Specific Passages

Extract just the measures you need:

```python
# Show only the measures with a specific motif
motif = render_notation("Bach_BWV_0772.mei", start_measure=7, end_measure=9)
```

### Generate Thumbnails

Create small previews with limited measures:

```python
preview = render_notation("Bach_BWV_0772.mei", start_measure=1, end_measure=2)
```

## Technical Details

### Rendering Process

1. **Load**: music21 parses the MEI file
2. **Select**: Specific measures are extracted
3. **Export**: Excerpt is converted to MusicXML
4. **Render**: verovio converts MusicXML to SVG

### SVG Output

The SVG returned is:
- **Scalable**: Can be displayed at any size
- **Text-based**: No binary dependencies needed
- **Inline**: Can be embedded directly in responses
- **Self-contained**: Includes all necessary notation elements

### Page Width

The `page_width` parameter affects:
- Horizontal spacing of notes
- System breaks
- Overall layout

Typical values:
- `1000-1200`: Standard display
- `1400-1600`: Wider, more spacious
- `800-1000`: Compact display

## Error Handling

### Invalid Measure Numbers

```python
# start_measure must be >= 1
render_notation("Bach_BWV_0772.mei", start_measure=0)  # ValueError

# end_measure must be >= start_measure
render_notation("Bach_BWV_0772.mei", start_measure=5, end_measure=2)  # ValueError
```

### Missing Measures

```python
# Requesting measures beyond the piece length
render_notation("Bach_BWV_0772.mei", start_measure=100, end_measure=105)
# ValueError: No music found in measures 100-105
```

## Best Practices

### Keep Excerpts Small

For performance and clarity, limit rendered measures:

- **1-4 measures**: Ideal for motifs
- **5-8 measures**: Good for phrases
- **8+ measures**: Use sparingly

### Match Width to Content

Adjust page width based on excerpt length:

```python
# Short excerpt - narrower is fine
render_notation("Bach_BWV_0772.mei", start_measure=1, end_measure=2, page_width=1000)

# Longer excerpt - wider is better
render_notation("Bach_BWV_0772.mei", start_measure=1, end_measure=8, page_width=1600)
```

### Coordinate with Analysis

Show notation alongside analysis results:

```python
# Get the data
ngrams = get_melodic_ngrams("Bach_BWV_0772.mei", n=3)

# Show the notation
notation = render_notation("Bach_BWV_0772.mei", start_measure=1, end_measure=4)

# Now both data and visual representation are available
```

## Limitations

- **No audio**: This tool only creates visual notation
- **Static output**: SVG is not interactive
- **Layout control**: Limited control over detailed layout decisions
- **File size**: Very long excerpts create large SVG files

## Related Tools

- [get_mei_metadata](metadata.md) - Get piece information before rendering
- [get_notes](intervals/notes.md) - See the notes in data form
- [get_melodic_intervals](intervals/melodic.md) - Analyze what's shown in the notation
- [list_available_mei_files](discovery.md) - Find files to render
