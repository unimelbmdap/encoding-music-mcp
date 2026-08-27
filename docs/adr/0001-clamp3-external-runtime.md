---
id: ADR-0001
title: CLaMP 3 external runtime
status: accepted
date: 2026-08-25
scope: module
modules: [score-embeddings]
topics: [clamp3, model-artifacts, subprocess, supply-chain]
---

## Context

`docs/scope.md` requires reproducible CLaMP 3 embeddings without network or installation side effects during imports or extraction. Upstream CLaMP 3 uses a Python 3.10/PyTorch environment, mutable downloads, and working-directory-sensitive scripts that should not share the MCP server runtime.

## Decision

We will operate CLaMP 3 as a pinned external runtime. An explicit setup command will acquire `sanderwood/clamp3` commit `9016d2b0c8d12d1aa79c2e0ab201e6822bdc83a8` into a configurable user cache, select the symbolic C2 configuration, and download the C2 weights from Hugging Face revision `791815a04a3a2bd9ab64cf590ba8307930c179e6`, verifying SHA-256 `e6fb0d139b24a1ec20836bb65bd652303d570ea9af2cddb20a1fc161421d64af`. Setup will prefetch and inventory transitive model assets and verify a separately provisioned CLaMP interpreter.

Extraction will run offline from controlled workspaces. The adapter will invoke the pinned XML-to-ABC, interleaved-ABC, and global-extraction scripts with argument arrays, captured diagnostics, and timeouts. Imports and extraction will never clone repositories, install packages, or download artifacts.

## Consequences

The hardware-specific CLaMP/PyTorch environment remains separate from the Python 3.12 MCP environment. Setup requires substantial storage because the C2 checkpoint alone is approximately 2.52 GB.

## Alternatives considered

Considered installing CLaMP into the MCP environment; rejected because its documented Python and PyTorch stack is heavyweight and independently versioned. Considered first-use downloads; rejected because extraction must be deterministic and offline-capable. Considered vendoring CLaMP and its weights; rejected because of size, provenance, and upgrade burden.
