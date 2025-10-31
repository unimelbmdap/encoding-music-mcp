# list_available_mei_files

Discover all built-in MEI files organized by composer.

## Overview

The `list_available_mei_files` tool provides a complete inventory of the 46 MEI files included with encoding-music-mcp. Files are organized into three collections by composer.

## Parameters

This tool takes no parameters.

## Returns

Returns a dictionary with four keys:

| Key | Type | Description |
|-----|------|-------------|
| `bach_inventions` | `List[str]` | List of Bach Two-Part Invention filenames (15 files) |
| `bartok_mikrokosmos` | `List[str]` | List of Bartók Mikrokosmos filenames (19 files) |
| `morley_canzonets` | `List[str]` | List of Morley Canzonet filenames (12 files) |
| `all_files` | `List[str]` | Complete list of all 46 filenames |

## Example Usage

### With Claude Desktop

!!! example "Natural language query"
    "What MEI files are available?"

### Example Output

```json
{
  "bach_inventions": [
    "Bach_BWV_0772.mei",
    "Bach_BWV_0773.mei",
    "Bach_BWV_0774.mei",
    ...
  ],
  "bartok_mikrokosmos": [
    "Bartok_Mikrokosmos_022.mei",
    "Bartok_Mikrokosmos_023.mei",
    ...
  ],
  "morley_canzonets": [
    "Morley_1595_01_Go_ye_my_canzonettes.mei",
    "Morley_1595_02_When_lo_by_break.mei",
    ...
  ],
  "all_files": [
    "Bach_BWV_0772.mei",
    "Bach_BWV_0773.mei",
    ...
  ]
}
```

## Use Cases

### Browsing by Composer

Use the composer-specific lists to focus on particular repertoire:

```python
# Get only Bach inventions
bach_files = result["bach_inventions"]
```

### Batch Analysis

Use `all_files` to process the entire collection:

```python
# Analyze keys of all pieces
for filename in result["all_files"]:
    key_info = analyze_key(filename)
    print(f"{filename}: {key_info['Key Name']}")
```

### Collection Statistics

Use the lists to gather collection information:

```python
total_files = len(result["all_files"])
bach_count = len(result["bach_inventions"])
bartok_count = len(result["bartok_mikrokosmos"])
morley_count = len(result["morley_canzonets"])
```

## File Naming Conventions

### Bach Inventions
Format: `Bach_BWV_XXXX.mei`

- `BWV`: Bach-Werke-Verzeichnis (Bach Works Catalog)
- Ranges from BWV 772 to BWV 786 (15 inventions)

### Bartók Mikrokosmos
Format: `Bartok_Mikrokosmos_XXX.mei`

- Numbers correspond to Mikrokosmos volume and piece numbers

### Morley Canzonets
Format: `Morley_1595_XX_Title.mei`

- `1595`: Publication year
- Includes descriptive titles

## Related Tools

- [get_mei_metadata](metadata.md) - Get detailed information about specific files
- [Resources: MEI Files](../resources/mei-files.md) - Learn more about the collection

## Implementation

The tool scans the `resources` directory and categorizes files based on filename prefixes:

- Files starting with `Bach_BWV_` → Bach inventions
- Files starting with `Bartok_Mikrokosmos_` → Bartók pieces
- Files starting with `Morley_` → Morley canzonets
