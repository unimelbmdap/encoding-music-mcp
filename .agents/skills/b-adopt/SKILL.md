---
name: b-adopt
description: Brownfield cold-start — reconstruct an orienting docs/ skeleton from an existing codebase and open an adoption phase.
---
<!-- GENERATED FILE — do not edit. Source: skills-src/commands/b-adopt.md. Regenerate: node scripts/build-adapters.cjs -->

# Bower Adopt

You are running Bower **brownfield adoption** in a project that has an existing codebase but has never been designed with Bower. This command reconstructs an orienting `docs/` skeleton *from the code as it is*, records the decisions it cannot attribute to intent in an **adoption ledger**, and puts the project into an **adoption phase** that ends when the ledger is drained.

This is the cold-start path for a codebase Bower has never touched. It is **not** `/b-upgrade` (which refreshes an already-adopted project across framework versions) and **not** `/b-design` (which frames a *new* project from intent, forward). Adoption runs backward: it infers framing from artefacts.

The request (the user's optional argument): the request as given in the message that invoked this skill.

## The governing idea

Code tells you *what*, never *why*. Existing docs and a `references/` folder give strong but partial *why*; git history gives weak, noisy *why*; the user is the only real oracle for intent, and an expensive one. So the docs this command produces are a **faithful, honestly-hedged snapshot of the as-built system** — reality, ugliness included — not an aspiration.

The honesty lives in one place, not smeared across every doc: the **adoption ledger** (`docs/adoption-ledger.md`) is the set of cross-cutting choices found in the code that could **not** be tied to a decision. It is a worklist of open questions, and it **shrinks monotonically** — every item is eventually drained by one of three exits, each of which deletes the line: *resolve* (the choice stays; capture its intent as an ADR), *remediate* (the choice was accidental or wrong; change it via `/b-feature`, or `/b-design` if the fix is architectural), or *dismiss* (deliberate/accepted, no record warranted). When it is empty, the adoption phase ends: remove the banner from `docs/index.md`.

Do **not** manufacture ADRs during adoption. An ADR asserts a captured decision; guessing intent from code and writing it up as a decision is exactly the confident fiction adoption must avoid. Unattributed choices go in the ledger, not the decision log.

## Important behavioural rules

- **Describe reality, do not fix it.** Adoption reconstructs what exists. It does not refactor, does not "clean up questionable adoptions," does not propose changes. Anything that looks wrong becomes a ledger item, not an edit. Renewal happens *after* adoption, through the normal `/b-*` flow, when a ledger item is drained via its *remediate* exit — `/b-adopt` records the concern; `/b-feature` or `/b-design` fixes it.
- **Writes are confined to `docs/` and index — and never clobber.** This command never touches source code, tests, build files, or anything outside the documentation footprint (their code is not at risk — say so up front). Within `docs/`, it never silently overwrites a pre-existing file: every write target is stat'd in Phase 0 and resolved at a gate by its collision class (Phase 0 step 4) — required anchors preserve only when already schema-compatible, narrative/human-owned docs default to preserve, and `docs/index.md` is always an in-place update. "Creates" is only true for paths that were empty.
- **Never guess intent.** When a choice looks cross-cutting but its rationale is unknown, the honest record is "observed; intent unknown" in the ledger — not an inferred ADR and not a confident architecture claim.
- **Hedge inferred framing; the banner carries the caveat.** The orienting docs stay in normal Bower shape (no per-claim provenance tags — that would tax the docs forever for a phase that ends). The adoption banner in `docs/index.md` is the single global signal that these docs were reconstructed and are provisional.
- **Gate every content group.** Like `/b-design`, present drafted content at an operator gate (binding: `_bower/framework.md` → *Runtime bindings*) before writing. The user is the intent oracle; the gates are where you consult them.
- **Elicit lazily.** Query the user up front only for what the *top-level framing* needs to be coherent (problem space, scope boundary, module boundaries). Detail-level intent is deferred to the ledger and drained later — do not interrogate them about the whole codebase.
- **Recommend, don't dictate.** Mark one option `(recommended)` with a brief rationale; the user chooses.
- **Literal-command handoff.** The closing handoff names exact slash commands, never free prose.

## Phase 0: Preconditions

1. **Not already adopted.** If `docs/scope.md` **and** `docs/architecture.md` already exist in Bower shape, this project is already designed with Bower. Stop and redirect: `/b-feature` for a change, `/b-upgrade` to move framework versions. Do not overwrite an existing design.
2. **Framework files present.** `_bower/` and the runtime's command/agent files should already be scaffolded (that is how this command reached the project). If `_bower/framework.md` is absent, tell the user to run the scaffold script first, and stop.
3. **Instruction files reach the router.** A brownfield repo usually arrives with an `AGENTS.md` or `CLAUDE.md` of its own, and the scaffold preserves those untouched — so this is the one command that routinely runs on a project whose instruction files were never wired to Bower. Check both: `AGENTS.md` must reference `_bower/framework.md` (the directive is the whole of Codex's path to the router), and `CLAUDE.md`, if present, must carry both `@AGENTS.md` and `@_bower/framework.md`. If either is missing, stop before the survey — it is a two-line edit for the user, and it is worth stopping for because every *later* session on this project silently loads no router, gates, bindings or schemas included. Quote the exact lines to add and say which file each belongs in. Do not add them yourself: adoption writes only under `docs/`, and a project's instruction files are its own.
4. **Collision scan — before writing anything.** A brownfield repo may already carry hand-written docs at the paths adoption wants to produce. Passing the "already adopted" check in step 1 does **not** mean these paths are clear — a repo can have a hand-written `architecture.md`, a `constitution.md`, or a `README`-style design note without having both Bower anchors. Adoption must **never silently overwrite a pre-existing file.** Stat every write target up front and classify each into one of three collision classes, because "preserve" does not mean the same thing for all of them:

   **(a) Required Bower anchors — `docs/scope.md`, `docs/architecture.md`, and each `docs/modules/<module>/module-status.md`.** These have a required shape that downstream commands depend on (`architecture.md` needs both a runtime view *and* a `## Software architecture` section; `scope.md` needs scope / non-goals / success-criteria, the criteria carrying `Delivered by:` module clauses and no status field; `module-status.md` needs `## Module integration` + `## Build order` + `## Module review`). On collision, offer **preserve _only if the existing file is already schema-compatible_** (it already carries the required shape — e.g. the project was partly hand-set-up). If it is **not** schema-compatible (a non-Bower file that merely occupies the path), do **not** offer preserve: the choices are **merge** (fold the required shape in around the existing content, shown for confirmation) or **abort**. Adoption may not report completion with a required anchor lacking its shape — a preserved non-Bower `architecture.md` would leave `/b-feature`, `/b-recap`, etc. without the structure they read.

   **(b) Narrative / human-owned — `docs/design/problem-space.md`, `docs/constitution.md`.** No rigid downstream-required structure, and human-owned by ownership rules. On collision, **preserve** is always valid and is the default — a pre-existing one is exactly the human intent adoption should defer to. (Offer merge/abort too, but do not force merge for want of a schema.)

   **(c) `docs/index.md` — not a preserve/merge/abort target at all.** Phase 5 must write the banner (when N ≥ 1) and regenerate derived state, so it can never be "left untouched." Treat an existing `index.md` as an **in-place curated update** per the `/b-index` regeneration contract (refresh derived state, preserve curated structure) — never as a skippable collision. `docs/adoption-ledger.md`, if it already exists, means a prior adoption is unfinished: stop and tell the user to finish or delete the existing ledger rather than starting over (re-running adoption is not a v1 operation).

   For classes (a) and (b): at each content gate, present the collision explicitly with only the options that class allows; there is no silent-overwrite path anywhere. Default to *preserve* wherever preserve is offered — an existing hand-written doc is human intent, which outranks anything adoption infers.
5. **Working tree.** Adoption creates and (on collision, only with consent) edits files under `docs/`. `git reset`/untracked-file cleanup is a safe undo **only from a clean baseline** — on a dirty tree it would destroy the user's uncommitted work, so it is *not* a valid recovery here. Recommend the user commit or stash first so the adoption is trivially reversible; if they decline, proceed but tell them plainly that the built-in undo is off the table and they own reverting adoption's writes by hand.

## Phase 1: Survey (delegated)

The repo survey is large and read-only — exactly the shape that belongs in an isolated context. **Delegate the survey to a read-only general-purpose subagent** if the runtime offers one (binding: `_bower/framework.md` → *Runtime bindings*) and have it return a **structured inventory**, so the heavy reading does not accumulate in this command's context. If the runtime cannot delegate, do the survey inline and say so in one line.

The survey subagent's brief:

- **Existing documentation.** Read `README.md`, anything under `docs/`, `CONTRIBUTING`, design notes, `ARCHITECTURE`-style files. These are the strongest *why* signal — capture what they assert.
- **Reference material.** Detect a `references/` (or `docs/reference/`) folder if present — vendored specs, briefs, prior design docs the operator staged. Treat as high-value cited signal. **Record whether any was found** — its absence drives a nudge at the framing gate (Phase 3).
- **Structure and stack.** Map the directory layout, package manifests (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, …), and any DB schema / migrations. From these, **propose** module / data-concern boundaries per the constitution's module rubric (a module is a set of features sharing data concerns). Boundaries are the highest-value, highest-error output — the subagent proposes; the user corrects at the Phase 3 gate.
- **Observed conventions.** Test runner and layout, lint/format config, CI — the raw material for an initial `constitution.md`.
- **Cross-cutting choices with unclear rationale.** Candidate ledger items: choices that appear to constrain more than one feature and whose *why* is not evident from code or docs (e.g. "auth tokens persisted in DB, not cache," "retry logic hand-rolled rather than using the queue").

The inventory comes back as structured sections (existing-docs summary, reference material, proposed modules with boundary rationale, stack, observed conventions, candidate ledger items). This command consumes it; it does not re-read the whole repo.

## Phase 2: Git signal detection (message-only, then offer)

Git history *can* carry decision rationale — but reading diffs/code-along-the-way is catastrophically expensive, and terse human commits carry almost no signal while agent-assisted commits carry a lot. So **detect before you spend**, and never read diffs.

1. **Cheap sampling pass, messages only.** `git log --format='%H%x09%an%x09%s%x09%b' -n 200` (messages and trailers only — **no** `-p`, no diffs). Score signal density from:
   - `Co-Authored-By:` trailers (agent involvement — strong marker)
   - consistent conventional-commit prefixes (`feat:`/`fix:`/`docs:`)
   - structured multi-line bodies with rationale prose vs. terse one-liners (`wip`, `fix stuff`)
2. **Decide and offer.**
   - **Signal-rich** → offer the full message-only pass at an operator gate, with an honest cost estimate ("~N commits, messages only, roughly M tokens") and what it buys (decision-shaped commit bodies feeding ledger attribution and architecture notes). Still message-only — the rationale in an agent commit lives in the message, not the diff.
   - **Signal-poor** → skip and say so: "History reads as terse human commits — low yield, skipping the git pass." Do not spend on it.
3. **Where recovered rationale goes.** If the pass runs, some candidate ledger items become *provisionally attributable* — a commit body appears to explain the *why*. Attribution is what can keep a choice **off** the ledger (the ledger is the *un*attributed set), but it is only ever a **proposal until the operator accepts it** at the Phase 3 architecture gate: a commit body can be stale, superseded, or describe a different past state than the code's current one. So a git find does not remove the item now — it is carried into Phase 3 as a *pending* attribution and presented for confirmation. An attributed choice must also not silently vanish: unlike a *dismiss*, a git find carries real recovered information worth keeping. On the operator's decision at the gate:
   - **Accept** — the citation explains the current choice. Retain the rationale in the doc where that kind of rationale lives — almost always `docs/architecture.md` prose (a structural choice or constraint), occasionally `docs/scope.md` — as an *observed, cited* note that names the commit (e.g. `(commit a1b2c3d)`) so its provenance is visible. The item is now attributed and does not enter the ledger. (This is not the per-claim provenance tagging the docs otherwise avoid: it's a specific citation on a specific reconstructed rationale, normal documentation practice, and there won't be many.)
   - **Reject as stale/inapplicable** — the commit does not explain the current choice. The item is *not* attributed: return it to the ledger as an open question (Phase 4), exactly as if the git pass had never touched it. Do not write the rejected citation into any doc.
   - **Reject because the choice itself is wrong** — the operator judges the code an accident, not just the citation stale. Route it to the *remediate* path (a ledger item the operator will drain via `/b-feature`/`/b-design`), not to cited prose.

   Do **not** auto-write an attributed choice as an ADR. A commit body is a *stated* rationale from a past moment, not a decision the user has ratified, and minting ADRs from archaeology reintroduces the confident-noise problem the ledger exists to avoid. If, at the Phase 3 architecture gate, the operator recognises an attributed choice as a genuine cross-cutting commitment they want ratified, *offer* a `/b-adr` at their discretion — but the default is cited prose, and ADR promotion is the operator's call, not adoption's.

## Phase 3: Draft and gate the orienting docs

From the inventory, draft the orienting docs — hedged where inferred, confident where cited or user-confirmed. Gate them in groups (mirroring `/b-design`'s content gates). Draft, present, write on confirmation; do not batch all writes to the end.

**Honour the Phase 0 collision scan at every gate**, using the option set for the target's collision class (Phase 0 step 4), never a fresh write when the path is occupied:
- **Required anchors** (`scope.md`, `architecture.md`, `module-status.md`): preserve *only if the existing file is already schema-compatible*; otherwise the gate offers merge or abort, because adoption cannot finish leaving a required anchor without its shape.
- **Narrative / human-owned** (`problem-space.md`, `constitution.md`): preserve is the default and always valid. `docs/constitution.md` is the most likely brownfield collision (many repos already have contribution conventions written down); a pre-existing one is preserved, not replaced.
- **`docs/index.md`** is not gated here — Phase 5 updates it in place per the `/b-index` contract.

- **Framing** — `docs/scope.md` (current scope, non-goals, success criteria — reconstructed from what the system *does*; each criterion gets a `*Delivered by: <module>*` clause naming the module(s) reconstructed in the previous step, and **no status field**, since criteria carry none) and `docs/design/problem-space.md` (the problem the code appears to solve; mark clearly where this is inferred vs. drawn from an existing doc). This is where you **elicit the minimum**: ask the user to confirm/correct the problem statement and the scope boundary, since those anchor everything downstream.
  - **Reference-material nudge.** If Phase 1 found no `docs/reference/` (or `references/`) material, say so once here, non-blocking: "No reference material found — staging any existing design docs, briefs, or architecture/decision notes in `docs/reference/` and re-running `/b-adopt` would turn hedged inference into cited framing and shorten the ledger. Continue without it, or pause to stage some?" Offer both; if the user continues, proceed — do not ask again. Skip this nudge entirely when reference material was found.
- **Modules** — the proposed module boundaries. Present them explicitly as a proposal for correction: "I read these data-concern boundaries from the code — confirm, merge, split, or rename." For each confirmed module, write `docs/modules/<module>/module-status.md` (a `## Module integration` section with `Test: not yet defined — ⏸` and a `Notes:` line, a `## Build order` listing observed features, and a `## Module review` section with `Review: ⏸`) — **unless that file already exists**, in which case apply the required-anchor collision rule (preserve only if it already carries the `## Module integration` + `## Build order` shape; otherwise merge or abort) rather than overwriting it. `Review: ⏸` is the honest state for an adopted module: nothing has reviewed it. Do not attempt to record a review on the strength of the adoption survey — the survey is an inventory, not a review, and `/b-review` cannot yet run on adopted features anyway (below). Do **not** fabricate per-feature `plan.md`/`status.md` — those are backfilled the normal way when a feature is next touched.
  - **Mark observed features `🚧`, never `✓`.** `✓` means *agreed acceptance criteria passed* — adoption has no recorded criteria and runs no verification, so a `✓` on code it merely *found* is a false completeness claim (the marker-level equivalent of manufacturing an ADR from inferred intent). The honest marker for "present in the codebase, not verified to Bower's bar" is `🚧` — as-built, unverified. A feature graduates to `✓` only when it is next worked and verified against criteria the operator confirms, the normal way. Do not attempt to run the existing test suite to justify a `✓` during adoption — that is out of scope for v1; if the operator *wants* an adopted feature verified, the route is `/b-feature` (which establishes the feature's `plan.md`/`status.md` and verifies against agreed criteria), **not** `/b-review`. `/b-review` cannot review an adopted feature: its reviewer reads each feature's `plan.md` and `status.md` in full and uses the plans to locate code — the very files adoption declines to create. `/b-review` becomes available for a module only once its features have been through `/b-feature` and thus have those files.
- **Architecture** — `docs/architecture.md` with both views: runtime (topology, components, stack, constraints — observed) and `## Software architecture` (one entry per confirmed module: purpose, data-concern boundary, inter-module dependencies — **not** a feature roster; that lives in the module's `## Build order`). Cross-reference ADRs by ID only where ADRs actually exist — on a fresh adoption there are usually none yet, so this view stands on its own. **Present each *pending* git attribution from Phase 2 for the operator's decision here** (accept / reject-as-stale / reject-because-wrong, per Phase 2 step 3). Write only *accepted* citations into the prose (naming the commit); a rejected-as-stale attribution returns to the Phase 4 ledger as an open question, and a reject-because-wrong goes to the remediate path — never write a rejected citation into the doc. If an accepted citation reads as a genuine cross-cutting commitment, offer the operator a `/b-adr` at this gate — their call, default prose.
- **Constitution** — `docs/constitution.md` is normally human-owned and never rewritten unprompted, but on adoption there is none, so drafting an *initial* one from observed conventions (test runner, lint/format, contribution norms) is creation, not rewrite. Draft it, gate it, and flag that the user owns it from here.
  - **Write it normatively, and only from what you verified.** A constitution states rules ("tests live in `tests/`", "run `pytest -q`", "`✓` requires the module integration test to pass"). A rule can be unmet, but it cannot be false. A *description* of what exists ("CI runs the integration suite on every PR") can be false, and once it is in a human-owned doc nothing will correct it — every agent that notices is told to leave it alone. Every convention you write must be one you confirmed in the repo: the config file, the workflow, the runner is really there, at a path you can cite.
  - **Anything inferred-but-unconfirmed goes under a `## Not yet in force` heading**, whose preamble tells agents to treat its contents as non-existent. A test directory with three files in a fifty-module repo is *not* the convention "modules are unit-tested" — it is a partial practice, and it belongs under that heading or nowhere. Same for a CI workflow that exists but is `continue-on-error`, or a lint config nothing invokes.
  - **Do not fold this into the adoption ledger.** The ledger holds cross-cutting choices whose *rationale* couldn't be attributed; this is a *convention* whose reach you couldn't confirm. Different exits: the ledger drains to an ADR, a fix, or a dismissal, whereas a not-yet-in-force item is put in force by the human doing the work and moving the line up.

## Phase 4: Build and gate the ledger

From the inventory's candidate ledger items, draft `docs/adoption-ledger.md`. Include every candidate **except those whose git attribution the operator *accepted* at the Phase 3 architecture gate** (those are now cited prose). A candidate whose attribution was *rejected as stale/inapplicable* belongs here as an open question, exactly as if git had never touched it — Phase 4 runs after the architecture gate, so the accept/reject decisions are already known. (A candidate the operator judged *wrong* is on the remediate path — still a ledger line, drained via `/b-feature`/`/b-design`.) **Hard format — one bullet per open item, no free-form body:**

```markdown
# Adoption ledger

Cross-cutting choices observed in the codebase whose rationale could not be attributed during adoption. Each is an open question. Drain each line by one of three exits, then delete it: **resolve** (the choice stays — capture its intent as an ADR via `/b-adr`), **remediate** (the choice was accidental or wrong — change it via `/b-feature`, or `/b-design` if the fix is architectural), or **dismiss** (deliberate/accepted, no record warranted). When this file is empty, remove the adoption banner from `docs/index.md`; the adoption phase is over.

- modules/auth · tokens persisted in DB, not cache — deliberate or drift?
- modules/billing · retry logic hand-rolled instead of using the queue — why?
```

Rules for the ledger:

- **One line each: `<location> · <the open question>`.** Location + question, full stop. Do **not** store the context (what the code does, why it looks cross-cutting) — it is cheaply re-derivable from the code at the moment the item is picked up, and storing it turns a worklist into a per-session token tax.
- **Open items only.** The file only ever holds unresolved questions. There is no checkbox and no strikethrough — presence *is* the open state.
- **All three drain paths remove the line.** Resolve → the intent becomes an ADR (cold, module-scoped, loaded only when that area is touched); delete the line. Remediate → the change lands via `/b-feature` (or `/b-design` for an architectural fix), reconciling docs the normal way; delete the line once the fix is in. Dismiss → delete the line (no tombstone in v1 — re-running adoption on an already-adopted project is not a supported operation).

Gate the drafted ledger: "Here are the choices I couldn't attribute. Confirm the list, add/remove items, or reword." Write on confirmation.

**Empty-ledger case (N = 0).** If, after the gate, there are zero unattributed choices, do **not** write `docs/adoption-ledger.md` and do **not** open the adoption phase in Phase 5. An empty ledger already satisfies the exit condition — writing a banner that points to an empty (or absent) ledger would be self-contradictory, adopting the project straight into the state it should immediately leave. Instead, adoption completes clean: the reconstructed docs stand as a normal (non-provisional) Bower project with no banner. Note this in the handoff. (The framing docs were still inferred, so the handoff's Confidence paragraph still applies — but there are no tracked open questions, so there is nothing for a banner to point at.)

## Phase 5: Set the adoption flag, regenerate the index, hand off

1. **Write the adoption banner** at the top of `docs/index.md` — **only if the ledger has one or more open items.** Its presence *is* the adoption-phase flag; greenfield projects, and clean N = 0 adoptions, simply never carry it. Skip this step entirely when N = 0. (`docs/index.md` was deliberately excluded from Phase 0's preserve/merge/abort collision handling — it is always updated in place here, never left untouched. If an `index.md` already existed, add the banner and refresh derived state without discarding the project's curated structure, per the `/b-index` regeneration contract.)

   ```markdown
   > 🌱 **Adoption in progress.** The orienting docs below were reconstructed from the existing codebase and are provisional. Open questions are tracked in [adoption-ledger.md](/docs/adoption-ledger.md) — resolve, remediate, or dismiss each, then delete this banner. Drain workflow: `_bower/framework-reference.md` → "Adoption phase".
   ```

2. **Regenerate the index.** Run `/b-index` if available, or write `docs/index.md` per the `b-index` schema — an existing file is refreshed in place (derived state recomputed, curated structure preserved), not overwritten wholesale. If a banner was written, it is curated structure and survives regeneration.
3. **Handoff block** — the only end-of-workflow output. Use the phase-open form when N ≥ 1, the clean form when N = 0.

   **N ≥ 1 (adoption phase open):**

   ```
   Bower adoption complete — the project is in the adoption phase.

   Reconstructed:
     - <one line per doc group written>
   Ledger: N open questions in docs/adoption-ledger.md

   Confidence:
     - <candid paragraph: what was cited/confirmed vs. inferred; which module
       boundaries you were least sure of; where the user should eyeball>

   Suggested commit point (advisory — do not commit yourself):
     docs: adopt Bower — reconstruct orienting docs from existing codebase

   Draining the ledger (each item, as you next work in its area):
     - /b-adr <slug>       capture intent for a choice you're keeping     (resolve)
     - /b-feature <name>   fix an accidental/wrong choice (/b-design if     (remediate)
                           architectural)
     - delete the line     deliberate/accepted, no record warranted        (dismiss)
   Delete the ledger line once the item is drained by any of these.
   When the ledger is empty, delete the banner from docs/index.md.

   Run /b-recap any time to re-orient.
   ```

   **N = 0 (clean — no phase opened):**

   ```
   Bower adoption complete — no unattributed choices, so no adoption phase.

   Reconstructed:
     - <one line per doc group written>
   No adoption ledger and no banner: nothing was left open, so the docs stand
   as a normal Bower project. They were still inferred — see Confidence below.

   Confidence:
     - <candid paragraph: what was cited/confirmed vs. inferred; which module
       boundaries you were least sure of; where the user should eyeball>

   Suggested commit point (advisory — do not commit yourself):
     docs: adopt Bower — reconstruct orienting docs from existing codebase

   Run /b-recap any time to re-orient.
   ```

<critical_constraints>
## What NOT to do

- Do not touch source code, tests, or build files — adoption writes only under `docs/` and `docs/index.md`
- Do not run the survey on a project whose `AGENTS.md`/`CLAUDE.md` do not reach `_bower/framework.md` — stop at Phase 0 with the exact lines quoted, and do not add them yourself; those files belong to the project
- Do not silently overwrite any pre-existing file — stat every write target in Phase 0 and resolve collisions at a gate; "creates" holds only for paths that were empty
- Do not offer *preserve* for a required anchor (`scope.md`, `architecture.md`, `module-status.md`) that is not already schema-compatible — a non-Bower file at that path must be merged or the command aborted, never left in place while adoption reports completion
- Do not treat `docs/index.md` as a preserve/skip collision — it is always an in-place curated update in Phase 5 (banner + derived-state refresh), never left untouched
- Do not start over when `docs/adoption-ledger.md` already exists — a prior adoption is unfinished; stop and have the user finish or delete it
- Do not write a ledger or a banner when there are zero unattributed choices — an empty ledger already meets the exit condition, so opening the phase would immediately contradict it; complete clean instead
- Do not claim `git reset` is a safe undo on a dirty tree — it destroys uncommitted work; recommend a clean baseline first and, if the user declines, tell them the built-in undo is unavailable
- Do not refactor, "fix," or propose changes to the codebase — observations become ledger items, not edits
- Do not manufacture ADRs from inferred intent — unattributed choices go in the ledger
- Do not auto-write an ADR even from git-attributed rationale — retain it as commit-cited prose in `architecture.md` (or `scope.md`); ADR promotion is the operator's call at the Phase 3 gate, never adoption's default
- Do not drop a git-attributed candidate from the ledger before the operator accepts the citation — attribution is provisional until the architecture gate; a rejected-as-stale citation returns to the ledger as an open question, and its text is never written into a doc
- Do not guess a rationale and write it as a confident architecture or scope claim — hedge, or make it a ledger item
- Do not add per-claim provenance tags to the docs — the banner carries the global caveat; per-claim tagging is a permanent tax for a phase that ends
- Do not interrogate the user about the whole codebase — elicit only the top-level framing; defer detail to the ledger
- Do not read git diffs — the git pass is message-only, and only after signal detection justifies it
- Do not store context in ledger entries — one line each, location + question only
- Do not leave checkboxes or strikethroughs in the ledger — presence is the open state; drained items are deleted
- Do not run on an already-adopted project — redirect to `/b-feature` or `/b-upgrade`
- Do not fabricate per-feature `plan.md`/`status.md` — backfill happens when a feature is next touched
- Do not mark observed features `✓` — `✓` means verified against agreed criteria, which adoption cannot do; mark as-built features `🚧` and let normal verified work promote them
- Do not run the existing test suite to justify a marker during adoption — verification of adopted code is a post-adoption `/b-feature` pass, not adoption's job
- Do not point adopted-feature verification at `/b-review` — its reviewer requires each feature's `plan.md`/`status.md`, which adoption doesn't create; `/b-review` only applies after features have been through `/b-feature`
- Do not run `git commit` — the commit point is advisory
- Do not emit free-prose next moves — the handoff names literal slash commands
</critical_constraints>
