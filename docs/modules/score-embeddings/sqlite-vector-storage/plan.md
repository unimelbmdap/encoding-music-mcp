# SQLite vector storage

## Purpose

Persist raw and normalized score embeddings with reproducibility evidence and catalog metadata, and provide local cosine-similarity retrieval under ADR-0003 and ADR-0004.

## Components

| File | Purpose |
|---|---|
| `src/encoding_music_mcp/score_embeddings/storage.py` | Schema migration, transactional repository, upsert, lookup, and similarity search |
| `tests/score_embeddings/test_storage.py` | Real SQLite and sqlite-vec persistence coverage |

## Schema

A relational `score_embeddings` table owns identity, nullable title, artist or composer, nullable work-creation date, provenance, validation JSON, dimensions, raw float32 bytes, and timestamps. A `vec0` table shares its integer key and stores normalized `float[768]` values with cosine distance. `PRAGMA user_version` owns forward-only schema migration. Catalog projections expose the requested descriptive fields and vector/result data while retaining internal reproducibility columns.

## Configuration

Database path is explicit. `sqlite-vec==0.1.9` is supplied by the optional `score-embeddings` dependency set.

## Integration points

Consumes validated extraction results and serves persistence, catalog projection, score-to-score similarity, and arbitrary normalized query-vector search to the pipeline, emotion-retrieval, and Python callers.

## Testing

- Schema creation, version rejection, and extension lifecycle
- Transactional relational/vector writes
- Stable logical-identity upsert and distinct changed provenance
- Dimension and finite-value rejection
- Cosine nearest-neighbor ordering without Python collection scans
- Forward migration and round-trip behavior for nullable title, artist or composer, and work-creation date
- Arbitrary normalized contrast-vector KNN with stable distance-and-ID ordering and catalog results

Schema version 2 migrates version-1 databases in place by adding nullable `title`, `artist`, and `work_created_date` columns. Descriptive metadata updates on logical-key conflict but does not participate in the ADR-0003 identity. Query vectors must be finite, dimensionally valid, non-zero, and L2-normalized before SQLite search.

Schema version 3 adds the `song_catalog` view with exactly `song_title`, `artist`, `date_created`, and normalized `vector_embedding`, while the relational and `sqlite-vec` tables remain authoritative. Exact model-identity predicates and the final limit execute inside SQLite.

Verification: 19 focused real-`sqlite-vec` storage tests plus the combined boundary suite.

Confirmed 2026-08-25
