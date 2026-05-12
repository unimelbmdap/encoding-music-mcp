# resolve_note_ids_for_highlight

Resolve analysis locations or spans to MEI note IDs for notation highlighting.

## Overview

This tool separates score-highlighting ID lookup from melodic n-gram extraction.
Use it whenever another tool returns a location you want to highlight, including
melodic n-grams, harmonic interval rows, cadence rows, and visualisation
occurrences.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `filename` | `str` | Yes | Name of the MEI file |
| `spans` | `list[dict]` | Yes | Analysis locations or ranges to resolve |

Each span may include:

| Field | Type | Description |
|-------|------|-------------|
| `start_measure` | `float` | Measure number from CRIM output |
| `start_beat` | `float` | Beat within the measure |
| `start_q` / `start_offset` | `float` | Quarter-note offset from the start of the piece |
| `staff` / `part` / `column` | `str` | Optional CRIM part label, such as `"1"` |
| `voice_pair` | `str` | Optional pair such as `"1,2"` from harmonic output |
| `duration` | `float` | Optional duration from the start location |
| `end_q` / `end_offset` | `float` | Optional exclusive end offset |
| `note_count` | `int` | Optional number of consecutive note events to collect |

## Returns

```python
{
    "filename": "Bach_BWV_0772.mei",
    "spans": [
        {
            "index": 0,
            "matched_parts": ["1"],
            "note_ids": ["nz7y0rb", "n1ecjh8t"],
            "start_measure": 1.0,
            "start_beat": 1.25,
            "column": "1",
        }
    ],
}
```

The original fields from each requested span are preserved, and the resolver
adds `index`, `matched_parts`, and `note_ids`.

## Examples

Resolve a cadence or harmonic interval row:

```python
resolve_note_ids_for_highlight(
    "Morley_1595_01_Go_ye_my_canzonettes.mei",
    [{"start_measure": 12.0, "start_beat": 1.0, "voice_pair": "1,2"}],
)
```

Resolve a melodic n-gram span:

```python
resolve_note_ids_for_highlight(
    "Bach_BWV_0772.mei",
    [
        {
            "column": "1",
            "start_measure": 1.0,
            "start_beat": 1.25,
            "start_offset": 0.25,
            "note_count": 5,
        }
    ],
)
```

Resolve a visualisation occurrence with an offset range:

```python
resolve_note_ids_for_highlight(
    "Bach_BWV_0772.mei",
    [{"staff": "1", "start_q": 0.0, "end_q": 2.0}],
)
```

## Related Tools

- [show_notation_highlight](../notation.md) - Display the returned `note_ids`
- [get_melodic_ngram_matches](ngram-matches.md) - Pattern-specific melodic n-gram spans
- [get_cadences](cadences.md) - Cadence rows with measure and beat
- [get_harmonic_intervals](harmonic.md) - Harmonic interval rows with measure and beat
