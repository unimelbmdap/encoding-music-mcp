# Bower Framework Reference

Detailed specifications behind the router in `_bower/framework.md`. This file is **not** loaded into every session — commands and agents read the section they need, when they need it.

## Document Layers and Ownership

Bower splits documentation into three layers by *audience* and *style*, not by directory. Design-layer docs (`architecture.md`, `ui.md`, `problem-space.md`, `constitution.md`, `scope.md`, ADRs) are narrative and human-primary. Operational-layer docs (`plan.md`, `status.md`, `module-status.md`, `index.md`) are terse, bulleted, agent-primary; word budgets apply here. Reference-layer docs (`docs/reference/**`) are external or vendored material consulted during implementation.

**Ownership semantics:** *human-owned* docs (`problem-space.md`, `constitution.md`) may be drafted by the agent during full design, but must not be rewritten unprompted afterwards. *Co-authored* docs (`architecture.md`, `ui.md`, `scope.md`, `plan.md`) are agent-updated in place as changes land, human-reviewed and edited freely. *Agent-owned* docs (`status.md`, `module-status.md`, the two index files) are routinely maintained by the agent. *External/vendored* material is read-only — consult it, don't edit it; refresh by re-vendoring. *ADR bodies* are immutable once accepted — only frontmatter (status, supersession links, applicability classification) is updated; new decisions go in new ADRs.

**Ownership governs edits, not truth.** Ownership answers *who may write this file*; it says nothing about whether the file is accurate, and for human-owned docs the two pull in opposite directions — the stronger the "don't touch" norm, the longer a false claim survives, because every agent that notices it has been told to leave it alone. Ownership protects the file from agents; nothing protects it from decay. So agents carry a **flag-don't-fix** duty on `constitution.md` and `problem-space.md`, exactly as they already do for immutable ADR bodies: when a claim in one of these contradicts the code, surface it — never silently obey the false claim, and never silently correct it.

Surfacing has a required shape, because a paraphrase invites a rubber-stamp and the point is to get the human into the file:

- Quote the claim **verbatim**, with its `docs/constitution.md:NN` location.
- State the contradicting evidence with its own exact path and line, or the command that was run and what it did.
- Ask whether to edit. If the human authorises it, that is *prompted* and the edit is permitted; absent that, the file is untouched.

**Coverage is opportunistic, not an audit.** Nothing in Bower verifies the constitution as a whole. Contradictions are caught only where an agent already reads the file *for a purpose* and happens to exercise the claim — `bower-implementer` runs the testing section's runner and fixtures, so it finds out empirically; `bower-reviewer` uses the constitution as the yardstick for coverage and status honesty, so it can see when the yardstick itself is false. A claim nothing executes (a deployment convention, a review process, "all endpoints are rate-limited") will not be caught by anyone. This is a backstop, and describing it as more than that would reproduce the very failure it guards against.

## constitution.md — Normative Shape

`constitution.md` is **normative**: it states rules the project has committed to — where tests live, the runner command, what "verified" means for a `✓`, contribution and review conventions. A rule can be *unmet*, but it cannot be *false*; an unmet rule shows up as work. That property is what makes the doc safe to treat as authority.

The failure mode is a **descriptive** claim smuggled into a normative doc — a statement about what *exists* ("CI runs the integration suite on every PR", "all modules have contract tests") written in the same register as a rule. Agents read it as fact and act on it, and the ownership norm keeps it from ever being corrected. Aspiration is welcome in a constitution; aspiration wearing the clothes of fact is not.

Two rules follow:

- **Every statement about what exists must be verifiable from the repo** — the file, the config, the command is really there — **or it does not go in the normative body.**
- **Aspirations live under a `## Not yet in force` heading**, and agents must treat everything under it as **non-existent**: do not rely on it, do not cite it as a convention, do not mark work `✓` on the strength of it. Moving an item out of that section is the human's act of putting it in force.

```markdown
## Not yet in force

Intended, but not true of the repo today. Agents: treat these as non-existent.

- Contract tests at every module boundary — only `auth` has one.
- CI gating on the integration suite — the workflow exists but is `continue-on-error`.
```

This is a shape rule, not a full template: the constitution's headings are otherwise the project's own business. The split is *prevention* — it stops the false claim being written in the form that fools everyone — and it matters more than the detection backstop above, which only ever catches the subset a running agent trips over.

**The two index files are derived-state-with-preserved-structure.** `docs/index.md` and `docs/adr/index.md` are agent-owned, but `/b-index` does not own their *prose*. On regeneration it recomputes only the derived state — status markers, ADR table rows, counts — and updates those in place, preserving any curated structure the project has grown around them (documentation maps, rationale narrative, an elaborated ADR schema reference). You may hand-author such narrative into these files — anything except prose reporting project state, which regeneration treats as derived and reduces to markers (*Status is never curated*, in `b-index.md`) — and `/b-index` will refresh the numbers without flattening the rest.

**But an index is read in full, so keep it navigational.** `docs/index.md` is the orientation entry point — it is loaded whole, every session, by every command, which makes its size a standing per-session tax rather than a cost paid only when someone opens it. Preserve-don't-flatten protects curated structure from `/b-index`; it does not give that structure a budget, and nothing else compacts it, so a curated section can only grow.

Two rules follow, and the second is the one that bites:

- **Point, don't summarise.** An index says what exists and where it lives, with derived markers. It does not restate what the documents it points at already say. A module's state lives in its `module-status.md`; a decision's substance lives in its ADR. A summary of either in the index is a second copy with no writer.
- **Narrative does not go in a table cell.** A cell is a short value. Prose in a cell cannot be surgically edited — it has no heading to anchor to, no section for an agent to target, and no writer that rewrites it wholesale — so the only available edit is to rewrite the whole paragraph inside the pipes, which is why in practice it is appended to instead and never compacted. Observed on a real project: a `Stage` cell in a hand-grown `## Status overview` table had accumulated ~15kB of narrative covering every module — 82% of a file that every command reads in full, which nothing in Bower ever read back.

**Documentation style:** design layer is narrative and explains *why*; operational layer is terse bullets and tables. Write for future-you in 6 months. Update docs as part of implementation, not after.

## Code Formatters and `docs/`

**Exclude `docs/` from the project's markdown formatter.** Record the exclusion wherever the project keeps formatter config (`.prettierignore` or equivalent), and note it in `docs/constitution.md` alongside the other process conventions, so it survives someone re-running the formatter repo-wide.

The reason is specific rather than stylistic. Formatters align markdown table columns by padding every cell out to the widest one in its column, so the cost of a table is *rows × widest cell* — set by the worst cell, with no ceiling and no warning. Prettier offers no option to turn that off (there is `proseWrap` for prose and nothing for tables), so it is all-or-nothing per file.

That amplifier is attached to exactly the documents Bower mandates. The operational layer is table-dense by design — `## Components`, `## Build order`, the two index files' tables — and these are the files on the orientation read-path of nearly every command. Padding is pure token cost, paid every session by every agent, carrying no information. Observed on a real project: 18% of the entire `docs/` tree was alignment padding, and `docs/index.md` had reached 111kB where its content was 34kB.

There is a second reason that applies even where the padding is small. Agent-owned docs are **rewritten wholesale** — `/b-feature` rebuilds `status.md` from scratch on every reconcile — so a formatter produces a cycle of align → rewrite → realign, and every pass lands a diff with no content change. That undercuts *living documentation, git is the change log*: the log fills with churn that records nothing.

What the exclusion costs is cosmetic and invisible to both audiences: trailing-whitespace normalisation, and consistent list markers and emphasis. GFM renders a misaligned table identically to an aligned one, and no agent reads a bullet character.

A table cell is for a **short value**. Narrative belongs in a document body — see the note on index files under *Document Layers and Ownership*.

## scope.md — Boundary, Not Tracker

`scope.md` answers *what is this project trying to be, right now* — three sections: current scope, current non-goals, and success criteria. It is a **present-state** doc: it is edited in place when the boundary moves, and it carries no history. A criterion the project has abandoned is **deleted outright**, not struck through and not annotated as withdrawn — `problem-space.md`, ADRs, and git hold history; scope holds the boundary.

**Success criteria carry no achievement state.** Each criterion is a statement of what must be true, followed by a `Delivered by:` clause naming the module or modules responsible:

```markdown
## Success criteria

- Ingested documents are searchable within 60 seconds of upload.
  *Delivered by: ingest, search*
- An operator can reconstruct why any given record was rejected.
  *Delivered by: audit*
```

No status column, no marker, no met/unmet field. Whether a criterion is *achieved* is derived: it holds when the modules named in its `Delivered by:` clause are complete (every feature ✓ **and** the `## Module integration` marker ✓). `/b-recap` computes and reports this; nothing writes it down.

Two reasons the state does not live here. First, **no command rewrites this file wholesale** — `/b-feature`, `/b-module`, `/b-integration`, and `/b-ui` each patch `scope.md` conditionally, seeing only their own change, so a stored status column is write-rarely and never-audited, and drifts silently while sitting on the orientation read-path of nearly every command. Second, the status marker vocabulary (`✓ 🚧 ⏸ …`) describes *build progress*, which is a property of features and modules; applied to a criterion it is a category error — a criterion is not "paused."

The `Delivered by:` pointer stops at the **module**. It does not name features or components. Scope states what must be true and who owns making it true; how the work is actually decomposed drifts between features as dependencies resolve, and scope should not track that drift.

**The general rule this follows:** *state has exactly one home, and a document may only hold state that some command rewrites wholesale.* Conditional patching of the same fact from several commands always drifts. Everything else references the home, or derives from it at read time.

## status.md — Resumption Framing

`status.md` answers one question: *if I picked this up tomorrow, what's the state and what's the next move?* That question has an answer only while the feature is unfinished, so the file has **two forms** and a lifecycle between them.

**Live form** — the feature is ⏸ 🚧 🟡 🔴. Current state in a short paragraph or bullets; `## Next move` explicit (a literal slash command); open issues only if they affect resumption. No history, no changelog, no solved-issue residue. Bug backlog belongs in the external tracker, not here. Budget ~150 words — over budget is a signal to compress, not to split.

If any acceptance criterion agreed at a gate has not yet been verified (typically manual checks the user deferred), include a `Pending verification:` line listing those checks. Empty or omitted means fully verified. A feature with pending verification is marked 🚧 in `module-status.md`, not ✓.

**Terminal form** — the feature is ✓. The resumption job is discharged, and `plan.md` is the durable record of how the thing works, so the file compresses to the marker, the evidence, and a closed next move. Budget ~50 words.

```markdown
# <feature> — ✓

## Verification

<date> — <what was run, what passed>
Qualification: <a standing caveat on that evidence, if any>

## Next move

(none — complete)
```

A stored next move is written as a `## Next move` section, as above. An inline `Next move:` (or `**Next move:**`) line in the body means the same thing and is read as such — it is the form the commands' printed handoffs use, so projects carry a mix — but new writes use the section.

Whatever command marks the feature ✓ compresses the file in the same pass. **Compress, never delete:** `## Verification` is the only durable record that the agreed criteria were actually exercised, and under what conditions.

**`Qualification:` is not `Pending verification:`.** A qualification bounds evidence that *was* gathered ("fake-LLM evidence only; real inference is owned by the test-harness feature"); pending verification names evidence that was *not*. The distinction is load-bearing rather than stylistic — a ✓ feature carrying `Pending verification:` is a false-completeness claim, so labelling a qualification that way manufactures one.

**A stored `Next move:` may only name work on its own feature** — `Run /b-feature <self>` to close a deferred check, or `(none — complete)`. It may not point at the next feature in the build order, at `/b-integration`, at `/b-review`, or at the next module. Those are *project-scoped* facts: they change whenever anything anywhere lands, and no command rewrites every feature's `status.md`, so storing one there breaks the one-home rule above and the line can only accrue — a long-finished module's features still calling for work that landed weeks ago. The project-scoped handoff is **printed** by the command that ran, and derived at read time by `/b-recap` and the docs viewer from the build-order, integration, and review markers. It is never written into a feature file.

## module-status.md — Integration and Build Order

`module-status.md` captures four things: the module-boundary integration test (location and status), the build order of features within the module, free-form integration notes, and the module's review state. Populated during full design (Stage 4), maintained as features progress. Budget ~250 words total.

```markdown
## Module integration

Test: <path or "not yet defined"> — ✓ | 🚧 | ⏸ | 🟡 | 🔴
Notes: <one-line behavioural rationale carried forward from Stage 4>
```

Only `/b-integration` (or `/b-module`'s in-pass integration step) flips this marker. `/b-feature` may refresh `Notes:` when a feature shifts what the integration test must assert, but does not touch the marker.

```markdown
## Build order

1. <feature-name> — ✓ | 🚧 | ⏸ | 🟡 | 🔴 | 🔧
2. <feature-name> — ⏸
3. <feature-name> — ⏸ (scope reduced by <feature>: <what already landed>. Remaining: <what is left to build>.)
```

Order reflects intra-module dependencies identified at design time; reorderings should be rare and driven by a genuine plan change. `/b-feature` and `/b-module` update build-order markers as features complete. Appending a new feature during a `/b-feature` add is normal — the build order is a living document, not a Stage-4 contract.

**`## Build order` is the module's feature roster, and the only one.** No other document lists a module's features. In particular, `architecture.md`'s `## Software architecture` entry states the module's purpose, data-concern boundary, and inter-module dependencies, and deliberately stops there — it does not enumerate features, because nothing maintains a second copy and a second copy therefore drifts. When you need to know what a module contains, read this section; when you add or remove a feature, this is the only roster to update.

**Pull-forward annotation.** Build order is a prediction made at design time, and dependencies routinely cause an earlier feature to absorb part of a later one's scope. That is benign in itself — it mirrors how the work actually falls out. What is not benign is the artifact it leaves behind: the later feature's `plan.md` was written before the absorption and now overstates its own scope, and that plan is exactly what the later feature's implementation pass is handed as its contract. So when a feature absorbs scope from a later entry, `/b-feature`'s reconcile annotates *that entry* with one clause naming who absorbed what, then a `Remaining:` clause naming what is still to build. The `Remaining:` half is the part that does the work — it is what stops the next pass from re-implementing what already exists. Add the annotation only when scope genuinely moved, and keep it to one line: the ~250-word budget is shared with the integration notes.

If the absorption leaves nothing to build, the entry stays ⏸ with `Remaining: none — verify and close via /b-feature <name>`. Do **not** mark it ✓ on the strength of another feature's criteria having passed: ✓ means *this* feature's agreed criteria were verified, and the code that landed early has not been checked against them. The entry earns ✓ through a normal (and now very short) `/b-feature` pass, or the operator removes it as no longer a distinct feature.

**Module-level status is a floor, not a sum.** `/b-index` derives a module's status as the worst across both feature markers and the module-integration marker. A module with all features ✓ but `## Module integration` still ⏸ surfaces as 🚧 — making the constitution's verified-for-✓ rule observable rather than aspirational. The review state (below) is **not** an input to this floor.

```markdown
## Module review

Review: ⏸ | 🚧 | ✓
```

Three states, and the section is mandatory — a module with no review yet carries `Review: ⏸`, not a missing section, because absence and not-yet-reviewed must not be the same string.

- **`⏸` never reviewed.** The starting state for every module, written at design time (Stage 4) alongside the rest of the file.
- **`🚧` in review.** A `/b-review` run diagnosed findings and reconciliation is owed. `docs/modules/<module>/review-plan.md` exists for exactly as long as this marker does; the two are written and cleared together.
- **`✓` reviewed, with a date and a roster snapshot** — `Review: ✓ 2026-07-30 (5 of 5 features)`. The count is the length of `## Build order` at the time the review was diagnosed.

**Only `/b-review` writes this line.** Not `/b-feature`, not `/b-module`, not `/b-index`, not `/b-integration` — a review is the only thing that establishes or discharges review state, exactly as only `/b-integration` (or `/b-module`'s integration pass) flips the `Test:` marker. This matters because the alternative — having `/b-feature` invalidate a stale review — would put a review obligation on the framework's hottest path for a fact it does not care about.

**Staleness is derived, never stored.** A module reviewed when it had 5 features and now carrying 8 has a review that predates three features. `/b-recap` and the docs viewer compute that by comparing the snapshot count against the current `## Build order` length and report it (`reviewed 2026-07-30 — stale, 3 features added since`); nothing writes a fourth marker state and no command has to remember to invalidate anything. The known limit: this catches features *added*, not features *modified in place*. That is deliberate — a review invalidated by every `/b-feature modify` pass would be stale almost always, which trains readers to ignore it.

**The review state is orthogonal to completion, and stays that way.** `/b-review` is explicitly optional (see *Module Review* below), so folding `Review:` into the module-status floor would silently make it mandatory and would flip every complete module in every existing project off `✓`. It is reported as its own axis — a column in `docs/index.md`'s modules table, its own `/b-recap` line, its own viewer lane. `Review: 🚧` *is* outstanding work and `/b-recap` reports it as such; `Review: ⏸` is not.

**A review can be diagnosed on an incomplete module.** `/b-review` recommends completion but does not require it, so `Review: ✓` on a module whose rollup is 🚧 is legal and merely worth noticing, not an error.

## ADRs — Architectural Decision Records

`docs/adr/` is the project's decision log. One file per decision, named `NNNN-kebab-case-title.md` with a zero-padded four-digit ID. IDs are immutable and never reused, even if a decision is later superseded; gaps are fine. ADRs cover any **cross-cutting commitment** — a choice that constrains more than one feature and would surprise a future reader if not written down. Single-feature implementation detail belongs in that feature's `plan.md`, not in an ADR.

**Frontmatter schema:**

```yaml
---
id: ADR-NNNN
title: <Title>
status: accepted | superseded | deprecated
date: YYYY-MM-DD
scope: universal | module | integration | operational
modules: [<bower-module-name>, ...]   # required when scope: module
topics: [<kebab-keyword>, ...]        # optional subject keywords
supersedes: [ADR-NNNN, ...]           # omit if empty
superseded-by: [ADR-NNNN, ...]        # omit if empty
narrows: [ADR-NNNN, ...]              # omit if empty; target keeps status: accepted
narrowed-by: [ADR-NNNN, ...]          # omit if empty
---
```

`scope` decides which changes load the ADR: `universal` (rare — constrains every feature; the only value that loads unconditionally), `module` (constrains the modules listed in `modules`), `integration` (constrains module interactions; loaded for integration-shaped work), `operational` (deployment, tooling, versioning; loaded for ops-shaped work). `topics` enables topical matching regardless of module. An accepted ADR with **no `scope` field is an unclassified pre-v0.20 entry** — commands load it on module, topic, or title match only, never wholesale. `modules` references exact directory names under `docs/modules/`; do not use sentinels.

**Body:** two required sections (`## Context`, `## Decision`) and two optional (`## Consequences` when there's a non-obvious cost or ongoing burden not already implied by the Decision; `## Alternatives considered` when real alternatives were weighed). Order is fixed. A good ADR is **~150 words** and rarely over 300. ADRs may bundle several closely-related decisions under one coherent umbrella title — the split test is whether the title honestly covers the scope. If the title would have to be "X and also Y," that's two ADRs.

**Lifecycle.** Bodies are **immutable once accepted**. Reversals are new ADRs with `supersedes: [ADR-NNNN]`; the old ADR's frontmatter gains `status: superseded`, `superseded-by: [ADR-NNNN]` — both files in one commit. Frontmatter is mutable — adding `scope`/`topics` classification to a legacy ADR is allowed and encouraged.

**Narrowing.** A decision that scopes an exception to an earlier one — leaving its central commitment in force — **narrows** rather than supersedes it. The new ADR carries `narrows: [ADR-NNNN]`; the narrowed ADR gains `narrowed-by: [ADR-NNNN]` and **keeps `status: accepted`**. Both sides are written in one commit by whichever command created the new ADR; a one-sided pair is an error, not a partial state. Rules:

- **The test.** Would someone implementing the earlier ADR's *main* decision today still be right? Yes → `narrows`. No → `supersedes`. Frontmatter that claims supersession while the body says the earlier decision stands is a defect: it marks live policy dead.
- **`narrows` never changes the target's `status`.** That is the whole point of the field. Nothing else about the target's frontmatter changes either.
- **The body must say what is narrowed and what survives.** The frontmatter is an index entry, not the explanation — a reader who follows `narrowed-by` must find the scope of the exception stated in the narrowing ADR's `## Context` and `## Decision`.
- A narrowed ADR stays in the index's active table, annotated with the relationship. It remains loadable and citable; it has not been retired.
- **Supersession prunes narrowing pointers.** Retiring either side of a pair must not leave the survivor pointing at a dead ADR. Superseding a *narrowing* ADR: its exception dies with it — remove its ID from each target's `narrowed-by` — unless the superseding ADR re-asserts the exception with its own `narrows`, in which case the target's `narrowed-by` moves to the new ID. Superseding a *narrowed* ADR: decide at the gate whether each narrowing ADR's exception still applies to the replacement decision — if yes, rewrite its `narrows` to the new ID and give the new ADR `narrowed-by`; if not, remove the retired ID from its `narrows`. Delete any field left empty; the narrowing ADR's own `status` never changes.

**Access pattern.** `docs/adr/index.md` is the canonical entry point — schema reference plus navigable index, regenerated from frontmatter by `/b-index`. Read the index first; open individual ADRs only when relevant to the current change. Do not grep frontmatter directly — the index absorbs schema evolution. Filter by `status: accepted` for "what's true now."

**Code is truth, ADR is hypothesis.** An accepted ADR records what the project *decided*, not necessarily what the code currently *does*. If an ADR names a library, file, or flag the code contradicts, the ADR is the stale one — flag it and supersede; do not silently trust it.

**When to write.** During `/b-design` Stage 2, every major decision gets an ADR. During `/b-feature` or `/b-module` reconcile, a change that introduced or invalidated a cross-cutting decision writes or supersedes one before closing. Don't pre-emptively record decisions that haven't been made; don't backfill history unless migrating from an older log format.

## Implementation Trajectory (multi-session features)

Multi-session features maintain an `## Implementation trajectory` section in `plan.md`. As each phase completes, its description is rewritten in place as a one-paragraph précis of *why* that direction was taken — not the steps, which are in git. Current and future phases stay detailed. Single-session features skip the section entirely.

## Reference Material

Two kinds of persistent reference material have a home in Bower:

- **Vendored external docs** (e.g. LLM-friendly framework indexes) live in `docs/reference/`. Create the directory only when needed. Treat contents as read-only; refresh by re-vendoring.
- **Out-of-tree source references** (e.g. a sibling prototype treated as a behavioural oracle) are pointed to from `docs/constitution.md` under working conventions, with the rationale logged as an ADR. The material itself stays where it lives on disk.

Reference material is consulted during implementation but never synthesised into project docs — if insight from it needs to persist, it belongs in `plan.md` or an ADR, not copied into `docs/reference/`.

## UI Changes — Paths in Detail

The router carries the decision table; this section carries the reasoning and worked examples. "Structural" means the change alters *what's there or how it relates*, not *how it looks*. "Well-specified" means the user named a *shape* (modal, tab, drawer, page), not only a *goal* (settings, navigation); if two or more plausible shapes exist and you'd have to pick one, treat it as underspecified.

**Path 1 — Ad-hoc, no doc impact.** Visual tweaks: move an icon, adjust colour, change copy, tighten spacing. Make the change directly; `docs/ui.md` records invariants, not pixels.

**Path 2 — Ad-hoc, reconcile the doc.** Structural changes tight enough not to need a proposal: "add a logout item to the user menu, opens a confirm modal." Make the change; update `docs/ui.md` (and any affected feature `plan.md`) as part of the reconcile.

**Path 3 — `/b-ui`.** Structural changes with branching choices the user should pick between: "add tab-based content navigation" — which tabs, switch behaviour, mobile, URL state are choices, not specifications.

Examples:

- "move the icon to the right" → Path 1
- "rename 'Submit' to 'Save changes'" → Path 1
- "add a logout item to the user menu, opens a confirm modal" → Path 2
- "the date picker should close on outside click" → Path 2 (interaction pattern + specified)
- "let's improve the dashboard" → underspecified; ask one clarifying question; lands in Path 1, 2, or 3
- "add a settings page" → Path 3 (page vs modal vs drawer, what sections)
- "swap React Router for TanStack Router" / "switch MUI to shadcn/ui" → architectural → `/b-design`

**Commit discipline.** Before a Path 1/2 burst, check `git status`. If the tree is dirty with unrelated non-trivial changes (multiple files, deletions/renames, rollback not describable in one sentence), surface it once and ask whether to commit first. For a one-line tweak the check is overhead — use judgement. The DX trade-off is deliberate: speed for the everyday case, `git` as the undo button; the architectural hard-redirect and the no-ad-hoc-cross-cutting-decisions rule stay on.

Out-of-band UI chat is, by design, *cheaper* than out-of-band feature chat. Read that as deliberate, not as a hole.

## Module Review

When a module reaches completion — every feature ✓ and the `## Module integration` marker ✓ — `/b-feature` and `/b-module` offer `/b-review <module>` as an *optional* next move. It is the one moment the module's emergent properties first become reviewable: whether tests cover the *interactions* between features, whether docs still match code, whether features built weeks apart answer the same question the same way, whether an accepted ADR has quietly drifted from the implementation.

Review delegates diagnosis to the read-only `bower-reviewer` subagent — the isolation buys adversarial freshness: the implementing agent is biased to read its own code as correct; a subagent given only docs, criteria, ADRs, and code hunts for where they *disagree*. The report is scoped to six dimensions (test coverage, spec↔code drift, cross-feature consistency, status honesty, ADR drift, boundary integrity) — deliberately not a linter or security audit.

Findings split into **owned** classes `/b-review` reconciles itself behind one triage gate (stale doc lines, missing tests for agreed behaviour, dishonest markers, drifted ADRs via `/b-adr`) and **routed** classes it never actions itself (behavioural fixes → `/b-feature`; boundary erosion → *always* `/b-design`). The split governs *who acts*, not what is tracked: **every accepted finding, owned and routed alike, goes in one `## Findings` checklist** in `docs/modules/<module>/review-plan.md`, written before anything is applied.

**A routed finding additionally carries the reviewer's `Location` / `Drift` / `Resolution` verbatim**, as indented sub-bullets under its checklist line. Owned findings do not: they are resolved in the same pass, with the report still in context, so the line is a checkbox against live knowledge. A routed finding is the opposite — deferred by definition into a fresh session, run by a command that was not present at diagnosis — so its plan entry is the entire handoff, and the report it came from no longer exists. `/b-feature` (Step 1) and `/b-design` (Stage 0) read the brief of any open routed item matching their invocation and treat it as a primary input to *verify*, not a conclusion to accept.

**The command that discharges a routed finding ticks it.** `/b-feature` rewrites that one `[ ]` to `[x]` after its own acceptance reconciliation and doc updates land, appending a completion note — `— done YYYY-MM-DD via /b-feature <slug>` — which is provenance for the audit, not evidence of the fix. `/b-design` does **not** tick, because a decision leaves the drift in the code; that asymmetry is the same one that makes discharge a property of the code rather than of a command having run. The grant is exactly one checkbox on exactly the finding the command was handed. Other items, `[~]` won't-fix dispositions, re-classification, the briefs, the `Review:` marker, and the plan's deletion all remain `/b-review`'s alone, and it re-verifies every routed tick at closeout.

**Both sweep every open plan, not the plan of the module they are changing.** A finding stays in the *reviewed* module's plan even when the fix belongs elsewhere — the plan is a review artifact, not a work queue — so `auth`'s review is where a billing fix is tracked, and nothing is ever written on billing's side. A lookup keyed on the target module's `Review:` marker would therefore miss exactly the cross-module case. The sweep is one glob of `docs/modules/*/review-plan.md`, empty on most projects. When such a finding is discharged, the review to resume is the one that *found* the drift, not the module that was changed.

**The finding reference lives inside the command**, which `/b-review` writes as `Run /b-feature modify <m> <slug> according to F<n> in docs/modules/<m>/review-plan.md`. The whole line is copied and run verbatim: the request is narrative, and a reference in it is an explicit selector that beats slug and topical matching. It is one line rather than a command plus an annotation because a two-part instruction is reassembled by hand, and the part that gets dropped is the one carrying the evidence. The path is load-bearing — finding IDs are module-local, so `F6` alone names a finding in every open plan at once.

Both **report the lookup's outcome even when it found nothing** — `/b-feature` in its inputs-selected ledger, `/b-design` at the Stage 0 gate. There is no enforcement here, only visibility, and that is the point: an unstated result is indistinguishable from a skipped check, so stating it is what lets the operator catch the miss at a gate rather than after the work is done.

**Review is a state with three phases**, and `## Module review`'s marker is the durable half of it:

1. **Diagnose.** The reviewer surveys, `/b-review` gates the findings, writes the plan, and sets `Review: 🚧`.
2. **Mediate.** Owned items are reconciled by `/b-review`; routed items are ticked — by the discharging command, or by `/b-review` after a re-classification — when **the drift they name is gone**, verified by reading the `Location:` in their brief, not when the command they name has run. The two coincide for `/b-feature`, which implements, and come apart for `/b-design`, which decides: a design run ends with an accepted ADR and often implementation work that no build order carries and no command schedules. A `route:/b-design` finding whose decision landed but whose code did not is **re-classified in place** to `route:/b-feature` — same `F<n>`, still open, brief rewritten to carry the ADR forward — on the same principle as a `test-backfill` that turns out to be a real defect. The closeout gate re-verifies every routed tick against the code before the plan is deleted, since that deletion is the last point at which any of it is recoverable — and since the tick is normally made by the command that also did the work, this audit is the only independent check the framework performs on it. Each item ends ticked (`[x]`, resolved) or won't-fixed (`[~]`, a recorded operator decision). This phase can span many sessions — re-invoking `/b-review <module>` resumes it and never re-diagnoses.
3. **Close out.** When every item carries a disposition, a closeout gate confirms, the plan is deleted, and `Review: ✓ <date> (<N> of <N> features)` is written.

A plan is written whenever there is at least one accepted finding — **including a routed-only review**, which is the common shape and the one that used to leave nothing on disk at all. `review-plan.md` and `Review: 🚧` are two sides of one fact, deliberately: the redundancy is what lets the docs viewer catch a crashed or abandoned review mechanically (marker set, plan missing) instead of needing an agent to read prose. Same reasoning as ADR `supersedes`/`superseded-by` symmetry.

**No permanent findings log.** Once a review closes, what got fixed is in the commits and what did not was an operator decision; a stored findings history would be a second copy of both with nothing maintaining it. The durable record is precisely `Review: ✓` plus its date and roster snapshot — enough to answer *was this reviewed, and is that review still current*, which is the question a findings log was never needed for.

One open plan per module. `/b-recap` surfaces both the marker and the open plan's progress; `/b-index` reports the marker as a modules-table column and still ignores the plan file itself.

## Findings queue

`docs/modules/<module>/findings.md` is an open queue of findings that emerged **outside** a review — most often a `/b-feature` run noticing a real problem it was not invoked to fix. Before v0.34 such an observation had nowhere to go: `review-plan.md` is a review artifact, so writing into it would invent a finding no reviewer diagnosed, and the note went to the console and died there.

**Same line schema as the review plan, different ID space.** A queue item is a checkbox, a module-local ID `Q<n>`, a gist, a class, and a runnable command ending `according to Q<n> in docs/modules/<module>/findings.md`, with the three-line `Location:` / `Drift:` / `Resolution:` brief indented beneath — all three, each non-empty. **Every** queue item carries a brief, where a review plan gives one only to its routed items: the plan's owned items are actioned in the same pass with the report still in context, and a queue item is deferred by construction, so the line is always the whole handoff to a command that was not present when the drift was seen. The `Q` prefix exists so a queue ID can never be mistaken for a review plan's `F<n>` in a pasted command.

```markdown
# Findings queue: <module>

Open findings recorded outside review. **Not living documentation** — each item is
deleted work: ticked on discharge, and the file is deleted when the last item is
disposed. This file implies no review state and holds nothing open.

Dispositions: `[ ]` open · `[x]` resolved · `[~]` won't fix (operator decision, with date).

## Findings

- [ ] Q1 — <gist> — route:/b-feature — Run /b-feature modify <m> <slug> according to Q1 in docs/modules/<m>/findings.md
  - Location: <file:line vs file:line>
  - Drift: <what disagrees with what>
  - Resolution: <what to do about it>
```

**Six rules:**

1. **No state machine.** No marker anywhere references this file. It does not pair with `Review:`, opens nothing, holds nothing open, and blocks no closeout. The `review-plan.md` ⇔ `Review: 🚧` invariant is deliberately *not* extended to it.
2. **Append is gated.** A command that surfaces an out-of-scope drift mid-run **offers** to record it — an operator gate, never a silent write — and then writes the whole line, brief included, while the evidence is still in context. Any command may do this. A queue entry written later from memory is the note-to-self this shape exists to avoid.
3. **Consumed by the same sweep.** `/b-feature` (Step 1) and `/b-design` (Stage 0) glob `docs/modules/*/{review-plan,findings}.md` in one call and match an open item against the invocation exactly as they match a routed review finding. A queue item may carry `route:/b-design`.
4. **Ticked by the discharging command; deleted when drained.** Same grant and same completion note as a routed review finding — with no `/b-review` to audit it, since there is no review. Whoever disposes of the last item deletes the file in the same pass. An empty queue left on disk is a broken state, reported by `/b-recap` and by the viewer. A `[~]` won't-fix is the operator's decision to make and no command's to take unprompted. **Nothing links to the queue** — refer to it by path, per `framework.md` → *Working Conventions*. A file with a death condition cannot be a link target: the link breaks on the day the queue drains, and if it was written into an ADR body no command may ever repair it, since those are immutable once accepted. Cleaning up on disposal is therefore not an available fix, which is why the rule is at the writing end.
5. **`/b-design` re-classifies a queue item it has discharged; it never ticks one.** In a review plan `/b-review` performs this move — a `route:/b-design` finding whose decision landed but whose code did not becomes `route:/b-feature`, same ID, still open. The queue has no such owner, so the design run does it itself, or the item is stranded: it still reads `route:/b-design`, and `/b-feature` loads only items routed to itself. The distinction holds because re-classifying reroutes work that is still owed, while ticking would declare it done — and nothing here would ever check that claim.
6. **Provenance decides the file.** Review-diagnosed findings live in the review plan; everything else lives here. The one sanctioned crossing is **absorb-at-triage**: a fresh `/b-review` presents the module's open queue items alongside the reviewer's findings, marked as pre-review, and those the operator accepts at the triage gate move into the plan — renumbered into the `F` sequence, brief carried verbatim, removed from the queue. Items not absorbed stay in the queue untouched. The reviewer's report may well expand on or contradict a queued item; once absorbed, the plan's copy is the one that counts.

The queue is deliberately weaker than the review plan: no gate authorises its contents as a set, no marker records that it existed, and nothing derives from it. It is a task list with a death condition, and that is the whole of its contract.

## Adoption phase

Brownfield adoption (`/b-adopt`) reconstructs orienting docs from an existing codebase and opens an **adoption phase** — a bounded state with an explicit exit. It carries zero standing cost for greenfield projects: the entire apparatus is two things that only exist while a project is mid-adoption, and both vanish when it ends.

- **The flag is a banner in `docs/index.md`.** `docs/index.md` is read on every session (it is the orientation entry point), so the presence of a `🌱 Adoption in progress` banner *is* the phase flag — no separate always-loaded state, no tax on projects that never adopt. A greenfield index simply has no banner. The banner is curated structure; `/b-index` preserves it across regeneration.
- **The ledger is fetched on demand.** `docs/adoption-ledger.md` holds the cross-cutting choices found in code whose rationale could *not* be attributed — one terse line each (`<location> · <open question>`), open items only, no stored context (it is cheap to re-derive from code when the item is picked up). An agent looks for it only because the banner told it to; nothing loads it otherwise. A choice whose git attribution the operator *accepts* at the adoption gate never enters the ledger; its rationale is retained as commit-cited prose in `architecture.md`/`scope.md`, and is promoted to an ADR only if the operator chooses — adoption never auto-writes ADRs. Attribution is provisional until that gate: a proposed citation the operator rejects as stale returns to the ledger as an open question (never written into a doc), and one the operator judges plain wrong goes to the remediate path.
- **No open questions ⇒ no phase.** If `/b-adopt` finds nothing it cannot attribute, it writes neither ledger nor banner: an empty ledger already meets the exit condition, so opening the phase would immediately contradict it. Such a project is a normal Bower project from the moment adoption finishes (its docs were still inferred — the adoption run's confidence note covers that — but there is nothing left open to track).

**Draining the ledger.** Each item has three exits, and all delete the line — the file shrinks monotonically toward empty:

- **Resolve** — the choice stays. The area is next worked on, the intent is recovered (from the user, now that there is a concrete reason to ask), and captured as an ADR via `/b-adr`. The ADR is cold, module-scoped, loaded only when that area is touched. Delete the ledger line.
- **Remediate** — the choice was accidental or wrong. Change it through the normal flow — `/b-feature` for a behavioural fix, `/b-design` if the fix is architectural — which reconciles the docs as it goes. Delete the ledger line once the change lands. This is where adoption's *renewal* actually happens: `/b-adopt` only records the concern; the fix is a normal gated change, not something adoption performs.
- **Dismiss** — the choice turns out deliberate or simply accepted, not worth a decision record. Delete the ledger line. No tombstone in v1: re-running adoption on an already-adopted project is not a supported operation, so there is nothing to guard against re-observing.

**As-built markers.** Adoption cannot mark observed features `✓`. `✓` means *agreed acceptance criteria passed*, and adoption has neither recorded criteria nor a verification pass — a `✓` on found code would be a false completeness claim, the marker-level twin of writing an inferred ADR. So `/b-adopt` marks every observed feature `🚧` (as-built, present in code, not verified to the `✓` bar) in the module's `## Build order`, and writes **no** per-feature `status.md`. A feature earns `✓` only when it is next worked and verified through the normal flow. Because adopted features have no `status.md`, `/b-index` takes their marker from the `## Build order` line and never promotes code-presence to `✓` on its own; module rollup therefore honestly shows `🚧` while as-built features remain unverified. The `🚧`-everywhere state is itself a drain signal, and the banner frames it as provisional — reusing the existing marker keeps adoption from taxing the framework's status vocabulary.

**Exit.** When the ledger is empty, delete the banner from `docs/index.md`. The docs are no longer provisional; the project is a normal Bower project. Adoption is not a mode you live in — it is a phase you leave. (Features may still legitimately sit at `🚧` after the ledger empties — adoption resolves *decision* attribution, not per-feature verification; those graduate to `✓` through normal work as each is touched.)

The discipline that makes this honest: `/b-adopt` never guesses intent. Code is *what*, not *why*; an unattributed choice is recorded as an open question, never written up as a confident ADR or architecture claim. Renewal — undoing choices that turn out to be mistakes — is not part of adoption; it emerges afterward through the normal `/b-*` flow as ledger items are drained.
