# Contributing

Thank you for your interest in contributing to encoding-music-mcp!

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/encoding-music-mcp.git
   cd encoding-music-mcp
   ```
3. **Install dependencies**:
   ```bash
   uv sync
   ```

## Development Workflow

### Making Changes

1. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the [Project Structure](structure.md)

3. **Format your code**:
   ```bash
   uv run ruff format .
   ```

4. **Run tests**:
   ```bash
   uv run pytest
   ```

5. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Add feature: description"
   ```

### Code Style

We use [Ruff](https://docs.astral.sh/ruff/) for code formatting and linting:

```bash
# Format code
uv run ruff format .

# Check for issues
uv run ruff check .
```

### Testing

All changes must include tests. See [Testing](testing.md) for details.

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_intervals.py

# Run with coverage
uv run pytest --cov=src/encoding_music_mcp
```

## Submitting Changes

1. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a Pull Request** on GitHub

3. **Wait for review** - maintainers will review your PR

## Types of Contributions

### Bug Fixes

- Report bugs via [GitHub Issues](https://github.com/unimelbmdap/encoding-music-mcp/issues)
- Include reproduction steps
- Fix the bug and add a test case

### New Tools

When adding new analysis tools:

1. Create the tool in `src/encoding_music_mcp/tools/`
2. Register it in `tools/registry.py`
3. Add comprehensive tests in `tests/`
4. Document the tool in `docs/tools/`

### Documentation

- Fix typos and improve clarity
- Add examples and use cases
- Update outdated information

### MEI Files

To add new MEI files:

1. Ensure files follow MEI standards
2. Include complete metadata headers
3. Update discovery tool if needed
4. Add documentation

## Development Environment

### Required Tools

- **Python** 3.11 or higher
- **uv** package manager
- **Git** for version control

### IDE Setup

We recommend:

- VS Code with Python extension
- PyCharm
- Any editor with Python support

### Running the Server Locally

```bash
uv run encoding-music-mcp
```

## Questions?

- Open an [issue](https://github.com/unimelbmdap/encoding-music-mcp/issues)
- Check existing issues and PRs
- Read the [development docs](structure.md)

## Code of Conduct

Be respectful and constructive. This is an academic project aimed at supporting music research and education.
