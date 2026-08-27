# Architectural Decision Records

This is the project's decision log. Each ADR records a cross-cutting commitment — a choice that constrains more than one feature. Bodies are immutable once accepted; reversals are written as new ADRs that supersede the old.

**Code is truth, ADR is hypothesis.** An accepted ADR records what the project *decided*, not necessarily what the code currently *does*. If an ADR contradicts current code, the ADR is the stale one — supersede it, do not silently trust it.

## Schema

Frontmatter fields:

| Field | Required | Notes |
|---|---|---|
| `id` | yes | `ADR-NNNN`, four-digit zero-padded, immutable |
| `title` | yes | Sentence case, matches the kebab portion of the filename |
| `status` | yes | `accepted` \| `superseded` \| `deprecated` |
| `date` | yes | `YYYY-MM-DD` |
| `scope` | new ADRs | `universal` \| `module` \| `integration` \| `operational` — decides which changes load the ADR; absent on pre-v0.20 ADRs (*unclassified*) |
| `modules` | when `scope: module` | List of Bower module names; omit when no specific module is implicated |
| `topics` | no | Kebab-case subject keywords for topical matching (e.g. `streaming`) |
| `supersedes` | no | List of ADR IDs this entry replaces |
| `superseded-by` | no | List of ADR IDs that replaced this entry |
| `narrows` | no | List of ADR IDs this entry scopes an exception to; those ADRs stay `accepted` |
| `narrowed-by` | no | List of ADR IDs that narrowed this entry — it remains `accepted` and in force |

Body sections (in order): `## Context`, `## Decision`, `## Consequences`, `## Alternatives considered`.

Filter by `status: accepted` for "what's true now." Older statuses are historical. Only `scope: universal` ADRs apply to every change; commands select the rest by module, topic, or title relevance.

Supersession retires a decision; **narrowing does not**. An ADR carrying `narrowed-by` is still `accepted` and still binding — an exception has been carved out of it by the named ADR, and the scope of that exception is stated in the narrowing ADR's body.

## Active decisions

| ID | Title | Scope | Modules | Topics | Relations | Date |
|---|---|---|---|---|---|---|
| [ADR-0001](/docs/adr/0001-clamp3-external-runtime.md) | CLaMP 3 external runtime | module | score-embeddings | clamp3, model-artifacts, subprocess, supply-chain | — | 2026-08-25 |
| [ADR-0003](/docs/adr/0003-sqlite-vector-storage-and-embedding-identity.md) | SQLite vector storage and embedding identity | module | score-embeddings | sqlite, vector-storage, persistence, embedding-identity | supersedes ADR-0002 | 2026-08-25 |
| [ADR-0004](/docs/adr/0004-contrastive-clamp-text-to-score-emotion-retrieval.md) | Contrastive CLaMP text-to-score emotion retrieval | integration | score-embeddings, emotion-retrieval | clamp3, cross-modal-retrieval, emotion, sqlite-vec, mcp | — | 2026-08-25 |

## Superseded and deprecated

| ID | Title | Status | Superseded by | Date |
|---|---|---|---|---|
| [ADR-0002](/docs/adr/0002-sqlite-vector-storage.md) | SQLite vector storage | superseded | ADR-0003 | 2026-08-25 |
