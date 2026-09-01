# Problem Space: Reproducible Score Embeddings

## Problem

Encoding Music MCP can inspect and analyze MEI scores, but it does not provide a production-ready path from a complete symbolic score to a learned CLaMP 3 embedding.

The available prototype depends on notebook state, hardcoded paths, manual repository setup, and opaque subprocess execution. It mutates music21 object relationships while standardizing streams and does not provide a repeatable validation boundary around score conversion. These properties make it difficult to run reliably in scripts, automated research workflows, or tests.

## Users

Computational musicologists and developers need to convert complete symbolic scores into comparable embeddings while retaining a clear relationship between each source score, its validated XML representation, and its resulting embedding.

They need both a typed Python API and a command-line workflow that can be automated without reproducing notebook setup steps. They also need durable local storage that keeps vectors connected to their source, validation evidence, and model provenance.

Researchers and MCP clients also need to discover songs along high-level semantic directions rather than only from a known reference score. Relevant characteristics include mood or emotion, energy or arousal, genre or style character, atmosphere, and texture. Claude translates a request into two ordered, genuinely contrasting poles expressed as matched ensembles of short music descriptions. Compatible text encoding, prompt normalization, ensemble aggregation, contrast construction, validation, and ranking remain deterministic application behavior.

## Existing alternatives

Researchers can run notebook cells that clone CLaMP, install dependencies, export files, and invoke extraction scripts. This is useful for experimentation but leaves dependency versions, model weights, cache ownership, error handling, output ordering, and storage semantics implicit.

They can also call music21, the CLaMP CLI, and a vector database directly. Doing so repeatedly recreates standardization, XML validation, subprocess handling, normalization, schema management, and provenance logic in each consuming project.

## Desired outcome

The project provides a deterministic workflow that:

- standardizes complete scores without mutating caller-owned streams;
- exports each score to an `.xml` MusicXML document;
- reparses and validates the exported score before inference;
- installs or locates a pinned CLaMP 3 runtime through an explicit setup operation;
- extracts and normalizes one embedding per score;
- preserves input-to-output ordering and validation evidence;
- persists raw and normalized embeddings, score identity, validation evidence, and model provenance in a local SQLite database;
- persists MEI-derived title, artist or composer, and nullable work-creation date alongside each score embedding;
- makes normalized embeddings available to vector-similarity queries through a SQLite vector extension; and
- encodes two ordered, equal-length ensembles of 3–5 caption-like prompts in the same CLaMP space as the scores;
- L2-normalizes each prompt embedding, averages each pole's unit vectors, L2-normalizes both centroids, and L2-normalizes the final positive-centroid-minus-negative-centroid direction;
- retrieves catalog-shaped matches through SQLite cosine search; and
- exposes actionable logs and failures through typed Python and CLI interfaces.

## Boundaries

This work does not introduce musical segmentation, phrase detection, model training, hosted inference, MCP-based batch embedding generation, a remote vector database service, or CLaMP-enabled container deployment. It exposes only query-time semantic-axis retrieval through MCP. This workflow is intended for broad musical characteristics represented in CLaMP embeddings, not exact key, BPM, chord, note, or bar-level properties.

## Constraints

Imports must not install software or access the network. External code and weights must have explicit provenance and integrity checks. Generated XML workspaces must have predictable ownership and cleanup. Database migrations and writes must be transactional. Automated tests must not require model downloads, network access, or accelerator hardware.
