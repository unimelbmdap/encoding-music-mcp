# Project Structure

Understanding the organization of encoding-music-mcp.

## Directory Layout

```text
encoding-music-mcp/
|-- src/
|   `-- encoding_music_mcp/
|       |-- __init__.py
|       |-- server.py                       # MCP server entry point
|       |-- tools/
|       |   |-- __init__.py
|       |   |-- registry.py                 # Tool registration
|       |   |-- helpers.py                  # Shared utilities
|       |   |-- discovery.py                # File discovery
|       |   |-- metadata.py                 # Metadata extraction
|       |   |-- key_analysis.py             # Key detection
|       |   |-- intervals.py                # Interval and n-gram analysis
|       |   |-- notation.py                 # Notation display (Verovio)
|       |   |-- play_excerpt.py             # Audio playback
|       |   |-- comprehensive_analysis.py   # Multi-tool summary workflow
|       |   |-- sampling_diagnostics.py     # Sampling diagnostics
|       |   `-- visualisation/
|       |       |-- __init__.py
|       |       |-- melodic_ngram_heatmap.py
|       |       |-- voice_ranges.py
|       |       `-- weighted_note_distribution.py
|       |-- resources/
|       |   |-- __init__.py
|       |   |-- mei.py
|       |   |-- registry.py                 # Resource registration
|       |   |-- GeneralUser-GS.sf2
|       |   |-- mei_files/                  # Built-in MEI files
|       |   `-- templates/                  # HTML templates for MCP Apps UIs
|       |-- prompts/
|       |   |-- __init__.py
|       |   |-- registry.py                 # Prompt registration
|       |   |-- comprehensive_analysis.py
|       |   `-- comprehensive_analysis_sampled.py
|       `-- templates/
|           `-- incipit_verovio_app.html
|-- tests/
|   |-- __init__.py
|   |-- test_discovery.py
|   |-- test_metadata.py
|   |-- test_key_analysis.py
|   |-- test_intervals.py
|   |-- test_notation.py
|   |-- test_play_excerpt.py
|   |-- test_voice_ranges.py
|   |-- test_weighted_note_distribution.py
|   |-- test_melodic_ngram_heatmap.py
|   `-- README.md
|-- docs/                               # Documentation
|   |-- index.md
|   |-- api-reference.md
|   |-- getting-started/
|   |-- resources/
|   |-- development/
|   `-- tools/
|       |-- index.md
|       |-- discovery.md
|       |-- metadata.md
|       |-- key-analysis.md
|       |-- notation.md
|       |-- play-excerpt.md
|       |-- intervals/
|       `-- visualisation/
|           |-- voice-ranges.md
|           |-- weighted-note-distribution.md
|           `-- melodic-ngram-heatmap.md
|-- pyproject.toml                     # Project configuration
|-- mkdocs.yml                         # Documentation configuration
|-- README.md                          # Project readme
|-- Dockerfile
|-- docker-compose.yml
`-- Caddyfile
```

## Key Files

### `src/encoding_music_mcp/server.py`

MCP server setup and transport selection:

```python
from fastmcp import FastMCP

mcp = FastMCP("encoding-music-mcp")

from .tools import registry
from .resources import registry as resources_registry
from .prompts import registry as prompts_registry

def main():
    mcp.run()
```

### `src/encoding_music_mcp/tools/registry.py`

Central tool registration:

```python
from ..server import mcp
from .metadata import get_mei_metadata
# ... other imports

mcp.tool()(get_mei_metadata)
mcp.tool()(analyze_key)
# ... other registrations
```

### `src/encoding_music_mcp/tools/helpers.py`

Shared utility functions, including MEI path resolution:

```python
def get_mei_filepath(filename: str) -> Path:
    """Convert filename to full path."""
    resources_dir = Path(__file__).parent.parent / "resources"
    return resources_dir / "mei_files" / filename
```

## Adding a New Tool

1. Create the tool in `src/encoding_music_mcp/tools/your_tool.py`:

```python
"""Your tool description."""

from typing import Any

from .helpers import get_mei_filepath

def your_tool(filename: str) -> dict[str, Any]:
    """Tool function with docstring."""
    filepath = get_mei_filepath(filename)
    # Implementation
    return {"filename": filename, "result": ...}
```

2. Register the tool in `tools/registry.py`:

```python
from .your_tool import your_tool

mcp.tool()(your_tool)
```

3. Add tests in `tests/test_your_tool.py`.

4. Document the tool in `docs/tools/your-tool.md`.

For visualisation tools, use the matching nested locations:

- Source: `src/encoding_music_mcp/tools/visualisation/your_tool.py`
- Documentation: `docs/tools/visualisation/your-tool.md`

## Module Organization

### Tools Module (`src/encoding_music_mcp/tools/`)

- `registry.py`: Central registration point
- `helpers.py`: Shared utilities
- `discovery.py`: File browsing
- `metadata.py`: MEI header parsing
- `key_analysis.py`: music21-based key detection
- `intervals.py`: CRIM Intervals analysis
- `notation.py`: Verovio-based notation rendering
- `play_excerpt.py`: Audio rendering and playback payloads
- `visualisation/`: Visual summary tools and app payload builders

### Documentation Tools (`docs/tools/`)

- Top-level tool docs live beside `docs/tools/index.md`
- Interval tool docs live in `docs/tools/intervals/`
- Visualisation tool docs live in `docs/tools/visualisation/`

### Tests Module (`tests/`)

Tests are organized by functionality, with one or more test files per tool area.

## Configuration Files

### `pyproject.toml`

Project metadata and dependencies:

```toml
[project]
name = "encoding-music-mcp"
version = "0.1.0"
dependencies = [
    "fastmcp>=3.0",
    "crim-intervals",
    "verovio>=5.5",
    "music21",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "ruff>=0.8.0",
    "mkdocs-material>=9.6.22",
]
```

### `mkdocs.yml`

Documentation site configuration using the Material theme.

## Dependencies

### Runtime

- **fastmcp**: FastMCP v3 framework for MCP server and Apps support
- **crim-intervals**: Interval, n-gram, and cadence analysis
- **verovio**: Music notation engraving (MEI to SVG)
- **music21**: Key detection and music analysis helpers

### Development

- **pytest**: Testing framework
- **ruff**: Code formatter and linter
- **mkdocs-material**: Documentation generator

## Build System

Uses `uv_build` backend with src-layout:

- Package installed as `encoding-music-mcp`
- Entry point: `encoding_music_mcp.server:main`
- Editable installs supported

## Related Documentation

- [Contributing Guide](contributing.md)
- [Testing Guide](testing.md)
