# Installation

This guide will help you install and set up encoding-music-mcp on your system.

## Prerequisites

Before you begin, ensure you have **[uv](https://docs.astral.sh/uv/getting-started/installation/)** installed on your system. uv is a fast Python package installer and resolver.

### Installing uv

=== "macOS/Linux"

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

=== "Windows"

    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

For alternative installation methods, see the [official uv documentation](https://docs.astral.sh/uv/getting-started/installation/).

## Installation Methods

There are two ways to install encoding-music-mcp:

### Option 1: Quick Start (Using uvx)

The fastest way to get started - no cloning required! This method runs the server directly from the GitHub repository.

!!! tip "Recommended for most users"
    This method is ideal if you just want to use the server without modifying the code.

Simply add the following configuration to your MCP client (see [Configuration](configuration.md) for details):

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

### Option 2: Local Development

For development or if you want to modify the code:

1. **Clone the repository:**

    ```bash
    git clone https://github.com/unimelbmdap/encoding-music-mcp.git
    cd encoding-music-mcp
    ```

2. **Install dependencies:**

    ```bash
    uv sync
    ```

3. **Verify installation:**

    ```bash
    uv run encoding-music-mcp
    ```

!!! note "Development Dependencies"
    The `uv sync` command installs both runtime and development dependencies, including:

    - `pytest` for running tests
    - `ruff` for code formatting
    - `mkdocs-material` for documentation

## Next Steps

- [Configure your MCP client](configuration.md) to use the server
- Try the [Quick Start guide](quick-start.md) to test the tools
- Explore the [Tools documentation](../tools/index.md) to learn what's available
