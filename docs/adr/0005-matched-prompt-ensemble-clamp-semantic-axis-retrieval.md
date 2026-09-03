---
id: ADR-0005
title: Matched-prompt-ensemble CLaMP semantic-axis retrieval
status: accepted
date: 2026-09-01
scope: integration
modules: [score-embeddings, semantic-axis-retrieval]
topics: [clamp3, cross-modal-retrieval, semantic-axis, prompt-ensembles, sqlite-vec, mcp]
supersedes: [ADR-0004]
narrowed-by: [ADR-0007]
---

## Context

Users need discovery along broad musical characteristics represented in CLaMP embeddings, including mood, energy, style, atmosphere, and texture. A single word per pole underspecifies the intended musical context and can confound the requested attribute with instrumentation, tempo, harmony, genre, or production. Cross-modal encoding, ensemble aggregation, contrast arithmetic, validation, and ranking must remain deterministic application behavior.

## Decision

Claude will supply ordered `positive_prompts` and `negative_prompts` ensembles containing 3–5 nonblank, caption-like music descriptions each. The ensembles must have equal cardinality, and prompts at matching positions should share musical context while differing primarily in the requested attribute.

The application will encode every prompt in one ordered call using the same pinned CLaMP configuration and model identity as the stored score vectors. It will validate output order, dimension, and finite values; L2-normalize every prompt embedding individually; average the unit embeddings within each pole; L2-normalize both centroids; subtract the negative centroid from the positive centroid; and L2-normalize the resulting semantic-axis direction. Zero prompt vectors, zero centroids, and zero or non-finite final directions are rejected.

`sqlite-vec` will perform cosine retrieval over normalized score vectors with exact model-identity filtering and stable tie ordering. Results retain both ordered prompt ensembles, aggregation provenance, model identity, score identity, catalog metadata, and distance.

## Consequences

Query-time inference remains offline through ADR-0001. Claude owns semantic decomposition and matched-context prompt construction, while application code owns all numerical operations. The workflow supports broad semantic characteristics, not exact key, BPM, chord, note, or bar-level properties.

## Alternatives considered

Single-word poles were rejected as underspecified. Averaging raw embeddings was rejected because prompt magnitude could distort the centroid. Averaging without centroid renormalization was rejected because pole magnitude would affect the final contrast. Python-side vector scanning remains rejected under ADR-0003.
