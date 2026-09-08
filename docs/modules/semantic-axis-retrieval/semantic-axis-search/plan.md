# Semantic axis search

## Purpose

Expose query-time song discovery through a Claude-facing MCP tool. Claude supplies two ordered, positionally matched ensembles of 3–5 caption-like music descriptions representing a requested semantic direction and its contrast. Deterministic application code encodes and normalizes every prompt, constructs normalized pole centroids and their normalized difference under ADR-0005, and retrieves compatible catalog rows.

The feature targets broad characteristics represented in CLaMP embeddings. It does not provide exact key, BPM, chord, note, or bar-level retrieval; generate score embeddings; segment music; expose numeric vectors to Claude; or download model assets.

## Components

| File | Purpose |
|---|---|
| `src/encoding_music_mcp/tools/semantic_axis_retrieval.py` | Typed configuration, ensemble validation, ADR-0005 axis construction, model-compatible catalog search, result projection, and actionable errors |
| `src/encoding_music_mcp/tools/registry.py` | Query-only FastMCP tool registration |
| `tests/test_semantic_axis_retrieval.py` | Unit coverage for the MCP contract, ensemble validation, normalization arithmetic, configuration, compatibility, result shape, and registration |
| `tests/score_embeddings/test_semantic_axis_integration.py` | Offline boundary test with fake aligned CLaMP outputs and real SQLite/`sqlite-vec` retrieval |
| `README.md`, `mkdocs.yml`, and `docs/` tool/operator references | Public API, navigation, setup, structure, and an intuitive semantic-axis guide that progresses from the two-pole mental model through component ownership, cold/warm CLaMP loading, deterministic vector construction, SQLite ranking, and operational details |

## API surface

`search_songs_by_semantic_axis(positive_prompts, negative_prompts, limit=10, return_z_score=False)` is the MCP-facing function. Both prompt arguments are `list[str]`, must contain 3–5 nonblank entries, and must have equal cardinality. When `return_z_score=True`, it retrieves all eligible vectors, calculates z-scores for all matches using `(raw - mean) / std`, and returns a `dict[str, float]` mapping song title to z-score for the top `limit` results.

The former `search_songs_by_emotion` function, `emotion_retrieval.py` module, and emotion-named payload, configuration, result, match, provenance, error, and internal-runner symbols are replaced by semantic-axis names without compatibility aliases.

`SemanticAxisSearchPayload` returns:

- the exact ordered `positive_prompts` and `negative_prompts`;
- aggregation provenance covering prompt L2 normalization, arithmetic-mean centroids, centroid L2 normalization, ordered centroid subtraction, and final L2 normalization;
- exact CLaMP model provenance; and
- ranked vector-free matches containing `embedding_id`, `score_id`, title, artist or composer, work date, and cosine distance.

Aggregation provenance has this stable shape:

```json
{
  "prompt_normalization": "l2",
  "centroid_aggregation": "arithmetic_mean",
  "centroid_normalization": "l2",
  "axis_operation": "positive_centroid - negative_centroid",
  "axis_normalization": "l2"
}
```

The MCP-facing function carries this exact tool description:

> Rank songs along a high-level semantic contrast using matched prompt ensembles.
>
> Best suited to broad musical characteristics represented in CLaMP embeddings,
> including mood or emotion, energy or arousal, genre/style character, atmosphere,
> and texture. It is not intended for exact properties such as key, BPM, individual
> chords, notes, or bar-level events.
>
> Claude must translate the user's request into two ordered, genuinely contrasting
> poles: the requested direction and its semantic opposite. For each pole, generate
> 3–5 short, caption-like music descriptions rather than isolated words or one long
> description.
>
> Prompts at the same position in each ensemble should have matching musical context
> and differ primarily in the requested attribute. Avoid introducing differences in
> genre, instrumentation, tempo, harmony, or production unless the user specified
> them. Both ensembles must be equally detailed.
>
> Example for "find the happiest songs":
>
> positive_prompts:
> - "Music expressing a joyful and optimistic mood."
> - "Happy, energetic music with a cheerful emotional character."
> - "Happy, calm music with a warm and contented character."
>
> negative_prompts:
> - "Music expressing a sorrowful and pessimistic mood."
> - "Sad, energetic music with a distressed emotional character."
> - "Sad, calm music with a melancholic and subdued character."
>
> Suitable contrasts include joyful–sorrowful, energetic–subdued, tense–peaceful,
> bright–dark, dense–sparse, playful–serious, acoustic–electronic, or an explicitly
> requested genre/style comparison such as jazz-like–classical-like.
>
> Do not invent an arbitrary opposite for a single category. For example, jazz and
> classical are only valid poles when the user explicitly requests that comparison.

## Axis construction

The tool concatenates positive prompts followed by negative prompts and encodes them in one ordered CLaMP call. It verifies returned text ordering, model identity, dimensions, and finite values.

For each pole:

1. reject zero prompt vectors;
2. L2-normalize every prompt vector;
3. compute the arithmetic mean of the unit vectors;
4. reject a zero or non-finite mean; and
5. L2-normalize the centroid.

The final direction is `positive_centroid - negative_centroid`. The tool rejects a zero or non-finite difference and L2-normalizes it once before repository search.

## Operator documentation

The semantic-axis guide begins with a non-mathematical “music on a ruler” mental model and a compact end-to-end workflow before introducing vector arithmetic. It distinguishes the responsibilities of the MCP client, the persistent CLaMP text worker, deterministic application code, and SQLite retrieval. A worked matched-prompt example explains why each positive prompt is paired with an equally detailed negative prompt, why individual vectors are normalized before aggregation, and how to interpret cosine distance.

The same guide retains the exact tool contract, environment configuration, response shape, limitations, and actionable failure behavior. It also explains that the first compatible request lazily loads CLaMP while later requests reuse the resident worker; documentation does not imply that the query creates score embeddings, returns vectors, or performs deterministic note-level musical analysis.

## Configuration

The MCP wrapper reads the existing database path, external CLaMP interpreter, optional cache path, and timeout from documented `ENCODING_MUSIC_*` environment variables at call time. No new environment variables are introduced. Imports remain side-effect free.

## Integration points

Depends on score-embeddings for `ClampRuntimeConfig`, ordered text encoding, model identity, the SQLite repository, catalog projections, and ADR-0008 `RetrievalService` / `SemanticAxisVector`. It registers with the existing FastMCP registry, consumes vectors transiently, and delegates to `RetrievalService` with z-index score standardisation so scores are interpretable without corpus context.

## Testing

- exact Claude-facing name, signature, docstring, schema, and registry exposure
- no retained emotion-named tool or compatibility alias
- actual list inputs with equal cardinality from 3 through 5, containing only nonblank strings, plus integer limits from 1 through 100
- deterministic positive-then-negative batch ordering
- individual prompt normalization before averaging
- arithmetic-mean centroid construction and centroid normalization
- final positive-centroid-minus-negative-centroid normalization
- dimension, order, non-finite, zero-prompt, zero-centroid, and zero-axis rejection
- environment parsing and actionable missing-path failures
- exact model-identity filtering in a mixed-model database
- deterministic vector-free results with complete ensemble and aggregation provenance
- offline integration using real SQLite/`sqlite-vec`, fake CLaMP output, and no network or model weights
- documentation accuracy against the implemented positive-then-negative batch order, normalization sequence, exact-model filtering, cold/warm worker lifecycle, parameter names, response names, and cosine-distance interpretation
- documentation rendering plus whitespace validation
- focused, score-embedding, and full-suite pytest runs plus Ruff and whitespace validation

Automated verification: all 29 focused semantic-axis unit and integration tests pass, including real SQLite/`sqlite-vec` retrieval. Repository-wide Ruff and whitespace checks pass. The score-embedding suite has 114 passing tests and one unrelated failure caused by a `%pip` cell in the user-modified Colab notebook. A broader run reached 97 passes before its eighth unrelated failure; the failures were the same notebook contract plus pre-existing chord-notation contract mismatches. The intuitive operator-guide revision passes the non-strict MkDocs build and whitespace validation; the strict build renders the guide but still rejects the pre-existing docs-to-notebook link because its target is outside the documentation tree. Operator review confirmed all five accuracy, contract, usability, lifecycle, and example-field checks.

Confirmed 2026-09-02
