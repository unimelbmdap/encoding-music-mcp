# Bower Framework Changes

Versioned log of framework changes. Most recent first. Each entry: what changed, why, and any migration notes for projects already on a previous version.

This file is the changelog for the *framework itself* — not for projects built with it. Project-level history belongs in git.

---

## Version index

Most recent first. **Migration** is the class of project-side work each version's notes require: *none* (no project changes), *mechanical* (direct file edits), *judgement* (the model must read project content and synthesise). Entries at v0.20 and above appear in full below; earlier entries are archived verbatim at `docs/changes-archive.md` in the framework repo (not scaffolded into projects).

| Version | Date | Summary | Migration |
| --- | --- | --- | --- |
| v0.34 | 2026-08-10 | The command that discharges a routed finding ticks it; drift found outside review gets a per-module findings queue with no state machine | mechanical |
| v0.33 | 2026-08-05 | The same workflows run on Claude Code and on OpenAI Codex, generated from one set of sources; `AGENTS.md` becomes the project instruction file and `CLAUDE.md` a two-line shim | judgement |
| v0.32 | 2026-07-31 | A routed review finding carries the reviewer's evidence into the session that discharges it, and is discharged by the code rather than by a command having run | judgement |
| v0.31 | 2026-07-31 | Open-review findings become readable in the viewer; review contracts and release guards are aligned around the same lifecycle | none |
| v0.30 | 2026-07-30 | A stored `Next move:` is feature-scoped and dies at ✓, where `status.md` compresses to a terminal form carrying `## Verification`; the project-scoped next move is printed and derived, never stored | mechanical |
| v0.29 | 2026-07-30 | Module review becomes a recorded three-state lifecycle: a `Review:` marker in `module-status.md`, routed findings tracked in one checklist across sessions, staleness derived | judgement |
| v0.28 | 2026-07-29 | The docs viewer ships in `_bower/viewer/`; index status prose becomes derived rather than curated, with a budget and four closed escapes; the scaffold prunes retired `_bower/` files | mechanical |
| v0.27 | 2026-07-29 | ADR narrowing gets frontmatter: `narrows` / `narrowed-by`, replacing body-only partial supersession | judgement |
| v0.26 | 2026-07-29 | One home each for module features (build order) and module purpose (`architecture.md`); repo-root doc links versioned and enforced | judgement |
| v0.25 | 2026-07-28 | Changelog split at v0.20; `/b-upgrade` reads one section at a time | none |
| v0.24 | 2026-07-28 | Success criteria stop carrying status — scope states the boundary, modules track the work | judgement |
| v0.23 | 2026-07-27 | Constitution truthfulness — normative shape, flag-don't-fix, consent gate | judgement |
| v0.22 | 2026-07-27 | Build-order pull-forward annotation | judgement |
| v0.21 | 2026-07-22 | `/b-adopt` — brownfield cold-start | none |
| v0.20 | 2026-07-17 | Context economy: delegated implementation, selective orientation, ADR applicability, slim framework import | judgement |

---

## v0.34 — 2026-08-10

### The command that discharges a routed finding ticks it

A routed review finding could previously be ticked only by `/b-review`, so discharging one cost an extra round trip: run `/b-feature`, then run `/b-review` again purely to tick a box. The rule existed to stop a command certifying its own work — but the check that does that is the *verification*, and it ran twice: once at a resumed review, once at closeout. Moving the tick to the discharging command loses neither. Closeout's audit is unchanged and is now the sole independent check, and a tick it finds is a claim to verify rather than a fact. `/b-design` keeps the full prohibition: a decision leaves the drift in the code, so ticking there would re-open the failure v0.32 closed. Reasoning in `_bower/rationale.md`, *Findings Outside Review, and Who Ticks the Box*.

- **`b-feature`** — Step 1.10 grants the tick on exactly the finding it was handed, with a completion note (`— done YYYY-MM-DD via /b-feature <slug>`); Step 6.11 performs it, after acceptance reconciled and docs landed; Step 7's handoff names `/b-review` as where mediation continues, not as a bookkeeping trip.
- **`b-design`** — Stage 0 and the handoff state the asymmetry rather than a bare prohibition.
- **`b-review`** — a new behavioural rule on who writes and who audits a tick; Step 5 leaves a pre-ticked item to closeout; Step 3's shape rules admit the completion note into the line schema; the closeout gate names itself as the only independent check and rules a completion note as provenance, not evidence.
- **`_bower/framework-reference.md`** — *Module Review* carries the grant and its limits.
- **`_bower/viewer/`** — the review page splits a completion note off the pointer, so the routed command stays copyable verbatim, and shows the note as a dated tag.

### A findings queue for drift found outside review

`docs/modules/<module>/findings.md` is an open queue of findings recorded outside a review — most often a `/b-feature` run noticing a problem it was not invoked to fix, which previously had nowhere to go but the console. It reuses the review plan's line schema and its three-line brief, with IDs `Q<n>` so a queue ID can never be read as a plan's `F<n>`, and deliberately has **no state machine**: no marker pairs with it, it holds nothing open, and it is deleted when the last item is disposed. Provenance decides the file; the one crossing is absorb-at-triage, where `/b-review` presents the queue's items alongside the reviewer's and moves the accepted ones into the plan. Schema and the six rules: `_bower/framework-reference.md` → *Findings queue*.

- **`_bower/framework-reference.md`** — new *Findings queue* section: schema, preamble template, the six rules.
- **`_bower/framework.md`** — one Working Conventions line: out-of-scope drift is offered to the queue at a gate, never written silently. A second: a transient file (`review-plan.md`, `findings.md`) is named by path, never linked — it is deleted by design, so a link into it breaks on a schedule, and a link written into an immutable ADR body could never be repaired.
- **`b-feature`** — Step 1's glob widens to `docs/modules/*/{review-plan,findings}.md`; Step 1.10 dispatches on which file matched; Step 6.12 offers to record out-of-scope drift; the inputs-selected ledger now reports both kinds.
- **`b-design`** — Stage 0's glob widens the same way; a queue item may carry `route:/b-design`, and because no `/b-review` owns the queue, the design run **re-classifies** such an item to `route:/b-feature` after its decision lands, rewriting the command and brief to carry the ADR forward. It still never ticks: re-classifying reroutes work that is still owed, ticking would declare it done.
- **`b-review`** — Step 2 prints open queue items as *pre-review findings*; the triage gate authorises absorbing them; Step 3 renumbers absorbed items into the `F` sequence and removes them from the queue.
- **`b-recap`** — reads the queues, reports open-item counts, and treats a queue with no open items as a broken state; an open queue blocks a `(none — project complete)` recommendation but never outranks planned work.
- **`b-index`** — the queue joins `review-plan.md` in the never-indexed list.
- **`bower-reviewer`** — told not to read the queue (or an open review plan): `/b-review` puts its items beside the reviewer's, which is only worth doing if the two were reached independently.

### `/b-review` prints its findings before the triage gate

Observed on a real review: the gate arrived without the findings block, leaving the operator asked to approve actioning items nobody had shown them — and the *deselect some* option unanswerable. Reinforcement only, no flow change.

- **`b-review`** — Step 2 opens with the print as a hard precondition; the triage gate refuses to present until it has run in this session, and says to reprint on a resume.

### The viewer stops hiding what is on disk

Two render-layer defects, both found on a real project. A module page enumerated features from the filesystem, so a designed-but-unbuilt module — every entry ⏸, no docs directories yet — read as having no features at all, in the state where the roster is the only thing there is to see. And the module walker registered viewer routes for exactly four filenames, so a file that existed and was correctly linked still rendered dead, with the drift report agreeing it was fine because `broken-link` tests existence and the renderer tests routability.

- **`_bower/viewer/lib/extract.cjs`** — any loose `.md` at a module root is registered as a routed page, mirroring the central-docs sweep; `findings.md` is classified as a Bower artifact and as transient; new `findings-queue-empty` check; `SCHEMA_VERSION` → `0.34`.
- **`_bower/viewer/web/app.js`** — the Build lifecycle stage counts against `## Build order`, not against materialised features; a build-order entry with no docs directory renders as a placeholder row carrying its name, order, marker and `Remaining:` clause, with no links and no invented state.
- **`_bower/viewer/README.md`** — schema-contract rows for the findings queue and for loose module-root files.

### Also deferred: external obligations have no home

Bower is a research software engineering framework, and the defining feature of RSE is that design must conform to contracts the project did not write and cannot amend — an approved ethics protocol, a data management plan, a funder condition, a data-sovereignty commitment. None of the existing document classes fits: `constitution.md` is normative but self-authored and freely amendable, an ADR records a decision the project *made* rather than a premise it answers to, and `docs/reference/` is read-only but not binding. The missing class is read-only **and** binding, and it inverts *code is truth* — against an approved protocol, contradicting code is the defect. Recorded rather than designed; nothing changes for existing projects.

- **`_bower/roadmap.md`** — new deferred item carrying the misfit analysis, the admission test that keeps it from becoming a drawer of value statements, the provisionality lifecycle, why an audit here could do harm, and its revisit trigger: the first real project constrained by an approved protocol.

### Migration

**Mechanical, and conditional — most projects have nothing to do.**

1. **Improvised `findings.md` files.** Glob `docs/modules/*/findings.md`. If none exist, this step is done — and that is the common case.

   For each one found, conform it to the v0.34 schema, which is a rewrite in place, not a new file. **Do not assume it already has the review plan's line shape.** The one real instance this schema was drawn from had: IDs of the form `F-A`, `F-B`; the gist in bold *inside* the checkbox line; no class field at all; the runnable command on its own indented `Route:` line rather than in the checkbox line; and `Location:` / `Drift:` / `Resolution:` as indented **paragraphs** rather than sub-bullets. All of that is fine and none of it survives — read what the file means, then write the target shape:
   - Replace the preamble with: a `# Findings queue: <module>` heading, then the paragraph *"Open findings recorded outside review. **Not living documentation** — each item is deleted work: ticked on discharge, and the file is deleted when the last item is disposed. This file implies no review state and holds nothing open."*, then the line *"Dispositions: `[ ]` open · `[x]` resolved · `[~]` won't fix (operator decision, with date)."*, then a `## Findings` heading.
   - Give every item a checkbox and a module-local ID `Q1`, `Q2`, … in file order. Renumber whatever scheme it used. Do not keep or reuse an `F` prefix: that belongs to review plans, and a mixed-up ID in a pasted command sends a command to the wrong file. If a routed command naming an old ID may still be in the operator's hands, say which old ID became which `Q<n>` when you report the upgrade — the renumber is the one part of this that can break a handoff someone is holding.
   - Write each item as `- [ ] Q<n> — <gist> — <class> — <runnable command>`, where the class is `route:/b-feature` or `route:/b-design` and the command ends `according to Q<n> in docs/modules/<module>/findings.md`. That trailing clause is part of the command, not a note beside it — the whole line is meant to be copied and run.
   - Give every item an indented, checkbox-free three-line brief: `- Location:`, `- Drift:`, `- Resolution:`. All three, each non-empty. Where a field cannot be reconstructed from what the file already says, **write the gap into the field** (`Location: not recorded when this was logged`) rather than leaving it blank or omitting the line — a partial brief that looks complete is worse than one that admits what is missing.
   - Delete any item already resolved, and delete the file entirely if that empties it. A queue with no open items is a broken state that `/b-recap` and the viewer will both report.
   - **Remove any markdown link whose target is the queue**, wherever it lives — `module-status.md`, `architecture.md`, an ADR body, anywhere. Grep for `findings.md` across `docs/` to find them. Replace each link with the bare path in prose (`docs/modules/<m>/findings.md`), keeping the surrounding sentence. The queue is deleted when it drains, so a link into it is a broken link on a schedule — and an ADR body is immutable once accepted, so a link written there could never be repaired afterwards. **If a link is inside an accepted ADR body, do not edit it**: report it to the operator with the ADR path and the line, and let them decide. That file is not yours to change, and the same immutability that makes the link unfixable makes it not an upgrade's business.
2. **An open `review-plan.md` needs one sentence corrected.** Glob `docs/modules/*/review-plan.md`. If none exist, this step is done. Each plan written before v0.34 carries a preamble claiming that `/b-review <module>` "is the only workflow that edits or disposes of them" — which the tick grant makes false, and which a `/b-feature` run reading the plan would take as an instruction not to tick. Replace that clause so the preamble's second sentence reads:

   > While it exists the module is in review (`Review: 🚧`): `/b-recap` summarises it and the docs viewer makes its findings readable. A command handed a routed finding ticks that one box on discharge, appending `— done <date> via <command>`; every other edit here, and the disposal of any item, belongs to `/b-review <module>` alone, which re-verifies each routed tick against the code before closing.

   Change nothing else in the file. The findings, their IDs, their classes and their briefs are unaffected — the grant is forward-only, `/b-review` resumes against the plan unchanged, and a finding ticked by `/b-review` under the old rule is verified at closeout exactly as before.
3. **Nothing else changes.** No marker, no schema, no new file is created by this upgrade. Projects with no `findings.md` — the normal case — have no project-side work at all.

## v0.33 — 2026-08-05

### One contract, two runtimes

Bower's workflows now run on **OpenAI Codex** as well as Claude Code, from one set of sources. The instruction bodies were neutralised: a workflow states the idiom — operator gate, batch gate, delegate, the request, handoff spelling — and `_bower/framework.md`'s new `## Runtime bindings` section supplies the mechanics for the runtime in use, in one place. Decision content at every gate is unchanged; what was implicit in `AskUserQuestion` (present the choices, stop, refuse a non-answer) is now written down. Codex ships as **experimental**; agent-managed refresh of `.agents/`/`.codex/` is a named unsupported primitive. Reasoning in `_bower/rationale.md`, *One Contract, Two Runtimes*.

- **`_bower/framework.md`** — new `## Runtime bindings`: operator gates, batch gates, delegation and its inline fallback, the request, handoff spelling, sessions, and permission-is-not-acceptance. The only place in the framework where a tool name may appear.
- **All 13 commands and 3 agents** — gate, delegation and argument idioms neutralised; `/b-design`, `/b-analysis` and `/b-review` gained the inline delegation fallback they lacked.
- **`b-upgrade`** — Step 5 probes for protected paths first and hands the operator the scaffold command rather than attempting a run that would half-succeed. The probe judges an absent directory by its nearest existing ancestor, as the scaffold's preflight does, so a project that predates the adapter trees is not misread as protected; resumption after an operator-run scaffold is verified against state, not a diff, because a scaffold over an already-current footprint changes nothing. Step 7 tells the operator to start a new session.
- **`_bower/brief-schema.md`, `_bower/review-schema.md`** — the optional `Context: inline` header, written by the caller on the fallback path only.
- **`_bower/rationale.md`, `_bower/roadmap.md`** — the reasoning; the roadmap item replaced by what remains (Codex graduation, plugin distribution, further runtimes).

### `skills-src/` is canonical; the adapters are generated

Editing thirteen commands in four places was never going to hold. `skills-src/` holds one body per command and agent; `scripts/build-adapters.cjs` emits the four trees and they are checked in. Transformations are mechanical — frontmatter, argument binding, TOML escaping — never prose. Lints fail the build on a runtime tool name, a literal `$ARGUMENTS`, or a `name:` that disagrees with its directory. This is framework-repo structure: projects receive generated files exactly as before.

- **`skills-src/`** (new, not scaffolded) — 16 canonical sources; **`scripts/build-adapters.cjs`** (new) — `--check` byte-compares and is a release gate.
- **`.agents/skills/b-*/SKILL.md`, `.codex/agents/bower-*.toml`** (new, generated) — the Codex adapter trees, alongside the existing `.claude/` ones.
- **`tools/adapter-test/`, `scripts/release.sh`** — golden comparison and TOML round-trip; the release now gates on adapter drift and both new acceptance tests. The tool-name lint matches by *pattern* rather than literal, because the coupling is easy to write by accident in prose that reads naturally ("with the Read tool's offset and limit") — one such site survived the neutralisation pass and was generated into a Codex skill for a tool Codex does not have. Bare verbs still pass; a control case asserts it.

### `AGENTS.md` is the project instruction file

Codex has no include mechanism, so the router cannot be `@`-included into it. A thin `AGENTS.md` — project content plus a one-line directive to read `_bower/framework.md` before any Bower work — was measured against three fresh sessions on the weakest supported model and carried all three, so it ships in preference to a scaffold-managed inline copy of the router. `CLAUDE.md` becomes a two-line shim so Claude Code keeps loading the router by include rather than by compliance.

- **`_bower/project-AGENTS.md`, `_bower/project-codex-config.toml`** (new templates) and **`_bower/project-CLAUDE.md`** (now `@AGENTS.md` + `@_bower/framework.md`) — all seeded only if absent, never edited again.
- **`scripts/scaffold.sh`, `scripts/scaffold.ps1`** — preflight writability check that aborts with zero writes before touching anything; namespace-scoped replace-and-prune of `b-*` and `bower-*` in the adapter trees, leaving a project's own skills alone; new seeds and summary lines. A *preserved* instruction file that does not reach the router now ends the run with an action-required block quoting the exact lines: seed-if-absent leaves an existing codebase's own `AGENTS.md`/`CLAUDE.md` unwired, and on a first install `VERSION` is seeded current, so no migration follows to repair it.
- **`b-adopt`** — Phase 0 stops when `AGENTS.md`/`CLAUDE.md` do not reach `_bower/framework.md`, before the delegated survey. Brownfield adoption is the path that routinely meets that state; adoption quotes the lines rather than writing them, since it writes only under `docs/`.
- **`tools/scaffold-test/`** (new) — fresh seed, idempotence, grown instruction files untouched, user skill survives a prune, read-only target aborts clean.

### Support tiers are claims with evidence attached

`docs/conformance/` (framework-repo only) holds eight behavioural scenarios, written pass criteria, and an append-only ledger. A tier states what has been demonstrated, and says so where it is short: Codex is *experimental* on a clean install plus the feature gate holding under an explicit trust waiver; Claude Code's *supported* predates the suite, so both claim sites name what it rests on and which rows are still owed. Degradations are named and scored, never slid past. The demotion rule binds contributors: a version that edits gate or delegation wording re-runs the gate and batch-gate scenarios, for the runtimes each applies to, before repeating a tier claim.

- **`docs/conformance/`** — `README.md` (tiers, demotion rule, cost), `c1`–`c8` scenario specs, `runs.md` ledger; **`tools/conformance/`** — fixture builder (5 kinds) and a `codex exec` harness.
- **`README.md`, `AGENTS.md`** — the two-runtime summary for readers; the contributor rules for generated adapters and conformance. The framework repo's own contributor instructions moved to `AGENTS.md` with `CLAUDE.md` reduced to an `@AGENTS.md` include, the same arrangement the scaffold gives projects — Codex reads no `CLAUDE.md`, so contributor rules kept there were invisible to it.

### A feature awaiting a manual check is not in-progress build work

`/b-recap`'s next-action ladder treated any feature at `🚧` with a `status.md` as work to continue — but a feature awaiting manual verification is pinned at `🚧` by design, so that signature covers two different states, and the command recommended `/b-feature` on features whose code was already complete. Found on a real project, where the same recap produced different recommendations on two runtimes: the weaker model followed the ladder as written, the stronger one silently inferred the feature was parked. The ladder was the defect, not the model. `/b-recap` also now derives its recommendation rather than adopting a feature's stored `## Next move`, which in this state points back at itself.

- **`b-recap`** — the `Pending verification:` line is the discriminator that the `🚧` marker cannot be: such features are skipped by the continue-in-progress rung, reported as `awaiting verification` rather than active, and surfaced as an `Operator action:` line that neither becomes nor suppresses the recommendation.

### Migration

This version changes how instructions are *delivered*, not what any document looks like. No `docs/` schema changed.

**Part 1 — already done by the scaffold, no action.** By the time you read this the scaffold has run. It added `.agents/skills/b-*/SKILL.md` (13 skills) and `.codex/agents/bower-*.toml` (3 agents), seeded `.codex/config.toml` and — only if the project had none — `AGENTS.md`, and refreshed `_bower/` and `.claude/`. Commit all of it; the adapters are meant to be checked in. If the project keeps its own skills in `.agents/skills/`, they were not touched: the scaffold only replaces and prunes the `b-*` and `bower-*` namespaces. Claude Code behaviour is unchanged — the commands say the same things in runtime-neutral wording.

**Part 2 — the judgement step: one home for project instructions.** Read the project's `CLAUDE.md` and `AGENTS.md` before deciding anything, and check the scaffold's summary line for `AGENTS.md` (it says `seeded` or `left alone`). The goal state is: **`AGENTS.md` carries the project's own instructions plus the router directive, and `CLAUDE.md` is exactly two lines.** Project content must end up in exactly one of the two files, never both.

The two lines `CLAUDE.md` must end with:

```
@AGENTS.md
@_bower/framework.md
```

The second line is not redundant. Claude Code loads the router by include; Codex reaches it by following the directive in `AGENTS.md`. Removing either weakens one runtime.

The router directive, to be present in `AGENTS.md` verbatim as its own paragraph near the top:

```
**Before any Bower work — any `/b-*` or `$b-*` skill, any question about project state, any change to `docs/` — read `_bower/framework.md` in full.** It is the router for how this project is designed, documented, and changed; acting without it produces non-conformant work.
```

Then work the case that matches:

- **`CLAUDE.md` is still the untouched v0.32 template** (an `@_bower/framework.md` line and an empty `## Project-Specific Code Standards` heading), `AGENTS.md` freshly seeded. Mechanical: overwrite `CLAUDE.md` with the two lines. Nothing is lost.
- **`CLAUDE.md` has grown project content**, `AGENTS.md` freshly seeded. Judgement. Move the project's own material — code standards, conventions, commands, anything the project wrote — into `AGENTS.md` under its `## Project-Specific Code Standards` heading, **verbatim**: do not summarise, do not reorder, do not "improve" it. Verbatim means the *characters*, not the sense — reproduce the source region exactly, including inline code markup and blank lines. Regenerating a line from what it means rather than from what it says is how backticks and paragraph breaks get dropped, and it has been observed doing so. Do not move the `@_bower/framework.md` include line or any other framework boilerplate; that is not project content. Then overwrite `CLAUDE.md` with the two lines. Show the operator the exact split — what moves, what is dropped as boilerplate — at the gate, before writing either file.
- **`AGENTS.md` already existed** (the scaffold left it alone). Never overwrite it. Add the router directive paragraph near the top, after any title heading, keeping everything else as it is. Then handle `CLAUDE.md` as above — and if `CLAUDE.md` and `AGENTS.md` now say the same thing in two places, keep the `AGENTS.md` copy and delete the duplicate from `CLAUDE.md`. Two homes for one instruction is the drift this framework forbids everywhere else.
- **`CLAUDE.md` carries genuinely Claude-specific material** that would be wrong for another runtime (tool names, Claude Code settings guidance). Rare. Leave that material in `CLAUDE.md` *below* the two include lines and put everything runtime-neutral in `AGENTS.md`. Name the split explicitly at the gate; it is a judgement call the operator should agree to.

After writing, read `CLAUDE.md` back and confirm it contains both include lines, and read `AGENTS.md` back and confirm the directive is present and the project's content survived. Report in the Step 7 self-assessment which case applied and what was moved.

**Part 3 — Codex notes, no file edits.** Report these once in the final summary; they are operator knowledge, not work:

- **A pre-v0.33 project must be bootstrapped once by hand before Codex can see anything.** `.agents/` and `.codex/` first ship in this version, so until the scaffold has run there is no skill for Codex to discover and no `$b-upgrade` to invoke — the thing that would automate the step is the thing that is missing. If this upgrade ran under Claude Code, the bootstrap is already done and there is nothing to do. If the project is coming to Codex from a pre-v0.33 scaffold, clone the framework and run `scripts/scaffold.sh <project-root>` from an ordinary terminal outside the sandbox; `_bower/VERSION` is preserved, so `$b-upgrade` still has its migration walk to do afterwards.
- **Trust is a hard gate.** Codex asks you to trust the repository when you first open it. Nothing Bower ships — skills, custom agents, project config — is reachable until you accept, and declining exits Codex; there is no partial mode.
- **Start a new session after an upgrade.** Instruction files are read once per run. If this upgrade ran under Codex, do not do further Bower work in this session.
- **`.agents/` and `.codex/` are read-only inside Codex's default sandbox**, and a write there fails outright rather than prompting for approval. That is why `/b-upgrade` probes first and hands you the scaffold command to run yourself. It is a named unsupported primitive, not a bug to route around.
- **`.codex/config.toml` is convenience, not enforcement.** Seeded only if absent, project-owned thereafter, and it sets `sandbox_mode = "workspace-write"`. Loosening the sandbox does not loosen a Bower gate, and tightening it does not create one — gates are semantic and live in the skill instructions.
- **Codex is experimental at v0.33.** Invocation, implicit routing, `/b-*` handoff lines, delegation to the TOML-defined agents, and read-only roles are all supported and evidenced. If a gate is skipped or a role writes when it should not, that is a reportable defect against this version.

**Part 4 — nothing else.** No document schema changed, so `docs/` needs no edits, the viewer parses the same shapes, and a project that only ever uses Claude Code needs nothing beyond Part 2.

## v0.32 — 2026-07-31

### Routed review findings carry their evidence

`review-plan.md` compressed every finding to one line, which is right for an owned finding — actioned in the same pass with the reviewer's report still in context — and wrong for a routed one, which is deferred into a fresh session run by a command that never saw the report. The line also spends its last field on the command rather than a location, so the class needing the most evidence carried the least; the receiving command re-derived the finding from code, and could conclude there was nothing there. Routed findings now carry the reviewer's `Location` / `Drift` / `Resolution` verbatim as indented, checkbox-free sub-bullets. Owned findings do not, and must not. Reasoning in `_bower/rationale.md`, *Review as Reconciliation, not Record*.

- `.claude/commands/b-review.md` — Step 3 writes the brief for routed items only; `route:/b-design` items now get a slug so the command is runnable; every routed command ends `according to F<n> in <plan path>`, so the pasted invocation carries its own reference (IDs are module-local, hence the path); a resumed review reports incomplete briefs rather than reconstructing them, and offers re-diagnosis instead.
- `.claude/commands/b-feature.md` — Step 1 gains item 10: read the matching open `route:/b-feature` finding's brief and treat it as a primary input to verify. The lookup sweeps *every* open plan (one glob in Step 1's batch), not the target module's: a finding stays in the reviewed module's plan even when the fix belongs elsewhere, so a marker-keyed lookup would miss exactly the cross-module case. The inputs-selected ledger always states the outcome, so a skipped check is visible at the gate. Step 7's next move becomes `/b-review <module>` when a routed finding was discharged.
- `.claude/commands/b-design.md` — Stage 0 gains step 0: match an open `route:/b-design` finding and pass its brief verbatim into the analyst prompt; the Stage 0 gate states the outcome either way.
- `.claude/commands/b-recap.md` — counts checkbox lines only; ignores briefs.
- `_bower/review-schema.md`, `_bower/framework-reference.md`, `_bower/rationale.md` — the contract, the spec, the reasoning.
- `_bower/viewer/lib/extract.cjs` — attaches briefs to their finding; new info check `review-routed-no-brief`, which requires all three fields non-empty and names the ones it lacks, gated on the project being ≥ v0.32 and exempt from the obsolescence tripwire. Free indented prose under a finding is kept as an annotation and sections beyond `Findings`/`Observations` are carried through — links to the plan resolve to the review page, so the page must never show less than the file. `SCHEMA_VERSION` → 0.32.
- `_bower/viewer/web/app.js`, `web/style.css`, `viewer/README.md` — the brief, annotations, and extra sections render under/after the findings; the findings grid caps the pointer column and lets it wrap, so one long path no longer starves every gist on the page; Schema contract rows added.
- `tools/viewer-test/` — fixture gains briefed and briefless routed findings, a finding annotation, and a non-schema section; asserts sub-content attaches to findings rather than counting as items, renders, and that the brief check stands down on a pre-v0.32 copy of the fixture.

### A routed finding is discharged by the code, not by the command

The tick rule — *ticked when the operator has run the command it names* — was a proxy for *the drift is gone*. It holds for `/b-feature`, which implements, and fails for `/b-design`, which decides: a design run ends with an accepted ADR and often implementation work that no build order carries and no command schedules. A real review closed with the ADR written, every box ticked, and the boundary erosion still in the code. Ticks are now verified against the `Location:` in the finding's brief — affordable only because that brief now exists — and a `route:/b-design` finding whose decision landed but whose code did not is re-classified in place to `route:/b-feature`, keeping its number and its open box. Reasoning in `_bower/rationale.md`, *Review as Reconciliation, not Record*; the general fix (an `implemented:` state on ADRs) is deferred with its trigger in `_bower/roadmap.md`.

- `.claude/commands/b-review.md` — Step 5's routed rule replaced; the closeout gate re-verifies every routed tick before deleting the plan and reopens the review rather than gating if one does not hold.
- `.claude/commands/b-design.md` — the handoff states that a design run does not discharge the finding that prompted it, and names implied `/b-feature` work when Stage 4 adds no build-order entries.
- `_bower/framework-reference.md`, `_bower/rationale.md`, `_bower/roadmap.md` — the spec, the reasoning, the deferred general fix.

### Migration

None — the new shape applies to the next diagnosed review. If a module already has an **open** review (`Review: 🚧` with a `review-plan.md` on disk), say so once and offer the operator a choice:

- **Carry on.** The plan still works — the commands run, the checkboxes track. Routed findings lack briefs, so whoever discharges one re-derives it from code, which is what happened before this version. The docs viewer reports `review-routed-no-brief` (info) per affected finding until the review closes. Nothing is broken.
- **Re-diagnose.** This is the only way to produce real briefs. It is not “re-run `/b-review`”: at `🚧`, that resumes mediation. For a fresh pass, delete `docs/modules/<module>/review-plan.md`, set `Review: ⏸` in that module's `module-status.md` `## Module review` section, then run `/b-review <module>`.

Before re-diagnosing, state the trade: it costs a reviewer run and re-surfaces `[~]` won't-fix findings for the operator to decline again. Resolved findings will not return because their drift is gone; old `route:/b-design` items whose decisions landed but whose implementation did not will return because the drift remains. That is safer than auditing old tick marks by hand.

Do not reconstruct briefs or audit old ticks by hand: both amount to a review with less context than `bower-reviewer` had. Never delete a plan without the operator's agreement — it is the review's only record.

## v0.31 — 2026-07-31

### An open review is readable, not just countable

The viewer read `review-plan.md` only for metrics — an in-review banner and a "3 of 7 findings disposed" line on the module's lifecycle panel — so the one artifact that says *what a review actually found* was reachable only by opening the file. Findings now have a page (`#/review/<module>`), which the banner and the review lane both link to: per finding, its disposition, gist, class, and pointer — the file (openable, line number kept) or the literal command that discharges it. The page lives exactly as long as the plan does, which matches the plan's own transience: at closeout it is deleted and `Review: ✓` is the whole record.

The lifecycle text is aligned with that shape: routed boundary findings remain tracked while `/b-design` owns the change, observations remain visible without becoming blocking work, and clean reviews pass through the same closeout gate. The release script now rejects unknown arguments and refuses to publish uncommitted or unpushed contents.

**Changed:**

- **`_bower/viewer/lib/extract.cjs`** — finding lines parse into id / gist / class / pointer against `/b-review`'s closed class vocabulary, with the preamble's diagnosis date and roster count and the plan's `## Observations`; an unparseable line keeps its raw text; `review-plan.md` now resolves to the review route rather than the module; `SCHEMA_VERSION` → `0.31`.
- **`_bower/viewer/web/`** — the review page; the module lifecycle's review lane becomes a link while a plan is on disk; file pointers open at their recorded line; disposition, routed-class and clickable-panel-head styles.
- **`_bower/viewer/README.md`** — schema-contract row for the finding-line shape; the rollup section describes the page.
- **`.claude/commands/b-review.md`, `_bower/review-schema.md`, `_bower/rationale.md`** — one lifecycle contract for routed findings, observations, clean-review closeout, and the viewer's read-only access.
- **`.claude/commands/`, `.claude/agents/bower-implementer.md`** — echo-only constraint blocks are removed from the main build/review pathways; unique guards remain at their operative step.
- **`scripts/release.sh`** — unknown arguments stop; a real release requires a clean HEAD equal to `origin/main` and pins the tag to that exact commit.
- **`README.md`** — the maintained-document tree and viewer summary include the transient open-review surface.
- **`tools/viewer-test/`** — the plan fixture gains an observation and an unparseable finding; extraction assertions plus direct rendering coverage for the page, exact-line link, routed command, and broken-state warning.

### Migration

None — no project-side changes required. The viewer ships in `_bower/`, which the scaffold step of `/b-upgrade` refreshes.

## v0.30 — 2026-07-30

### A stored next move is feature-scoped; the project-scoped one is derived

`/b-feature` chose a feature's `Next move:` from a menu that was mostly about other things — the next feature in the build order, the module's integration test, the next module. Each such line is true when written and decays immediately, because the work it names is completed by a *different* feature's pass and nothing rewrites this feature's file again. Observed on a real project: a long-finished module's features still calling for the first feature of the module after it. A stored `Next move:` may now only name work on its own feature, or `(none — complete)`; the project-scoped answer is printed in a handoff and derived at read time from markers by `/b-recap` and the viewer. `/b-recap` already did this and needed no change. Reasoning in `_bower/rationale.md`, "State Has One Home."

**Changed:**

- **`_bower/framework-reference.md`** — *status.md — Resumption Framing* gains the feature-scoped rule and its rationale.
- **`_bower/framework.md`** — Working Conventions gains the stored-vs-printed distinction; the `/b-review` resume clause, absent in v0.29, is added to Status Markers.
- **`.claude/commands/b-feature.md`** — Step 6.7 restricted to feature-scoped next moves; the project-scoped menu moves to a new **Step 7: Handoff**, printed and transient; behavioural rules extended.
- **`.claude/commands/b-module.md`** — Step 3.7 and the literal-command rule carry the same restriction.
- **`_bower/viewer/`** — the next-moves panel excludes ✓ features (it is labelled *outstanding*, which was false for them) and gains a derived project ladder — the next non-✓ build-order entry per module, or integration where features are all ✓ — as a new `ladder` graph field. Review is deliberately not in the ladder: `Review: ⏸` is not outstanding work, and listing it made an optional command look owed once per finished module.

### `status.md` has a terminal form at ✓

The resumption question a `status.md` answers has no answer once the feature is done, but the file kept its live shape forever. At ✓ it now compresses to the marker, a `## Verification` section (dated evidence, plus `Qualification:` for a standing caveat on it), and `Next move: (none — complete)`. ~50 words. Compress, never delete — `## Verification` is the only durable record that the agreed criteria were exercised and under what conditions. Deleting the file at ✓ was considered and ruled out for that reason. `## Verification` is newly specified, though the viewer already parsed it where projects had grown it.

`Qualification:` and `Pending verification:` are not interchangeable: the first bounds evidence that *was* gathered, the second names evidence that was not, and a ✓ feature carrying the second is an error-severity honesty finding.

**Changed:**

- **`_bower/framework-reference.md`** — the section gains live and terminal forms, the terminal template, `## Verification` as spec, and the qualification-vs-pending rule.
- **`_bower/framework.md`** — the terminal form summarised in Working Conventions; `status.md`'s budget row notes both forms.
- **`.claude/commands/b-feature.md`** (Step 6.7), **`b-module.md`** (Step 3.7 and the manual-verification PASS branch), **`.claude/commands/b-review.md`** (`status-fix`) — write the terminal form whenever a feature ends a pass at ✓.
- **`_bower/review-schema.md`** — the status-honesty dimension checks for the terminal form; a forward-pointing next move on a finished feature is `status-fix`.
- **`_bower/viewer/`** — new `next-move-on-complete` warn check, judged against the status file's own marker so it does not double-report `marker-disagreement`; `SCHEMA_VERSION` → `0.30`; README schema-contract row added.
- **`_bower/viewer/lib/`** — the extractor read only a `## Next move` *section*, so the inline `Next move:` / `**Next move:**` line every command's handoff prints — and hand-written status files copy — was invisible: on a real project 20 stale forward-pointers, none of them parsed. Both spellings are now read. Two parser defects fixed alongside, both of which turned conformant docs into findings: `md.cjs`'s `labelled()` leaked a bold label's closing `**` into the value (so a properly closed `(none — …)` read as live work), and it matched a label named in surrounding prose — labels prone to being discussed can now require their own line.
- **`tools/viewer-test/`** — the conformant module's two ✓ features move to terminal form (one carrying a `Qualification:`); new `stale-pointer` fixture feature owns the new condition and is written in the inline bold form; seven assertions covering both spellings, the emphasis leak, the prose-mention trap, and the two exclusions.

### Migration

Two mechanical passes over `docs/`. Neither requires reading code.

**1. Compress every ✓ feature's `status.md` to the terminal form.** For each module under `docs/modules/`, read `module-status.md`'s `## Build order`. For every entry marked ✓, open `docs/modules/<module>/<feature>/status.md` (skip features that have none — adopted features legitimately lack one) and rewrite it as:

```markdown
# <feature> — ✓

## Verification

<date> — <what was run, what passed>
Qualification: <standing caveat on that evidence, if any>

## Next move

(none — complete)
```

Sourcing the `## Verification` body: use whatever verification evidence the existing `status.md` already states (test names, counts, commands run, dates). If it states none, take what `plan.md`'s Testing section records. If neither gives a date, use the file's last git commit date (`git log -1 --format=%ad --date=short -- <path>`) and say what was run without inventing a count. Do **not** run tests, and do **not** infer evidence from code — an unsupported `## Verification` line is worse than a thin one.

Preserve any standing caveat the old file carried — a note that evidence came from a stub, a fake, or a partial environment — as a `Qualification:` line. **Never** write such a caveat as `Pending verification:`. That label means an agreed acceptance criterion has not been checked, and on a ✓ feature it is a false-completeness error; a qualification is a bound on evidence that *was* gathered. Conversely, if a ✓ feature's `status.md` genuinely carries a `Pending verification:` line, that feature is mismarked: leave the file in its live form, leave the line intact, and flip the build-order entry to 🚧 — do not compress it, and report it in the upgrade summary as a marker corrected.

Drop the rest of the old body. `plan.md` is the durable record of how the feature works; the resumption snapshot is discharged.

**2. Fix forward-pointing next moves on unfinished features.** For every non-✓ feature with a `status.md`, find its next move and check what it names. If it names a *different* feature, `/b-integration`, `/b-review`, `/b-module`, or `/b-recap`, replace it with `Run /b-feature <this feature>` (or, for 🟡/🔴, whatever command resumes *this* feature's work). A stored next move may only name work on its own feature; the project-level suggestion it used to carry is now printed by commands and derived by `/b-recap`.

Look for **both spellings** — a `## Next move` section and an inline `Next move:` or `**Next move:**` line in the body (`grep -rn "Next move" docs/modules --include=status.md` finds both). Projects carry a mix. Keep whichever form the file already uses; only the target changes. Step 1 rewrites ✓ files wholesale, so those end up in the section form regardless.

Report in the upgrade summary: how many files were compressed, how many next moves rewritten, any `## Verification` sections written without a dated source, and any features whose markers you corrected under the `Pending verification:` rule above. The dates and evidence strings are the judgement-bearing part of an otherwise mechanical pass — name them so the operator can spot-check.

## v0.29 — 2026-07-30

### Module review is a recorded state, not an unrecorded pass

Until now nothing recorded that a module had been reviewed. `review-plan.md` existed only while reconciliation was owed and was deleted when it finished, so a reviewed-and-reconciled module was indistinguishable from one never reviewed — and a module reviewed *clean* wrote no plan at all, making the best outcome the one with no evidence. `module-status.md` gains a `## Module review` section carrying `Review: ⏸ | 🚧 | ✓ <date> (<N> of <N> features)`, written by `/b-review` alone. It records the fact of a review, not its findings: what was fixed is in the commits, and what was not was an operator decision at a gate. Reasoning in `_bower/rationale.md`.

**Changed:**

- **`_bower/framework-reference.md`** — `module-status.md` schema gains the `## Module review` section: three states, the roster snapshot, single-writer rule, derived staleness, and why review is orthogonal to the status floor.
- **`_bower/framework.md`** — Status Markers gains the `Review:` writer rule; per-feature state line names review state.
- **`.claude/commands/b-index.md`** — renders the marker as a `· Review: <marker>` clause on each module heading; never writes it; reports modules with no section in the run summary.
- **`.claude/commands/b-recap.md`** — new *Review state* output section covering all four cases plus marker/plan disagreement; derives staleness; an open review competes for the next action.
- **`.claude/commands/b-design.md`**, **`b-adopt.md`** — write `Review: ⏸` when creating a `module-status.md`.
- **`_bower/viewer/`** — `extract.cjs` parses the section and adds four checks (`review-open-no-plan`, `review-plan-not-open` — warn; `review-stale`, `review-section-missing` — info); `app.js` gains a per-module *Lifecycle* panel (build · integration · review) and a review column in the module list; `SCHEMA_VERSION` → `0.29`; README schema-contract rows and check list updated.
- **`tools/viewer-test/`** — new `reviewstale` fixture module, review conditions across three others, 17 new assertions.

### Findings survive the session, routed ones included

A review that turned up mostly `/b-feature`-class findings wrote no plan, printed them to the console, and lost them on scroll. Owned-vs-routed now governs *who acts*, not what is tracked: every accepted finding goes in one `## Findings` checklist and holds the review open until resolved (`[x]`) or won't-fixed (`[~]`). Diagnosis sets `Review: 🚧`; a closeout gate fires only when every item is disposed of, then deletes the plan and writes `Review: ✓`. Re-running `/b-review <module>` resumes mediation and never re-diagnoses.

**Changed:**

- **`.claude/commands/b-review.md`** — Step 0 becomes a marker×plan mode table with a broken-state path; the plan's two sections merge into one `## Findings` checklist with three dispositions; a plan is written for any accepted finding including routed-only; Step 5 becomes *Mediate*; new *Gate: Closeout*; handoff leads with review state; constraints extended.
- **`_bower/review-schema.md`** — resolution-class table and preamble updated: routed findings are tracked plan items, not console-only next moves.
- **`.claude/commands/b-feature.md`**, **`b-module.md`** — the optional `/b-review` offer says the review is resumable.
- **`_bower/roadmap.md`** — adoption-aware `/b-review` split out of the `/b-adopt` v2 item with the four surviving review dimensions analysed; new item on the diagnosis-time vs closeout-time roster snapshot.

### Migration

Three parts. Part A is mechanical. Part B is **judgement-required** — it decides each module's initial review state from evidence, and getting it wrong either claims a review that never happened or discards one that did. Part C is a one-line check.

**Part A — add the section to every module.** For each `docs/modules/<module>/module-status.md` in the project, append a new section at the end of the file:

```markdown
## Module review

Review: ⏸
```

Do this for every module, including modules that are mid-build or empty. The section is mandatory: a missing section and a never-reviewed module must not be the same string, which is why `⏸` is written explicitly rather than left implied. Do not add the section to anything other than a `module-status.md`.

**Part B — decide whether any module has actually been reviewed, and record it.** `⏸` from Part A is the default and the safe answer. Change it only on positive evidence, and only with the operator's confirmation.

1. Grep every `module-status.md` for pre-existing prose about reviews — `grep -rn -i 'review' docs/modules/*/module-status.md`. Earlier versions of the framework defined no slot for this, so an agent may have written an unstructured note ("reviewed 2026-06-14", "review complete", a `Reviewed:` line). Anything you find is the strongest available evidence.
2. Check for a `docs/modules/*/review-plan.md` still on disk. If one exists, that module has a review **open**, not complete.
3. Ask the operator directly: "Have any of these modules had a `/b-review` pass? I found evidence for `<list>`; the rest will be recorded as never reviewed." Present what you found per module — quote the prose line and its file, or say "no evidence". Do **not** search git history to reconstruct review dates: a commit touching a `review-plan.md` shows a review happened but not what it covered, and a date without a roster count produces a snapshot that cannot be checked for staleness.
4. Write each module's state from the operator's answer:
   - **Never reviewed** → leave `Review: ⏸`. This is the default; use it whenever evidence is absent or ambiguous.
   - **Reviewed and finished** → `Review: ✓ YYYY-MM-DD (<N> of <N> features)`, where the date is the one the operator confirms (use the date found in prose if there is one; if the operator knows a review happened but not when, ask them for an approximate date rather than inventing one) and `<N>` is the number of entries in that module's `## Build order` **as it is now**. The snapshot will slightly over-claim if features were added since — say so in the upgrade report, and note that the alternative (guessing the historical roster) is worse.
   - **Review open** → `Review: 🚧`, and confirm `docs/modules/<module>/review-plan.md` exists. The marker and the plan are two sides of one fact from this version on; the viewer reports a mismatch as a broken state.
5. If a `review-plan.md` exists whose checklist splits into `## Reconciliations` and `## Routed` sections (the pre-v0.29 shape), convert it: merge both into a single `## Findings` section, keeping each item's existing tick state, giving each line its resolution class, and turning routed bullets into unticked `- [ ]` items naming the command to run. Add the disposition legend line: ``Dispositions: `[ ]` open · `[x]` resolved · `[~]` won't fix (operator decision, with date).`` Routed items now hold the review open, so this conversion may reopen work the old shape treated as closed — that is the intended behaviour, and it is worth naming to the operator explicitly.

**Part C — regenerate the index.** Run `/b-index` so the review state appears in `docs/index.md`. Which edit that means depends on the index's existing shape, and `/b-index` handles both: heading-form module entries gain a `· Review: <marker>` clause after the status marker; an index that renders modules as a table gains a dedicated `Review` column (added if absent — never appended inside the Status cell, which readers parse as a single status marker). Modules whose `module-status.md` somehow still lacks the section will be reported in the run summary rather than getting a `⏸` — if any appear, Part A missed them.

Nothing else changes. No `docs/` document other than `module-status.md` (and any open `review-plan.md`) is edited by this migration, and no source code is touched.

---

## v0.28 — 2026-07-29

### The docs viewer ships with the framework

`_bower/viewer/` is a zero-dependency, read-only local web view of a project's `docs/`: module graph and dependency spine, plans and status, faceted ADRs, an inverse file → owning-feature index, success criteria with satisfaction derived rather than stored, and a drift report of ~two dozen mechanical checks comparing one document against another or against the files on disk. It sits inside `_bower/`, so the scaffold copies it and `/b-upgrade` refreshes it alongside the schemas it parses. Human-facing only — no `/b-*` command consumes it. Reasoning in `_bower/rationale.md`.

**Changed:**

- **`_bower/viewer/`** — new: `lib/md.cjs` (markdown structure), `lib/extract.cjs` (`docs/` → one graph), `serve.cjs` (static server + `fs.watch` + SSE live reload), `web/` (hash-routed client, vendored `marked`), `README.md`.
- **`_bower/framework.md`** — new *Seeing the State* section: how to run it, and that it is for the human rather than an orientation source for agents.
- **`README.md`** — new *Seeing the state* section covering the viewer and the drift report.
- **`CLAUDE.md`** — new contributor section *Changing a document schema? Check the viewer*, naming the three same-commit obligations; repository layout gains `_bower/viewer/` and `tools/`.
- **`_bower/rationale.md`** — new subsections on the viewer as a derived reading surface rather than a second source of truth, and on why schema-parsing tooling needs a tripwire.
- **`_bower/roadmap.md`** — two new deferred items with revisit triggers: wiring the drift checks into `/b-review`, and a VS Code extension shell.

### Brought up to current schemas

The tool was prototyped against v0.22 shapes, so five versions of schema change had moved under it — most visibly v0.26, whose roster removal made one check fire on every feature of a real project.

**Changed (all in `_bower/viewer/`):**

- **v0.26** — `arch-feature-unlisted` and `arch-feature-orphan` are replaced by their inverse, `arch-feature-roster`: a surviving `**Features.**` list in `architecture.md` is now the finding. The roster comes from `## Build order` alone, which also brings a new `build-order-orphan` check.
- **v0.27** — `narrows` / `narrowed-by` are read, shown as relations in the ADR list and labelled chains on the ADR page, and checked four ways: pair symmetry, dangling pointers, `narrows` and `supersedes` on one target, and a narrowed ADR whose `status` is not `accepted`.
- **v0.24** — success criteria and their `Delivered by:` clauses are parsed and satisfaction derived as `/b-recap` derives it. New scope view; new `criterion-no-owner`, `criterion-stale-pointer` and `criterion-carries-status` checks.
- **v0.23** — `constitution.md`'s `## Not yet in force` items are surfaced as a distinct panel above the document.
- **v0.22** — pull-forward annotations are parsed, and the `Remaining:` clause displaces the plan's own summary on the module and feature views.
- **v0.21** — the 🌱 banner is detected as the adoption-phase flag and `docs/adoption-ledger.md` gets a view; `missing-status` stands down during adoption, where features carry no `status.md` by design.
- **framework-reference `status.md` spec** — a `Pending verification:` line or section is read; ✓ over outstanding checks is an error.
- **`/b-review`** — an open `review-plan.md` surfaces as a banner with its unapplied count.

### Keeping the viewer honest across framework changes

A parser coupled to document schemas fails silently when they move, so the coupling is held by four mechanisms rather than guidance alone. Reasoning in `_bower/rationale.md`.

- **`_bower/viewer/README.md`** — new **Schema contract** table: every convention the extractor parses, against the `framework-reference.md` section defining it.
- **`_bower/viewer/lib/extract.cjs`** — declares `SCHEMA_VERSION`, compared with the target project's `_bower/VERSION` and reported as `schema-version-skew` on mismatch; and emits `check-may-be-obsolete` for any check that fires on every candidate.
- **`tools/viewer-test/`** (not scaffolded) — new: `run.cjs` plus `fixture/` (one instance of every drift condition and a conformant module that must yield zero findings; the expected set of finding kinds is exact), `fixture-adoption/`, and `fixture-obsolete/`.
- **`scripts/release.sh`** — gates on that test and on `SCHEMA_VERSION` matching `_bower/VERSION`; warns and skips if `node` is absent.
- **`lib/extract.cjs`** — new `build-order-unparsed` check: a `## Build order` whose numbered entries all fail to parse is one named finding rather than an empty roster cascading into per-feature warnings.
- **`serve.cjs` / `web/app.js`** — a failed re-extract pushes an `extract-error` event instead of a reload, so the client says the graph on screen is the last good one rather than toasting success over stale data.

### Bower's documents separated from the project's own

`docs/` holds both, and nothing distinguished them. Each document now carries an `origin`: Bower's set (the central five, `design/problem-space.md`, ADRs, module docs, the adoption ledger) against everything else a project keeps there.

**Changed (all in `_bower/viewer/`):**

- **`lib/extract.cjs`** — new `origin` field on every document.
- **`web/app.js`** — the rail breaks after the Bower groups into a *Project docs* section, one collapsible fold per subdirectory with its state remembered; project documents carry a strap saying no Bower schema or convention applies to them.

### Formatters stay off `docs/`, and an index points rather than summarises

A markdown formatter aligns table columns by padding every cell to the widest, so a table costs *rows × widest cell* — and Prettier offers no way to disable it. That amplifier sits on the document classes Bower mandates, on the read-path of nearly every command. Separately, an index is read in full every session, and `/b-index`'s preserve-don't-flatten rule gives curated sections no writer and therefore no budget. The structural rework of `docs/index.md` is deferred with a trigger in `_bower/roadmap.md`.

**Changed:**

- **`_bower/framework-reference.md`** — new `## Code Formatters and docs/` section: exclude `docs/` from the project's markdown formatter, why the cost is unbounded, and the align→rewrite→realign churn on wholesale-rewritten docs. *Document Layers and Ownership* gains two rules for index files — point rather than summarise, and no narrative in a table cell, because prose in a cell has nothing to anchor a surgical edit to.

### The index ratchet: status prose is derived, not curated

Stating that an index points rather than summarises, and reporting an oversized cell, are both downstream of the growth. Neither touches the two things that cause it: `/b-index` still classified prose status as protected curated structure, and four commands still offered a free-text index edit as an alternative to running it. Observed on a real project — a `Stage` cell grew to ~15kB, 82% of a file that every entry point reads in full, and nothing in Bower ever read it. Because prose status is not mechanically reproducible it classified as curated, so regeneration was what made each append permanent. Reasoning in `_bower/rationale.md`.

**Changed:**

- **`.claude/commands/b-index.md`** — the regeneration contract gains **Status is never curated** (a section reporting project state is derived however it is worded; reduce it to markers or delete it — the one exception to "if you cannot tell, preserve it"), with two boundaries: never re-seed a status section a project has removed, and static orientation facts like `Stack` or `Deployment` are not status, the test being whether a completed feature would ever prompt an edit to the cell. Also **Curated does not mean unbounded** (report a curated section past its budget rather than rewriting it, extended to any `module-status.md` past ~250 words, which nothing else observed) and **Compress on completion** (per-feature detail in preserved narrative collapses to the module-level outcome when a module reaches ✓). New `## Run summary` section defines what a regeneration reports; the *Preserve, don't flatten* rule now names the exception.
- **`.claude/commands/b-feature.md`, `.claude/commands/b-module.md`, `.claude/commands/b-review.md`** — the reconcile step's `/b-index` **or** hand-edit alternative is removed: run the command, or leave the index to the next regeneration. The markers already written are the durable record.
- **`.claude/commands/b-design.md`** — the `/b-index`-unavailable fallback is narrowed to the module table (new rows and markers), with narrative excluded explicitly.
- **`_bower/framework.md`** — the Document Authority row for the two index files gains a prose budget (~300 words excluding derived tables), which is what makes the overflow report actionable. It was the only agent-owned doc in the table with a style and no size.
- **`_bower/rationale.md`** — *State Has One Home* gains the index case and two generalisations: an unbudgeted free-text field compounds rather than grows linearly, because its own content is the only exemplar of house style; and "curated" answers who may rewrite a section, not how large it may become, so preserve-don't-flatten needs a budget beside it or it is a ratchet.
- **`_bower/roadmap.md`** — the index-rework item records what this version closed and restates what stays open.

Two further corrections in the same area:

- **`.claude/commands/b-design.md`** — Stage 5's *Linter / formatter config* item now excludes `docs/` from a markdown-capable formatter at the moment the config is written, and notes it in `constitution.md`. The `docs/` exclusion is stated as a rule but nothing established it, and project scaffolding is the only point at which it is cheap.
- **`_bower/framework-reference.md`** — the *narrative in a table cell* rule no longer cites formatter padding as its evidence. Once `docs/` is excluded from the formatter there is no padding, so the padding argument told a reader who had followed the neighbouring rule that the cell was now fine. The cost that survives the exclusion is the one that matters: a 15kB cell in a file every command reads in full, which nothing reads back.

### Document cost is now visible

A table cell holding a paragraph is expensive in a way that does not look expensive: a markdown formatter aligns every sibling row out to the widest cell, so on a real project one ~15kB cell in `docs/index.md` became ~75kB of padding — in a file nearly every command reads to orient. New `oversized-table-cell` check reports the cell, since the cell is the defect and the padding is the symptom; ordinary column alignment costs a few kB, is what a formatter is for, and is not reported.

**Changed (all in `_bower/viewer/`):**

- **`lib/extract.cjs`** — new `oversized-table-cell` check over central docs, ADRs, `module-status.md`, `plan.md` and `status.md`, skipping vendored `docs/reference/`; the `docs/index.md` tagline is clamped, since it becomes a one-line page subtitle.

### Interface corrections

- **The feature page showed the Components table twice** — the structured panel (with on-disk checks and editor links) and the plan body's own `## Components` table. The panel is now the only rendering: table lines are stripped from the plan body, prose in the section is kept, and the `components` anchor moves to the panel when the heading goes too.
- **In-page anchors were broken.** Table-of-contents links emitted a bare `#slug`, which replaced the route and landed on Not Found; `render()` now strips the fragment, `tocOf` prefixes the current route, and cross-document links keep their fragment instead of dropping it.
- **The overview strip** is an equal-column grid with each tile's breakdown on its own lines; it was a flex row whose basis came from one long interpuncted string, so six tiles fitted no screen.
- **`narrows` and `narrowed` are visually distinct** — they are opposite relations and read as one badge in a single colour.
- **`#/health`** is *Documentation health* in the title and *health* in the rail; drift is what the checks look for, not what the page is.
- **The constitution's not-yet-in-force notice** links to the section rather than restating its items unformatted.

### Deployment choices revised for upstream use

- **`--host` defaults to `127.0.0.1`**, not `0.0.0.0`; the graph embeds every document body, so subnet exposure is opt-in.
- **`/open` and the static handler resolve and verify containment** rather than stripping leading `../`.
- **`docs/` subdirectories and root-level `.md` files are discovered**, not matched against a hardcoded list of four names.

### The scaffold prunes retired `_bower/` files

The `_bower/` copy was additive — no deletion pass — so any file the framework stopped shipping persisted in every project indefinitely (`.claude/agents` and `.claude/commands` were already replaced wholesale). Observed on a real project as a v0.11 copy of the framework README, sixteen versions stale, in the directory an agent reads to learn what the framework is. `VERSION` and `SOURCE` are project-owned and never pruned. Directories are now replaced rather than merged into, so a file retired *inside* `_bower/viewer/` cannot orphan either.

**Changed:**

- **`scripts/scaffold.sh`** — prune pass after the `_bower/` copy; directories replaced wholesale; each removal printed as `removed (retired upstream)` in the summary.
- **`scripts/scaffold.ps1`** — same, for parity.
- **`.claude/commands/b-upgrade.md`** — Step 5 names the removal lines and carries them into the final report.

### Migration

Five parts, all mechanical. Parts A and B concern the viewer and touch nothing in `docs/`; Parts C, D and E edit `docs/index.md`, report on document size, and settle formatter configuration.

**Part A — pick up the viewer.** Re-run the scaffold script over the project (`/b-upgrade` does this for you before walking these notes). It copies the new `_bower/viewer/` directory along with the rest of `_bower/`. Then confirm it works:

1. Run `node _bower/viewer/serve.cjs --build /tmp/bower-graph.json` from the project root. It should print a one-line summary (modules, features, ADRs, indexed files, error/warn counts) and exit 0. If it exits non-zero, report the error and stop — do not attempt to fix the viewer from inside a project; it is framework code, refreshed by the scaffold.
2. If the summary line reports a non-zero error count, that is genuine documentation drift the project can now see. **Do not fix it as part of this upgrade.** Note the count in the upgrade report and offer `node _bower/viewer/serve.cjs` as a next step so the operator can read the findings themselves. Reconciling drift is normal `/b-feature`, `/b-adr` or `/b-index` work, gated as usual — not something an upgrade does silently.
3. Delete `/tmp/bower-graph.json`.

The scaffold's output may also include `removed (retired upstream)` lines — files the framework no longer ships, now pruned (projects scaffolded before v0.12 will see `_bower/original-README.md` go, for example). No action needed; name them in the upgrade report.

**Part B — stop ignoring it, if the project was ignoring it.** Some projects trialled this tool locally and added an ignore rule for it. It is framework code now and belongs in version control with the rest of `_bower/`.

1. Check the project's `.gitignore` (and `.git/info/exclude`) for a rule matching `_bower/viewer`. A rule may appear as `_bower/viewer/`, `_bower/viewer`, or under a comment such as `# local tool, not yet upstreamed`.
2. If such a rule exists, delete the rule and its comment line, then `git add _bower/viewer` so the directory is tracked.
3. If no such rule exists, there is nothing to do — this is the expected outcome for almost every project.

Do **not** add a new ignore rule for `_bower/viewer/`. Nothing in it is generated or machine-local: `graph.json` is held in memory and only written when `--build` is passed explicitly, to a path the caller names.

**Part C — delete narrative status from `docs/index.md`.** Skip if the project has no `docs/index.md`.

1. Read `docs/index.md`. Look for prose reporting project state: a table row whose cell holds a sentence or more (commonly labelled `Stage`, `Status`, `Current state`, `Progress`), a `## Status overview` / `## Current state` section containing paragraphs, or any narrative dashboard describing what has been built.
2. Distinguish it from **static orientation facts**, which stay: `Project`, `Stack`, `Auth`, `Deployment`, `Repository` and similar are descriptions of what the project *is*, and have no marker that could replace them. The test is whether completing a feature would ever prompt an edit to that cell — if yes it is status, if no it is orientation.
3. Delete the status prose. Do not attempt to condense or relocate it: the module and feature markers in `docs/index.md`'s module table, each module's `## Build order`, and each feature's `status.md` already carry that state, and `/b-recap` synthesises the narrative form on demand. Nothing is lost, and git holds the old text.
4. If deleting it empties a section, delete the heading too. If the heading was `## Status overview` and static orientation rows remain under it, rename it to something that does not invite status back — `## At a glance` is the shape — so the next agent does not read the heading as an instruction.
5. If the file has no such prose, there is nothing to do. Do not add a status section; its absence is a decision.

**Part D — report anything over budget, do not fix it.**

1. Run `/b-index`. Its run summary now names curated sections past the index's ~300-word prose budget and any `module-status.md` past ~250 words.
2. Report those to the operator as findings and stop. Compacting an over-budget document is content work, gated as normal `/b-feature` or `/b-index` work — not something an upgrade does on its own.

**Part E — exclude `docs/` from the project's markdown formatter.** Only if the project runs one.

1. Look for formatter config at the repo root: `.prettierrc*`, a `prettier` key in `package.json`, `.prettierignore`, `dprint.json`, or an equivalent for the project's stack. If there is none, there is nothing to do.
2. If the formatter handles markdown (Prettier does by default), add `docs/` to its ignore file — creating `.prettierignore` if absent — alongside any existing `_bower/` and `.claude/` entries.
3. Note the exclusion in `docs/constitution.md` under its process conventions, so it survives someone re-running the formatter repo-wide.
4. If the formatter had already been run over `docs/`, the tables there carry alignment padding. **Do not de-pad them as part of this upgrade** — it is a whole-tree rewrite with no content change, and it belongs in its own commit where the diff can be read as exactly that. Report the situation instead: name the largest affected files and offer the rewrite as a follow-up the operator can take or leave.

Report to the operator: what was deleted from `docs/index.md` (with its approximate size), whether a heading was renamed, any budget overflows the regeneration surfaced, and whether a formatter exclusion was added.

**A note on what did not change.** No document *schema* moved in this version — no frontmatter field, marker meaning or section name changed shape, so no project document needs restructuring beyond the index prose Part C removes. The viewer's drift report may nevertheless show findings on a conformant project — those are pre-existing inconsistencies that nothing previously surfaced, not regressions introduced here.

---

## v0.27 — 2026-07-29

### ADR narrowing becomes frontmatter, not prose

Partial supersession — a decision that scopes an exception to an earlier one whose central commitment still holds — was already a first-class concept in seven places, with the rule "leave the old one `accepted`, describe the relationship in the new body." Body-only is legible to a model holding both files and to nothing else: an index, a `grep`, or a rendering tool could not distinguish a narrowed decision from an unqualified one. That left an author with two bad options — overclaim `supersedes` (marking live policy dead, which tools then act on) or stay silent (conformant, invisible). The relationship now has a field, and the operation is renamed from `partial-supersedes` to `narrows` so there is one vocabulary end to end. `narrows` was chosen over `partially-supersedes` partly because the latter contains `supersedes`/`superseded-by` as substrings, so every existing string match would silently match the new fields. Full reasoning in `_bower/rationale.md`.

**Changed:**

- **`_bower/framework-reference.md`** — the frontmatter schema gains `narrows` and `narrowed-by`; a new **Narrowing** paragraph states the symmetry, the status-preservation rule, the body requirement, the supersede-vs-narrow test, and the pruning rule for superseding either side of an existing pair.
- **`.claude/commands/b-adr.md`** — Step 2 is renamed *Determine ID and Relationship* and its partial-supersession bullet becomes a narrowing branch that now writes the target's frontmatter; new prose gives the choice test and routes genuine ambiguity to the gate. Step 4 gains the `narrowed-by` write with an explicit leave-`status`-alone instruction, a rule that both sides of a relationship are one write (aborting rather than leaving a half-written pair), and pruning rules so superseding an ADR that participates in a narrowing pair transfers or removes the pointers in the same write. The gate shows the target's diff and states what survives; the handoff and `<critical_constraints>` gain narrowing lines.
- **`.claude/commands/b-index.md`** — schema table gains both fields; the **Active decisions** table gains a `Relations` column rendering `narrows` / `narrowed by` / `supersedes` from frontmatter, which is what makes narrowing visible given the status is correctly still `accepted`. The regeneration contract adds the column when absent, and the otherwise-curated schema block now gains any field row it is missing. Regeneration also verifies each pair is symmetric and live, reporting one-sided or dead pointers rather than repairing them.
- **`.claude/commands/b-design.md`** — Stage 2's `partial-supersedes` operation becomes `narrows` and now drafts the target's frontmatter update, dropping "neither's frontmatter changes." `supersedes` operations now also draft the pointer updates for any narrowing pair the retired ADR participates in.
- **`.claude/agents/bower-analyst.md`, `_bower/brief-schema.md`** — operation renamed in ID pre-allocation and the Stage 2 template; the semantics line states the choice test.
- **`.claude/commands/b-feature.md`, `.claude/commands/b-module.md`, `.claude/commands/b-ui.md`** — the *Narrowed* reconcile branches (and `/b-module`'s gate line) name the fields and the status-preservation rule.
- **`.claude/agents/bower-reviewer.md`, `.claude/commands/b-review.md`** — the `adr-supersede` finding class explicitly covers partial contradiction too; `/b-adr`'s supersede-vs-narrow test decides which is recorded.
- **`_bower/rationale.md`** — new paragraphs: frontmatter as the machine-legible projection of the body, the operation-implies-a-field rule, and why narrowing is the one sanctioned exception to *State Has One Home* (one writer, both copies, one operation).
- **`_bower/roadmap.md`** — the duplicated-schema item records that this change nearly fired its revisit trigger, and why canonicalisation was not bundled in.

### Migration

Four parts. Part A is judgement-required; B, C and D are mechanical. Skip all of it if the project has no `docs/adr/` directory.

**Part A — find and record existing narrowing relationships.** These exist in bodies today and are invisible in frontmatter. Do not infer them silently; propose and confirm.

1. Read every ADR under `docs/adr/` whose `status` is `accepted`. For each, scan the body — `## Context`, `## Decision`, `## Consequences` — for language asserting a *partial* relationship to another ADR: "narrows", "does not supersede", "scopes an exception to", "remains correct", "remains in force", "still applies except", "unlike ADR-NNNN", or any sentence naming another ADR and limiting rather than replacing it.
2. For each candidate, identify the target ADR ID and apply the test: **would someone implementing the target's main decision today still be right?** If yes, it is a narrowing. If no, the body is describing a supersession that was never recorded — that is a different finding; report it and do not treat it as a narrowing.
3. Present every candidate pair to the operator before writing anything: the narrowing ADR's ID and title, the target's ID and title, and the sentence from the body that establishes the relationship. Ask for confirmation per pair. Do not batch-apply.
4. On confirmation, for each pair: add `narrows: [ADR-TARGET]` to the narrowing ADR's frontmatter, and add `narrowed-by: [ADR-NARROWER]` to the target's frontmatter. **Do not change the target's `status`** — it stays `accepted`. **Do not edit either body** — bodies are immutable, and the body already says what is needed. Extend the list if either field already exists.

**Part B — repair frontmatter that overclaims supersession.** This is a pre-existing conformance defect that Part A's reading will surface.

1. For each ADR carrying `supersedes: [ADR-NNNN]`, read its body. If the body states that ADR-NNNN's decision still holds, is still correct, or is only partly displaced, then the `supersedes` claim is false: it is a narrowing.
2. Confirm with the operator, quoting the contradicting sentence. On confirmation: remove `ADR-NNNN` from `supersedes` (delete the field if the list becomes empty), add `narrows: [ADR-NNNN]` instead, and on ADR-NNNN remove this ADR's ID from `superseded-by` (deleting the field if empty) and add `narrowed-by`. Then, **only if ADR-NNNN's `superseded-by` is now empty**, set its `status: accepted`; if another ADR still genuinely supersedes it, leave `status: superseded`.
3. If a target's `status` was `superseded` **only** because of this false claim, it is now `accepted` again and re-enters the active set — say so explicitly in the report, because it changes which ADRs commands load.

**Part C — add the two field rows to the project's ADR index schema block.** `/b-index` treats that block as curated and will not overwrite it, so this will not happen on its own.

1. Open `docs/adr/index.md` and find the frontmatter-fields table in its `## Schema` section. If the file or table does not exist, skip to Part D.
2. After the `superseded-by` row, add these two rows verbatim, matching the table's existing column count and separator style:

   ```
   | `narrows` | no | List of ADR IDs this entry scopes an exception to; those ADRs stay `accepted` |
   | `narrowed-by` | no | List of ADR IDs that narrowed this entry — it remains `accepted` and in force |
   ```

3. Leave every other row, and any prose the project added around the table, exactly as written.

**Part D — regenerate.** Run `/b-index`. It adds the `Relations` column to the active-decisions table and populates it from the frontmatter written in Parts A and B.

Report to the operator: every pair recorded in Part A with the evidence sentence, every overclaim repaired in Part B including any ADR whose status returned to `accepted`, and whether Part C found a schema table to amend.

## v0.26 — 2026-07-29

### `architecture.md` stops listing module features — the build order is the only roster

The `## Software architecture` entry listed each module's constituent features, duplicating that module's `module-status.md` `## Build order`. No command ever wrote the roster back into `architecture.md` — it was populated once at `/b-design` Stage 3 or `/b-adopt` and decayed from there; a real project was found two features out of date. This fails the one-home rule in `framework-reference.md` ("scope.md — Boundary, Not Tracker"). The dependency lists in the same entry are kept: nothing else records them, so they are the view's own state, not a copy. Full reasoning in `_bower/rationale.md`.

**Changed:**

- **`.claude/commands/b-design.md`** — Stage 3's software-architecture view drops `constituent features` from the entry fields, with an explicit instruction not to enumerate features and a pointer to the build order as the roster's only home.
- **`.claude/commands/b-adopt.md`** — the architecture deliverable's entry fields drop the feature roster; adoption writes it to `## Build order` only (which it already did).
- **`.claude/agents/bower-reviewer.md`** — Phase 1 input 3 no longer reads constituent features from `architecture.md`, and takes the roster from `module-status.md` (input 1) instead.
- **`_bower/brief-schema.md`** — the Stage 3 view description, the software-architecture delta line format (`edit (purpose / data concern / depends on / consumed by)`), and the worked example all drop the features field. Feature-roster deltas were already reported under Stage 4's build-order subsection.
- **`_bower/framework-reference.md`** — the `## Build order` spec gains a paragraph naming it the module's only feature roster and stating that `architecture.md` deliberately stops short of one.
- **`_bower/rationale.md`** — the two-view paragraph drops the field; new paragraphs record why, the keep/drop test for future fields, and the rejected illustrative-list option.

### `/b-index` sources module descriptions from `architecture.md`, not `module-status.md`

The same defect in the other direction. `/b-index` was told to take module descriptions from `module-status.md`, which defines no description field — its schema is the integration marker, the build order, and integration notes. Module purpose lives in `architecture.md` `## Software architecture`. Satisfying the old instruction meant either paraphrasing the integration `Notes:` (what the boundary test asserts, not what the module is for) or growing a purpose line in `module-status.md` that nothing maintains.

**Changed:**

- **`.claude/commands/b-index.md`** — Process step 1 now reads each module's one-line purpose from `docs/architecture.md` `## Software architecture` alongside the system overview. The description rule names that section as the single source, states why `module-status.md` is the wrong source, and directs the command to omit a description (and note the gap) rather than invent one when a module has no software-architecture entry.
- **`.claude/commands/b-spec.md`** — the spec template's per-module description had the same wrong source; it now draws from the module's `## Software architecture` entry (purpose and data concern), which Step 1 already reads.

### Repo-root-based doc links

This convention was added to `_bower/framework.md` Working Conventions after v0.25 without a version entry:

> **Doc links are repo-root-based.** Write `[ADR-xxxx](/docs/adr/xxxx-yyy.md)`, never `../../../adr/…`. Targets must start with `/`, `#` or a URL scheme.

It is versioned here with the conformance work it needed: two commands emit links from templates, and every template target was relative, so `/b-index` wrote non-conformant links on every run.

**Changed:**

- **`.claude/commands/b-index.md`** — all eight link targets in the `docs/index.md` seed template and the `docs/adr/index.md` ADR-table row are now repo-root-based (`/docs/architecture.md`, `/docs/modules/<module>/module-status.md`, `/docs/adr/NNNN-kebab-title.md`, …), with the rule stated for the template — it holds even though these links sit inside `docs/`, where a relative target resolves. On regeneration, relative targets in an existing `docs/index.md` are rewritten: link targets are derived values, so preserve-don't-flatten does not shield them.
- **`.claude/commands/b-adopt.md`** — the adoption banner's ledger link becomes `/docs/adoption-ledger.md`.

### Migration

Three parts. Part A is judgement-required; Parts B and C are mechanical, and B may find nothing to do.

**Part A — remove feature rosters from `architecture.md`. Do not perform this as a blind delete.** The drift runs in both directions, and one direction destroys information.

1. Read `docs/architecture.md` and locate the `## Software architecture` section. If the file has no such section, or no entry in it names features, there is nothing to do — stop here.
2. For each module entry that lists features (a `Features:` clause, a `Features.` sentence, or a bulleted feature list inside the entry), read that module's `docs/modules/<module>/module-status.md` `## Build order`.
3. Compare the two lists by feature name:
   - **Names in `## Build order` but not in the architecture entry** — this is the common case and needs no action. The build order is authoritative and already complete.
   - **Names in the architecture entry but not in `## Build order`** — the architecture entry is the sole surviving record of that feature, and deleting the clause would destroy it. Do **not** silently append and do **not** silently drop. Surface each such name to the operator with both lists quoted, and ask which it is: a feature that should be appended to `## Build order` (add it with a `⏸` marker, placed where its dependencies dictate, or `🚧` if code for it plainly exists), a feature that was renamed (identify the current name and confirm), or a design-time feature that was folded into another or abandoned (drop it). Apply the operator's answer to `## Build order` before step 4.
4. Once every name is accounted for, delete the feature list from the architecture entry. Keep the entry's purpose, data-concern boundary, and depends-on / consumed-by clauses. Do not add a replacement pointer line such as "Features: see module-status.md" — the convention is stated once in `_bower/framework-reference.md` and a per-entry pointer is noise. If deleting the clause leaves a stub sentence or dangling punctuation, repair the prose.
5. If any module has an architecture entry but no `module-status.md`, or a `module-status.md` with no `## Build order`, that is a separate pre-existing defect — report it rather than fixing it here, since creating a build order requires design input.

Report to the operator: which entries were edited, and every name from step 3 that required a decision along with the decision taken.

**Part B — remove any module description that accumulated in `module-status.md`.**

1. For each module under `docs/modules/`, read its `module-status.md`. The valid shape is a `## Module integration` section (`Test:` and `Notes:` lines) and a `## Build order` section, plus the optional pull-forward annotations on build-order entries. Look for anything beyond that which reads as a *description or purpose statement* for the module — a leading sentence or paragraph before the first heading, a `## Purpose` / `## Overview` / `## Description` section, or a `Purpose:` line.
2. If there is none, this module needs nothing. This is the expected outcome for projects that followed the schema.
3. If there is one, compare it with the module's purpose line in `docs/architecture.md` `## Software architecture` (Part A step 1 already located that section):
   - **Says the same thing** — delete it from `module-status.md`. `architecture.md` is the home.
   - **Says something `architecture.md` does not** — the `module-status.md` copy is carrying real information. Move the substance into the architecture entry's purpose line (condensing to one line; if it is genuinely about what the boundary test asserts rather than what the module is for, it belongs in the `## Module integration` `Notes:` line instead), then delete it from `module-status.md`. Show the operator the before/after of the architecture entry.
   - **No architecture entry exists for this module** — do not delete anything. Report it; this is the same gap Part A step 5 covers.
4. Do not add a description to any `module-status.md` that lacks one, and do not otherwise reformat these files.

Then run `/b-index` so `docs/index.md`'s module descriptions are regenerated from `architecture.md`. Report which `module-status.md` files were trimmed and any purpose text that was moved rather than deleted.

**Part C — convert doc links to the repo-root form.** Mechanical.

1. Find every relative markdown link target in `docs/` — a target that starts with neither `/`, `#`, nor a URL scheme (`http:`, `https:`, `mailto:`). Both `../` forms and bare same-directory forms (`architecture.md`, `adr/index.md`) count. A grep such as `grep -rnE '\]\([^/#][^)]*\)' docs/ --include='*.md'` finds candidates; it will also match URL schemes, so filter those out by eye.
2. Rewrite each to the repo-root form: the path the target resolves to from the repository root, with a leading `/`. A link to `architecture.md` from `docs/index.md` becomes `/docs/architecture.md`; a link to `../../adr/0007-caching.md` from `docs/modules/search/ranking/plan.md` becomes `/docs/adr/0007-caching.md`. **Resolve each target against the file it lives in** — do not pattern-match the filename, because the same basename can appear in more than one directory.
3. If a target does not resolve to an existing file, do not invent a path. Leave it and report it — a relative link that was already broken is a separate finding, and rewriting it would only hide the breakage.
4. Anchors within a target are preserved: `../scope.md#success-criteria` becomes `/docs/scope.md#success-criteria`. A bare `#anchor` target is already conformant — leave it.
5. Leave links inside `_bower/` alone. Those are framework files, refreshed by the scaffold rather than maintained by the project.

Report the count of links rewritten and any unresolvable targets from step 3.

---

## v0.25 — 2026-07-28

### Changelog split at v0.20; `/b-upgrade` reads one section at a time

`_bower/changes.md` had reached 713 lines / 122 KB, two thirds of it entries for a framework that no longer has that shape. Two costs, both real. Every scaffolded project carried the whole file. And `/b-upgrade` read it *whole* — Step 3 pulled the entire file into context just to enumerate the `## vX.Y` headings, then Step 6a re-opened it once per migration step, so a three-step upgrade paid for 122 KB four times over and left every migration's notes sitting in context while a different migration was being applied.

The split point is v0.20 (2026-07-17), chosen on two independent signals: it is the only substantial date gap in the log (v0.19 landed 2026-06-03), and it is the release that established the current architecture — delegated implementation via `bower-implementer`, the slim `framework.md` router with `framework-reference.md` behind it, and ADR applicability metadata. Entries below it describe surfaces that have since been replaced.

**What changed**

- **`docs/changes-archive.md` is new** and holds v0.8–v0.19 **verbatim** — cut and pasted, not reworded or compacted, so no historical migration note has been altered. It lives under `docs/` in the framework repo, which the scaffold does not copy, so projects stop carrying 80 KB they never read. It remains reachable to `/b-upgrade`, which clones the framework repo anyway. It carries its own version index above the entries.
- **`_bower/changes.md` keeps v0.20 and above.** The split removed 431 lines / 79 KB, taking the file from 713 lines / 122 KB to 301 lines / 47 KB including this entry. It gains a **`## Version index`** table at the top: version, date, one-line summary, and the class of project-side migration work each required (*none* / *mechanical* / *judgement*). The index covers the current era only; the archive indexes its own. A closing `## Earlier versions` section points at the archive.
- **`.claude/commands/b-upgrade.md` no longer reads the changelog whole.** Step 3 enumerates headings with `grep -n '^## v[0-9]'` and keeps the line numbers; a new fifth item in Step 3 greps the archive's headings too and records which file carries each step, stopping outright if a step version appears in neither. Step 6a reads exactly one version's line range with `offset`/`limit`, from the project's `changes.md` for v0.20+ or from `<clone>/docs/changes-archive.md` for older steps. This is the durable part of the change: with per-section reads, the changelog's total size no longer bounds an upgrade, whatever it grows to next.
- **`scripts/release.sh`** heading regex tightened from `^## v` to `^## v[0-9]`, so the new `## Version index` heading can never be mistaken for a version boundary when extracting release notes.
- **`CLAUDE.md`** gains an *Archiving old changelog entries* section (when to cut again, and the verbatim-move rule) and a four-place version-bump checklist — `_bower/VERSION`, `_bower/framework.md`, `README.md`, and the changelog heading. The README string had in fact gone stale in this very change before being caught, which is why it is now written down.
- **`_bower/roadmap.md`** records a 1.0-gated successor shape: migrations as per-version files under `docs/migrations/` behind an index, which would retire the line-number bookkeeping this version introduces.

**Why archive rather than compact**

Compacting old entries would mean rewriting migration notes whose whole value is being the exact instructions a past upgrade followed. A project on v0.14 upgrading today needs v0.15's notes as written, not a summary of them. Splitting costs nothing in fidelity; compaction risks silently changing what an upgrade does. The framework's own migration-notes discipline ("self-contained, written for a model audience") applies to the archived notes too, and paraphrasing is the fastest way to break it.

### Migration

None — no project-side changes required.

The next scaffold (or `/b-upgrade`) replaces the project's `_bower/changes.md` with the shorter current-era file and refreshes `.claude/commands/b-upgrade.md`. Nothing under `docs/` changes, no project file needs editing, and no history is lost — pre-v0.20 entries are verbatim in `docs/changes-archive.md` in the framework repo, indexed there and pointed to from the tail of `_bower/changes.md`. A project upgrading *from* a pre-v0.20 version is unaffected: the refreshed `/b-upgrade` reads archived migration notes from its clone of the framework repo.

---

## v0.24 — 2026-07-28

### Success criteria stop carrying status — scope states the boundary, modules track the work

Observed on a real project: `docs/scope.md` held a success-criteria table with a status column, and an agent reading it found all ten criteria marked *paused* when seven were in fact complete. The stored status was not merely stale — it had never been maintained, and its vocabulary was borrowed from a doc it had nothing to do with.

Two distinct defects, and both are structural rather than a one-off agent error.

**1. State with no wholesale writer.** Four commands patched criteria status — `/b-feature` step 8, `/b-module` step 11, `/b-integration`, `/b-ui` — and every one of them was *conditional* and *local*: each saw only its own change and asked "did I close a criterion?" Nothing ever read the whole set and reconciled it against module state. Write-rarely plus never-audited guarantees drift. Compare `status.md`, which stays honest precisely because `/b-feature` rewrites it from scratch every reconcile, and the index files, which stay honest because `/b-index` recomputes their derived rows. And this particular drift was load-bearing: `scope.md` sits on the orientation read-path of `/b-feature`, `/b-module`, `/b-integration`, `bower-analyst`, and `/b-recap`, so a criterion wrongly reading unmet makes an agent plan work that already exists, and one wrongly reading met hides work.

**2. An undefined state vocabulary invited a leak.** The framework said criteria carried "met/unmet state" and never defined the values. Given a status column with no defined domain, drafting agents reached for the one marker set they did have — the build-order markers — and wrote `⏸ planned`. A criterion cannot be paused: build progress is a property of features and modules, not of a statement about the world. The category error was available because the framework left the field's domain open.

**The fix is to derive, not to maintain.** A criterion is met exactly when the work that delivers it is done, and that work's state already lives under `docs/modules/` under full-rewrite discipline. So `scope.md` now states each criterion followed by a `*Delivered by: <module>[, <module>]*` clause and **no status field of any kind**; `/b-recap` derives satisfaction at read time (all features ✓ **and** the `## Module integration` marker ✓ for every named module) and reports `N of M satisfied` with the blocking modules for the rest.

**The pointer stops at the module, deliberately.** It does not name features or components. Work drifts between features as dependencies resolve live — that is normal and healthy — and a criterion pinned to a feature would need re-pointing every time scope moved between siblings, reintroducing exactly the maintenance burden this change removes. Scope says what must be true and who owns making it true; the module tree owns how.

**Withdrawn criteria are deleted, not annotated.** `scope.md` is present-state: it describes the boundary of what is being built now. History lives in `problem-space.md`, ADRs, and git. A struck-through criterion with a withdrawal note is history wearing scope's clothes.

**What changed**

- **`_bower/framework-reference.md`** — new `## scope.md — Boundary, Not Tracker` section: the three-section shape, the criterion + `Delivered by:` form with a worked example, the explicit no-status-column rule, why the pointer stops at the module, and the general rule the change follows — *state has exactly one home, and a document may only hold state that some command rewrites wholesale.*
- **`_bower/framework.md`** — the *Current boundary* navigation line now carries the rule in the always-loaded router, since ad-hoc work outside `/b-*` commands is where a status column would otherwise be reinvented. The *What to Update When* table's `Scope shift / criterion closed` row is renamed to `Scope boundary shift (incl. criterion added/deleted/reworded/re-pointed)` — "criterion closed" is no longer a `scope.md` write reason.
- **`_bower/brief-schema.md`** — the Stage 1 guidance no longer offers "close a success criterion" as a scope edit; briefs may propose boundary edits (scope, non-goals, criterion add/remove/reword/re-point) but never marking a criterion met.
- **`_bower/rationale.md`** — *Scope as Current State* revised; new *State Has One Home* subsection recording both the wholesale-writer rule and the undefined-vocabulary-invites-a-leak lesson.
- **`.claude/commands/b-design.md`** — Stage 1 drafts criteria with `Delivered by:` clauses and no status. Stage 3 gains a cross-stage rule: once modules are named, every criterion must point at an existing one; backfill clauses Stage 1 left open, re-point any the stage renamed or dissolved, and surface an unowned criterion at the gate rather than inventing a pointer. Stage 3's write set now includes those `scope.md` clauses.
- **`.claude/commands/b-recap.md`** — new derived **Success criteria** section, an output-shape block for it, and a completion rule that refuses `(none — project complete)` while any criterion is unresolvable. Handles three edge cases explicitly: a criterion with no clause (underivable — report, never infer a module from the wording), a clause naming a module that no longer exists (stale pointer), and the adoption phase (as-built `🚧` is not ✓, so criteria correctly read outstanding).
- **`.claude/commands/b-feature.md`, `b-module.md`, `b-integration.md`, `b-ui.md`** — the four "update `scope.md` if a criterion is met" instructions are gone. Each now writes `scope.md` only when the *boundary* moves: scope changed, a non-goal changed, or a criterion added, deleted, reworded, or re-pointed. Orientation reads are re-scoped to match. The `b-module`/`b-integration` handoff option `(none — all modules ✓ and scope criteria met)` becomes `(none — all modules ✓; project completion is /b-recap's call, which derives success-criteria satisfaction)` — neither command derives criteria, so neither may claim them met.
- **`.claude/commands/b-adopt.md`** — reconstructed criteria get `Delivered by:` clauses from the modules reconstructed in the prior step and no status field; the `scope.md` schema-compatibility test for the required-anchor gate is updated to match.

**Why not just fix the write path**

Making every command recompute the full criteria table on every reconcile was the alternative. It costs a full module-tree read on changes that have nothing to do with scope, and it still leaves the same fact stored in two places and able to disagree. Deriving in the one command whose whole job is orientation costs nothing extra — `/b-recap` already reads every `module-status.md`.

### Migration

Two steps. The first is mechanical. The second is judgement-required and should be done with the user in the room, because it involves deleting content from a co-authored doc and inferring ownership the old file did not record.

**1. Re-scaffold.** Run the scaffold script over the project to pick up the updated `_bower/framework.md`, `_bower/framework-reference.md`, `_bower/rationale.md`, `_bower/brief-schema.md`, `.claude/commands/b-design.md`, `.claude/commands/b-recap.md`, `.claude/commands/b-feature.md`, `.claude/commands/b-module.md`, `.claude/commands/b-integration.md`, `.claude/commands/b-ui.md`, and `.claude/commands/b-adopt.md`. No project content is touched by this step.

**2. Convert `docs/scope.md`'s success criteria — judgement required.**

If the project has no `docs/scope.md`, or it has no success-criteria section, there is nothing to do — skip to the end.

Read `docs/scope.md`. Locate the success-criteria section, in whatever form it takes — commonly a table with a Status or State column, sometimes a bulleted list with `✓`/`⏸` markers or "met"/"unmet" annotations.

**Do not read the existing status values as evidence of anything.** They are the defect this version removes; on the project that prompted the change, seven of ten were wrong. Do not carry them forward, do not use them to decide which criteria to keep, and do not use them to cross-check your work in the next step.

Then, for each criterion:

- **Determine the responsible module(s).** List the directories under `docs/modules/`. For each criterion, read enough to decide which module owns making it true: each module's `module-status.md` (its `## Module integration` notes and `## Build order` name the features it contains) and, where the module's purpose is not obvious from that, the `## Software architecture` section of `docs/architecture.md`, which states each module's purpose and data-concern boundary in one place. Most criteria map to one module; some genuinely span two or three, and listing several is correct — list every module whose completion the criterion depends on, since `/b-recap` requires all of them to be complete before it reports the criterion satisfied. **Do not name features or components** — the pointer stops at the module by design.
- **If no module delivers it**, do not guess. Collect these and raise them with the user at the end (see below).

Rewrite the section in the new form: each criterion as a statement of what must be true, followed on the next line by an italic `*Delivered by: <module>[, <module>]*` clause. Drop the Status column, the markers, and any met/unmet annotation entirely. If the criteria were a table, a bulleted list is usually the better target form, since a table with one content column is just a list. For example:

```markdown
## Success criteria

- Ingested documents are searchable within 60 seconds of upload.
  *Delivered by: ingest, search*
- An operator can reconstruct why any given record was rejected.
  *Delivered by: audit*
```

Leave the `## Current scope` and `## Non-goals` sections alone; this migration touches only the criteria.

**Then bring the user one list before writing anything**, since this is a co-authored doc and the mapping is inferred:

- The proposed `Delivered by:` clause for each criterion, with a few words on why that module. Flag any you were unsure about.
- Any criterion **no module delivers**. Each is one of three things and the user decides which: the criterion is genuinely abandoned and should be **deleted** (scope is present-state — delete it outright, do not strike it through or annotate it as withdrawn); a module is **missing** from the design, which is a real finding and probably wants `/b-design`; or the criterion is worded at the wrong level and should be **reworded** to something a module can own.
- Any criterion the user wants deleted for other reasons — this is a natural moment to ask whether the stated criteria still reflect what the project is trying to be.

Write the file only after the user confirms. Then run `/b-recap` and check the new **Success criteria** line against the user's own sense of where the project is: this migration's whole purpose is that the derived number is trustworthy, so a surprising count means either a `Delivered by:` clause is pointing at the wrong module or a module's status markers are themselves stale — worth resolving now rather than discovering later.

## v0.23 — 2026-07-27

### Constitution truthfulness — normative shape, flag-don't-fix, consent gate

Observed on a real project: `docs/constitution.md` claimed something existed when it was in fact an aspiration, and agents downstream became confused about what was real. The framework's only protection for that file is **ownership** — human-owned, never rewrite unprompted — which guards against unauthorised edits and says nothing about accuracy. The two are close to opposites here: the stronger the "don't touch" norm, the longer a false claim survives, because every agent that notices it has been told to leave it alone. Ownership protects the file from agents; nothing protected it from decay.

Two distinct defects were tangled in "human-owned", and they get different fixes.

**1. The doc shape (prevention).** A constitution is *normative* — rules the project has committed to. A rule can be unmet, but it cannot be false; an unmet rule surfaces as work. The failure was a *descriptive* claim smuggled into a normative doc, written in the same register as a rule, so it read as fact. `_bower/framework-reference.md` gains a **`## constitution.md — Normative Shape`** section: every statement about what exists must be verifiable from the repo or it does not go in the normative body, and aspirations live under a **`## Not yet in force`** heading whose contents agents must treat as non-existent. This is a shape rule, not a full template — headings otherwise stay the project's business.

**2. Ownership vs. truth (detection).** The framework already has exactly the right pattern one paragraph away, for ADRs: *code is truth, ADR is hypothesis — flag and supersede, don't silently trust.* ADR bodies are immutable and it works, because flagging is decoupled from editing. There was no equivalent for human-owned docs, so "never rewrite unprompted" collapsed into "never mention." `_bower/framework.md` and `framework-reference.md` now state the missing half: **ownership governs edits, not truth.** Never silently obey a false claim, never silently fix it — quote it verbatim with `file:line`, show the contradicting evidence, and ask.

**No freshness gate.** A periodic constitution sweep was considered and rejected: it has no natural trigger and degrades into nagging. Instead the check sits where the constitution is *already read for a purpose*, so it is free and contextual.

**What changed**

- **`_bower/framework.md`** — an *ownership governs edits, not truth* paragraph under Document Authority, with the verbatim-quote-and-ask protocol and a pointer to the normative shape.
- **`_bower/framework-reference.md`** — the ownership-semantics section gains the flag-don't-fix duty, the required surfacing shape, and an explicit **coverage is opportunistic, not an audit** caveat; plus the new `## constitution.md — Normative Shape` section.
- **`.claude/agents/bower-implementer.md`** — the strongest detection point in the framework: it reads the constitution's testing section and then *actually runs the thing*, so it discovers empirically when a stated runner, fixture, CI step, or `✓` rule is false. New behavioural rule (work around it, don't edit it, report it), `docs/constitution.md` added to the barred write surface, a new `## Constitution contradictions` report section, and a failure mode for silently routing around a false convention. A contradiction is not a divergence and does not change the outcome.
- **`.claude/agents/bower-reviewer.md` + `_bower/review-schema.md`** — the reviewer judges coverage and status honesty *against* the constitution, which is precisely where a false yardstick does most damage: every finding measured against it inherits the error. New `## Constitution contradictions` report section, deliberately **outside the six dimensions and outside the resolution-class machinery**, carrying a `Bearing:` line naming which findings leaned on the claim. Bounded to what the module survey actually contradicted — not an audit.
- **`.claude/commands/b-feature.md`** — a **Constitution reconciliation** block in Step 5, before Step 6 and never inside it (Step 6 is gate-free agent-owned doc maintenance; a human-owned doc must not ride that path). Prints the verbatim quote and line number, then asks: correct · move to `## Not yet in force` · leave alone.
- **`.claude/commands/b-review.md`** — a **Gate: Constitution consent**, separate from the triage gate, that runs even when triage was cancelled or every dimension came back clean. Contradictions never enter `review-plan.md`. If a correction moves the bar a reconciliation was judged against, that item is re-confirmed.
- **`.claude/commands/b-adopt.md`** — the initial constitution is drafted only from conventions confirmed in the repo, with inferred-but-unconfirmed practice placed under `## Not yet in force`. Explicitly distinguished from the adoption ledger, which has different exits.
- **`_bower/roadmap.md`** — the *Constitution template and archive rules* item records its trigger as fired for the constitution half; the full heading schema and the `_bower/archive/` rules stay deferred.

**Why this shape**

Prevention matters more than detection here, and the framework should not overclaim otherwise. Nothing audits the constitution as a whole: a claim no agent executes — a deployment convention, a review process, "all endpoints are rate-limited" — is caught by nobody. The detection hooks are an opportunistic backstop at two points that already read the file; the normative/aspirational split is what stops the false claim being written in the form that fooled everyone. Describing the backstop as a truthfulness guarantee would reproduce the exact bug it guards against.

The consent gate requires a **verbatim quote with a line number**, not a summary, because the objective is to get the human to open the file. A paraphrase invites a rubber-stamp; the human owns the doc and must see what is being proposed against it. Only an explicit instruction to change it makes the edit *prompted*, which ownership already permits.

This is the same disease Bower treated once before at the marker level: v0.15's floor-not-sum rule exists to make the verified-for-`✓` bar "observable rather than aspirational", and `/b-adopt` already refuses to mark found code `✓` because that would be a false completeness claim. Same failure, a different document.

### Migration

Two steps. The first is mechanical; the second requires judgement and should be done with the user in the room.

**1. Re-scaffold.** Run the scaffold script over the project to pick up the updated `_bower/framework.md`, `_bower/framework-reference.md`, `_bower/review-schema.md`, `.claude/agents/bower-implementer.md`, `.claude/agents/bower-reviewer.md`, `.claude/commands/b-feature.md`, `.claude/commands/b-review.md`, and `.claude/commands/b-adopt.md`. No project content is touched by this step.

**2. Audit `docs/constitution.md` against the repo — judgement required, and the user decides every edit.** This file is human-owned. Do not rewrite it unprompted, including as part of this migration: propose, then ask.

If the project has no `docs/constitution.md`, there is nothing to do — skip to the end.

Read `docs/constitution.md` in full. For each statement, classify it:

- **Normative** — a rule the project has committed to ("tests live in `tests/`", "run `pytest -q`", "`✓` requires the module integration test to pass"). Leave it alone. Rules can be unmet; that is not a defect in the doc.
- **Descriptive** — a claim about what *exists* or what is *currently true* ("CI runs the integration suite on every PR", "every module has contract tests", "all endpoints are rate-limited", "the staging environment mirrors production"). These are the risk. For each one, try to verify it against the repo: does the named workflow file, config, test directory, script, or dependency actually exist, and does it actually do what the claim says? Cite the path and line you checked.

Then bring the user a single list with three columns of your own conclusion — *verified* (evidence cited), *false* (evidence cited showing otherwise), *cannot verify from the repo* (say why: it concerns infrastructure, an external service, or team process that leaves no trace in the code). Quote each claim verbatim with its `docs/constitution.md:NN` so they can read it in place.

For the *false* and *cannot verify* items, propose one of three dispositions per item and let the user choose each:

- **Rewrite normatively** — turn the description into the rule it was trying to be. "CI runs the integration suite on every PR" becomes "the integration suite must pass before merge". A rule that is not yet honoured is visible as work; a false description is a phantom guarantee.
- **Move to `## Not yet in force`** — it was an aspiration. Create the section at the end of the file if it does not exist, with this preamble:

  ```markdown
  ## Not yet in force

  Intended, but not true of the repo today. Agents: treat these as non-existent —
  do not rely on them, do not cite them as conventions, and do not mark work ✓ on
  the strength of them. Moving an item out of this section puts it in force.
  ```

- **Delete** — it was never true and is not wanted.

Apply only the dispositions the user confirms. A user who wants to leave a claim exactly as it stands is exercising ownership; record nothing and move on.

Expect this audit to be most productive on the testing section, since that is the part with the most repo-visible surface — and the part `bower-implementer` will otherwise trip over on the next `/b-feature`.

---

## v0.22 — 2026-07-27

### Build-order pull-forward annotation

Observed on a real project: within a module, dependencies routinely cause an earlier feature to absorb part of a later feature's scope. By the time the last component came around, most of it was already built. This is benign — it mirrors how the work falls out under human coding too — and the framework already surfaces it at orient time, so arriving at a hollow component is a cheap surprise.

The expensive case is the inverse, and it was unhandled. When an earlier feature absorbs a later one's scope **incompletely**, the later feature's `plan.md` — written at module-design time, before the absorption — still claims the full scope. That plan is then handed to `bower-implementer` in a fresh context *as the contract*, with an explicit instruction not to re-litigate the design. The result is work done twice, or done a second way.

A survey of the observed project found the asymmetry precisely: *deferrals* get recorded (an earlier feature's `plan.md` non-goals name what it is leaving for feature 7), and *absorptions* get recorded retrospectively by the arriving feature's `status.md` — but nothing is written at the moment of pull-forward saying "I have taken part of feature 7." Structurally, there was nowhere to write it: feature 7's `plan.md` does not exist yet when feature 3 runs. The only document spanning the whole build order is `module-status.md`, whose `## Build order` was markers-only.

**What changed**

- **`_bower/framework-reference.md`** — the `## Build order` schema gains an optional scope-reduced clause on an entry, plus a **Pull-forward annotation** paragraph: when a feature absorbs scope from a later entry, that entry is annotated with one clause naming who absorbed what and a `Remaining:` clause naming what is left. Bounded to one line, because `module-status.md`'s ~250-word budget is shared with the integration notes. If the absorption leaves nothing to build, the entry stays ⏸ with `Remaining: none — verify and close via /b-feature <name>`; it is **not** promoted to ✓ on another feature's passing criteria, since ✓ means *this* feature's agreed criteria were verified.
- **`.claude/agents/bower-implementer.md`** — `## Doc implications` in the report template now includes downstream build-order scope absorbed, and a new failure mode names silent absorption. The implementer already receives `module-status.md` as orientation, so it can see the later entry; it is correctly barred from writing it, so the report is the channel. It is the only party that knows.
- **`.claude/commands/b-feature.md`** — Step 9 gains the authority to annotate a downstream entry when the report's `## Doc implications` names one (previously reconcile could only touch its own entry's marker). Step 1 gains the read side: a scope-reduced annotation on the target feature's entry **wins over its `plan.md`**, and the shrunk scope is surfaced in the Step 2 proposal so the operator sees the change.
- **`.claude/commands/b-module.md`** — the same annotation duty at per-feature completion, so both commands that write build order honour the schema.

**Why this shape**

The annotation lands on the build-order line rather than in the downstream `plan.md` because that plan usually does not exist yet, and because the build-order line is already in the next pass's orientation set — the note is read where it is needed without anyone having to look for it. A dedicated reconciliation pass was considered and rejected: it would re-litigate module design at every feature, which is `/b-review`'s job, once, at the end. Cross-*module* composition drift (a feature that ended up in a different module than designed) is a distinct problem and is not addressed here.

### Migration

Two steps. The first is mechanical; the second requires reading project content and exercising judgement — note in the `/b-upgrade` self-assessment which modules you inspected and what you concluded.

**1. No schema rewrite needed.** The annotation is additive and optional. Existing `module-status.md` `## Build order` sections are already valid — an entry with no annotation means no scope has moved. Do not add annotations to entries where nothing moved.

**2. Backfill mid-build modules only.** For each module under `docs/modules/`, read `module-status.md` `## Build order`. Skip the module unless it has **both** at least one ✓ or 🚧 entry **and** at least one ⏸ entry — a fully-built module gains nothing from the annotation (the plans are already reconciled and no future pass will read it), and an untouched module cannot have drifted yet. For each qualifying module:

   - For each ⏸ entry, read that feature's `plan.md` if one exists (many will not — plans are created at plan time, so an unbuilt feature usually has none). Where there is no `plan.md`, use the module's `## Module integration` `Notes:` and the completed features' plans to understand what that entry was meant to cover.
   - Determine whether part of that scope **already exists in the code**, landed by an earlier feature. The completed features' `plan.md` files and `status.md` files are the best evidence — a `status.md` noting that a mechanism "already existed" from an earlier feature is a direct signal. Grep the source for the capability rather than trusting the docs alone.
   - If part of it exists, append one clause to that ⏸ entry in this exact form:

     ```
     7. framing-probe-personas — ⏸ (scope reduced by feature 3: persona receives
        framing per ADR-0014; and feature 5: framing-target annotations.
        Remaining: the curated catalogue definitions.)
     ```

     Name the absorbing feature(s) and what landed, then `Remaining:` and what is genuinely left. Keep it to one line's worth of prose; the file's budget is ~250 words total including the integration notes.
   - If nothing of it exists, leave the entry exactly as it is.
   - Do **not** edit the ⏸ feature's `plan.md`, and do **not** change any marker. If a backfill reveals that an ⏸ entry has *nothing* left to build, write `Remaining: none — verify and close via /b-feature <name>` and leave the marker ⏸. Promoting it to ✓ would claim criteria that were never verified.

If a backfill turns up something that looks like a module-boundary problem rather than intra-module pull-forward (scope that landed in a *different module* than designed), do not annotate it — record it and surface `Run /b-review <module>` in the upgrade handoff.

---

## v0.21 — 2026-07-22

### `/b-adopt` — brownfield cold-start (v1, pending real-project validation)

Bower previously had no story for adopting an existing codebase. Adopting an SDD framework is non-trivial because it requires rebuilding the design rationale from the existing code. This release adds `/b-adopt` to fill that gap.

**What changed**

- **New command `.claude/commands/b-adopt.md`.** Reconstructs an orienting `docs/` skeleton — `scope.md`, `design/problem-space.md`, `architecture.md` (both views), an initial `constitution.md` from observed conventions, and `module-status.md` placeholders for inferred module boundaries — *from the code as it is*. The heavy read-only repo survey is delegated to a subagent (`general-purpose`/`Explore`) to keep it out of the command's context, with an inline fallback. Content is gated in groups like `/b-design`. Writes are confined to `docs/` and `docs/index.md`: adoption never touches source, tests, or build files.
- **User-facing adoption guide + prep nudge.** `README.md` gains an "Adopting an existing project" section covering the one high-leverage prep step — staging existing design docs, briefs, and decision rationale in `docs/reference/` before running, so they become *cited* framing rather than hedged inference — plus what the agent surveys, what it asks, and how the adoption phase drains. `/b-adopt` reinforces it in-flow: when the survey finds no reference material, it nudges (non-blocking) at the framing gate that staging some and re-running would improve attribution.
- **As-built markers, never `✓`.** The same honesty rule extends to status markers: adoption has no recorded acceptance criteria and runs no verification, so it marks observed features `🚧` (as-built, unverified) — never `✓`, which would be a false completeness claim. No per-feature `status.md` is written; `/b-index` reads the build-order marker for adopted features and never promotes code-presence to `✓`. Reuses the existing `🚧` rather than minting an adoption-only marker, so the framework's status vocabulary is untouched.
- **The adoption ledger and phase.** The governing design decision: code tells you *what*, never *why*, so `/b-adopt` never guesses intent. Cross-cutting choices it cannot attribute to a decision go into `docs/adoption-ledger.md` as one-line open questions (`<location> · <question>`, no stored context) rather than being written up as confident ADRs or architecture claims. The ledger is a worklist that **shrinks monotonically**: each item is drained by one of three exits, all of which delete the line — *resolve* (the choice stays; capture intent as an ADR via `/b-adr`), *remediate* (the choice was accidental/wrong; fix it via `/b-feature` or `/b-design`), or *dismiss* (deliberate/accepted, no record). The remediate exit is where adoption's *renewal* happens — through the normal gated flow, not inside adoption. When empty, the phase ends.
- **The flag is a banner in `docs/index.md`.** Its presence *is* the adoption-phase flag — `docs/index.md` is already read every session, so this carries **zero standing cost for greenfield projects** (they simply never have the banner) and the ledger is fetched only when the banner points to it. `.claude/commands/b-index.md` gains a rule to preserve the `🌱 Adoption in progress` banner across regeneration (curated structure, removed only by hand when the ledger empties).
- **`/b-recap` is adoption-aware.** `.claude/commands/b-recap.md` now detects the banner and reads a `🚧` feature with no `status.md` as *adopted-but-unverified* (as-built from existing code) rather than *in progress* — a fresh adoption would otherwise report every feature as underway with no state to summarise, and recommend building on code that already exists. In the adoption phase it reports the phase and open-ledger count, lists as-built features under a distinct *Adopted (unverified)* section, and recommends draining the ledger as the next move rather than `/b-feature`.
- **On-demand mechanics documented.** `_bower/framework-reference.md` gains an **Adoption phase** section (flag, ledger, drain paths, exit condition) — loaded on demand, not in the always-loaded router. `_bower/framework.md` gains one router line registering the command under Maintenance. `_bower/roadmap.md`'s brownfield item moves from "Ready to schedule" back to deferred with a validation trigger.

**Why**

Adoption inverts Bower's normal direction (docs drive code); the risk is manufacturing confident fiction — inferred docs that every later `/b-*` invocation then trusts. The design concentrates all adoption-specific honesty into one banner + one monotonically-shrinking ledger, both of which evaporate when the phase ends, so greenfield performance is untouched and the "provisional" caveat is unmissable while it matters. Renewal (undoing choices that were mistakes) is deliberately *not* bundled into adoption — you cannot critique against a baseline that does not yet exist — and instead emerges through the normal flow as ledger items drain. This is a v1 shipped to be tried on a real project and reported back on; the report is expected to reshape it.

### Migration

None — no project-side changes required. `/b-adopt` is a new command for cold-starting a brownfield codebase; projects already designed with Bower never invoke it, and the new `framework-reference.md` "Adoption phase" section plus the `b-index.md` banner-preservation rule are additive (they take effect only in a project that runs `/b-adopt`). Existing `docs/` shapes, ADRs, and index files are unchanged. The scaffold refresh (`/b-upgrade`) delivers the new command and reference text; nothing else moves.

---

## v0.20 — 2026-07-17

### Context economy: delegated implementation, selective orientation, ADR applicability, a slim framework import

This release responds to a context-consumption review of a real Bower project, where `/b-feature` sessions regularly reached 250–300k context tokens. The dominant cause was workflow packaging — orientation, proposal, implementation mechanics, and reconciliation accumulating in one context — with secondary costs from unbatched tool use, whole-file architecture reads, over-broad ADR loading, and a 307-line framework import in every session.

**What changed**

- **New subagent `.claude/agents/bower-implementer.md` — `/b-feature` implementation is delegated.** After the gate and the Step 3 `plan.md` write, a fresh implementer receives a curated packet (approved plan path, acceptance criteria verbatim, constraining ADR paths, architecture section names, testing conventions) and implements + tests in an isolated context, returning a fixed-section **implementation report** (`## Outcome`, `## Changed files`, `## Acceptance mapping`, `## Test run`, `## Divergences`, `## Implementation footnotes`, `## Doc implications`). The orchestrating command retains the gate, acceptance and decision reconciliation, and doc updates. The implementer is the first write-capable subagent in the set: safe by construction because it executes an already-gated plan, its write surface is bounded (source, tests, minor-divergence `plan.md` edits — never status docs, ADRs, or architecture), and every decision-needing path returns a `DIVERGED-STOPPED` report so the orchestrator can re-gate with the user. Inline implementation remains as an explicit fallback when the Agent tool is unavailable. `/b-module` deliberately stays inline; extension is a roadmap item pending real-project validation.
- **`.claude/commands/b-feature.md` Step 1 becomes a selective, batched orientation algorithm.** Section-directed `architecture.md` reads (system overview + the affected module's `## Software architecture` subsection, whole file only when the change can't be located); grep-then-open sibling plans on modify/remove; `scope.md` and `docs/ui.md` read conditionally; `constitution.md` testing detail deferred to the Step 4 packet; all independent reads batched; a closing **inputs-selected ledger** keeps omissions auditable. `/b-module` Step 1 gains the batched-reads directive.
- **ADR applicability metadata.** New ADR frontmatter fields: `scope: universal | module | integration | operational` (required for new ADRs; only `universal` loads unconditionally) and optional `topics: [<kebab-keywords>]`. A missing `modules` field now means **unclassified legacy ADR** — loaded on module, topic, or title match only, never "load for every feature." `/b-adr` drafts and audits the classification; `/b-index` renders Scope/Topics columns and surfaces unclassified counts; `/b-feature`, `/b-module`, and `bower-reviewer` select by the new semantics. Frontmatter remains mutable, so legacy ADRs can be classified without touching bodies.
- **`_bower/framework.md` cut from 307 to ~112 lines.** The always-loaded `@`-include target is now a router: identity, guards (including the architectural hard-redirect), document-authority table, status markers, what-to-update-when, out-of-band conventions, the UI path decision table, and one-line command routing. Detailed specs move to the new on-demand **`_bower/framework-reference.md`**: ownership semantics, `status.md`/`module-status.md` schemas, the full ADR spec, UI path examples and commit discipline, module review, implementation trajectory, reference-material conventions. The include target keeps its name, so no project CLAUDE.md changes.
- **Completed-plan size discipline.** `/b-feature` Step 6: a completed `plan.md` principally describes the system as it now exists — purpose, current contract, component map, integration points, testing categories; dated counts and implementation history are compressed aggressively.
- **`_bower/rationale.md`** reframes *Subagents for Isolated Analysis and Execution* — three subagents, with the implementer justified by context economy at the recovery-anchor boundary. **`_bower/roadmap.md`** marks the CLAUDE.md-tiering item realised and adds two deferred items (extend delegation to `/b-module`; index/module-status slimming with a separate `integration-plan.md`). `b-design.md`'s ADR shape description is also caught up to the v0.17 lightweight form it had missed (~150 words, two required sections — previously still said 200–600 words and four sections).

**Why**

The review's headline finding: the post-gate `plan.md` was already the crash-recovery anchor, so using it deliberately as a *context boundary* costs nothing and sheds the implementation mechanics (the dominant late-session growth) from the planning context. The remaining changes attack the pre-gate baseline: a project with 18 unclassified ADRs was loading ~65k characters of decisions for every feature, every session paid for the full framework import plus a whole-file architecture read, and unbatched read/edit/test cycles multiplied turn count. None of the framework's safeguards move: the gate, explicit acceptance criteria, ADR discipline, and living documentation are unchanged — the review judged those the valuable parts, and the delegation design routes every decision-needing path back through them.

### Migration

Two steps: a mechanical scaffold refresh, then a judgement-required ADR classification pass.

**Mechanical — refresh the framework files.** Re-run the scaffold (`/b-upgrade` does this): `.claude/agents/bower-implementer.md` and `_bower/framework-reference.md` arrive as new files; `_bower/framework.md` and the `.claude/commands/` set are replaced. No project CLAUDE.md edit is needed — the `@_bower/framework.md` include target keeps its name and simply resolves to the slimmer router. No file under `docs/` changes shape.

**Judgement-required — classify existing ADRs.** v0.20 changes ADR loading semantics: previously, an accepted ADR with no `modules` field was treated as cross-cutting and loaded for every `/b-feature` run; now such an ADR is *unclassified* and loads only when its topics or title match the change. Until classified, a genuinely universal legacy ADR (e.g. an error-handling convention) may stop being loaded automatically. To classify: for each `status: accepted` file under `docs/adr/`, read its body and add to the frontmatter a `scope:` field choosing the **narrowest true value** — `universal` (constrains every feature in the project; rare — every `/b-feature` run pays to load it), `module` (constrains the module(s) in `modules:`; add `modules:` with exact directory names under `docs/modules/` if missing), `integration` (constrains how modules interact at boundaries), or `operational` (deployment, tooling, versioning, maintenance). Optionally add `topics: [<kebab-keywords>]` where subject-matter keywords would help future changes find the ADR (e.g. `topics: [streaming, control-codes]`). Do not edit ADR bodies — frontmatter only. Superseded and deprecated ADRs may be left unclassified. When done, run `/b-index` to regenerate `docs/adr/index.md`; it will render the new Scope/Topics columns and drop the unclassified note. If uncertain how to classify a specific ADR, leave it unclassified and list it for the operator rather than guessing `universal`.

**Behavioural notes (no action required).** The first `/b-feature` run after upgrade will spawn the `bower-implementer` subagent after the gate — this is expected, and the command falls back to inline implementation (announcing it) if subagents are unavailable in the session. `docs/index.md` and `docs/adr/index.md` need no manual restructuring; the next `/b-index` run refreshes them in place per the regeneration contract.

---

## Earlier versions

v0.19 and below are archived verbatim in `docs/changes-archive.md` in the [framework repo](https://github.com/ANU-HDRH/bower-framework), which carries its own version index over those releases. They are not scaffolded into projects; `/b-upgrade` reads them from its clone when a project is upgrading from a pre-v0.20 version.
