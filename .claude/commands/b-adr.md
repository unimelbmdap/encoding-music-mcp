---
description: Scaffold a new Architectural Decision Record, or supersede or narrow an existing one.
argument-hint: the user's description of the decision
---
<!-- GENERATED FILE — do not edit. Source: skills-src/commands/b-adr.md. Regenerate: node scripts/build-adapters.cjs -->

# Bower ADR

You are scaffolding an Architectural Decision Record (ADR) — a single-file, append-only entry in the project's decision log at `docs/adr/`. ADRs capture cross-cutting commitments: choices that constrain more than one feature and would surprise a future reader if not written down.

This command produces exactly one deliverable: a new ADR file (and, if superseding or narrowing, a frontmatter update to the ADR being replaced or narrowed). It does not modify code, plans, or status documents — those are the job of the command that called this one (typically `/b-feature` reconcile or `/b-design` Stage 2).

The request (the user's description of the decision): $ARGUMENTS

## Important Behavioural Rules

- **One coherent scope per ADR.** An ADR may bundle several closely-related decisions under an umbrella title (e.g. "sidecar accommodation for patterns" covering artefact layout, build-time merging, and provenance rendering). The split test is whether the title honestly covers the scope — if you find yourself drafting "and also we switched the build tool," that's a second ADR. Naming more than one commitment in the body is fine when the umbrella holds.
- **Bodies are immutable once accepted.** This command writes a new ADR or amends frontmatter only. It never edits an existing ADR's body.
- **Consult before writing.** Confirm the draft at an operator gate (binding: `_bower/framework.md` → *Runtime bindings*) before committing it to disk.
- **Classify applicability.** Every new ADR carries a `scope` field — it decides which future changes load the ADR, so an over-broad scope taxes every `/b-feature` run. `universal` is rare and means "constrains every feature in the project"; most decisions are `module`, `integration`, or `operational`. Add `topics` when the decision is findable by subject-matter keywords (e.g. `[caching, invalidation]`).
- **Use exact Bower module names.** The `modules` field references directories under `docs/modules/`. Omit the field when no specific module is implicated; do not invent sentinels like `[*]` or `[all]`.
- **Status is `accepted`.** Bower has no `proposed` workflow — decisions are confirmed at gates before being written to disk.

## Step 1: Understand Context

1. Read `docs/adr/index.md` if it exists — confirms the next available ID and lets you check for adjacent or related decisions.
2. If no `docs/adr/` directory exists yet, this is the first ADR; the next ID is `0001`.
3. If the user's description implies superseding an existing ADR (e.g. "we're switching from Redis to in-process caching, ADR-0011 is wrong"), read that ADR's full contents.
4. Read `docs/architecture.md` and any module's `module-status.md` referenced by the decision, only insofar as needed to fill in `modules` correctly and to write a defensible `## Context` section.

Do **not** load every ADR. The point of the index is that you don't have to.

## Step 2: Determine ID and Relationship

- **ID.** Scan `docs/adr/*.md` filenames for the highest existing `NNNN-` prefix; the new ID is that number + 1, zero-padded to four digits. If the directory is empty or missing, the new ID is `0001`. IDs are immutable and never reused — gaps from deleted entries are fine.
- **Supersession.** If the user's description names an existing ADR being replaced, this is a supersession. The new ADR will carry `supersedes: [ADR-NNNN]` and the old ADR's frontmatter will be updated with `superseded-by: [<new-id>]` and `status: superseded`. Both files will be written in this command's output. The old ADR's **body is not touched**.
- **Narrowing.** If the user describes a decision that scopes an exception to an existing ADR rather than fully replacing it (e.g. "ADR-0011 says use Postgres for all stores; this module uses ClickHouse instead"), this is a **narrowing**. The new ADR carries `narrows: [ADR-NNNN]` and the old ADR's frontmatter gains `narrowed-by: [<new-id>]` — and **nothing else**: its `status` stays `accepted`, because its central decision is still in force. Both files are written in this command's output. The old ADR's **body is not touched**.

**Choosing between them.** Apply this test before deciding: *would someone implementing the old ADR's main decision today still be right?* If yes, it is a narrowing — the old decision survives with an exception carved out. If no, it is a supersession. When the answer is genuinely unclear, put the question to the user at the gate rather than guessing; the two are not interchangeable, and recording a narrowing as a supersession marks live policy dead. Do not use `supersedes` for a relationship the new ADR's own body describes as partial.

## Step 3: Draft the ADR

Compose the file. Two sections are required (`## Context`, `## Decision`); two are optional and earn their place only when they carry real content (`## Consequences`, `## Alternatives considered`). Order is fixed.

```markdown
---
id: ADR-NNNN
title: <Title in sentence case, matching the filename minus the ID prefix>
status: accepted
date: YYYY-MM-DD
scope: universal | module | integration | operational
modules: [<module-name>, ...]
topics: [<kebab-keyword>, ...]
supersedes: [ADR-NNNN]
narrows: [ADR-NNNN]
---

## Context

<Two sentences max. Name the question that forced a decision and point to the
doc that frames it — `architecture.md`, an earlier ADR, a referenced design doc.
Do not restate what those docs already say.>

## Decision

<What did we decide. Active voice, present tense. "We will use X." One paragraph.
Lead with the central sentence — if someone reads only the first line, they
should know what's true. An ADR may name more than one commitment here when they
share the umbrella scope of the title.>

## Consequences   <!-- OPTIONAL -->

<Include only when there is a non-obvious cost, an ongoing maintenance burden,
or a downstream commitment that is not already implied by the Decision sentence.
If the consequence is "this means X will be true" — that's already in Decision;
omit this section. When in doubt, leave it out.>

## Alternatives considered

<One sentence per alternative + the rejection reason. "Considered Redis; rejected
because [reason]." This is the section that earns the ADR's keep — the trace of
why x and not y, which a future reader (human or model) can't reconstruct from
the code. Include it whenever real alternatives were weighed.>
```

Frontmatter rules:

- `scope:` — required for new ADRs. Pick the narrowest true value:
  - `universal` — constrains every feature in the project (e.g. an error-handling convention, a language/runtime commitment). Rare; loaded by every `/b-feature` run, so it must earn that cost.
  - `module` — constrains the module(s) named in `modules:`. The default for most decisions.
  - `integration` — constrains how modules interact at their boundaries; loaded for integration-shaped work, not everyday feature changes.
  - `operational` — deployment, tooling, versioning, maintenance; loaded for ops-shaped work only.
- `modules:` — required when `scope: module` (exact directory names under `docs/modules/`); otherwise include only if a specific module is implicated. Do not write `modules: []`.
- `topics:` — optional list of kebab-case subject keywords (e.g. `[streaming, control-codes]`). Include when the decision should surface for topically-related changes regardless of module.
- `supersedes:` and `superseded-by:` — omit when empty.
- `narrows:` and `narrowed-by:` — omit when empty. Symmetric: if the new ADR carries `narrows: [ADR-MMMM]`, then ADR-MMMM must gain `narrowed-by: [<new-id>]` in the same write. Never both `supersedes` and `narrows` naming the *same* ADR — pick one per relationship. Do not add `narrows` targeting an ADR whose status is `superseded` or `deprecated`; there is nothing left to narrow, and if the retired decision is the right subject, the live ADR that replaced it is what the new one narrows.
- `date:` — today's date in `YYYY-MM-DD`.
- `status:` — `accepted`.

Legacy ADRs (pre-v0.20) lack `scope`. Frontmatter is mutable — when you touch a legacy ADR for supersession, or the operator asks for classification, adding `scope`/`topics` to an existing accepted ADR's frontmatter is allowed and encouraged; the body stays immutable.

Filename: `docs/adr/NNNN-kebab-case-title.md`. Lowercase, hyphens, no punctuation, no trailing period. The kebab title should match the frontmatter title.

Body length: aim for ~150 words across all sections combined, ceiling 300. If you're approaching 300, check whether the prose is doing real work or just filling sections — pad Context with restatement of framing docs, or write pseudo-Consequences that just rephrase the Decision, and you've blown the budget without adding signal. The Alternatives section is the one that may legitimately grow when several real alternatives were weighed.

## Gate: Confirm or Adjust

Present the drafted ADR to the user at the operator gate. Show:

- The proposed filename and ID
- The full frontmatter
- The full body

Before presenting, self-audit: does the Decision section's central sentence fit under the title? If not, flag a possible second ADR. Does `## Consequences`, if included, name a non-obvious cost — or is it restating the Decision? If the latter, propose omitting it. Is `## Context` paraphrasing a doc already referenced? If so, tighten to one or two sentences pointing at the doc. Is `scope` the narrowest true value — would `universal` really constrain *every* feature, or is this a module, integration, or operational decision wearing a broad label?

If this is a supersession, also show the frontmatter change to the older ADR (status, superseded-by, date). If this is a narrowing, show the older ADR's frontmatter change too (`narrowed-by` added, `status` unchanged at `accepted`) and state in one line what the narrowing leaves in force — that is the claim the user is confirming, and it is the one a mistaken supersession would have destroyed. If the ADR being superseded participates in a narrowing pair (`narrows` or `narrowed-by` in its frontmatter), show the pointer updates to those third ADRs too — and where a narrowing ADR's exception may or may not survive the replacement decision, ask rather than assume (see Step 4's pruning rules).

Frame as: "Here's the ADR I'd write. Confirm to commit it to disk, or tell me what to adjust."

**Do not write any file until the user confirms.**

## Step 4: Write

After confirmation:

1. Create `docs/adr/` if it does not exist.
2. Write the new ADR to `docs/adr/NNNN-kebab-title.md`.
3. If superseding, update the older ADR's frontmatter:
   - Set `status: superseded`
   - Add or extend `superseded-by: [<new-id>]`
   - Leave the body completely untouched.
   - If the older ADR carries `narrows` or `narrowed-by`, prune those pointers per the paragraph below — a retired ADR must not stay referenced by a live one.
4. If narrowing, update the narrowed ADR's frontmatter:
   - Add or extend `narrowed-by: [<new-id>]`
   - **Leave `status` as `accepted`.** Do not change it. Do not add `superseded-by`.
   - Leave the body completely untouched.

**Superseding either side of a narrowing pair prunes the pointers.** If the ADR being superseded carries `narrows: [ADR-T]`, the exception it carved dies with it: remove its ID from each target's `narrowed-by` (deleting the field if empty) — unless the new ADR re-asserts the exception by carrying its own `narrows: [ADR-T]`, in which case update the target's `narrowed-by` to the new ID instead. If it carries `narrowed-by: [ADR-X]`, whether ADR-X's exception survives against the replacement decision is a judgement — it was asked at the gate. If it survives, rewrite ADR-X's `narrows` entry to the new ID and add `narrowed-by: [ADR-X]` to the new ADR; if not, remove the retired ID from ADR-X's `narrows` (deleting the field if empty). ADR-X's own `status` never changes either way.

**Both sides of a relationship are written together.** A `narrows` or `supersedes` field on the new ADR and the matching `narrowed-by` or `superseded-by` on the target are one write, not two steps that might be separated. Write the new ADR and the target's frontmatter update before doing anything else — before running `/b-index`, before emitting the handoff. If the target file cannot be written (missing, unreadable, malformed frontmatter), stop and report it rather than leaving the new ADR on disk claiming a relationship the other side does not record. This command is the only writer of both fields, and that is what keeps them consistent; there is no later reconcile pass that would notice a half-written pair.

5. Run `/b-index` to regenerate `docs/adr/index.md` (and `docs/index.md` if it references the ADR section). If `/b-index` is not available in this session, write a minimal `docs/adr/index.md` yourself — see schema in `b-index.md`.

## Step 5: Handoff

Emit a single short handoff block. The next move depends on context:

- If invoked from `/b-feature` reconcile: `Run /b-feature <name>` to return to the parent change. (In practice the parent command resumes automatically; the handoff is a safety net for restarts.)
- If invoked from `/b-design` Stage 2: continue Stage 2 (the parent command handles it).
- If invoked directly: `(none — ADR recorded; resume your next task)`.

```
ADR-NNNN recorded: <title> [<status>]
<Filename>
<If supersession: ADR-MMMM marked superseded.>
<If narrowing: ADR-MMMM narrowed (still accepted).>

Next move:
  - <literal slash command, or "(none — ADR recorded; resume your next task)">
```
