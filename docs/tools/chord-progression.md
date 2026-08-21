# Chord Progression Tools

Inspect MEI harmony coverage and retrieve a chronological chord progression. A
score whose `<harm>` annotations all contain usable descendant text is read
directly; every other score is inferred from multi-pitch music21 sonorities.

## `inspect_harmony`

```python
inspect_harmony(filename: str) -> HarmonyInspection
```

Returns the number of `<harm>` annotations, available MEI staff and layer `n`
identifiers, whether every annotation has an explicit label, and whether chord
retrieval will require music21 inference.

```json
{
  "harmony_count": 1,
  "staves": ["1", "2", "3", "4", "5"],
  "layers": ["1"],
  "has_explicit_labels": true,
  "requires_inference": false
}
```

## `get_chord_progression`

```python
get_chord_progression(
    filename: str,
    start_measure: int | None = None,
    end_measure: int | None = None,
    staff: str | None = None,
    layer: str | None = None,
) -> list[ChordEvent]
```

Measure bounds are inclusive. Staff and layer filters use the MEI `n`
identifiers advertised by `inspect_harmony`. Unknown identifiers, non-positive
measure bounds, and reversed ranges raise `ValueError`; missing scores raise
`FileNotFoundError`.

Each event contains:

| Field | Type | Meaning |
|---|---|---|
| `name` | `str` | Normalized encoded harmony text or music21 root-bearing pitched common chord name |
| `measure_number` | `int | None` | MEI/music21 measure number when available |
| `beat_str` | `str | None` | Encoded MEI timestamp or music21 beat string when available |
| `elements` | `list[str]` | Ordered pitch names with octave for inferred chords; empty when an explicit `<harm>` does not encode chord members |
| `staff` | `str | None` | Explicit staff, or the requested inferred staff filter |
| `layer` | `str | None` | Explicit layer, or the requested inferred layer filter |
| `xml_id` | `str | None` | MEI harmony XML ID; always `null` for inference |
| `source` | `"explicit_harm" | "inferred"` | Event provenance |

Explicit example:

```json
[
  {
    "name": "6 5♯",
    "measure_number": 3,
    "beat_str": "2",
    "elements": [],
    "staff": "5",
    "layer": "1",
    "xml_id": "m-146",
    "source": "explicit_harm"
  }
]
```

Inference considers only sonorities with at least two distinct pitches. Its
`name`, `measure_number`, and `beat_str` values correspond to music21's
`Chord.pitchedCommonName`, `Chord.measureNumber`, and `Chord.beatStr`; `elements`
contains ordered `Pitch.nameWithOctave` strings. Inferred events have
`source="inferred"` and `xml_id=null`; unavailable locations are returned as
`null`. Raw music21 objects are never returned through MCP.
