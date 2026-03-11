# Agents Guide — encoding-music-mcp

## What this project is

An MCP server for analysing MEI (Music Encoding Initiative) files. It provides tools for metadata extraction, musical analysis (intervals, n-grams, cadences, key detection), and notation display via Verovio SVG rendering. Ships with 46 built-in MEI files (Bach, Bartók, Morley).

## Key documentation

Start here to understand the project:

- **[docs/api-reference.md](docs/api-reference.md)** — Complete tool catalogue with parameters and return types
- **[docs/development/structure.md](docs/development/structure.md)** — Project layout and module organisation
- **[docs/development/testing.md](docs/development/testing.md)** — How to run tests
- **[docs/development/contributing.md](docs/development/contributing.md)** — Development workflow and conventions

## Architecture

```
src/encoding_music_mcp/
├── server.py              # FastMCP server (stdio + http transport)
├── tools/
│   ├── registry.py        # Central tool registration
│   ├── helpers.py          # Shared utilities (MEI filepath resolution)
│   ├── discovery.py        # list_available_mei_files
│   ├── metadata.py         # get_mei_metadata
│   ├── key_analysis.py     # analyze_key (music21)
│   ├── intervals.py        # get_notes, get_melodic_intervals, get_harmonic_intervals,
│   │                       # get_melodic_ngrams, get_cadences (CRIM Intervals)
│   └── notation.py         # show_notation (Verovio SVG rendering)
├── resources/
│   ├── registry.py         # Resource registration
│   ├── mei.py              # MEI file resource handlers
│   ├── mei_files/          # 46 built-in MEI files
│   └── notation_app.html   # Interactive notation viewer (MCP Apps extension)
└── prompts/
    ├── registry.py         # Prompt registration
    └── comprehensive_analysis.py
```

## Key dependencies

- **fastmcp** (≥3.0) — MCP server framework with Apps support
- **crim-intervals** — Music analysis (intervals, n-grams, cadences)
- **verovio** (≥5.5) — MEI to SVG notation rendering
- **music21** — Key detection (via analyze_key)

## Conventions
- Tests live in `tests/` and use pytest
- Formatting/linting via ruff
- Docker deployment: multi-stage Dockerfile with Caddy reverse proxy

## Deployment

- **Local**: `uvx encoding-music-mcp` or `uv run encoding-music-mcp`
- **Docker**: `docker compose up -d --build` (serves via Caddy on ports 80/443)
- Dockerfile uses split dependency/project install layers to cache Verovio compilation