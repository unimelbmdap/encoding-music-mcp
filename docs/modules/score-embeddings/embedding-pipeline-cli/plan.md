# Embedding pipeline CLI

## Purpose

Tie whole-score XML validation, MEI catalog metadata extraction, offline CLaMP extraction, SQLite persistence, manifests, and similarity queries into typed Python orchestration and a standalone CLI.

## Components

| File | Purpose |
|---|---|
| `src/encoding_music_mcp/tools/score_embeddings/pipeline.py` | Input discovery, orchestration, manifests, logging, argument parsing, and exit codes |
| `src/encoding_music_mcp/tools/score_embeddings/__init__.py` | Stable public Python exports |
| `tests/score_embeddings/test_pipeline.py` | Orchestration and CLI coverage |
| `tests/score_embeddings/test_integration.py` | Module-boundary workflow using real music21/SQLite and fake CLaMP scripts |

## API surface

Expose typed pipeline configuration/results and `setup`, `extract`, and `similar` CLI commands through `encoding-music-embeddings`. Ingestion maps MEI title, artist or composer, and work-creation date into nullable catalog fields while preserving distinct ingestion timestamps. Retrieval orchestration accepts deterministic normalized query vectors but does not choose semantic poles inside storage.

Input discovery distinguishes score-bearing MEI documents from include-only aggregate manifests. Directory scans skip recognized aggregates, log them, and retain their paths, reasons, and referenced movement files in the run manifest. Explicitly supplying an aggregate fails before `music21` with an actionable message naming its referenced files. Malformed XML and non-aggregate no-score inputs remain in the normal per-score diagnostic path rather than being silently discarded.

## Configuration

Inputs, output directory, database, cache, CLaMP interpreter, tolerance, timeout, logging, and intermediate retention are CLI arguments. No hardcoded notebook paths are used.

## Integration points

Orchestrates all earlier module features without importing or registering with FastMCP.

The Python package is `encoding_music_mcp.tools.score_embeddings`; the
`encoding-music-embeddings` command remains unchanged. Checkout discovery must
resolve the repository root from this nested package and reject installed-wheel
locations. The separate runtime lock and worker script remain sibling resources
included in the wheel. Package relocation preserves existing artifacts and does
not change generated output paths or database tables.

## Validation boundary

Every exported XML remains available for validation evidence and optional diagnostics, but only accepted conversions are copied into the transient CLaMP input directory. Failed conversions remain in the manifest and cannot reach inference or persistence. If CLaMP produces embeddings for only part of an accepted music batch, each present embedding is persisted and each omitted score receives a per-score manifest error without a database identity. A partial run has no run-level error but returns the existing partial-failure CLI status. Unexpected outputs, malformed vectors, and a batch producing no embeddings remain fatal run-level failures. The accepted-only staging directory is cleaned with the run workspace and is not part of retained intermediates.

## Testing

- Deterministic recursive MEI discovery and stable identities
- Mixed-batch failed-validation exclusion, ordered storage, and manifest contents
- Partial CLaMP output persistence, per-score omission diagnostics, and partial-failure exit status
- Fatal handling for unexpected outputs and batches that produce no embeddings
- Cleanup and retained-intermediate behavior
- Setup/extract/similar parsing, logging, and exit codes
- Module-boundary success and subprocess-failure propagation without network or weights
- Default CI provisions the optional `score-embeddings` dependency before running the unconditional suite
- MEI metadata fidelity plus deterministic missing and ambiguous metadata behavior
- Query-vector validation and catalog-shaped retrieval results
- Include-only aggregate classification, directory-scan skipping and reporting, explicit-file diagnostics, namespace variants, and real bundled CRIM parent/child behavior

Metadata extraction reads arbitrary input MEI paths directly. Title prefers work title and falls back to file title; artist maps the composer role; work creation date is nullable and must not be substituted with publication or ingestion time. Tests cover complete and missing metadata, manifest/storage propagation, and user-facing similarity JSON.

Aggregate handling does not resolve or concatenate referenced movements; the referenced score-bearing MEI files remain the embedding units.

Verification: 21 focused pipeline tests plus the 87-test score-embedding suite exercise metadata, manifests, CLI JSON and partial-failure status, partial CLaMP persistence, fatal zero-output handling, include-only aggregate classification/reporting, explicit diagnostics, malformed input preservation, and bundled CRIM behavior.

Confirmed 2026-08-27
