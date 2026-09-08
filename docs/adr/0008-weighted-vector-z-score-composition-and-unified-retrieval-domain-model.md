---
id: ADR-0008
title: Weighted-vector z-score composition and unified retrieval domain model
status: accepted
date: 2026-09-08
scope: integration
modules: [score-embeddings, prototype-retrieval, semantic-axis-retrieval]
topics: [clamp3, cross-modal-retrieval, composed-query, weighted-vector, z-score, normalization, performance]
narrows: [ADR-0005, ADR-0006]
---

## Context

Retrieval requires composing multiple independent prototypes and bipolar semantic axes with arbitrary weights. ADR-0005 and ADR-0006 established single-axis and single-prototype search, while ADR-0007 introduced dataset z-score standardization to measure outlierness fairly across differing distribution variances. However, running sequential full-table SQLite KNN searches ($k=100000$) and separate CLaMP subprocess calls for each sub-query causes severe latency and client timeouts. Furthermore, procedural retrieval code in tool modules lacks a unified domain model.

## Decision

We unify vector retrieval into an object-oriented domain model (`QueryVector`, `PrototypeVector`, `SemanticAxisVector`, `WeightedQuery`, `ComposedQuery`, `TextEncoder`, `EmbeddingRepository`, `RetrievalService`, `SearchResult`) and leverage the mathematical linearity of dot products under z-score standardization:

$$\sum_i w_i z_i(x) = x \cdot \left(\sum_i \frac{w_i}{\sigma_i} v_i\right) - \sum_i \frac{w_i \mu_i}{\sigma_i}$$

Each `WeightedQuery` holds its baseline dataset average ($\mu_i$) and standard deviation ($\sigma_i$), providing its adjusted vector $v'_i = \frac{w_i}{\sigma_i} v_i$ and offset $\text{offset}_i = \frac{w_i \mu_i}{\sigma_i}$.

`ComposedQuery` synthesizes a single composite vector $V_{\text{composed}} = \sum v'_i$ and total offset $C_{\text{composed}} = \sum \text{offset}_i$, allowing `RetrievalService` to execute a single SQLite KNN query for `top_k` using normalized direction $q = V / \|V\|$ and recover the exact combined z-score via $\|V\|(1-d) - C$.

`TextEncoder` owns resident CLaMP worker communication and encodes all prompts across all components of a `ComposedQuery` in a single batched inference pass. Results always return scores as z-index (z-score) so a single score makes sense on its own without needing external dataset context.

## Consequences

Eliminates multiple full-table 100k SQLite sorts and multi-pass CLaMP worker subprocess invocations, reducing composed query latency by >90% while preserving exact dataset z-score ranking and outlierness metrics. The repository accepts a clean `QueryVector` contract without maintaining separate prototype and axis search paths, and returned scores are self-interpreting z-indices.

## Alternatives considered

Considered uncalibrated raw vector addition ($V = \sum w_i v_i$); rejected because unstandardized concept distributions allow high-variance queries to arbitrarily dominate the ranking. Considered retaining multiple $k=100000$ SQLite KNN searches and pandas joins; rejected because 100k row sorting and serialization is the direct cause of query timeouts.
