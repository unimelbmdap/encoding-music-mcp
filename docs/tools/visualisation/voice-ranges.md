# Voice Ranges

The `plot_voice_ranges` tool displays the pitch range of each staff in a single MEI score as a compact horizontal chart.

## Overview

This tool is useful for quickly seeing the ambitus of each staff or voice layer in one piece. It reuses the note data produced by `get_notes`, finds the lowest and highest sounding pitch in each staff, and sends that summary to an interactive viewer.

## Prerequisites

This tool requires an MCP client that supports the MCP Apps extension (for example, Claude Desktop with the extension enabled). Without the extension, the tool still returns a short text description.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `filename` | `str` | Yes | Name of the MEI file (e.g., `"Bach_BWV_0772.mei"`) |

## Return Value

The tool returns a `ToolResult` with:

- **Text content**: A short description of the score being shown
- **Structured content**: Metadata, x-axis note labels, and per-staff range summaries for the viewer app

```python
{
    "filename": "Bach_BWV_0772.mei",
    "title": "Invention No. 1 in C major, BWV 772",
    "composer": "Bach, Johann Sebastian",
    "x_min_midi": 36,
    "x_max_midi": 84,
    "tick_values": [36, 37, 38, ...],
    "tick_labels": ["C2", "C#2", "D2", ...],
    "staff_ranges": [
        {
            "staff": "1",
            "label": "Staff 1",
            "lowest_note": "C4",
            "highest_note": "C6",
            "lowest_midi": 60,
            "highest_midi": 84,
            "range_semitones": 24,
            "color": "#ff6b6b",
        }
    ],
}
```

## Usage

!!! example "Try asking:"
    "Plot the voice ranges for Bach_BWV_0772.mei"

The viewer shows one horizontal bar per staff. Each bar begins at the staff's lowest note and ends at its highest note.

## How It Works

1. The tool calls `get_notes` for the selected MEI file
2. The returned CSV is parsed to collect note tokens by staff
3. The lowest and highest pitch in each staff are converted to MIDI numbers
4. The viewer renders those spans against a chromatic x-axis

## Use Cases

- Compare upper and lower staff range in keyboard music
- Inspect the ambitus of individual parts in polyphonic textures
- Check whether a score stays within expected vocal or instrumental ranges

## Related Tools

- [get_notes](../intervals/notes.md) - Source note data reused by this tool
- [show_notation](../notation.md) - View the score as engraved notation
