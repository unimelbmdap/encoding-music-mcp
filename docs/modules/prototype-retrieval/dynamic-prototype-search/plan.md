# Dynamic prototype search

## Purpose

Expose query-time song discovery through a Claude-facing `search_songs_by_prototype` MCP tool. Claude supplies one independent high-level musical concept and a dynamically generated ensemble of 3–5 equivalent descriptions. Deterministic application code encodes and normalizes the prompts, preserves the requested arithmetic mean of their individual cosine similarities, and retrieves compatible catalog rows without a fixed prototype catalogue or a Python corpus scan.

The feature serves independent concepts such as genre or style, instrumentation, ensemble type, emotional category, atmosphere, setting, production or vocal character, rhythmic character, texture, broad harmonic language, and cultural or historical character. Genuine bipolar continua remain the responsibility of semantic-axis retrieval; exact key, BPM, notes, chords, intervals, progressions, or bar locations remain the responsibility of deterministic symbolic-analysis tools. Multiple-concept fusion, fixed prototypes, z-scores, percentile calibration, reciprocal-rank fusion, and pseudo-relevance feedback are outside this feature.

## Components

| File | Purpose |
|---|---|
| `src/encoding_music_mcp/tools/prototype_retrieval.py` | Typed validation, prompt normalization, ADR-0006 prototype construction, mean-cosine score recovery, timing logs, response projection, actionable errors, and query-resource lifecycle |
| `src/encoding_music_mcp/tools/registry.py` | Query-only FastMCP tool registration |
| `src/encoding_music_mcp/server.py` | Shutdown cleanup for prototype-retrieval resources |
| `src/encoding_music_mcp/tools/score_embeddings/storage.py` | Exact-model eligible/excluded counts alongside vector-free catalog KNN |
| `tests/test_prototype_retrieval.py` | Unit and MCP contract coverage for validation, scoring, response shape, errors, registration, and lifecycle |
| `tests/score_embeddings/test_prototype_retrieval_integration.py` | Offline boundary test using fake aligned CLaMP output and real SQLite/`sqlite-vec` retrieval |
| `tests/score_embeddings/test_prototype_retrieval_timing.py` | FastMCP Client timing coverage, including an opt-in prepared-runtime cold/warm run |
| `README.md`, `mkdocs.yml`, and `docs/` tool/operator references | Public API, navigation, setup, structure, retrieval routing, scoring, result interpretation, and timing instructions |

## API surface

`search_songs_by_prototype(concept, prompts, top_k=10)` is the MCP-facing function.

- `concept` is a nonblank traceability label for one independent high-level musical concept.
- `prompts` is an actual `list[str]` containing 3–5 ordered, nonblank, concise, caption-like descriptions. Every prompt describes the same concept at approximately equal specificity without adding unrelated tempo, instrumentation, emotion, genre, or production constraints unless the user requested them.
- `top_k` is an integer from 1 through 100.
- `return_z_score` is a boolean (default False). When True, returns a single `dict[str, float]` mapping song title to its dataset-normalized z-score instead of the full metadata list.

The response contains the exact `concept` and ordered `prompts`; the mean-cosine score definition and a warning that semantic alignment is not definitive classification; canonical CLaMP model provenance; exact-model `eligible_count` and `excluded_count`; and ranked vector-free results. Each result contains `rank`, nullable `song_title` as the primary display identity, stable `score_id` and `embedding_id` technical provenance, artist or composer, nullable work-creation date, and `score`.

Titles are descriptive metadata and may be null or duplicated, so technical identifiers remain present. Numeric vectors are never returned.

## Prototype construction and ranking

The tool encodes all prompts in one ordered call through the persistent CLaMP text worker and verifies returned text order, model identity, dimensions, and finite values. It L2-normalizes every prompt independently and computes their arithmetic mean `c` without renormalizing the prototype used by the reported score.

Non-finite centroids and centroids with norm no greater than `numpy.finfo(numpy.float32).eps` are rejected. To retain SQLite-only corpus ranking, the tool queries the repository with the normalized direction `q = c / ||c||`. For every normalized stored score vector `m` and SQLite cosine distance `d`, it recovers the required mean-prompt score under ADR-0006:

```text
m · c = ||c|| × (1 - d)
```

The positive query-wide norm preserves SQLite's ascending-distance order as descending mean-cosine score order. Equal scores use ascending embedding ID as the stable tie-break. The reported score is not z-scored by default. If `return_z_score=True`, all eligible rows are evaluated, the raw mean-cosine scores are z-scored against the dataset distribution using `(raw - mean) / std`, and the top `top_k` are returned as a dictionary.

`eligible_count` is the number of stored rows matching the query's exact CLaMP commit, model revision, model-weight hash, and dimension. `excluded_count` is the total stored-row count minus that eligible count. Invalid stored vectors do not contribute because storage rejects them transactionally.

## Configuration

The MCP wrapper reads the existing database path, external CLaMP interpreter, optional cache path, and timeout from the documented `ENCODING_MUSIC_*` environment variables at call time. No new runtime configuration is introduced. Imports and server startup remain side-effect free, and queries never run setup, download assets, or generate corpus embeddings.

## Timing and observability

The prototype tool emits one structured `prototype_search` timing event per call with `text_encoding_seconds`, `prototype_construction_seconds`, `sqlite_vec_retrieval_seconds`, and `result_projection_seconds`. Existing persistent-worker events retain interpreter startup, model/tokenizer construction, checkpoint loading, warm-up, tokenization, and model-inference timings.

The FastMCP Client timing test closes resident retrieval and worker resources, invokes the registered tool once cold and multiple times warm, captures server-side timing events in-process, and prints structured JSON when pytest output capture is disabled. Every measured end-to-end retrieval invocation must complete in less than 90 seconds or the test fails. The cold result includes CLaMP startup stages; compatible warm calls reuse the resident worker and omit startup timings. A deterministic fake path verifies timing separation and the 90-second deadline in the default suite. The real offline path is opt-in through `ENCODING_MUSIC_RUN_REAL_TIMING=1` plus the existing database, interpreter, cache, and timeout environment variables, and applies the same deadline to the real cold and warm calls.

## Integration points

Depends on score-embeddings for ordered ADR-0001 CLaMP text encoding, canonical model identity, ADR-0003 SQLite retrieval, and ADR-0008 `RetrievalService` / `PrototypeVector`. It follows ADR-0006 for prompt normalization, score preservation, eligibility accounting, and result provenance, and ADR-0008 for unified domain execution with z-index score standardisation so single scores are interpretable without corpus context. It registers with the existing FastMCP registry and shares the server's worker lifecycle without owning durable score vectors.

Semantic-axis retrieval remains an independent sibling module. Public documentation routes independent concepts to this tool, genuine continua to `search_songs_by_semantic_axis`, and exact musical properties to symbolic-analysis tools.

## Testing

- exact MCP name, signature, schema, description, registration, and title-first vector-free response
- nonblank concept, actual-list prompt ensembles of 3–5 nonblank strings, and integer `top_k` from 1 through 100
- ordered one-batch CLaMP encoding plus exact output-order, dimension, finite-value, and model-identity validation
- independent prompt L2 normalization and explicit per-prompt mean-cosine equivalence
- normalized-centroid SQLite KNN plus positive centroid-norm score recovery without corpus loading in Python
- zero, near-zero, and non-finite centroid rejection
- exact-model eligibility/exclusion counts, empty or short eligible sets, stable score-and-ID ordering, and nullable or duplicate title handling
- existing `catalog_similarity_search` compatibility for semantic-axis callers
- actionable missing configuration, unavailable assets, invalid encoder output, and degenerate-prototype errors
- import-time and server-startup CLaMP laziness plus shutdown cleanup
- offline real-`sqlite-vec` integration with fake aligned CLaMP output and no network or model weights
- FastMCP Client invocation with deterministic timing-category separation, an end-to-end duration below 90 seconds for every measured retrieval, and an opt-in real-runtime cold/warm timing run subject to the same deadline
- public API, usage, routing, configuration, scoring, timing, and result-interpretation documentation
- focused, score-embedding, and full-suite pytest runs plus Ruff, MkDocs, and whitespace validation

Implementation and verification are pending.
Confirmed 2026-09-02
