# Score embeddings

## Module integration

Test: `tests/score_embeddings/test_integration.py` — ✓
Notes: Exercise bundled MEI through real standardization, `.xml` validation, MEI metadata persistence, compatible fake CLaMP text/music outputs, positive-minus-negative normalization, transactional schema migration and SQLite/`sqlite-vec` persistence, contrast-vector ranking, manifests, cleanup, logging, and subprocess failure propagation without network access or model weights.

## Build order

1. sheet-music-processing — ✓
2. clamp3-extraction — ✓
3. sqlite-vector-storage — ✓
4. embedding-pipeline-cli — ✓
5. gpu-extraction-notebook — ✓

## Module review

Review: ✓ 2026-08-25 (4 of 4 features)
