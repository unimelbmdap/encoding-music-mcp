---
id: ADR-0003
title: SQLite vector storage and embedding identity
status: accepted
date: 2026-08-25
scope: module
modules: [score-embeddings]
topics: [sqlite, vector-storage, persistence, embedding-identity]
supersedes: [ADR-0002]
---

## Context

ADR-0002 established local vector persistence, but its four-field logical identity omits the model revision already treated as reproducibility evidence by the score-embeddings architecture and implementation. The storage and identity commitments need one complete, current statement.

## Decision

We will use Python's `sqlite3` with pinned `sqlite-vec==0.1.9`, loading the packaged extension only during connection initialization. A relational table will retain score identity, source and processing hashes, validation evidence, model provenance, dimensions, and raw float32 embeddings; a `vec0` table sharing its row ID will store normalized 768-dimensional vectors with cosine distance. Transactional migrations will use `PRAGMA user_version`, and paired relational/vector writes will commit atomically. Logical identity will combine source SHA-256, processing fingerprint, CLaMP commit, model revision, and model-weight SHA-256; reprocessing that identity updates it, while any identity-field change creates a distinct record.

## Consequences

The model revision is a durable identity component even when the resolved weight bytes are unchanged. `sqlite-vec` remains pinned and upgrades require migration and compatibility testing.

## Alternatives considered

Considered retaining the four-field identity from ADR-0002; rejected because it discards pinned model-revision provenance used to distinguish reproducible runtime configurations. Considered Python-side vector search; rejected because it would load the collection into Python.
