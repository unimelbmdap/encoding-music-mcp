---
name: b-design
description: Six-stage design for greenfield projects and architectural revisions; Stage 0 delegates to bower-analyst for a change brief. Required whenever architecture, decisions, scope, or module structure shift.
---
<!-- GENERATED FILE — do not edit. Source: skills-src/commands/b-design.md. Regenerate: node scripts/build-adapters.cjs -->

# Bower Design

You are running the Bower design process. This is a six-stage workflow that produces (or revises) the design documentation and runnable scaffolding for a project. Stage 0 produces a **change brief** via the `bower-analyst` subagent; Stages 1–5 execute against that brief. The brief is the contract — stages do not re-derive what work needs doing.

Use for greenfield projects and for revisions that cross architectural boundaries (new modules, new technology, cross-cutting decisions, scope shifts). For changes within existing architecture that don't touch cross-cutting commitments, use `/b-feature` instead — it has its own propose-and-confirm gate, and will redirect back here if a request turns out to need design treatment.

The request (the user's description of the change): the request as given in the message that invoked this skill.

## Important Behavioural Rules

- **The brief is the contract.** Stage 0 produces a change brief and gates on it. Stages 1–5 execute against the confirmed brief — they do not re-derive applicability. If a stage's brief section is `Status: nothing to do`, that stage emits a one-line acknowledgment and proceeds. The applicability question is settled once, up front, not re-asked five times.
- **ADR IDs are pre-allocated in the brief.** Stage 2 operations in the brief carry real, pre-allocated IDs (e.g. `new ADR-0034`). Stages 1, 3, and 4 cross-reference these IDs verbatim when drafting edits to `scope.md`, `architecture.md`, or `plan.md` files — **never use `ADR-NNNN` as a literal placeholder** in any draft, because draft content is what gets written to disk on gate confirmation. If the brief lacks pre-allocated IDs for `new`/`supersedes`/`narrows` operations, halt and surface the issue rather than inventing or placeholdering them.
- **Surface mid-flight discoveries.** If a stage uncovers work that wasn't in the brief, surface it to the user and ask whether to amend the brief or skip it. Do not silently expand scope; do not silently shrink it either.
- **Consult at every content gate.** Stages with non-nil delta present the **drafted content** (the ADR text, the architecture edit, the plan touches) at an operator gate (binding: `_bower/framework.md` → *Runtime bindings*) — not applicability, which Stage 0 has already settled.
- **Per-stage writes.** Each stage with delta writes its files immediately after its gate is confirmed. There is no consolidated write step.
- **Recommend, don't dictate.** When presenting options, mark one as (recommended) with a brief rationale, but make it clear the user chooses.
- **Literal-command handoff.** The post-design handoff names exact slash commands the operator types next, never free prose.
- **Write docs, not code.** This workflow produces documentation files and (in Stage 5) scaffolding only. Feature code belongs to `/b-feature` or `/b-module`.
- **Don't re-run the analyst mid-flow.** The brief is locked at Stage 0. If the user wants a re-analysis, that's a new `/b-design` invocation, not an in-flow restart.

## Stage 0: Change Analysis

**Goal:** Produce a change brief identifying what each downstream stage needs to do (including the legitimate outcome of "nothing to do").

**Process:**

0. **Check for a routed finding first** — before delegating anything. Glob `docs/modules/*/{review-plan,findings}.md` and scan each for open `route:/b-design` items. Both kinds carry the same line shape and the same brief: a review plan's items are `F<n>` and hold a review open; a findings queue's are `Q<n>` and hold nothing open (spec: `_bower/framework-reference.md` → *Findings queue*). Boundary erosion is *always* routed here and never actioned by `/b-review`, so a design run is frequently the discharge of one, and the operator may well have typed `/b-design` bare because the plan told them to.

   - **No open items:** proceed with the request as-is.
   - **One matches** — in priority order: the request names the finding explicitly, which always wins; or its slug matches; or the request is empty; or it is topically the same concern. Routed commands end `according to <ID> in <path>`, so a pasted invocation hands you the file and the ID outright — open that file and take that finding, without globbing. Looser forms (`F7`, `according to F7 in the review plan`) are fine, but an ID without a path is ambiguous, since finding IDs are module-local; if several open files carry that ID, ask. A named finding that is not in the file named, or already disposed of, is worth saying so about rather than guessing. Then: read its indented `Location:` / `Drift:` / `Resolution:` brief and **pass all three verbatim into the analyst prompt** alongside the change description, labelled with its source — a review finding from module `<module>`, finding `<Fn>`, or a queued finding from module `<module>`, `<Qn>`. Say in one line that you are doing so.
   - **Several match, or one exists and the request is unrelated:** ask which at an operator gate, offering the findings and "none of these — proceed with what I typed."

   The brief is the surviving evidence of a whole-module survey that has since been discarded. Without it the analyst re-derives a boundary violation from code alone — expensive, and it can quietly conclude there is nothing there, which reads as the finding being wrong rather than as the evidence being missing. Treat it as an input to verify, not a conclusion: if the survey contradicts it, that goes in the brief's `## Considered and ruled out` and the operator decides at the Stage 0 gate.

   Never edit `review-plan.md` — the checkbox included. A command that *implements* a routed finding ticks it on discharge; a design run does not, and the asymmetry is designed rather than overlooked: your output is a decision, and the drift the finding names is still in the code when you finish. Everything in that file beyond an implementing command's own tick is `/b-review`'s. Name the finding in the post-design handoff so the operator knows to run `/b-review <module>`.

   **A `findings.md` item is different, and the difference cuts both ways.** You still never tick it — nothing owns that file and nothing audits it, so a tick made on the strength of an ADR would be checked by nobody. But the queue also has no `/b-review` to re-classify it, so leaving it exactly as you found it strands the item: it still reads `route:/b-design`, and `/b-feature` only picks up items routed to itself. **So you re-classify it yourself, after the decision lands** — see *Post-Design Handoff*. Re-classifying reroutes work that is still owed; it never declares any of it done.

1. **Delegate to the `bower-analyst` subagent** (binding: *Runtime bindings → Delegation*) and wait for its brief. The prompt to the subagent must include:
   - The change description verbatim (the request).
   - The project root (the current working directory).
   - Any routed review-finding brief from step 0, verbatim.
   - An instruction to conform exactly to `_bower/brief-schema.md`.

   Do not attempt the analysis inline while delegation is available. The subagent exists precisely so the analysis happens in isolated context, focused on the survey. If this runtime cannot delegate, that is the one exception: you — the calling workflow — follow `bower-analyst`'s definition inline, say so in one line, and mark the resulting brief `Context: inline` before gating on it.

2. **Read the returned brief** carefully — particularly `## Considered and ruled out` and `## Ambiguities and assumptions`. These sections are the operator's primary safety checks, and you need to surface them at the gate.

3. **Handle the no-op case.** If the brief is `Status: nothing to do` for all five stages and the considered-and-ruled-out section confirms nothing material was found, the change is a no-op. Emit a single line ("Brief: nothing to do — `<reason>`. Stopping.") and stop. The operator can re-run with a refined description if appropriate.

4. **Gate:** Present the brief to the user at an operator gate. Show the `## Summary` section, the `## Ambiguities and assumptions` section, and the `## Considered and ruled out` section as the primary surfaces. Reference the rest as available for inspection. **State step 0's outcome in one line here** — which routed finding was folded in, or that the glob found no open `route:/b-design` items. Say it even when there is nothing: an unstated result is indistinguishable from a skipped check, and this is the operator's only chance to catch a design run that ignored the finding it was meant to discharge. Ask:
   - "Here's the change brief from the analyst. Confirm to proceed, amend it (tell me what to add/remove/change), or stop."

5. **If the user amends the brief**, update it in working memory and proceed. Do not re-delegate to the analyst for amendments — incorporate the operator's correction directly. The corrected brief is the contract for Stages 1–5.

**Brief is now locked.** Proceed to Stage 1.

## Stage shape (applies to Stages 1–5)

Each of Stages 1–5 follows the same shape:

1. **Read the brief's stage-N section.**
2. **If `Status: nothing to do`:** emit one line — `Stage N: nothing to do — <reason from brief>` — and proceed to the next stage. No gate, no drafting, no writes.
3. **If `Status: delta`** (or any non-nil status): draft the change(s) per the stage's specific rules below, present the drafts at a content gate (an operator gate), write files on confirmation.

Stage-specific drafting and write rules follow.

## Stage 1: Problem Framing

**Brief section consumed:** `## Stage 1 — Problem framing`.

**Drafting:**

- **Greenfield (full draft):** Draft `docs/design/problem-space.md` covering the problem and who has it, current alternatives and why they're insufficient, success criteria, scope boundaries, and constraints. Draft `docs/scope.md` covering current scope, current non-goals, and success criteria. **Criteria carry no status field** — each is a statement of what must be true followed by a `*Delivered by: <module>[, <module>]*` clause naming the responsible module(s), and nothing else. No status column, no marker, no met/unmet field: achievement is derived from module completion by `/b-recap`, never stored here. At Stage 1 the module names may not exist yet; if the brief has not settled the module decomposition, write the criteria now and add the `Delivered by:` clauses in Stage 3 once modules are named. Full shape: `_bower/framework-reference.md` § `scope.md — Boundary, Not Tracker`.
- **Revision (partial draft):** Draft only the specific edits the brief calls for — often a paragraph added to `docs/scope.md`, more rarely a `problem-space.md` amendment (which is framing history and should be edited with care).

**Gate:** Present the drafted text. Ask: "Confirm the framing/scope draft, or tell me what to adjust."

**Write:** `docs/design/problem-space.md` and `docs/scope.md` per the confirmed draft. Create the `docs/design/` directory if it doesn't exist.

## Stage 2: Decisions

**Brief section consumed:** `## Stage 2 — Decisions` (a list of operations).

**Drafting:** For each operation in the brief's list:

- **new** — Draft a new ADR per the schema in `/b-adr`: frontmatter (including `scope`, and `modules`/`topics` where applicable) + two required sections (Context, Decision) and two optional (Consequences, Alternatives considered). ~150 words, ceiling 300.
- **supersedes ADR-NNNN** — Draft the new ADR with `supersedes: [ADR-NNNN]` in the frontmatter. Also draft the frontmatter update for the superseded ADR (`status: superseded`, `superseded-by: [<new-id>]`). The superseded ADR's body is **not** edited. If the superseded ADR carries `narrows` or `narrowed-by`, also draft the pointer updates on those third ADRs per the narrowing rules in `_bower/framework-reference.md` — a retired ADR must not stay referenced by a live one; where a narrowing ADR's exception may or may not survive the replacement, ask at the gate.
- **narrows ADR-NNNN** — Draft the new ADR with `narrows: [ADR-NNNN]` in the frontmatter, referencing the original in `## Context` and `## Decision` and stating what the exception is and what remains in force. Also draft the frontmatter update for the narrowed ADR: `narrowed-by: [<new-id>]` added, **`status` left at `accepted`**. The narrowed ADR's body is **not** edited. Do not use this operation where the earlier decision no longer holds at all — that is `supersedes`.
- **confirms ADR-NNNN** — **No file is written.** Acknowledge in the stage output: "Confirmed ADR-NNNN, no new ADR written." This is a deliberate signal that the operator considered it.

**ID verification.** The brief's Stage 2 operations carry pre-allocated IDs (per `_bower/brief-schema.md`). Before writing, scan `docs/adr/*.md` for the current highest existing `NNNN-` prefix and verify the brief's pre-allocated IDs are `<highest> + 1`, `<highest> + 2`, etc. — i.e. no ADR has been created between Stage 0 and now. If verification passes, use the brief's IDs throughout. If a discrepancy is found (another ADR was added in the interim), surface it at the gate: ask the operator whether to renumber the new ADRs forward or abort the stage.

**Gate:** Present the drafted ADRs (and any supersession or narrowing frontmatter changes) together. Ask: "Confirm the ADRs and the supersession/narrowing updates, or adjust before writing."

**Write:** New ADR files to `docs/adr/NNNN-kebab-title.md`. Frontmatter updates to superseded and narrowed ADRs (bodies untouched) — written in the same step as the ADR that names them, never left one-sided. Create `docs/adr/` if it doesn't exist.

## Stage 3: Architecture

**Brief section consumed:** `## Stage 3 — Architecture`.

`architecture.md` carries two views that must both be present on greenfield and maintained as the project evolves:

- **Runtime view** — system overview, topology, components (containers, processes, external services), data flow, technology stack, known constraints, extension points. Cross-references the ADRs written in Stage 2 by ID rather than restating decisions.
- **Software architecture view** — a `## Software architecture` section listing each Bower module with: its purpose in one line, the data concern that justifies the module boundary (per the constitution's module rubric), and inter-module dependencies (depends on / consumed by). This is the code-structure complement to the runtime view; it is the home for *why these modules and not others*. **Do not enumerate the module's features here** — the feature roster lives in that module's `module-status.md` `## Build order`, which is the only place any command maintains it.

**Drafting:**

- **Greenfield:** Draft `docs/architecture.md` covering both views. The software-architecture section is sourced from the module breakdown that Stage 4 will produce — draft it consistent with Stage 4's planned modules so the two stay aligned.
- **Revision:** Draft the specific edits the brief calls for. The brief distinguishes runtime-view deltas from software-architecture deltas; honour that distinction in the drafted edit. Show each edit in context (surrounding sentences) so the gate can confirm placement, not just text. **If `docs/ui.md` exists, read it first** — architectural revisions in projects with an interface often shift logic-UI interactions (routing, state, data flow into and out of screens), and the existing experience surface is the constraint those edits have to respect. The drafted architecture edit should name any `docs/ui.md` reconciliation it implies, so Stage 4 (or follow-up `/b-ui` / ad-hoc work) picks it up.

**Cross-stage rule — success-criteria coverage.** Once the modules are named here, every success criterion in `docs/scope.md` must carry a `*Delivered by: <module>[, <module>]*` clause naming existing modules. Check them: backfill any clause Stage 1 left open, and correct any that names a module this stage renamed or dissolved. A criterion no module delivers is a real finding — surface it at this stage's gate (the criterion is unowned, or a module is missing) rather than inventing a pointer. Include these clauses in the drafted content presented at the gate, and write them to `docs/scope.md` alongside `architecture.md`.

**Cross-stage rule.** Every Stage 4 `new module` operation requires a corresponding software-architecture entry in this stage. If the brief lists a new module under Stage 4 without a Stage 3 delta covering its software-architecture entry, surface this at the Stage 3 gate as a brief inconsistency and ask the operator to amend before drafting.

**Gate:** Present the drafted architecture content, grouping runtime-view edits and software-architecture edits separately so the gate is scannable. Ask: "Confirm the architecture content, or adjust."

**Write:** `docs/architecture.md` (edit in place; on greenfield, full new file), plus any `Delivered by:` clauses in `docs/scope.md` this stage backfilled or corrected.

## Stage 4: Module and Feature Plans

**Brief section consumed:** `## Stage 4 — Module and feature plans` (plan touches, build-order changes, integration notes, new modules).

This is the stage that most often does real work on revisions. It covers four kinds of edits, any of which the brief may list:

**Drafting:**

- **Plan touches** (existing `plan.md` files): Draft each edit per the brief's one-line reason. Touches range from a sentence to a paragraph. Show the edit in context.
- **Build-order updates** (existing `module-status.md` `## Build order` sections): Draft the reordering or append.
- **Module integration notes** (existing `module-status.md` `## Module integration` `Notes:` line): Draft the refreshed line. Do not flip the integration marker — that's `/b-integration`'s job.
- **New modules** (greenfield, or a revision that adds a module): Draft the new module's `module-status.md` placeholder with a `## Module integration` section (`Test: not yet defined — ⏸` and `Notes:` from the brief), a `## Build order` section listing the module's features in order, each marked `⏸`, and a `## Module review` section with `Review: ⏸`. Do not create feature `plan.md` or `status.md` files — those belong to implementation.

**Gate:** Present all Stage 4 drafts together. Group by file path so the gate is scannable. Ask: "Confirm the plan and module-status edits, or adjust."

**Write:** All affected files. For new modules, create directories under `docs/modules/<module-name>/` first.

## Stage 5: Scaffolding

**Brief section consumed:** `## Stage 5 — Scaffolding`.

**Drafting:** If `Status: nothing to do`, skip per the stage shape. Otherwise, follow the existing Stage 5 rubric — delta-only on existing projects, full-draft on greenfield:

- **Package manifest** — `package.json`, `pyproject.toml`, `Cargo.toml`, etc. per Stage 2 decisions.
- **README.md** — If a stock README exists (from `create-*` tooling, or from adopting Bower itself), move it to `_bower/original-README.md` and generate a project-specific README drawn from `scope.md` and `architecture.md`. The new README must include a short "Built with Bower" section linking to `_bower/original-README.md`.
- **.gitignore** — Stack-appropriate.
- **Linter / formatter config** — per Stage 2 decisions. If the stack's formatter handles markdown (Prettier and most of its peers do), exclude `docs/` in the same step — `.prettierignore` or the equivalent — and note the exclusion in `constitution.md`. This is the only moment the exclusion is cheap to establish; retrofitting it means undoing the damage first. Reason: `_bower/framework-reference.md` § *Code Formatters and `docs/`*.
- **Test runner setup** — per the testing approach in `constitution.md`.
- **Directory skeleton** — empty module directories matching the Stage 4 breakdown (the `module-status.md` placeholders have already been written in Stage 4).

For each item, classify as *create* / *modify* / *archive* / *skip (already present)*.

**Gate:** Present the scaffolding plan. Ask: "Confirm the scaffolding plan, or strike items."

**Execute:** Confirmed actions only.

## Index Regeneration

After Stage 5 completes (or is skipped), regenerate the index files so they reflect the new state:

1. Run `/b-index` if available in this session — it regenerates both `docs/index.md` and `docs/adr/index.md`.
2. If `/b-index` is not invokable, write `docs/adr/index.md` directly per the schema in `b-index.md`, and update `docs/index.md`'s **module table only** — new module rows and their status markers. Add no narrative: index prose is subject to *Status is never curated* in `b-index.md`, and a design pass is exactly the moment an agent is holding the kind of news that accretes there.

This is mechanical and does not gate.

## Post-Design Handoff

After Stage 5 (or its skip) and index regeneration, emit a single handoff block. This is the only end-of-workflow output — do not also print a generic file summary.

The block must include:

1. **Confirmation** — "Design complete." (greenfield) or "Design revision complete." (revision).
2. **Summary of changes** — One line per stage that had non-nil delta, naming what was written or edited. Stages marked `nothing to do` are listed in a single line at the end (e.g. "Stages 1, 5: nothing to do.").
3. **Suggested commit point** — A proposed commit message. Advisory only: do **not** run `git commit` yourself.
4. **Next move** — Drawn from the brief's `## Suggested next move (post-design)` section, refined if you have better information:
   - **Greenfield:** recommend `/b-module <first-module>` if the first module has ≤3 features and an unambiguous plan; otherwise `/b-feature <first-feature>`. Mention the other option in one line.
   - **Revision:** typically a list of `/b-feature <name>` invocations, one per touched plan, in the order the brief suggested.
5. **Orientation hint** — "Run `/b-recap` any time to re-orient."

If Stage 0 consumed a routed review finding, add `Run /b-review <reviewed-module>` to the next moves naming the finding ID — the module whose plan holds it, which for a cross-module finding is not the module the decision most affects. The item is still open in `review-plan.md`, and you left it open deliberately: an implementing command ticks the finding it discharges, a design run does not. Say explicitly that the finding is **not** discharged by this design run — an ADR is a decision, and the finding names a drift in the code that is still there. `/b-review` decides what happens to it next, most likely re-classifying it to `route:/b-feature` so the implementation is scheduled rather than assumed.

**If the finding came from a module's `findings.md` instead, re-classify it in place before emitting the handoff.** There is no review to resume and no other command that will do this, so an item left reading `route:/b-design` is stranded: `/b-feature` loads only items routed to itself, and a design run is the one thing that has already happened. Same shape as `/b-review`'s re-classification rule, and the same reason — a class is a claim about who can discharge a finding, and once the decision has landed that claim is out of date. In the queue's line, keeping the box open (`[ ]`) and the ID `Q<n>` unchanged:

- replace `route:/b-design` with `route:/b-feature`;
- replace the command with the implementation command, ending `according to Q<n> in docs/modules/<module>/findings.md`;
- rewrite the brief so the design output is carried forward — `Location:` still names the offending code, `Resolution:` becomes *implement ADR-00NN's decision here*, `Drift:` names the accepted ADR as the side the code now contradicts.

Then name the item and its new command in the next moves, and say you re-classified it and why. Do **not** tick it, and do not dispose of it as `[~]` — if the decision made the item moot, say so and leave it open for the operator to won't-fix, which is their call and not yours. The ID is deliberately kept: the operator may be holding a handoff that names it.

**Name implied work that no build order will carry.** A design run normally emits work as build-order entries, and `/b-index` then tracks it. When a decision implies code changes that are *not* new features — reshaping an existing component, removing a dependency, relocating a concern — Stage 4 legitimately adds no roster entries, and that work is then scheduled by nothing at all. An accepted ADR is a commitment, not a work item, and no command reads `docs/adr/` asking whether it was built. So when Stage 3 or Stage 4 concluded that the roster does not change but the code must, list the `/b-feature` invocations the decision implies under the next moves, marked as implied-not-tracked. This is a printed pointer, not a record: it does not go in a file, and if it is lost the drift is still in the code where a future review will find it.

Example shape (revision):

```
Design revision complete.

Summary of changes:
  - Stage 2: ADR-0034 written (supersedes ADR-0011); ADR-0011 marked superseded.
  - Stage 3: architecture.md — one-paragraph edit in "Turn structure" section.
  - Stage 4: 4 plan touches across ui-module, eval-mode, test-harness, prompt-module.
  - Stages 1, 5: nothing to do.

Suggested commit point — stage the design revision:

  docs: extend control-code taxonomy with framing codes (ADR-0034)

Next move:
  - /b-feature framing-element-ui              (response-display)
  - /b-feature framing-turn-annotation         (eval-mode)
  - /b-feature framing-probe-personas          (test-harness)
  - /b-feature framing-prompt-principle        (prompt-module)

Run /b-recap any time to re-orient.
```
