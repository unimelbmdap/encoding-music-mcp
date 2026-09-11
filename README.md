# Encoding Music MCP retrieval setup

This repository includes a prepared song-embedding database. After setup, Claude
can search it with semantic-axis, prototype, and combined retrieval tools. You do
not need to create embeddings or build a database.

## Requirements

- Git
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Several GB of free disk space for the CLaMP model and Python packages

Supported systems:

- Windows x64
- Linux x86_64
- Apple Silicon Mac (M1 or newer), using a native terminal rather than Rosetta

Intel Macs are not supported by the pinned CLaMP runtime.

## 1. Clone and set up retrieval

```bash
git clone https://github.com/unimelbmdap/encoding-music-mcp.git
cd encoding-music-mcp
uv run --extra score-embeddings --locked encoding-music-embeddings bootstrap
```

The command creates the local CLaMP environment and downloads the model files.
The included database is used automatically from:

```text
src/encoding_music_mcp/resources/score-embeddings.sqlite
```

No CLaMP environment variables or database path are required.

## 2. Add the server to Claude Desktop

Open **Claude Desktop → Settings → Developer → Edit Config** and add:

```json
{
  "mcpServers": {
    "encoding-music-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/encoding-music-mcp",
        "run",
        "--extra",
        "score-embeddings",
        "--locked",
        "encoding-music-mcp"
      ]
    }
  }
}
```

Replace `/absolute/path/to/encoding-music-mcp` with the cloned repository path.
On Windows, escape backslashes, for example:

```json
"C:\\Users\\your-name\\encoding-music-mcp"
```

Restart Claude Desktop after saving the configuration.

## 3. Search the included database

Ask Claude requests such as:

- “Find songs that sound joyful rather than sorrowful.”
- “Find songs with a pastoral character.”
- “Find tense modernist music combined with a peaceful character.”

Claude can use:

- `search_songs_by_semantic_axis` for a contrast such as joyful–sorrowful
- `search_songs_by_prototype` for one concept such as pastoral
- `search_songs_by_combined_criteria` to combine several criteria

The first search loads the CLaMP model and may take longer. Later searches reuse
the loaded model.

For detailed retrieval behavior and troubleshooting, see:

- [Semantic-axis retrieval](docs/tools/semantic-axis-retrieval.md)
- [Prototype retrieval](docs/tools/prototype-retrieval.md)
- [CLaMP setup](docs/getting-started/clamp3-pipeline.md)
