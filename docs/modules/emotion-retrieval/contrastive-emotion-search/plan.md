# Contrastive emotion search

## Purpose

Expose query-time song discovery through a Claude-facing MCP tool. Claude supplies one ordered emotion dichotomy as a positive target pole and a negative contrast pole; deterministic application code embeds both with the pinned CLaMP runtime, constructs the normalized positive-minus-negative direction, and retrieves compatible catalog rows. The feature does not generate score embeddings, segment music, expose numeric vectors to Claude, or download model assets.

## Components

| File | Purpose |
|---|---|
| `src/encoding_music_mcp/tools/emotion_retrieval.py` | Typed configuration, contrast construction, model-compatible catalog search, MCP result projection, and actionable errors |
| `src/encoding_music_mcp/tools/registry.py` | Query-only FastMCP tool registration |
| `tests/test_emotion_retrieval.py` | Unit coverage for pole validation, vector arithmetic, configuration, compatibility, result shape, and tool registration |
| `tests/score_embeddings/test_emotion_integration.py` | Offline boundary test with fake aligned CLaMP outputs and real SQLite/`sqlite-vec` retrieval |

## API surface

`search_songs_by_emotion(positive_emotion, negative_emotion, limit=10)` is the MCP-facing function. Its descriptions instruct Claude to decompose requests such as “happiest songs” into `happy` and `sad`. Results include the ordered poles, explicit `positive - negative` operation, CLaMP model provenance, and ranked `embedding_id`, `score_id`, `title`, `artist`, `work_created_date`, and cosine distance. Stored or query vectors are not returned.

The internal typed workflow accepts an explicit configuration and injectable subprocess runner for Python callers and tests. It embeds both poles in one ordered call, subtracts raw negative from raw positive, validates shape and finite values, L2-normalizes once, rejects a zero direction, and requests only rows with identical model commit, model revision, weight hash, and dimension.

## Configuration

The MCP wrapper reads an explicit database path, external CLaMP interpreter, optional cache path, and timeout from documented `ENCODING_MUSIC_*` environment variables at call time. Missing or invalid configuration fails actionably. Imports never open a database, invoke a subprocess, install dependencies, or access the network.

## Integration points

Depends on score-embeddings for `ClampRuntimeConfig`, `embed_clamp3_texts`, model identity, the SQLite repository, and catalog projections. Registers with the existing FastMCP tool registry. It consumes vectors transiently and owns only pole/query provenance and catalog-result presentation.

## Testing

- Claude-facing signature and registry exposure with no import-time side effects
- required, distinct, non-blank ordered poles and positive limits
- exact raw `positive - negative` arithmetic and single L2 normalization
- dimension, non-finite, and zero-direction rejection
- environment configuration parsing and actionable missing-path failures
- exact model-identity filtering in a mixed-model database
- deterministic vector-free catalog results with pole and model provenance
- offline integration using real SQLite/`sqlite-vec`, fake CLaMP subprocess output, and no network or model weights

Verification: 15 focused unit/integration tests cover the MCP contract, call-time configuration, ordered raw-vector subtraction, normalization, validation, exact mixed-model filtering, catalog results, and real `sqlite-vec` without network or weights.

Confirmed 2026-08-25
