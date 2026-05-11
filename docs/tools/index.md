# Tools Overview

encoding-music-mcp provides a suite of tools for analyzing MEI files. Tools work with the [built-in MEI collection](../resources/mei-files.md) and MEI files registered during the current server session.

## Available Tools

### Discovery Tools

| Tool | Purpose | Learn More |
|------|---------|------------|
| [`list_available_mei_files`](discovery.md) | Browse and discover the 46 built-in MEI files | [Documentation](discovery.md) |

### Upload Tools

| Tool | Purpose | Learn More |
|------|---------|------------|
| [`register_mei_file_from_path`](uploads.md) | Register a user-exposed local MEI path, with optional elicitation | [Documentation](uploads.md) |

### Metadata Tools

| Tool | Purpose | Learn More |
|------|---------|------------|
| [`get_mei_metadata`](metadata.md) | Extract title, composer, editors, dates, and copyright info | [Documentation](metadata.md) |

### Analysis Tools

| Tool | Purpose | Learn More |
|------|---------|------------|
| [`analyze_key`](key-analysis.md) | Detect musical key with confidence scores | [Documentation](key-analysis.md) |
| [`get_notes`](intervals/notes.md) | Extract all notes with pitch and octave information | [Documentation](intervals/notes.md) |
| [`get_melodic_intervals`](intervals/melodic.md) | Analyze melodic intervals within voices | [Documentation](intervals/melodic.md) |
| [`get_harmonic_intervals`](intervals/harmonic.md) | Analyze harmonic intervals between voices | [Documentation](intervals/harmonic.md) |
| [`get_melodic_ngrams`](intervals/ngrams.md) | Find recurring melodic patterns | [Documentation](intervals/ngrams.md) |
| [`count_melodic_ngrams`](intervals/ngram-counts.md) | Count and rank melodic n-gram patterns | [Documentation](intervals/ngram-counts.md) |
| [`resolve_note_ids_for_highlight`](intervals/note-id-resolution.md) | Resolve analysis locations to MEI note IDs for highlighting | [Documentation](intervals/note-id-resolution.md) |
| [`get_melodic_ngram_matches`](intervals/ngram-matches.md) | Group note-ID spans by melodic n-gram pattern | [Documentation](intervals/ngram-matches.md) |
| [`get_first_occur_melodic_ngrams`](intervals/first-occur.md) | Find first-occurrence melodic patterns with playback positions | [Documentation](intervals/first-occur.md) |

### Notation Tools

| Tool | Purpose | Learn More |
|------|---------|------------|
| [`show_notation`](notation.md) | Display rendered sheet music with interactive pagination | [Documentation](notation.md) |

### Visualisation Tools

| Tool | Purpose | Learn More |
|------|---------|------------|
| [`plot_voice_ranges`](visualisation/voice-ranges.md) | Display compact per-staff pitch ranges for a single score | [Documentation](visualisation/voice-ranges.md) |
| [`plot_weighted_note_distribution`](visualisation/weighted-note-distribution.md) | Display a duration-weighted pitch-class radar chart for a single score | [Documentation](visualisation/weighted-note-distribution.md) |
| [`plot_melodic_ngram_heatmap`](visualisation/melodic-ngram-heatmap.md) | Display top melodic n-gram spans across scores and staves | [Documentation](visualisation/melodic-ngram-heatmap.md) |
| [`plot_sonority_ngram_progress`](visualisation/sonority-ngram-progress.md) | Display low-line sonority n-grams by normalized score progress | [Documentation](visualisation/sonority-ngram-progress.md) |

### Playback Tools

| Tool | Purpose | Learn More |
|------|---------|------------|
| [`play_excerpt`](play-excerpt.md) | Render a score or excerpt to streamed audio playback | [Documentation](play-excerpt.md) |

## Tool Categories

### 🔍 Discovery

Tools for exploring the MEI collection:

- **[list_available_mei_files](discovery.md)**: Browse files by composer
- **[register_mei_file_from_path](uploads.md)**: Make a user-supplied MEI path available to analysis tools

### 📋 Metadata

Tools for extracting descriptive information:

- **[get_mei_metadata](metadata.md)**: Get complete metadata from MEI headers

### 🎵 Musical Analysis

Tools for analyzing musical content:

- **[analyze_key](key-analysis.md)**: Key detection using music21
- **[Interval Analysis](intervals/index.md)**: Comprehensive interval analysis using CRIM Intervals
    - Notes extraction
    - Melodic intervals
    - Harmonic intervals
    - N-gram pattern matching

### 🎼 Notation Display

Tools for viewing rendered sheet music:

- **[show_notation](notation.md)**: Render MEI files as SVG notation with interactive pagination (requires [MCP Apps extension](https://modelcontextprotocol.io/docs/extensions/apps))

### Visualisation

Tools for viewing derived visual summaries:

- **[plot_voice_ranges](visualisation/voice-ranges.md)**: Plot the lowest and highest pitch reached by each staff in one score
- **[plot_weighted_note_distribution](visualisation/weighted-note-distribution.md)**: Plot duration-weighted pitch classes as a radar chart
- **[plot_melodic_ngram_heatmap](visualisation/melodic-ngram-heatmap.md)**: Plot top melodic n-gram spans as coloured rectangles across scores and staves
- **[plot_sonority_ngram_progress](visualisation/sonority-ngram-progress.md)**: Plot low-line sonority n-grams by normalized score progress

### Playback

Tools for listening to rendered score audio:

- **[play_excerpt](play-excerpt.md)**: Render an MEI score or excerpt as audio in an inline player

## Tool Design Philosophy

All tools in encoding-music-mcp follow these principles:

### 1. Direct File Access
Tools read directly from disk with no intermediate caching, ensuring:

- ⚡ Fast response times
- 💾 Minimal memory usage
- 🔄 Always up-to-date results

### 2. Structured Output
All tools return structured dictionaries with consistent keys:

```python
{
    "filename": "Bach_BWV_0772.mei",  # Always included
    "key_name": "...",                 # Tool-specific data
    # ...
}
```

### 3. Error Handling
Tools provide clear error messages when files don't exist or can't be processed:

```python
FileNotFoundError: Could not load MEI file: nonexistent.mei
```

### 4. Dataframe Format
Analysis tools return data in readable tabular format:

- Rows: Measure and beat positions
- Columns: Voice parts or analysis dimensions
- Values: Musical data (notes, intervals, patterns)

## Common Parameters

Most tools accept a `filename` parameter:

```python
filename: str  # Name of the MEI file (e.g., "Bach_BWV_0772.mei")
```

For user-supplied files, call `register_mei_file_from_path(file_path, filename)`
first, then pass the registered `filename` to analysis, notation, visualisation,
or playback tools. Omit `file_path` to ask the user for it via elicitation when
supported.

Analysis tools may accept additional parameters:

```python
n: int  # For ngrams: length of patterns (default: 4)
```

## Using Tools with AI Assistants

### Natural Language Queries

Simply ask your AI assistant in natural language:

- "What MEI files are available?"
- "Analyze the key of Bach_BWV_0772.mei"
- "Get melodic 5-grams from Bartok_Mikrokosmos_022.mei"

### Direct Tool Invocation

MCP clients can also invoke tools directly:

```json
{
  "tool": "get_mei_metadata",
  "arguments": {
    "filename": "Bach_BWV_0772.mei"
  }
}
```

## Next Steps

- Browse specific tool documentation using the navigation menu
- Try the [Quick Start guide](../getting-started/quick-start.md) for examples
- Explore the [MEI Resources](../resources/mei-files.md) available for analysis
