# MEI Files

encoding-music-mcp includes 46 carefully curated MEI files from three major collections.

## Overview

All files are stored in the `resources` directory and are immediately accessible through the MCP server. No additional downloads or configuration required.

## Collections

### Bach Two-Part Inventions (15 files)

J.S. Bach's Two-Part Inventions (BWV 772-786) - pedagogical keyboard works demonstrating contrapuntal technique.

[View Bach collection details →](bach.md)

### Bartók Mikrokosmos (19 files)

Selected pieces from Béla Bartók's Mikrokosmos - progressive piano pieces exploring 20th-century musical techniques.

[View Bartók collection details →](bartok.md)

### Morley Canzonets (12 files)

Thomas Morley's Canzonets from 1595 - Renaissance vocal music demonstrating English madrigal style.

[View Morley collection details →](morley.md)

## File Format

All files follow the MEI (Music Encoding Initiative) standard:

- **Format**: XML-based music notation encoding
- **Extension**: `.mei`
- **Encoding**: UTF-8
- **Standard**: MEI 4.0 or compatible

## Quality and Provenance

All files include detailed metadata:

- **Composer** information
- **Title** and work information
- **MEI editors** who created the encoding
- **Publication dates**
- **Copyright/licensing** information

Use the [`get_mei_metadata`](../tools/metadata.md) tool to view this information for any file.

## Discovering Files

Use the [`list_available_mei_files`](../tools/discovery.md) tool to browse all available files:

```json
{
  "bach_inventions": [15 files],
  "bartok_mikrokosmos": [19 files],
  "morley_canzonets": [12 files],
  "all_files": [46 files total]
}
```

## Using Files

All tools accept filenames as parameters:

```python
# Example: Analyze a Bach invention
analyze_key("Bach_BWV_0772.mei")

# Example: Get melodic intervals from Bartók
get_melodic_intervals("Bartok_Mikrokosmos_022.mei")

# Example: Extract notes from Morley
get_notes("Morley_1595_01_Go_ye_my_canzonettes.mei")
```

## File Statistics

| Collection | Files | Period | Style |
|-----------|-------|--------|-------|
| Bach | 15 | Baroque (1720s) | Contrapuntal, Two-voice |
| Bartók | 19 | 20th century (1926-1939) | Progressive, Pedagogical |
| Morley | 12 | Renaissance (1595) | Vocal, Polyphonic |

## Adding Your Own Files

Currently, encoding-music-mcp works only with the built-in collection. Future versions may support:

- Custom file paths
- User-provided MEI files
- URL-based file access

## License Information

Each file may have different licensing terms. Use [`get_mei_metadata`](../tools/metadata.md) to check copyright and availability information for specific files.

## Related Documentation

- [Bach Inventions Details](bach.md)
- [Bartók Mikrokosmos Details](bartok.md)
- [Morley Canzonets Details](morley.md)
- [Discovery Tool](../tools/discovery.md)
- [Metadata Tool](../tools/metadata.md)
