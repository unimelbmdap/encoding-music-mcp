# Configuration

This guide explains how to configure encoding-music-mcp with various MCP clients.

## Claude Desktop

Claude Desktop is the most common MCP client for using encoding-music-mcp.

### Locating the Configuration File

The configuration file location depends on your operating system:

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

## Standalone Mode

You can also run the server directly without an MCP client (useful for testing):

```bash
uv run encoding-music-mcp
```

This starts the server and listens for MCP connections via stdio.

## Next Steps

- Try the [Quick Start guide](quick-start.md) to test your configuration
- Explore the [Tools documentation](../tools/index.md) to see what's available
