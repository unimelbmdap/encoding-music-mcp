# Sheet music processing

## Purpose

Standardize complete music21 scores without mutating caller-owned streams, export only `.xml` MusicXML, and produce structured round-trip evidence before inference. Segmentation and MIDI output are excluded.

## Components

| File | Purpose |
|---|---|
| `src/encoding_music_mcp/tools/score_embeddings/music_processing.py` | Typed configuration, events, conversion reports, standardization, XML export, and validation |
| `tests/score_embeddings/test_music_processing.py` | Unit and real MusicXML round-trip coverage |

## API surface

Expose typed standardization, event extraction, comparison, XML export, and combined processing functions. Conversion status is represented as an enum and reports retain counts, pitch agreement, timing agreement, and diagnostics.

## Configuration

No new environment variables. Tempo, velocity, timing tolerance, and warning threshold are explicit typed arguments.

## Integration points

Consumes music21 streams and produces validated XML paths and reports for `clamp3-extraction` and the pipeline.

## Testing

- Non-mutation and deterministic nested metadata replacement
- Note, chord, tie, and empty-score event extraction
- Exact, warning, length-mismatch, and failure comparison outcomes
- `.xml` suffix enforcement and deterministic safe filenames
- Real music21 XML export/reparse validation
