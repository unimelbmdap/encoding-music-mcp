# Tests

This directory contains tests for all encoding-music-mcp tools.

## Test Structure

- `test_discovery.py` - Tests for MEI file discovery tool (`list_available_mei_files`)
- `test_metadata.py` - Tests for MEI metadata extraction (`get_mei_metadata`)
- `test_key_analysis.py` - Tests for key analysis tool (`analyze_key`)
- `test_intervals.py` - Tests for interval analysis tools (notes, melodic/harmonic intervals, n-grams)

## Running Tests

### Run all tests

```bash
uv run pytest
```

### Run with verbose output

```bash
uv run pytest -v
```

### Run specific test file

```bash
uv run pytest tests/test_intervals.py
```

### Run specific test function

```bash
uv run pytest tests/test_intervals.py::test_get_notes_bach
```

### Run tests with coverage

```bash
uv run pytest --cov=src/encoding_music_mcp --cov-report=term-missing
```

## Test Resources

All tests use the built-in MEI files from the `src/encoding_music_mcp/resources` directory:

- **Bach_BWV_0772.mei** - Bach Invention No. 1 in C major (primary test file)
- **Bartok_Mikrokosmos_1_001.mei** - Bartók Mikrokosmos piece
- **Morley_1_01.mei** - Morley Canzonet

## Writing New Tests

When adding new tools, follow these conventions:

1. Create a new test file named `test_<module_name>.py`
2. Import the tool functions from `src.encoding_music_mcp.tools.<module>`
3. Test against at least one resource file from each composer
4. Verify return types, expected keys, and data formats
5. Include error handling tests (e.g., invalid filenames)

### Example test structure:

```python
"""Tests for new tool."""

import pytest
from src.encoding_music_mcp.tools.new_tool import new_function

def test_new_function_bach():
    """Test new function with Bach piece."""
    result = new_function("Bach_BWV_0772.mei")

    assert isinstance(result, dict), "Result should be a dictionary"
    assert "expected_key" in result, "Should contain expected key"
    # Add more assertions...

def test_new_function_invalid_file():
    """Test error handling for invalid files."""
    with pytest.raises(FileNotFoundError):
        new_function("nonexistent_file.mei")
```
