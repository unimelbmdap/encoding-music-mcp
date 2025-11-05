# Testing

encoding-music-mcp includes a comprehensive test suite to ensure reliability.

## Running Tests

### All Tests

```bash
uv run pytest
```

### Verbose Output

```bash
uv run pytest -v
```

### Specific Test File

```bash
uv run pytest tests/test_intervals.py
```

### Specific Test Function

```bash
uv run pytest tests/test_intervals.py::test_get_notes_bach
```

### With Coverage

```bash
uv run pytest --cov=src/encoding_music_mcp --cov-report=term-missing
```

## Test Structure

Tests are organized in the `tests/` directory:

```
tests/
├── __init__.py
├── test_discovery.py       # Discovery tool tests
├── test_metadata.py         # Metadata extraction tests
├── test_key_analysis.py     # Key analysis tests
├── test_intervals.py        # Interval analysis tests
└── README.md                # Testing documentation
```

## Test Files

### test_discovery.py (4 tests)
- File discovery functionality
- Collection organization
- Naming conventions

### test_metadata.py (5 tests)
- Metadata extraction
- Multiple composers
- Error handling

### test_key_analysis.py (6 tests)
- Key detection
- Confidence factors
- Multiple pieces

### test_intervals.py (13 tests)
- Notes extraction
- Melodic intervals
- Harmonic intervals
- N-gram patterns

## Writing Tests

### Test Structure

```python
"""Tests for new tool."""

import pytest
from src.encoding_music_mcp.tools.new_tool import new_function


def test_new_function_bach():
    """Test new function with Bach piece."""
    result = new_function("Bach_BWV_0772.mei")

    assert isinstance(result, dict), "Result should be a dictionary"
    assert "expected_key" in result, "Should contain expected key"


def test_new_function_invalid_file():
    """Test error handling for invalid files."""
    with pytest.raises(FileNotFoundError):
        new_function("nonexistent_file.mei")
```

### Test Resources

Tests use built-in MEI files:

- `Bach_BWV_0772.mei` - Primary test file
- `Bartok_Mikrokosmos_022.mei` - Bartók test file
- `Morley_1595_01_Go_ye_my_canzonettes.mei` - Morley test file

### Assertions

Test for:

- **Return types**: `isinstance(result, dict)`
- **Expected keys**: `"key_name" in result`
- **Data formats**: String, lists, numbers
- **Error handling**: `pytest.raises(Exception)`
- **Data content**: Value ranges, formats

## Continuous Integration

Tests run automatically on:

- Every commit
- Pull requests
- Before releases

## Test Coverage

Current coverage: ~100% for all tools

View coverage report:

```bash
uv run pytest --cov=src/encoding_music_mcp --cov-report=html
open htmlcov/index.html
```

## Adding Tests for New Tools

When adding a new tool:

1. Create tests in `tests/test_your_tool.py`
2. Test with multiple files (Bach, Bartók, Morley)
3. Test error conditions
4. Verify return structure
5. Check data formats

Example:

```python
def test_your_tool_bach():
    """Test with Bach piece."""
    result = your_tool("Bach_BWV_0772.mei")
    assert isinstance(result, dict)

def test_your_tool_bartok():
    """Test with Bartók piece."""
    result = your_tool("Bartok_Mikrokosmos_022.mei")
    assert isinstance(result, dict)

def test_your_tool_invalid():
    """Test error handling."""
    with pytest.raises(FileNotFoundError):
        your_tool("nonexistent.mei")
```

## Interactive Testing with MCP Inspector

For interactive testing and debugging of the MCP server, use the MCP Inspector:

```bash
uv run mcp dev dev_server.py:mcp
```

This will start the MCP Inspector at `http://localhost:6274` where you can:

- Browse all available tools, resources, and prompts
- Test tools interactively with different parameters
- View real-time responses and outputs
- Debug server behaviour and responses

**Note:** Requires the package to be installed. Run `uv sync` first if needed.

### What is the MCP Inspector?

The MCP Inspector is a web-based development tool that provides:

- **Tool Testing**: Call any tool with custom parameters and see results immediately
- **Resource Browser**: View all available resources and their contents
- **Prompt Testing**: Try prompt templates with different arguments
- **Debug View**: Inspect request/response JSON for debugging

This is especially useful for:

- Testing new tools before writing unit tests
- Debugging issues with tool parameters or responses
- Exploring the server's capabilities interactively
- Demonstrating functionality to others

## Related Documentation

- [Contributing Guide](contributing.md)
- [Project Structure](structure.md)
