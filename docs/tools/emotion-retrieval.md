# Emotion Retrieval

## `search_songs_by_emotion`

Search a prepared local score-embedding catalog along an ordered emotional direction.

### Parameters

- `positive_emotion` (`str`): target pole, such as `happy`
- `negative_emotion` (`str`): opposing pole to subtract, such as `sad`
- `limit` (`int`, default `10`): number of matches, from 1 to 100

Claude should translate the user's intent into one distinct ordered pair. The application embeds both poles with the configured pinned CLaMP runtime, computes `positive - negative`, normalizes the result, and performs exact-model cosine retrieval through `sqlite-vec`.

### Configuration

The MCP server process requires:

- `ENCODING_MUSIC_EMBEDDINGS_DATABASE`
- `ENCODING_MUSIC_CLAMP_PYTHON`

Optional overrides are `ENCODING_MUSIC_CLAMP_CACHE_DIR` and `ENCODING_MUSIC_CLAMP_TIMEOUT_SECONDS`. Assets and score embeddings must be prepared first; the tool never downloads or generates score embeddings.

### Returns

```json
{
  "positive_emotion": "happy",
  "negative_emotion": "sad",
  "operation": "positive - negative",
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

No vectors are returned to the MCP client. Blank/equal poles, invalid limits, missing configuration, incompatible assets, and degenerate contrast directions fail with actionable errors.
