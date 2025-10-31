# Tools Overview

encoding-music-mcp provides a suite of tools for analyzing MEI files. All tools work with the [built-in MEI collection](../resources/mei-files.md).

## Available Tools

### Discovery Tools

| Tool | Purpose | Learn More |
|------|---------|------------|
| [`list_available_mei_files`](discovery.md) | Browse and discover the 46 built-in MEI files | [Documentation](discovery.md) |

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

## Tool Categories

### 🔍 Discovery

Tools for exploring the MEI collection:

- **[list_available_mei_files](discovery.md)**: Browse files by composer

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
