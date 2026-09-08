# Dynamic Prototype Retrieval

Use `search_songs_by_prototype` to find songs that resemble one independent,
high-level musical concept—for example *jazz*, *piano-led*, *pastoral*, or
*lo-fi production*.

## Intuition

Think of each prompt as one witness describing the same idea. CLaMP places each
description in the same semantic space as the stored scores. The tool gives each
witness equal influence by normalizing the prompt embeddings separately, then
averages them into a temporary prototype. Songs are ranked by their average
cosine similarity to all prompts.

The prototype is created for this call only. There is no fixed genre catalogue,
and the numeric vectors are never returned.

## Parameters

```text
search_songs_by_prototype(concept, prompts, top_k=10)
```

- `concept`: a nonblank label for one concept
- `prompts`: an actual list of 3–5 nonblank, caption-like descriptions of that
  same concept, at similar specificity
- `top_k`: 1–100 results (default 10)

Example:

```json
{
  "concept": "jazz",
  "prompts": [
    "Jazz music with improvisatory melodic gestures.",
    "A performance shaped by jazz phrasing and harmony.",
    "Music expressing a recognizably jazz stylistic character."
  ],
  "top_k": 10
}
```

Use one concept per call. Do not quietly mix constraints such as genre, tempo,
instrumentation, and mood. Use
[`search_songs_by_semantic_axis`](semantic-axis-retrieval.md) for a genuine
bipolar continuum such as bright–dark, and symbolic-analysis tools for exact
keys, notes, chords, intervals, progressions, BPM, or bar locations.

## How ranking works

1. All prompts are embedded in one ordered call to the persistent CLaMP text
   worker.
2. Every prompt vector is L2-normalized independently.
3. Their arithmetic mean `c` becomes the dynamic prototype. It is not
   renormalized for the reported score.
4. SQLite searches with the unit direction `q = c / ||c||` and cosine distance.
5. For each stored unit score vector `m`, the tool recovers the requested score:

```text
mean cosine similarity = m · c = ||c|| × (1 - sqlite cosine distance)
```

The positive query-wide factor `||c||` means SQLite's nearest-neighbor order is
also the correct mean-similarity order. Equal distances are ordered by stable
embedding ID. A zero or near-zero mean is rejected because contradictory prompts
do not define a reliable direction.

## Result

The response echoes the exact concept and ordered prompts, explains the score,
warns that semantic alignment is not definitive classification, and includes
exact CLaMP provenance. `eligible_count` counts rows made with that exact model;
`excluded_count` counts stored rows with different model provenance.

Each vector-free result includes rank, `song_title` as the display identity,
stable `score_id` and `embedding_id` provenance, artist, work-creation date, and
the mean cosine score. Titles may be missing or duplicated, so they are not used
as database identity.

## Configuration

For a source checkout, run once:

```bash
uv run --extra score-embeddings --locked encoding-music-embeddings bootstrap
```

The server discovers `.venv-clamp`, `.clamp3-cache`, and the bundled database
without environment variables. For external runtimes or to override these defaults:

```bash
export ENCODING_MUSIC_EMBEDDINGS_DATABASE=/absolute/path/score-embeddings.sqlite3
export ENCODING_MUSIC_CLAMP_PYTHON=/absolute/path/to/clamp-python
export ENCODING_MUSIC_CLAMP_CACHE_DIR=/absolute/path/to/clamp-cache  # optional
export ENCODING_MUSIC_CLAMP_TIMEOUT_SECONDS=3600                     # optional
```

The tool never downloads assets or creates corpus embeddings.

## Timing check

Run the deterministic FastMCP Client timing contract with:

```bash
uv run pytest -q tests/score_embeddings/test_prototype_retrieval_timing.py -s
```

For a prepared real runtime, add `ENCODING_MUSIC_RUN_REAL_TIMING=1`. The output
separates CLaMP startup/checkpoint/warm-up, text encoding, prototype construction,
SQLite search, projection, and total client-visible retrieval time. Every
measured cold and warm invocation must finish in strictly less than 90 seconds.
