# Unified vector domain — Status

✓ complete

## Verification evidence

- Mathematical proof of single-query vector synthesis: Verified in `test_composed_query_mathematical_equivalence`, showing $\|V_{\text{composed}}\|_2(1-d) - C_{\text{composed}} = \sum w_i z_i(x)$ within float32 numerical tolerance across synthetic song embeddings.
- Vector domain validation & building: Verified `QueryVector`, `PrototypeVector`, and `SemanticAxisVector` dimension, finite value, and centroid arithmetic constraints.
- Centralized prompt batching: Verified `TextEncoder` prompt collection and single-batch encoding pass.
- Vectorized baseline statistics: Verified `EmbeddingRepository.compute_baseline_statistics()` against empirical mean and standard deviation distributions.
- End-to-end composed retrieval: Verified single-query SQLite KNN search with exact z-index recovery, metadata, and component score breakdown.
- User-confirmed Option 1 Rich List: Verified `search_songs_by_combined_criteria` returns `list[dict]` where every result item contains `title`, `song_title`, `artist`, `work_created_date`, `score_id`, `embedding_id`, `rank`, `score` (z-index), `component_scores`, and `score_definition`.
- Test suite:
  - `tests/score_embeddings/test_unified_vector_domain.py` (8 passed)
  - `tests/test_combined_retrieval.py` (2 passed without modification)
  - `tests/test_prototype_retrieval.py` (22 passed)
  - `tests/test_semantic_axis_retrieval.py` (30 passed)
  - `tests/score_embeddings/test_storage.py` (21 passed)
  - Total 83 passed in 8.35s
- Linting: `ruff check` passed with zero errors.

Confirmed 2026-09-09

