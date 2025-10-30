# encoding-music-mcp

MCP server for analyzing MEI (Music Encoding Initiative) files. Provides tools to extract metadata, analyze musical structure, and understand encoded scores.

## Features

- **46 Built-in MEI Files**: Bach Inventions, Bartók Mikrokosmos, Morley Canzonets - ready to analyze
- **MEI Metadata Extraction**: Extract title, composer, editors, analysts, publication dates, and copyright information
- **Simple & Efficient**: Tools read directly from disk - no token waste

## Installation

Install using uv:

```bash
uv sync
```

## Usage

### With Claude Desktop

1. **Find your Claude Desktop configuration file:**
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

2. **Add this configuration:**

```json
{
  "mcpServers": {
    "encoding-music": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/encoding-music-mcp",
        "run",
        "encoding-music-mcp"
      ]
    }
  }
}
```

3. **Restart Claude Desktop**

4. **Try it out:**
   - "What MEI files are available?" → Lists 46 built-in files
   - "Tell me about Bach_BWV_0772.mei" → Reads resource and extracts metadata

### Standalone

Run the server directly:

```bash
uv run encoding-music-mcp
```

## Available Tools

### `list_available_mei_files`

Discover all built-in MEI files.

**Returns**: Dictionary with:
- `total_count`: Total number of files
- `bach_inventions`: List of Bach files
- `bartok_mikrokosmos`: List of Bartók files
- `morley_canzonets`: List of Morley files
- `all_files`: Complete list of filenames

### `get_mei_metadata`

Extract detailed metadata from a built-in MEI file.

**Parameters**:
- `filename` (string, required): Name of the MEI file (e.g., "Bach_BWV_0772.mei")

**Returns**: Dictionary with metadata including:
- Title and work title
- Composer
- MEI editors
- XML editors
- Analysts
- Publication date
- Copyright/availability information
- Application used to create the file

**Example output**:
```json
{
  "title": "Invention No. 1 in C major",
  "composer": "Bach, Johann Sebastian",
  "mei_editors": ["Freedman, Richard"],
  "xml_editors": ["Schölkopf, Tobias"],
  "analysts": ["Student, This"],
  "publication_date": "2024-11-19"
}
```

## Built-in Files

The server includes 46 MEI files:
- **15 Bach Two-Part Inventions** (BWV 772-786)
- **19 Bartók Mikrokosmos pieces**
- **12 Morley Canzonets** from 1595

Use `list_available_mei_files()` to discover all available files.

## Development

The project uses uv for dependency management:

```bash
# Install dependencies
uv sync

# Run the server
uv run encoding-music-mcp

# Format code
uv run ruff format .
```

## Coming Soon

Additional tools planned:
- Note counting and frequency analysis
- Key and time signature detection
- Pitch histograms
- Lyrics extraction
- Full note sequence analysis

## License

MIT
