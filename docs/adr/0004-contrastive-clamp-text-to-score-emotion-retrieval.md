---
id: ADR-0004
title: Contrastive CLaMP text-to-score emotion retrieval
status: accepted
date: 2026-08-25
scope: integration
modules: [score-embeddings, emotion-retrieval]
topics: [clamp3, cross-modal-retrieval, emotion, sqlite-vec, mcp]
---

## Context

Users need emotion-based discovery over stored score embeddings. Claude can interpret an emotion request semantically, but its own embedding space and generated numeric values are not guaranteed to align with CLaMP music vectors. Cross-modal encoding and contrast arithmetic therefore require a deterministic boundary shared by the external model adapter, repository, and MCP interface.

## Decision

Claude will supply two ordered text poles: a positive target and a negative contrast. The application will encode both with the same pinned CLaMP configuration and model identity as the stored music vectors, validate their dimension and finite values, compute `positive - negative`, L2-normalize the result, and reject a zero direction. `sqlite-vec` will perform cosine retrieval over normalized score vectors with stable tie ordering. Results will retain both poles, model identity, score identity, catalog metadata, and distance. If compatible text encoding requires a different CLaMP model identity, scores must be re-embedded before retrieval.

## Consequences

Query-time inference requires the explicit ADR-0001 runtime and remains offline after setup. Claude owns semantic decomposition, not numeric vector construction. Tests may use aligned fake embeddings but must verify ordering, normalization, validation, and SQLite-side ranking.

## Alternatives considered

Considered Claude-generated or unrelated language-model vectors; rejected as incompatible. Considered positive-pole-only search and Python-side scans; rejected because they omit the requested contrast and violate ADR-0003 retrieval constraints.
