# CLaMP 3 extraction

## Purpose

Acquire and verify the ADR-0001 external runtime explicitly, execute symbolic extraction offline, and load ordered global embeddings safely. It does not install CLaMP or PyTorch into the MCP environment.

## Components

| File | Purpose |
|---|---|
| `src/encoding_music_mcp/tools/score_embeddings/clamp_extractor.py` | Setup, cache manifest, subprocess adapter, extraction, and normalization |
| `tests/score_embeddings/test_clamp_extractor.py` | Mocked setup/subprocess and NumPy validation coverage |

## API surface

Expose typed runtime configuration and setup results, readiness checks, batch music extraction, aligned text-pole embedding, and embedding loading. Music-batch loading can admit a requested subset of outputs, preserving requested order while rejecting unexpected stems; strict loading remains the default and is used for text encoding. Text encoding reports the exact model identity shared with stored score embeddings. Domain exceptions distinguish setup, process, compatibility, and output-validation failures.

## Configuration

Cache path, external interpreter, command timeout, pinned source revision, model revision, weight checksum, and expected dimension are explicit. Network access is confined to setup.

## Integration points

Consumes validated `.xml` files and provides raw/normalized vectors plus model provenance to storage and orchestration. When upstream symbolic preprocessing silently omits individual music scores, the adapter exposes the embeddings that were actually produced so orchestration can retain successful work. Unexpected, duplicate, malformed, dimensionally incompatible, non-finite, and zero-vector outputs remain validation failures. For query-time retrieval it accepts ordered text strings, runs the pinned aligned text encoder offline, and returns typed vectors without constructing the contrast direction itself.

## Testing

- Idempotent pinned checkout and checksum-verified download behavior
- Symbolic C2 configuration and manifest generation
- Offline readiness and safe command/cwd/environment construction
- Timeout, non-zero exit, and missing-script diagnostics
- Deterministic output ordering, optional missing-output admission for music batches, and rejection of unexpected outputs
- Dimensionality, finite-value, and zero-vector normalization
- Compatible text/music model identity and offline text readiness
- Deterministic pole ordering plus text-vector dimensionality and finite-value rejection

The text adapter uses the pinned upstream `extract_clamp3.py` `.txt` input path with `--get_global`; the same checkpoint and projection space are therefore used for text and symbolic music. Tests exercise safe temporary text files, exact stem ordering, subprocess arguments, cleanup, blank input rejection, and malformed output handling with a fake runner and no model download.

Verification: 22 focused extraction tests plus the 87-test score-embedding suite. Partial music-output tests cover requested ordering and continued rejection of unexpected outputs; strict text-output tests remain in the same suite.

Confirmed 2026-08-27
