# Quick Start

This guide will help you get up and running with encoding-music-mcp in minutes.

## Prerequisites

Before starting, ensure you have:

1. ✅ [Installed uv](installation.md#installing-uv)
2. ✅ [Configured your MCP client](configuration.md)

## Your First Queries

Once configured, you can start asking your AI assistant about MEI files. Here are some example queries to try:

### Discovering Available Files

!!! example "Try asking:"
    "What MEI files are available?"

This uses the [`list_available_mei_files`](../tools/discovery.md) tool and returns all 46 built-in files organized by composer.

**Expected response:**
```
- 15 Bach Two-Part Inventions (BWV 772-786)
- 19 Bartók Mikrokosmos pieces
- 12 Morley Canzonets from 1595
```

### Extracting Metadata

!!! example "Try asking:"
    "Tell me about Bach_BWV_0772.mei"

This uses the [`get_mei_metadata`](../tools/metadata.md) tool to extract detailed information about the file.

**Sample output:**
```json
{
  "title": "Invention No. 1 in C major",
  "composer": "Bach, Johann Sebastian",
  "mei_editors": ["Freedman, Richard"],
  "xml_editors": ["Schölkopf, Tobias"],
  "analysts": ["Student, This"],
  "publication_date": "2024-11-19"
}
```

### Analyzing Keys

!!! example "Try asking:"
    "What key is Bach_BWV_0772.mei in?"

This uses the [`analyze_key`](../tools/key-analysis.md) tool to detect the musical key.

**Sample output:**
```json
{
  "Key Name": "C major",
  "Confidence Factor": 0.9451
}
```

### Getting Melodic Intervals

!!! example "Try asking:"
    "Get the melodic intervals for Bach_BWV_0772.mei"

This uses the [`get_melodic_intervals`](../tools/intervals/melodic.md) tool to extract interval analysis.

**Sample output:**
```
Measure Beat      1     2
1.0     1.000  Rest  Rest
        1.500    M2   NaN
        1.750    M2   NaN
        2.000    m2   NaN
        ...
```

### Finding Melodic Patterns

!!! example "Try asking:"
    "Find melodic 4-grams in Bach_BWV_0772.mei"

This uses the [`get_melodic_ngrams`](../tools/intervals/ngrams.md) tool to identify recurring melodic patterns.

**Sample output:**
```
Measure Beat              1            2
1.0     1.500      2_2_2_-3          NaN
        1.750      2_2_-3_2          NaN
        2.000     2_-3_2_-3          NaN
        ...
```

## Understanding the Results

### Notes and Intervals

- **Notes**: Represented as pitch + octave (e.g., `C4`, `D5`)
- **Intervals**: Standard music theory notation
    - `M2` = Major 2nd
    - `m2` = Minor 2nd
    - `P5` = Perfect 5th
    - Negative values indicate descending intervals (e.g., `-M3`)

### Dataframe Format

Most tools return data in a tabular format:

- **Rows**: Measure and beat positions (as floats)
- **Columns**: Voice parts or voice pairs
- **Values**: Notes, intervals, or n-grams

### Confidence Factors

Key analysis returns a confidence factor between 0.0 and 1.0:

- **> 0.8**: Very confident (clear tonal center)
- **0.5 - 0.8**: Moderate confidence
- **< 0.5**: Low confidence (possibly modal or atonal)

## More Complex Queries

Try combining tools or asking analytical questions:

!!! example "Advanced queries:"
    - "Compare the keys of all Bach inventions"
    - "Find common melodic patterns across Bartók pieces"
    - "What's the harmonic interval structure of Morley_1595_01?"
    - "Analyze the melodic contour of Bach_BWV_0773.mei"

## Next Steps

- Explore the [Tools documentation](../tools/index.md) for detailed tool reference
- Browse the [MEI Resources](../resources/mei-files.md) to learn about available files
- Check the [API Reference](../api-reference.md) for programmatic usage
