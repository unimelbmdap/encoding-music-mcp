# Configuration

This guide explains how to configure encoding-music-mcp with various MCP clients.

## Claude Desktop

Claude Desktop is the most common MCP client for using encoding-music-mcp.

### Opening the Configuration File

The easiest way to open the configuration file is from Claude Desktop:

1. Open **Settings**
2. Select **Developer**
3. Under **Local MCP servers**, click **Edit Config**

This locates the correct `claude_desktop_config.json` file for your installation.

If you need to find the file manually, common locations are:

=== "macOS"

    ```
    ~/Library/Application Support/Claude/claude_desktop_config.json
    ```

=== "Windows"

    ```
    %APPDATA%\Claude\claude_desktop_config.json
    ```

=== "Linux"

    ```
    ~/.config/Claude/claude_desktop_config.json
    ```

### Configuration Methods

Choose the configuration method that matches your [installation method](installation.md):

=== "Method A: Using uvx (Recommended)"

    For users who installed via uvx (no local clone):

    ```json
    {
      "mcpServers": {
        "encoding-music-mcp": {
          "command": "uvx",
          "args": [
            "--from",
            "git+https://github.com/unimelbmdap/encoding-music-mcp.git",
            "encoding-music-mcp"
          ]
        }
      }
    }
    ```

=== "Method B: Using Local Clone"

    For users who cloned the repository locally:

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

    !!! warning "Use Absolute Paths"
        Replace `/absolute/path/to/encoding-music-mcp` with the actual absolute path to your cloned repository.

        - ✅ Good: `/Users/alice/projects/encoding-music-mcp`
        - ❌ Bad: `~/projects/encoding-music-mcp`
        - ❌ Bad: `./encoding-music-mcp`

### Applying Configuration

After editing the configuration file:

1. **Save the file**
2. **Restart Claude Desktop** completely
3. **Verify connection** by looking for the MCP server indicator in Claude Desktop

!!! tip "Troubleshooting"
    If the server doesn't appear:

    - Verify the JSON syntax is valid (no trailing commas, proper brackets)
    - Check that the path is absolute and correct
    - Ensure uv is installed and in your PATH
    - Check Claude Desktop logs for error messages

## Other MCP Clients

encoding-music-mcp should work with any MCP-compatible client. The general configuration pattern is:

```json
{
  "command": "uvx",
  "args": [
    "--from",
    "git+https://github.com/unimelbmdap/encoding-music-mcp.git",
    "encoding-music-mcp"
  ]
}
```

Consult your MCP client's documentation for specific configuration instructions.

## Semantic retrieval environment

For a local clone on Windows x64, Linux x86_64, or macOS on Apple Silicon,
run once from its root:

```bash
uv run --extra score-embeddings --locked encoding-music-embeddings bootstrap
```

CPU is the default and is the supported profile on Mac. Use a native arm64
terminal and uv/Python installation on Apple Silicon, not Rosetta.
Add `--profile cu128` for a compatible NVIDIA CUDA 12.8 GPU on Windows or Linux.
The [pipeline guide](clamp3-pipeline.md) covers prerequisites and troubleshooting.
Use the local-clone launcher above, which includes `--extra score-embeddings --locked`.
Both retrieval tools discover `.venv-clamp` and `.clamp3-cache` relative to the
loaded source checkout, independently of Claude's working directory. They use the
bundled embedding database by default. Restart Claude after setup or configuration changes.

For example, after bootstrap on Windows:

```json
{
  "mcpServers": {
    "encoding-music-mcp": {
      "command": "C:\\Users\\warda\\.local\\bin\\uv.exe",
      "args": [
        "--quiet",
        "--directory",
        "D:\\Work\\mcp_test\\encoding-music-mcp",
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

Adjust the executable and checkout paths for your machine.

For an externally provisioned runtime or an installed package, an `env` object
beside `command` and `args` overrides discovery:

```json
"env": {
  "ENCODING_MUSIC_EMBEDDINGS_DATABASE": "/absolute/path/score-embeddings.sqlite3",
  "ENCODING_MUSIC_CLAMP_PYTHON": "/absolute/path/to/clamp-python",
  "ENCODING_MUSIC_CLAMP_CACHE_DIR": "/absolute/path/to/clamp-cache",
  "ENCODING_MUSIC_CLAMP_TIMEOUT_SECONDS": "3600"
}
```

Every setting is optional for a bootstrapped checkout. Invalid interpreter overrides
raise an error instead of silently using the local environment. An explicit external
interpreter uses the repository cache if present; otherwise it retains the platform
user-cache default. Set the cache override too when using a different prepared cache.
These settings enable both `search_songs_by_semantic_axis` and
`search_songs_by_prototype`; imports and queries never install packages, download
model assets, or generate corpus embeddings.

## Remote HTTP endpoint

Clients that support remote Streamable HTTP can connect to:

```text
https://encoding-music.drdanielrb.com/mcp
```

Use the MCP endpoint as written rather than the `/health` URL. Opening `/mcp`
in an ordinary browser can return HTTP 406 because browsers do not send MCP
streaming headers; this is expected. The `/health` endpoint is available for a
simple browser or uptime check.

## Standalone Mode

You can also run the server directly without an MCP client (useful for testing):

```bash
uv run --extra score-embeddings --locked encoding-music-mcp
```

This starts the server and listens for MCP connections via stdio.

## Next Steps

- Try the [Quick Start guide](quick-start.md) to test your configuration
- Explore the [Tools documentation](../tools/index.md) to see what's available
