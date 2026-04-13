# Play Excerpt

The `play_excerpt` tool renders an MEI score to audio and opens an inline audio player for the full piece or a selected excerpt.

## Overview

This tool converts MEI notation into playable audio by rendering MIDI with Verovio, synthesising that MIDI with FluidSynth, trimming the requested segment if needed, and converting the result to MP3 for streaming in the app viewer.

## Prerequisites

This tool requires:

- An MCP client that supports the MCP Apps extension
- `fluidsynth` installed and available on `PATH`, or at the configured Windows fallback location
- `ffmpeg` installed and available on `PATH`, or at the configured Windows fallback location
- The bundled SoundFont file used for synthesis

Without the Apps extension, the tool still returns a small text response and structured payload, but the inline audio player will not render.

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `filename` | `str \| None` | No | `None` | Name of the MEI file (e.g., `"Bach_BWV_0772.mei"`). If omitted, the server asks the user which score to play when the client supports elicitation. |
| `start_q` | `float` | No | `0.0` | Start position in quarter-note units from the beginning of the piece |
| `end_q` | `float \| None` | No | `None` | Optional end position in quarter-note units; if omitted, playback continues from `start_q` to the end of the piece |
| `bpm` | `int` | No | `60` | Playback tempo in beats per minute |

## Return Value

The tool returns a `ToolResult` with:

- **Text content**: A short status message such as `"Prepared streaming audio"`
- **Structured content**: Metadata and an `audio://` resource URI used by the player app

```python
{
    "filename": "Bach_BWV_0772.mei",
    "audio_resource_uri": "audio://files/...",
    "mime_type": "audio/mpeg",
    "start_q": 8.0,
    "end_q": 16.0,
    "bpm": 72,
    "duration_sec": 6.84,
}
```

## Usage

### Full piece

!!! example "Try asking:"
    "Play Bach_BWV_0772.mei"

Renders the whole score and opens it in the audio player.

### Missing filename

!!! example "Try asking:"
    "Play the music score for me"

If the filename is missing, the server elicits the score name instead of immediately failing.

### Selected excerpt

!!! example "Try asking:"
    "Play Bach_BWV_0772.mei from beat 8 to beat 16 at 72 bpm"

Renders only the requested excerpt and opens it in the audio player.

## How It Works

1. The MEI file is loaded from the built-in collection
2. The requested tempo is inserted or updated in the MEI
3. Silent `vel="0"` note events are normalised for audible playback
4. Verovio renders the score to MIDI
5. FluidSynth synthesises the MIDI to WAV using the bundled SoundFont
6. If `start_q` and/or `end_q` are provided, the WAV is trimmed to the requested quarter-note range
7. FFmpeg converts the result to MP3
8. The tool returns an `audio://` MCP resource URI that the player app loads

## Notes

- `start_q` is zero-based: `0.0` means the beginning of the piece
- If `filename` is omitted and the user declines the follow-up elicitation, the tool returns a validation error
- `end_q` must be greater than `start_q`
- If `end_q` is not provided, the rendered audio runs from `start_q` through to the end of the piece
- A small timing buffer is added at the end of excerpts so the final note is less likely to be cut off too early
- Repeated requests for the same file, tempo, and range reuse cached rendered audio

## Related Tools

- [show_notation](notation.md) - View the same score as rendered notation
