---
id: ADR-0002
title: SQLite vector storage
status: superseded
date: 2026-08-25
scope: module
modules: [score-embeddings]
topics: [sqlite, vector-storage, persistence]
superseded-by: [ADR-0003]
---

## Context

`docs/scope.md` requires durable local storage and vector-similarity queries while keeping the embedding workflow self-contained. The store must retain reproducibility metadata and must not turn the project into a hosted database service.

## Decision

We will use Python's `sqlite3` module with the pinned `sqlite-vec==0.1.9` extension, installed through the score-embedding optional dependency set. Connections will enable extension loading only long enough to load the packaged `sqlite-vec` binary and will disable it immediately afterward.

A relational table will store score identity, source and processing hashes, validation evidence, model provenance, dimensions, and the raw float32 embedding. A `vec0` virtual table sharing the relational row ID will store the normalized 768-dimensional float32 embedding with cosine distance. Schema migrations will use `PRAGMA user_version`, run transactionally, and reject databases created by newer schema versions.

The logical identity will combine the source SHA-256, processing-configuration fingerprint, CLaMP commit, and model-weight hash. Reprocessing that identity will atomically upsert its data; changing any identity component will create a distinct record.

## Consequences

`sqlite-vec` remains pre-v1, so its exact version is pinned and upgrades require migration and compatibility tests. Database writes must keep the relational and virtual tables synchronized in one transaction.

## Alternatives considered

Considered plain SQLite BLOBs with Python-side search; rejected because similarity queries would load the collection into Python. Considered SQLite's newer `vec1`; rejected for now because its build and Python distribution are less mature. Considered an external vector database; rejected because local single-file operation is an explicit project boundary. Considered `sqlite-vss`; rejected in favor of its portable successor.
