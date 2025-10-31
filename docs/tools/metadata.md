# get_mei_metadata

Extract comprehensive metadata from MEI file headers.

## Overview

The `get_mei_metadata` tool extracts descriptive information from MEI files, including title, composer, editors, analysts, publication dates, and copyright information.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `filename` | `str` | Yes | Name of the MEI file (e.g., "Bach_BWV_0772.mei") |

## Returns

Returns a dictionary with the following keys:

| Key | Type | Description |
|-----|------|-------------|
| `title` | `str` | Title of the work |
| `composer` | `str` | Composer name |
| `mei_editors` | `List[str]` | List of MEI encoding editors |
| `xml_editors` | `List[str]` | List of XML editors |
| `analysts` | `List[str]` | List of analysts who worked on the encoding |
| `publication_date` | `str \| None` | Publication or encoding date |
| `copyright` | `str \| None` | Copyright or availability information |
| `application` | `str \| None` | Software used to create the MEI file |

## Example Usage

### With Claude Desktop

!!! example "Natural language queries"
    - "Tell me about Bach_BWV_0772.mei"
    - "What's the metadata for Bartok_Mikrokosmos_022.mei?"
    - "Who encoded Morley_1595_01_Go_ye_my_canzonettes.mei?"

### Example Output

```json
{
  "title": "Invention No. 1 in C major",
  "composer": "Bach, Johann Sebastian",
  "mei_editors": ["Freedman, Richard"],
  "xml_editors": ["Schölkopf, Tobias"],
  "analysts": ["Student, This"],
  "publication_date": "2024-11-19",
  "copyright": "Available under CC-BY-NC-SA 4.0",
  "application": "Sibelius 8.7.0"
}
```

## Use Cases

### Cataloging

Build a catalog of your MEI collection:

```python
metadata = get_mei_metadata("Bach_BWV_0772.mei")
print(f"{metadata['composer']}: {metadata['title']}")
```

### Attribution

Track who contributed to the encoding:

```python
print(f"MEI Editors: {', '.join(metadata['mei_editors'])}")
print(f"Analysts: {', '.join(metadata['analysts'])}")
```

### Quality Control

Verify encoding information before analysis:

```python
if metadata['publication_date']:
    print(f"Last updated: {metadata['publication_date']}")
```

## Metadata Sources

The tool extracts information from MEI header elements:

- **`<title>`**: Work title
- **`<composer>`**: Composer name
- **`<editor>`**: Editor and analyst information (with role attributes)
- **`<pubStmt>`**: Publication and date information
- **`<availability>`**: Copyright and licensing
- **`<appInfo>`**: Software used for encoding

## Error Handling

If a file doesn't exist:

```python
FileNotFoundError: [Errno 2] No such file or directory:
  'src/encoding_music_mcp/resources/nonexistent.mei'
```

## Related Tools

- [list_available_mei_files](discovery.md) - Discover available files
- [Resources: MEI Files](../resources/mei-files.md) - Learn about the collection

## Implementation Notes

- Empty fields return empty lists `[]` or `None` rather than raising errors
- Multiple editors/analysts are returned as lists
- Date formats may vary by file
