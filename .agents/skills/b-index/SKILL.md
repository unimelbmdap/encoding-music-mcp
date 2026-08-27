---
name: b-index
description: Regenerate docs/index.md and docs/adr/index.md — derived state refreshed in place, curated structure preserved.
---
<!-- GENERATED FILE — do not edit. Source: skills-src/commands/b-index.md. Regenerate: node scripts/build-adapters.cjs -->

# Bower Index Generator

Regenerate `docs/index.md` and (if `docs/adr/` exists) `docs/adr/index.md` by scanning the current state of project documentation.

## Regeneration contract

`docs/index.md` and `docs/adr/index.md` are **derived-state files with preserved structure**. Both jobs matter, and they are not the same job:

- **Derived state is authoritative.** Status markers, ADR table rows, and counts are recomputed from the current `status.md` / `module-status.md` / ADR frontmatter and overwrite whatever the file currently shows. This is the whole point of the command — never carry a stale marker forward.
- **Curated structure is preserved.** If a file already exists, update its derived values *in place* and leave everything else untouched: section ordering, hand-written narrative (documentation maps, parallelism/rationale prose), a richer schema reference, legend tables. **Do not flatten an existing file to the templates below** — projects routinely grow a richer index than the seed template, and that curation is not yours to discard.
- **The templates below are first-generation seeds, not a ceiling.** Use them verbatim only when the file does **not yet exist**. When the file exists, the template tells you which derived values to refresh and where they live structurally; the project's own layout wins.

Deciding derived vs. curated: a section is *derived* only if its content is mechanically reproducible from status markers or ADR frontmatter — the module table's status column, the ADR tables, the accepted/superseded counts. Everything else is curated; preserve it verbatim. If you cannot tell, preserve it.

**Status is never curated.** A section reporting *what state the project is in* is derived by definition, however it is worded and wherever it sits — project state lives in the status markers, `status.md`, and `module-status.md`, and `/b-recap` synthesises the narrative form on demand. So if an existing index carries a **prose** status field — a `Stage` table row, a "current state" paragraph, a narrative dashboard — it is **not** protected curated structure. Reduce it to the derived markers, or delete it outright where the markers already say the same thing. This is the single exception to "if you cannot tell, preserve it", and it exists because preserve-don't-flatten would otherwise make every past append permanent: prose status is not mechanically reproducible, so it classifies as curated, so it is carried forward forever. Running this command must *fix* that, not perpetuate it.

Two boundaries on that rule:

- **Never re-seed a status section a project has removed.** Its absence is a decision, not a gap. If `docs/index.md` has no status prose, there is nothing to do here — do not add one, and do not restore one from the seed template below.
- **Static orientation facts are not status.** A row like `Stack | TypeScript, Postgres` or `Deployment | Fly.io` describes what the project *is*, not what state it is *in*; it has no marker that could replace it and it does not grow per feature. Preserve those. The test is whether a completed feature would ever prompt an edit to the cell: if yes it is status, if no it is orientation.

**Curated does not mean unbounded.** Preserved sections still carry the style budgets in `_bower/framework.md`'s Document Authority table. Where a curated section has grown past its budget, do not silently rewrite it — **report it in the run summary**: name the section, its size, and the derived source that already covers it. Preservation protects a project's structure, not its accretion. Extend the same report to any `module-status.md` you read that is past its ~250-word budget; you are already reading all of them, and nothing else in the framework observes that ceiling.

**Compress on completion.** When a module reaches ✓, any preserved narrative that enumerates its features individually collapses to the module-level outcome — one clause for the module, not one per feature. This is the compaction that keeps a curated section flat over a project's life, and it is the *only* point at which non-status per-feature detail in an index legitimately disappears (status prose goes whenever *Status is never curated* says it goes).

## Process

1. Read `docs/architecture.md` (if it exists) for the system overview **and**, from its `## Software architecture` section, each module's one-line purpose — that section is where module purpose lives, and it is the source for the module descriptions in the output below
2. Read `docs/constitution.md` to confirm it exists
3. Read `docs/ui.md` if it exists. Its presence enables the `UI` link in the index; if the file has a leading summary sentence or paragraph, use it for the link description (otherwise use the canonical "Experience surface (navigation, screens, interaction patterns)"). Parallel to how `architecture.md` is scanned for the system overview.
4. Scan `docs/design/` for design documents
5. Scan `docs/adr/` for ADR files (any file matching `NNNN-*.md`); parse frontmatter from each
6. Scan `docs/modules/` for all modules, features, and their status files
7. For each feature, read its `status.md` to determine the current status marker
8. For each module, read its `module-status.md` for both the `## Build order` markers and the `## Module integration` `Test:` marker

## Output: `docs/index.md`

If `docs/index.md` already exists, follow the **Regeneration contract** above: refresh the derived status markers in place and preserve the project's structure. The structure below is the seed used only on first generation:

```markdown
# Project Index

## Core System
- [Architecture](/docs/architecture.md) — System overview and key decisions
- [UI](/docs/ui.md) — Experience surface (navigation, screens, interaction patterns)
- [Constitution](/docs/constitution.md) — Development conventions and standards

## Design Context
- [Problem Space](/docs/design/problem-space.md) — What we're solving and why
- [Decision Log](/docs/adr/index.md) — Architectural Decision Records (N accepted, M superseded)

## Feature Modules

### <Module Name> [<status>] · Review: <review marker>
<Brief description from the module's architecture.md `## Software architecture` entry>
- [<Feature>](/docs/modules/<module>/<feature>/) [<status>]
- ...
- [Module Status](/docs/modules/<module>/module-status.md)
```

Every link target is **repo-root-based** — a leading `/`, per the doc-link convention in `_bower/framework.md` Working Conventions. Write `/docs/architecture.md`, never `architecture.md` or `../../architecture.md`, even though these links sit inside `docs/` and a relative target would resolve. On regeneration, if the existing `docs/index.md` carries relative targets, rewrite them to the repo-root form as part of the derived-value refresh — link targets are derived, not curated structure.

The UI line is included only if `docs/ui.md` exists. The Decision Log line is included only if `docs/adr/` exists and contains at least one ADR. Counts come from frontmatter `status` fields. Omit the Design Context section entirely if neither `docs/design/` nor `docs/adr/` exists.

## Output: `docs/adr/index.md`

If `docs/adr/` does not exist, skip. If `docs/adr/index.md` already exists, follow the **Regeneration contract** above: refresh the derived tables and the accepted/superseded counts in place, and preserve the project's schema reference, section ordering, and any prose — including the project's existing table *layout* (a pre-v0.20 index may still split active decisions into module-scoped and cross-cutting tables; refresh those in place rather than restructuring, but add a Scope column if absent so classification is visible, and a Relations column if absent so narrowing and supersession are visible). The structure below is the seed used only on first generation:

```markdown
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
| [ADR-NNNN](/docs/adr/NNNN-kebab-title.md) | <title> | <scope or *unclassified*> | <modules or —> | <topics or —> | <relations or —> | <date> |

(Listed by ascending ID. Includes all `status: accepted` ADRs. An ADR with no `scope` field is shown as *unclassified* — a pre-v0.20 entry awaiting classification; commands treat it as loadable on module or topical match only, never as universal.)

The **Relations** cell is derived from frontmatter and renders each relationship this ADR participates in, comma-separated: `narrows ADR-NNNN`, `narrowed by ADR-NNNN`, `supersedes ADR-NNNN`. Write `—` when the ADR carries none. This is the column that makes narrowing visible: without it, a narrowed ADR is indistinguishable from an unqualified one, since its status is correctly still `accepted`. `superseded-by` never appears here — an ADR carrying it is not in this table.

## Superseded and deprecated

| ID | Title | Status | Superseded by | Date |
|---|---|---|---|---|

(Listed by ascending ID. Includes `status: superseded` and `deprecated`. Omit the section heading if empty.)
```

The schema section is **boilerplate** — on first generation, write it verbatim. It is the canonical schema reference for the project. On regeneration, treat it as curated: if the project has elaborated it (e.g. expanded the field notes, added lifecycle or access-pattern prose), leave that intact rather than overwriting it with this seed. The tables underneath are derived from frontmatter and are always recomputed.

One exception to that curated treatment: the field table must not omit a field the project's ADRs actually use. On regeneration, check the field table for a row per field named in the seed above; if a row is missing, add it with the seed's wording and leave every other row as the project wrote it. A schema reference that omits `narrows`/`narrowed-by` while ADRs carry them teaches the wrong schema to the next reader.

While deriving the Relations column, verify the pairs are symmetric and live: every `narrows` entry should have a matching `narrowed-by` on its target (and vice versa), and neither field should name an ADR whose `status` is `superseded` or `deprecated`. Report any one-sided pair or dead pointer to the operator as a probable interrupted write — do not repair the frontmatter yourself; `/b-adr` owns those fields and the fix belongs there.

## Rules

- **Preserve, don't flatten.** When an index file already exists, update derived values in place per the Regeneration contract; never replace a richer existing file with the seed template. The templates in this skill are minimums, not the required shape. The one thing this rule does **not** protect is prose that reports project state — see *Status is never curated* in the contract above.
- Order modules in `docs/index.md` by dependency sequence (build order), not alphabetically
- Derive status markers from status.md files: ✓ 🚧 ⏸ 🟡 🔴 🔧
- If a feature listed in a module's `## Build order` has **no** `status.md` (an adopted feature awaiting its first Bower touch — see the adoption banner), take its marker from the build-order line as-is. Do **not** treat a missing `status.md` as an error and do **not** synthesize `✓` from the feature merely existing in code — adoption marks as-built features `🚧`, and only verified work promotes them to `✓`.
- Module-level status is the "worst" status across both its feature markers *and* its `## Module integration` `Test:` marker (🔴 > 🟡 > 🚧 > ⏸ > 🔧 > ✓). A module with all features ✓ but module integration ⏸ surfaces as 🚧 — the constitution's verified-for-✓ rule made observable.
- **Review state is a separate field, never an input to that rollup.** Take each module's `## Module review` `Review:` marker verbatim and render it after the status marker: `### Auth [✓] · Review: ✓ 2026-07-12`, or `· Review: 🚧` / `· Review: ⏸`. Review is *optional* framework work, so folding it into the worst-of derivation would silently make it mandatory and would knock every complete-but-unreviewed module off `✓`. Omit the `· Review:` clause entirely for a module whose `module-status.md` has no `## Module review` section (a project that predates it) — do not write `⏸`, which would claim the state is recorded when it is not, and note the gap in the run summary. Never synthesise the marker from git history, from a `review-plan.md`, or from anything but that line. **In an index that renders modules as a table rather than headings, the review marker gets its own `Review` column — add the column if absent (as with the ADR index's Scope column), and never append the marker inside the Status cell.** Anything parsing that cell (the docs viewer included) reads it as a single status marker, and a second marker in the same cell makes the declared status ambiguous.
- Only include sections that exist (skip Design Context if no `design/` and no `adr/` directory)
- Include a brief description for each module, taken from that module's entry in `docs/architecture.md` `## Software architecture` — its one-line purpose, condensed if needed. Module purpose has exactly one home and that is it. Do **not** source the description from `module-status.md`: that file is operational (integration marker, build order, integration notes) and defines no description field, so taking one from there means either paraphrasing the integration `Notes:` — which states what the boundary test asserts, not what the module is for — or inducing projects to grow a duplicate purpose line that nothing maintains. If a module has no `## Software architecture` entry, omit its description rather than inventing one, and note the gap in the run summary.
- If no modules exist yet, write the Core System and Design Context sections only
- For ADR tables: render `scope` literally; an accepted ADR with no `scope` field is *unclassified* (pre-v0.20) — never promote it to universal. Order ADRs by ID ascending. Do **not** invent rows — read frontmatter literally.
- If any accepted ADRs are unclassified, add one line under the active-decisions table: `N unclassified pre-v0.20 ADRs — classify by adding scope/topics frontmatter (see the v0.20 migration notes in _bower/changes.md).`
- If an ADR is malformed (missing required field, unknown status), include it in a final `## Malformed` section with the file path and the issue, so it can be fixed manually. This is the only way schema violations surface.
- Ignore any `docs/modules/*/review-plan.md` and any `docs/modules/*/findings.md` — both are transient work lists, not project state, and neither ever appears in the index. For the review plan the index carries the durable `Review:` marker instead; a findings queue has no durable counterpart at all and is meant to have none. Their existence is `/b-recap`'s and the viewer's business.
- Never write a module's `Review:` marker. `/b-review` is its only writer — this command reads and renders it, exactly as it reads the `## Module integration` `Test:` marker without flipping it.
- Preserve a `🌱 Adoption in progress` banner at the top of `docs/index.md` verbatim if present — it is the adoption-phase flag (curated structure), not derived state. It is removed only by hand when `docs/adoption-ledger.md` is emptied, never by regeneration.

## Run summary

Close with a short report — a few lines, not a narrative. It carries the things a regeneration noticed but is not allowed to fix silently:

- Which files were written, and the module / feature / ADR counts.
- **Status prose reduced or deleted**, per *Status is never curated*: name the section and what replaced it. This is an edit the operator did not ask for, so it is always reported.
- **Curated sections over budget**, and any `module-status.md` over its ~250-word budget: name the section, its approximate size, and the derived source that already covers its content. Report only — the operator decides.
- Modules with no `## Software architecture` entry (description omitted), unclassified ADRs, malformed ADRs, and any one-sided or dead `narrows` / `narrowed-by` pair.
- Modules whose `module-status.md` has no `## Module review` section (review clause omitted) — the project predates the section and its review state is unrecorded.

If none of these apply, one line is the right length.
