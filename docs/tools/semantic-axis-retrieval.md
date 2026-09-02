# Semantic Axis Retrieval

## `search_songs_by_semantic_axis`

Rank a prepared local score-embedding catalog along a broad semantic contrast represented in CLaMP embeddings. Suitable attributes include mood or emotion, energy or arousal, genre/style character, atmosphere, and texture. Use other analysis tools for exact key, BPM, chords, notes, or bar-level events.

### Parameters

- `positive_prompts` (`list[str]`): 3–5 short, caption-like descriptions of the requested direction
- `negative_prompts` (`list[str]`): 3–5 descriptions of its genuine semantic contrast
- `limit` (`int`, default `10`): number of matches, from 1 to 100

The two ensembles must have equal length. Prompts at the same position should have matching musical context and differ primarily in the requested attribute. Keep both ensembles equally detailed, and avoid changing genre, instrumentation, tempo, harmony, or production unless the user requested that change.

For “find the happiest songs,” Claude might supply:

```yaml
positive_prompts:
  - "Music expressing a joyful and optimistic mood."
  - "Happy, energetic music with a cheerful emotional character."
  - "Happy, calm music with a warm and contented character."
negative_prompts:
  - "Music expressing a sorrowful and pessimistic mood."
  - "Sad, energetic music with a distressed emotional character."
  - "Sad, calm music with a melancholic and subdued character."
```

Suitable contrasts include joyful–sorrowful, energetic–subdued, tense–peaceful, bright–dark, dense–sparse, playful–serious, and acoustic–electronic. Do not invent an arbitrary opposite for a category: jazz-like–classical-like is valid only when the user explicitly requests that comparison.

### Axis construction

The application embeds all positive prompts followed by all negative prompts in one ordered CLaMP batch. It then:

1. L2-normalizes every individual prompt embedding;
2. computes the arithmetic mean for each pole;
3. L2-normalizes each resulting centroid;
4. subtracts the negative centroid from the positive centroid; and
5. L2-normalizes the final semantic-axis direction.

Zero or non-finite prompts, centroids, and axes are rejected. The resulting unit vector is searched against normalized score vectors through `sqlite-vec`, using cosine distance and exact CLaMP model-identity filtering.

### Configuration

The MCP server process requires:

- `ENCODING_MUSIC_EMBEDDINGS_DATABASE`
- `ENCODING_MUSIC_CLAMP_PYTHON`

Optional overrides are `ENCODING_MUSIC_CLAMP_CACHE_DIR` and `ENCODING_MUSIC_CLAMP_TIMEOUT_SECONDS`. Assets and score embeddings must be prepared first; the tool never downloads assets or generates score embeddings.

The CLaMP process is lazy: starting the MCP server does not import PyTorch or
load the tokenizer, model, or checkpoint. The first semantic-axis call starts
the offline worker, and compatible later calls reuse its full-precision model.
Changing the configured interpreter, checkout/model configuration, or checkpoint
identity replaces the worker safely.

### Cold and warm timing pipeline

With the configuration above pointing to an already prepared offline runtime,
measure one cold search followed by warm searches with:

```bash
uv run --extra score-embeddings \
  python -m encoding_music_mcp.score_embeddings.semantic_axis_timing \
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

### Returns

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

No vectors are returned to the MCP client. Invalid ensembles or limits, missing configuration, incompatible assets, unexpected embedding output, and degenerate axes fail with actionable errors.
