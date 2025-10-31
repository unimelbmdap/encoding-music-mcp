# Project Structure

Understanding the organization of encoding-music-mcp.

## Directory Layout

```
encoding-music-mcp/
├── src/
│   └── encoding_music_mcp/
│       ├── __init__.py
│       ├── server.py           # MCP server entry point
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── registry.py     # Tool registration
│       │   ├── helpers.py      # Shared utilities
│       │   ├── discovery.py    # File discovery
│       │   ├── metadata.py     # Metadata extraction
│       │   ├── key_analysis.py # Key detection
│       │   └── intervals.py    # Interval analysis
│       └── resources/          # MEI files (46 files)
│           ├── Bach_BWV_*.mei
│           ├── Bartok_Mikrokosmos_*.mei
│           └── Morley_*.mei
├── tests/
│   ├── __init__.py
│   ├── test_discovery.py
│   ├── test_metadata.py
│   ├── test_key_analysis.py
│   ├── test_intervals.py
│   └── README.md
├── docs/                       # Documentation (you are here)
│   ├── index.md
│   ├── getting-started/
│   ├── tools/
│   ├── resources/
│   └── development/
├── pyproject.toml             # Project configuration
├── mkdocs.yml                 # Documentation configuration
├── README.md                  # Project readme
└── main.py                    # Legacy entry point
```

## Key Files

### `src/encoding_music_mcp/server.py`

MCP server setup:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("encoding-music-mcp")

# Tools are imported from registry
from .tools import registry

def main():
    mcp.run()
```

### `src/encoding_music_mcp/tools/registry.py`

Central tool registration:

```python
from ..server import mcp
from .metadata import get_mei_metadata
# ... other imports

# Register tools
mcp.tool()(get_mei_metadata)
mcp.tool()(analyze_key)
# ... other registrations
```

### `src/encoding_music_mcp/tools/helpers.py`

Shared utility functions:

```python
def get_mei_filepath(filename: str) -> Path:
    """Convert filename to full path."""
    resources_dir = Path(__file__).parent.parent / "resources"
    return resources_dir / filename
```

## Adding a New Tool

1. **Create the tool** in `src/encoding_music_mcp/tools/your_tool.py`:

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

2. **Register the tool** in `tools/registry.py`:

```python
from .your_tool import your_tool

mcp.tool()(your_tool)
```

3. **Add tests** in `tests/test_your_tool.py`

4. **Document** in `docs/tools/your-tool.md`

## Module Organization

### Tools Module (`src/encoding_music_mcp/tools/`)

- **registry.py**: Central registration point
- **helpers.py**: Shared utilities
- **discovery.py**: File browsing
- **metadata.py**: MEI header parsing
- **key_analysis.py**: Music21-based key detection
- **intervals.py**: CRIM Intervals analysis

### Tests Module (`tests/`)

One test file per tool module, organized by functionality.

## Configuration Files

### `pyproject.toml`

Project metadata and dependencies:

```toml
[project]
name = "encoding-music-mcp"
version = "0.1.0"
dependencies = [
    "mcp>=1.0.0",
    "crim-intervals>=2.0.61",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "ruff>=0.8.0",
    "mkdocs-material>=9.6.22",
]
```

### `mkdocs.yml`

Documentation site configuration using Material theme.

## Dependencies

### Runtime
- **mcp**: Model Context Protocol implementation
- **crim-intervals**: Interval analysis (includes music21)

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
