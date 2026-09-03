---
id: ADR-0007
title: Opt-in dataset-normalized z-scores for CLaMP retrieval
status: accepted
date: 2026-09-03
scope: integration
modules: [score-embeddings, prototype-retrieval, semantic-axis-retrieval]
topics: [clamp3, cross-modal-retrieval, z-score, normalization]
narrows: [ADR-0005, ADR-0006]
---

## Context

Downstream combined retrieval systems require standardized distributions to correctly weight semantic-axis and prototype scores against each other. ADR-0005 and ADR-0006 prohibit z-score calibration in default responses to preserve transparent vector distances and additive SQLite queries.

## Decision

We will add an opt-in `return_z_score` flag to both prototype and semantic-axis retrieval tools. When this flag is enabled, the tools will retrieve the entire eligible vector dataset, compute the mean and standard deviation of all raw cosine or mean-cosine scores, and return a dictionary of dataset-normalized z-scores for the top records. The default behaviour remains uncalibrated.

## Alternatives considered

Considered pre-computing global z-scores during embedding generation; rejected because prototype and axis queries are dynamically constructed at query time, so the score distribution is only known at query time. Considered pushing z-score computation to the Claude client; rejected because the client lacks access to the full dataset of raw scores necessary to compute the standard deviation.
