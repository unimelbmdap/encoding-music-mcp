# Unified vector domain

## Purpose

Unify vector retrieval into a cohesive object-oriented domain model under ADR-0008, combining prototype concepts and bipolar semantic axes with weighted-vector z-score composition. The feature provides:
- A polymorphic vector domain (`QueryVector`, `PrototypeVector`, `SemanticAxisVector`).
- Query composition (`WeightedQuery`, `ComposedQuery`) supporting arbitrary mixtures of prototypes and axes.
- Centralized prompt batching in `TextEncoder` to encode all prompts in a single CLaMP worker call.
- Vectorized baseline statistics evaluation ($\mu_i, \sigma_i$) and `QueryVector` acceptance in `EmbeddingRepository`.
- Single-query SQLite KNN search with exact z-index score recovery via `RetrievalService` ($\|V_{\text{composed}}\|_2(1-d) - C_{\text{composed}}$).
- Rich context around search results (rank, title, artist, date, score_id, embedding_id, component scores, z-index score definition).

It does not alter existing SQLite database schemas or migrations, MusicXML extraction pipelines, or FastMCP tool registrations.

## Components

| File | Purpose |
|---|---|
| `src/encoding_music_mcp/tools/score_embeddings/storage.py` | `QueryVector` class, vector search extension, vectorized baseline statistics evaluation |
| `src/encoding_music_mcp/tools/score_embeddings/clamp_extractor.py` | `TextEncoder` class wrapping resident worker for single-batch prompt encoding |
| `src/encoding_music_mcp/tools/score_embeddings/retrieval.py` | `PrototypeVector`, `SemanticAxisVector`, `WeightedQuery`, `ComposedQuery`, `SearchResult`, `RetrievalService` |
| `src/encoding_music_mcp/tools/score_embeddings/__init__.py` | Export unified domain classes |
| `src/encoding_music_mcp/tools/combined_retrieval.py` | Reconcile `search_songs_by_combined_criteria` to delegate to `RetrievalService` and return rich list results |
| `tests/score_embeddings/test_unified_vector_domain.py` | Unit and mathematical verification of weighted vector composition, baseline stats, and z-index recovery |
| `tests/test_combined_retrieval.py` | End-to-end multi-criteria combination test suite |

## Schema / API surface / Access model

### QueryVector
- `values: np.ndarray`: float32 normalized vector of shape `(dimension,)`
- `dimension: int = 768`
- `model_identity: ClampModelIdentity | None = None`
- `query_type: str = "generic"`
- `raw_norm: float = 1.0`

### PrototypeVector & SemanticAxisVector
- `PrototypeVector`: builds from concept and 3–5 prompts, retains centroid norm $\|c\|$, direction $c / \|c\|$.
- `SemanticAxisVector`: builds from positive and negative prompt ensembles, retains normalized contrast direction.

### WeightedQuery
- `query: QueryVector`
- `weight: float`
- `mean_similarity: float` ($\mu$)
- `std_similarity: float` ($\sigma$)
- `adjusted_vector()`: $\frac{w}{\sigma} v$ (with $\|c\|$ factor for prototypes)
- `offset()`: $\frac{w \mu}{\sigma}$

### ComposedQuery
- `weighted_queries: list[WeightedQuery]`
- `all_prompts() -> list[str]`: deduplicated prompts across all sub-queries
- `compose_vector() -> tuple[np.ndarray, float, float]`: returns $(q, \|V\|, C)$ where $q = V / \|V\|$, $V = \sum v'_i$, $C = \sum \text{offset}_i$.

### SearchResult
- `rank: int`
- `title: str | None`
- `song_title: str | None`
- `artist: str | None`
- `work_created_date: str | None`
- `score_id: str`
- `embedding_id: int`
- `score: float` (dataset-normalized z-index)
- `component_scores: dict[str, float]`
- `score_definition: str`

### RetrievalService
- Coordinates single-batch prompt encoding via `TextEncoder`, vector building, baseline stats from `EmbeddingRepository`, composite vector synthesis, single SQLite KNN search, and exact z-index score recovery:
  $$\text{score} = \|V_{\text{composed}}\|_2 (1 - d) - C_{\text{composed}}$$

## Configuration

No new environment variables. Reuses existing `ENCODING_MUSIC_*` variables for database path, CLaMP interpreter, cache path, and timeouts.

## Integration points

Exposes domain classes to `score-embeddings`, `prototype-retrieval`, `semantic-axis-retrieval`, and `tools/combined_retrieval.py`. Consumes `EmbeddingRepository` and `PersistentClampTextEncoder`.

## Testing

- Mathematical equivalence test: verify $\|V_{\text{composed}}\|_2 (1 - d) - C_{\text{composed}}$ reproduces $\sum w_i z_i(x)$ within float32 tolerance.
- Single-batch prompt encoding test: verify `TextEncoder` issues one forward pass for composed queries.
- Vectorized baseline statistics test: verify $(\mu, \sigma)$ calculated via matrix multiplication matches empirical distribution.
- End-to-end composed retrieval test: verify `search_songs_by_combined_criteria` returns rich result list with Bartók / Bach matches and valid z-indices.
- Backward compatibility: verify existing `tests/test_combined_retrieval.py` passes without modification.
