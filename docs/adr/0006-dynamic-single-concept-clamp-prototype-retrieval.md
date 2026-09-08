---
id: ADR-0006
title: Dynamic single-concept CLaMP prototype retrieval
status: accepted
date: 2026-09-02
scope: integration
modules: [score-embeddings, prototype-retrieval]
topics: [clamp3, cross-modal-retrieval, dynamic-prototypes, sqlite-vec, mcp]
narrowed-by: [ADR-0007, ADR-0008]
---

## Context

Independent musical concepts such as jazz, piano, playful, or pastoral do not have a necessary opposite. A fixed prototype catalogue would limit query-time expression, while averaging raw prompts or normalizing an averaged prototype would obscure the requested mean-of-similarities score. Retrieval must retain the SQLite-only corpus boundary and exact CLaMP compatibility checks.

## Decision

Claude will supply a nonblank `concept`, an ordered ensemble of 3–5 nonblank, equally specific caption-like `prompts`, and `top_k` from 1 through 100. The application will encode the prompts once with the CLaMP identity matching stored score vectors and L2-normalize every prompt independently.

Let `c` be the arithmetic mean of the normalized prompt vectors. Non-finite centroids and centroids with norm no greater than float32 machine epsilon are rejected. The repository searches SQLite with `q = c / ||c||`, exact model identity, and stable distance-then-ID ordering. For each normalized score vector `m`, the application reports the required mean cosine score using:

`m · c = ||c|| × (1 - cosine_distance(m, q))`.

Because `||c||` is a positive query-wide constant, SQLite's ascending cosine distance order is the same as descending mean-cosine score order. The reported score is not z-scored, calibrated, interpreted as a probability, or based on a renormalized prototype centroid.

Results retain the concept, exact prompts, canonical model provenance, score definition, model-ineligible `excluded_count`, `song_title` as the primary display identity, technical score and embedding IDs, catalog metadata, and a classification warning. Numeric vectors are not returned.

## Consequences

Only corpus embeddings are precomputed. Prototype ensembles are generated at query time and remain inspectable. Invalid stored vectors do not contribute to `excluded_count` because storage rejects them; the count covers exact-model ineligibility. Multiple-concept fusion, fixed prototypes, z-scores, percentile calibration, reciprocal-rank fusion, and pseudo-relevance feedback require separate decisions.

## Alternatives considered

Considered Python corpus scans, raw-prompt averaging, normalized-centroid scores, fixed prototype catalogues, and treating titles as unique database keys; rejected for violating the SQLite boundary, requested scoring semantics, dynamic-query goal, or durable identity requirements.
