# encoding-music-mcp

MCP server for analyzing MEI (Music Encoding Initiative) files. Provides tools to extract metadata, analyze musical structure, and understand encoded scores.

## Features

Currently supports:
- **MEI Metadata Extraction**: Extract title, composer, editors, analysts, publication dates, and copyright information from MEI files

## Installation

Install using uv:

```bash
uv sync
```

## Usage

### With Claude Desktop

Add to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "encoding-music": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/encoding-music-mcp", "run", "encoding-music-mcp"]
    }
  }
}
```

### Standalone

Run the server directly:

```bash
uv run encoding-music-mcp
```

## Available Tools

### `get_mei_metadata`

Extract detailed metadata from an MEI file.

**Parameters**:
- `filepath` (string, required): Absolute path to the MEI file

**Returns**: Formatted metadata including:
- Title and work title
- Composer
- MEI editors
- XML editors
- Analysts
- Publication date
- Copyright/availability information
- Application used to create the file

**Example**:
```
Title: Invention No. 1 in C major
Composer: Bach, Johann Sebastian
MEI Editors: Richard Freedman
XML Editors: Tobias Scholkopf
Publication Date: 2023-01-15
```

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
