# Semantic Axis Retrieval

## Think of the catalog as music on a ruler

`search_songs_by_semantic_axis` ranks a prepared local catalog along a broad
musical contrast. Imagine a ruler with the requested quality at one end and its
genuine contrast at the other:

```text
sorrowful <--------------------------------------------> joyful
negative pole                                      positive pole
```

Claude describes both ends with several matched examples. CLaMP translates
those descriptions into the same semantic space as the stored score embeddings,
and the application asks SQLite which scores lie closest to the positive end.
The tool is useful for broad characteristics represented in CLaMP embeddings,
such as mood, energy, style, atmosphere, and texture.

It is not a deterministic music-theory analyzer. When presenting results to
the user, Claude stipulates that individual results might be incorrect, but
usually the returned results are correct on average. Use the other analysis tools
for exact key, BPM, chords, notes, or bar-level events.

## The workflow at a glance

```text
MCP request
    |
    v
matched positive and negative prompt pairs
    |
    v
CLaMP text vectors (positive prompts first, then negative prompts)
    |
    v
normalized positive centroid ---- normalized negative centroid
                    \              /
                     \            /
                      semantic axis
                           |
                           v
             SQLite/sqlite-vec cosine ranking
                           |
                           v
                 vector-free MCP results
```

Each part has a distinct responsibility:

- **Claude or another MCP client** turns the user's request into two ordered,
  positionally matched prompt ensembles.
- **The persistent external CLaMP worker** loads the tokenizer, full-precision
  model, and checkpoint, then encodes the ordered text batch. It does not create
  score embeddings during a search.
- **Deterministic application code** validates the returned vectors, constructs
  the two pole centroids and their direction, and verifies model compatibility.
- **SQLite with `sqlite-vec`** compares that direction with already-stored score
  vectors and ranks compatible catalog rows.

Numeric vectors remain internal throughout the workflow.

## Writing the two poles

The real MCP parameters are:

- `positive_prompts` (`list[str]`): 3–5 short, caption-like descriptions of
  the requested direction
- `negative_prompts` (`list[str]`): 3–5 descriptions of its genuine semantic
  contrast
- `limit` (`int`, default `10`): number of matches, from 1 to 100

Both prompt lists must contain the same number of entries. Match prompts by
position so that each pair keeps its musical context while changing mainly the
quality being measured. This prevents an apparent joyful–sorrowful axis from
accidentally becoming, for example, a fast-orchestral–slow-piano axis.

For “find the happiest songs,” an end-to-end call can use:

```json
{
  "positive_prompts": [
    "Music expressing a joyful and optimistic mood.",
    "Happy, energetic music with a cheerful emotional character.",
    "Happy, calm music with a warm and contented character."
  ],
  "negative_prompts": [
    "Music expressing a sorrowful and pessimistic mood.",
    "Sad, energetic music with a distressed emotional character.",
    "Sad, calm music with a melancholic and subdued character."
  ],
  "limit": 10
}
```

The first pair is general. The second holds energy constant, and the third holds
calmness constant. All three change the intended emotional quality. Keep both
sides equally detailed, and do not introduce differences in genre,
instrumentation, tempo, harmony, or production unless the user requested them.

Useful contrasts include joyful–sorrowful, energetic–subdued, tense–peaceful,
bright–dark, dense–sparse, playful–serious, and acoustic–electronic. Do not
invent an arbitrary opposite for a category: jazz-like–classical-like is valid
only when the user explicitly requests that comparison.

## How the ruler is calculated

The application combines `positive_prompts` followed by `negative_prompts` and
sends that sequence in one ordered CLaMP call. It verifies the returned order,
dimensions, finite values, and model identity before doing any arithmetic.

It then:

1. L2-normalizes every individual prompt vector.
2. Takes the arithmetic mean of the normalized vectors for each pole.
3. L2-normalizes each pole's mean to create two centroids.
4. Calculates `positive_centroid - negative_centroid`.
5. L2-normalizes that difference to create the final semantic-axis direction.

Normalizing each prompt first gives every description an equal vote; otherwise,
a vector with a larger magnitude could dominate its pole. Normalizing each
centroid prevents one ensemble's magnitude from dominating the contrast. The
final normalization makes the direction suitable for cosine search.

Zero or non-finite prompt vectors, centroids, and final axes are rejected.
SQLite searches normalized score vectors using exact CLaMP model-identity
filtering, so vectors produced by a different checkpoint or model revision are
not mixed into the ranking. Stable tie ordering keeps repeated searches
deterministic.

The returned `distance` is cosine distance: **a lower value means the score is
closer to the requested positive direction**. It is a relative ranking signal,
not a probability or a measured amount of joy, energy, or any other quality.

## Cold and warm CLaMP requests

Starting the MCP server does not import PyTorch or load CLaMP. On the first
compatible semantic-axis request, the server lazily starts a separate offline
worker. That cold request includes interpreter startup, tokenizer/model
construction, checkpoint loading, and a text warm-up, so it is slower.

Compatible later requests are warm: they reuse the resident worker and its
already-loaded full-precision model, then tokenize and encode only the new
prompts. Changing the configured interpreter, checkout/model configuration, or
checkpoint identity safely replaces the worker. The worker loads only from the
prepared offline runtime; a query never downloads assets or runs setup.

## Configuration

For a local source checkout, prepare the runtime once:

```bash
uv run --extra score-embeddings --locked encoding-music-embeddings bootstrap
```

The tool discovers `.venv-clamp`, `.clamp3-cache`, and the bundled database without
configuration. Optional environment overrides are:

- `ENCODING_MUSIC_EMBEDDINGS_DATABASE`
- `ENCODING_MUSIC_CLAMP_PYTHON`
- `ENCODING_MUSIC_CLAMP_CACHE_DIR`
- `ENCODING_MUSIC_CLAMP_TIMEOUT_SECONDS`

An external runtime or installed package requires an explicit interpreter path.
See [Configuration](../getting-started/configuration.md) for precedence and the Claude launcher.

The database, CLaMP runtime, model assets, and score embeddings must be prepared
before retrieval. The tool does not download assets, generate score embeddings,
or add score data to the database.

## Measuring cold and warm timing

After bootstrap, or with overrides pointing to a prepared offline runtime,
measure one cold search followed by warm searches with:

```bash
uv run --extra score-embeddings \
  python -m encoding_music_mcp.tools.score_embeddings.semantic_axis_timing \
  --positive "Music expressing a joyful and optimistic mood." \
  --positive "Happy energetic music with a cheerful character." \
  --positive "Happy calm music with a warm contented character." \
  --negative "Music expressing a sorrowful and pessimistic mood." \
  --negative "Sad energetic music with a distressed character." \
  --negative "Sad calm music with a melancholic subdued character." \
  --warm-runs 3
```

The JSON output separates interpreter startup, model/tokenizer initialization,
checkpoint loading, warm-up, tokenization, inference, axis construction,
`sqlite-vec` retrieval, result projection, and total search time. The timing
pipeline closes existing resources before the cold run and after measurement;
it does not run setup or download assets.

## Response

The tool returns the exact ordered prompt ensembles, aggregation and model
provenance, and ranked catalog metadata using these response names:

```json
{
  "positive_prompts": [
    "Music expressing a joyful and optimistic mood.",
    "Happy, energetic music with a cheerful emotional character.",
    "Happy, calm music with a warm and contented character."
  ],
  "negative_prompts": [
    "Music expressing a sorrowful and pessimistic mood.",
    "Sad, energetic music with a distressed emotional character.",
    "Sad, calm music with a melancholic and subdued character."
  ],
  "aggregation": {
    "prompt_normalization": "l2",
    "centroid_aggregation": "arithmetic_mean",
    "centroid_normalization": "l2",
    "axis_operation": "positive_centroid - negative_centroid",
    "axis_normalization": "l2"
  },
  "model": {
    "model_commit": "...",
    "model_revision": "...",
    "model_weight_sha256": "...",
    "dimension": 768
  },
  "matches": [
    {
      "embedding_id": 1,
      "score_id": "Bach_BWV_0772",
      "title": "Invention No. 1 in C major",
      "artist": "Bach, Johann Sebastian",
      "work_created_date": null,
      "distance": 0.12
    }
  ]
}
```

No vector is returned to the MCP client. The response preserves enough
provenance to explain how the ranking was requested without exposing numeric
embeddings.

## Limits and failure behavior

Retrieval quality depends on what the pinned CLaMP model represents and on the
scores already embedded in the configured catalog. The two axes of a broader
multi-axis exploration are independent semantic directions; the tool does not
make them mathematically orthogonal or combine them into a two-dimensional
projection.

The tool fails with actionable errors rather than silently weakening the query:

- invalid prompt counts, blank prompts, unequal ensemble sizes, or a `limit`
  outside 1–100 identify the invalid request;
- missing required database or interpreter configuration, nonexistent configured
  paths, or an invalid timeout identifies the relevant configuration problem;
- unavailable or incompatible offline CLaMP assets identify the runtime or
  model-provenance mismatch;
- unexpected prompt order, dimensions, or non-finite output identifies invalid
  encoder output; and
- zero prompt vectors, zero centroids, or a zero final axis identify a
  degenerate semantic contrast.
