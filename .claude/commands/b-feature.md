---
description: The everyday change command (add / modify / remove within existing architecture) — orient, propose, gate, plan, delegate implementation, reconcile.
argument-hint: the user's description of what they want to change
---
<!-- GENERATED FILE — do not edit. Source: skills-src/commands/b-feature.md. Regenerate: node scripts/build-adapters.cjs -->

# Bower Change

You are running the Bower change workflow — the everyday command for any work that fits within existing architecture. One gate before any code is written.

This command covers three intents:

- **Add** — a new feature within an existing module, a new component, a new capability that fits the current architecture.
- **Modify** — change the behaviour, contract, or implementation of something that already exists.
- **Remove** — delete a feature, component, or capability that's no longer wanted.

The shape is the same across all three: read context → propose → gate → implement → reconcile → update docs. The differences show up in *which* files you read in Step 1 and *which* docs you update in Step 6; those branches are called out where they apply.

<intent_redirects>
Before proceeding, check whether this request is actually for this skill:

- **Architectural revision** (new module, new technology, scope expansion) → recommend `/b-design`. **Hard** redirect — see the constraint at the bottom of this file.
- **Pure experience-surface change** (navigation, screen composition, layout grammar, interaction patterns) → recommend `/b-ui` for branching choices, or the appropriate ad-hoc path in `_bower/framework.md` → *UI Changes — Paths and the Gate*. **Soft** redirect.

Backend feature work and small under-the-hood code changes belong here. **Mixed work stays here** — a feature that includes backend (model, API, controller) plus UI scaffolding (a new screen, components) runs in `/b-feature` and reconciles `docs/ui.md` in Step 6 alongside the feature's `plan.md`. Pure-UI work routes out; mixed work stays.
</intent_redirects>

The request (the user's description of what they want to change): $ARGUMENTS

## Important Behavioural Rules

- **Consult before building.** Present your proposal at an operator gate (binding: `_bower/framework.md` → *Runtime bindings*) and get explicit confirmation before writing any code. The user is an engineer — they expect to review the plan.
- **Read first.** Read the existing architecture, relevant module docs, and any affected plan.md/status.md files before proposing changes.
- **Scope tightly.** Only propose changes needed for this specific request. Don't redesign what works.
- **Acceptance is explicit.** Propose how the change will be verified (tests, manual checks, or both) and get agreement on that too.
- **Plan is the recovery anchor.** Write `plan.md` immediately after the gate, before any code is touched (Step 3). The plan is intent on disk — if the session crashes mid-implementation, this file plus `git status` is what makes recovery possible. The completion stamp and any implementation footnotes are appended at Step 6, not written from scratch there.
- **Implementation is delegated.** After the gate and the plan write, a fresh `bower-implementer` subagent implements and tests against the approved plan and returns an implementation report; you retain the gate, acceptance and decision reconciliation, and doc updates. Fall back to inline implementation only if this runtime cannot delegate — and say so explicitly when you do (Step 4.4).
- **Literal-command handoff.** Every "next move" you emit (in `status.md`, in any handoff line) names the exact slash command to type next, never free prose. "Run `/b-integration foundation`" — yes. "Write the integration test next" — no.
- **Stored next moves are feature-scoped; printed ones are project-scoped.** The `Next move:` written into a feature's `status.md` may only name work on *that* feature (Step 6.7). What to do next given the whole project — the next feature, integration, review, the next module — is printed in the Step 7 handoff and never stored, because nothing rewrites every feature's `status.md` to keep such a line true.

## Step 1: Understand Context

Orientation is **selective**: read what this change needs, not the whole project. Batch all independent reads — issue them together, not one per turn.

1. Read `docs/index.md` and the affected module's `module-status.md` (batched) — project structure, `## Build order`, and the `## Module integration` `Notes:`. **Glob `docs/modules/*/{review-plan,findings}.md` in the same batch** (item 10 acts on the result). One call covering both kinds of tracked finding — an open review plan, and a module's findings queue — and empty on most projects, but a routed finding may be the reason this invocation is happening at all.
2. Read the target feature's `plan.md` and `status.md`, plus those of any other components likely affected. **If this feature's build-order entry carries a scope-reduced annotation, that annotation wins over the plan.** It was written by the feature that absorbed the scope; the plan was written before the absorption and now overstates what is left. Treat the annotation's `Remaining:` clause as the real scope, verify against the code rather than assuming either document is current, and say so in Step 2's proposal — the operator agreed to the original plan and needs to see that the change shrank.
3. Read `docs/architecture.md` **selectively**: the system overview, the affected module's `## Software architecture` subsection, and any named data flows or constraints the change touches. Read the whole file only when the change crosses sections or you cannot confidently locate it within them.
4. **Load relevant ADRs.** If `docs/adr/index.md` exists, read it. From the index, identify ADRs with `status: accepted` that (a) have `scope: universal`, (b) list the affected module(s) under `modules`, (c) have a `topics` entry matching the change, or (d) have a title topically relevant to the change — e.g. an ADR about caching strategy when the change touches a cache, even if it's filed under another module. An ADR with no `scope` and no `modules` is *unclassified* (pre-v0.20) — load it on topical or title match only, never wholesale. Open and read each selected ADR. These are the constraints the proposal must respect or explicitly contradict. Skip if no `docs/adr/` exists.
5. **For modify or remove intents:** search sibling `plan.md` files in the module for exact references to the feature, API, or component being changed (Grep, not full reads); open only the matches. Other features' plans often describe interactions with the thing you're changing — those references go stale if you don't catch them. List any that need updating in the Step 2 Impact section.
6. Read `docs/scope.md` only when the intent is add or remove, or you suspect the change moves the scope boundary. Note that criteria carry no status here — a change that *achieves* a criterion is not by itself a reason to read or write this file.
7. Read the relevant sections of `docs/ui.md` (if it exists) once UI impact is established — the change touches a screen, adds UI scaffolding, or could shift navigation, layout grammar, or interaction patterns. Even backend-heavy work often introduces a screen as scaffolding; the experience surface needs to reconcile in Step 6.
8. Do **not** read `docs/constitution.md`'s testing detail here — it goes to the implementer in the Step 4 packet. Read other conventions from it only if the proposal itself needs them.
9. Read relevant source code to understand the current implementation — batch the files the plans name; don't rediscover what the component maps already locate.
10. **Check for a routed finding — in every file item 1's glob returned, not just this module's.** A review's findings stay in the *reviewed* module's plan even when the fix belongs elsewhere: `/b-review` writes `Run /b-feature modify billing <slug>` into `auth`'s plan and nothing is ever written on billing's side. So the file that owns this invocation's finding is frequently a module you are not touching, and one whose `Review:` marker you have no reason to read. Read each returned file's `## Findings` checklist and look for an open `route:/b-feature` item whose command matches this invocation. Match in this order:

    1. **An explicit finding reference in the request.** Routed commands end `according to <ID> in <path>`, so an operator who pasted one has handed you the file and the ID outright — open that file and take that finding. This wins over everything else and is never overridden by a slug that disagrees. Accept looser forms too (`F1`, `review finding F1`, `according to F1 in the review plan`, `Q2 in the findings queue`), but note that **an ID without a path is ambiguous** — IDs are local to the file that holds them, so `F1` exists in every open review plan and `Q1` in every queue. If more than one file has an open item with that ID, ask rather than picking.
    2. **The slug** in `Run /b-feature modify <module> <slug>`, across every file the glob returned.
    3. **A topical match on the gist**, which is a guess — say so when you rely on it.

    If the operator named a finding that is not in the file they named, or is already disposed of, say so and ask rather than silently falling through to a slug match. **If the item they named is `route:/b-design`, stop and redirect** — that is the architectural hard guard arriving by another door, and an explicit reference does not override it. The route out is `/b-design`, which re-classifies the item to `route:/b-feature` once its decision has landed; come back then. If one matches, read its indented `Location:` / `Drift:` / `Resolution:` brief.

    **That brief is a primary input, not background.** Whoever wrote it saw something you cannot see from here, and their context is gone — that is true of both kinds. Treat `Drift:` as an observation to verify against the code, not as a conclusion to accept: if the code no longer shows it, say so in Step 2 rather than inventing work. Cite the finding ID **and the file that holds it** in the proposal, so the operator can tie it back.

    **Which file matched changes the provenance you state and the handoff you emit — nothing in between.** The two carry the same line shape and the same brief, so everything from here to Step 6 is identical:

    - **`review-plan.md`, IDs `F<n>`** — diagnosed by `bower-reviewer` against the whole module at once, which is a view this command does not have; weigh the brief accordingly. The item holds a review open, and `/b-review` owns the file and audits your tick at closeout. Name the **module whose plan holds it** in the Step 7 handoff alongside `/b-review`: the review to resume is the one that *found* the drift, which on a cross-module finding is not the module you just changed.
    - **`findings.md`, IDs `Q<n>`** — the module's findings queue: recorded outside any review, by whatever command happened to be running when the drift was noticed, which may have been surveying nothing wider than its own change (spec: `_bower/framework-reference.md` → *Findings queue*). There is no plan, no review, and no owning command — so there is nothing to resume, nothing holds open, and **nothing will audit your tick**. That is a reason to confirm the drift is really gone before making it, not a reason to be casual. Tick it the same way; if it was the **last open item in that file, delete the file** in the same pass, since an empty queue on disk is a broken state.

    **You may tick this one box, and only this one.** Once Step 5's acceptance reconciliation has passed and Step 6's doc updates have landed, rewrite that finding's `[ ]` to `[x]` in the file that holds it and append a completion note naming what discharged it and when (Step 6.11 fires this):

    ```
    - [x] F2 — non-owner 404 vs 403 — route:/b-feature — Run /b-feature modify auth non-owner-response-consistency according to F2 in docs/modules/auth/review-plan.md — done 2026-08-10 via /b-feature non-owner-response-consistency
    ```

    Leave the rest of the line intact, briefs included — the tick is the only edit. Nothing else in that file is yours: not other findings, not a `[~]` won't-fix, not a re-classification, not the briefs, not `module-status.md`'s `Review:` marker, and — in a `review-plan.md` — never the file's deletion. In a review plan `/b-review` owns all of that and re-verifies your tick against the code before closing; in a queue nobody does, so the same restraint is yours to keep rather than another command's to enforce. Either way your note is not the evidence — it tells a later reader which command and which date to attribute the claim to.

**Inputs-selected ledger.** Close orientation with a short ledger (a few lines) naming what you read and what you deliberately skipped and why — e.g. "skipped scope.md: modify intent, boundary unchanged." This keeps omissions auditable at the gate.

**The ledger always states the tracked-findings outcome**, in one line covering both kinds, even when there is nothing to report — `tracked findings: none open`, `tracked findings: auth review-plan (3 open), billing queue (1 open) — none route here`, or `tracked findings: auth F6 loaded — routes into this module from auth's review`. Name the files the glob found, not the module being changed: a bare "no open review" is the answer to a question nobody asked when the finding lives in another module's file. This is the one ledger entry with no "deliberately skipped" form. Everything else in Step 1 is selective by design, so an absence is ambiguous; here an absence means the check did not happen, and the operator can say so at the gate before a proposal is built on a finding nobody read.

**Intent re-check.** After reading, ask once: is this work primarily on the experience surface (navigation, screens, interaction patterns, layout, copy) with at most incidental backend? If yes, stop and recommend `/b-ui` for branching choices or the ad-hoc path described in `_bower/framework.md`. Mixed work (backend + UI scaffolding for a new feature) stays here; pure-UI work routes out. The intro redirect handles the obvious cases; this re-check catches the ones that become clear only after reading.

**ADR posture.** Treat accepted ADRs as constraints to confirm against current code, not as ground truth. If an ADR names a specific library, file, or flag and the code contradicts it, the ADR is the stale one — flag it in the proposal so the gate can decide whether to supersede. Do not silently rely on a stale ADR.

**Build order check:** If the requested change is **adding a new feature** to a module, append it to the module's `## Build order` as part of Step 6 — the build order is a living document, not a Stage-4 contract. If the requested change is on a feature that is part of a module with a `## Build order` and earlier features in that order are not yet complete (not ✓), surface this to the user as part of the proposal in Step 2. Do not hard-block — warn and let the user proceed anyway. Working out of order is sometimes the right call; the warning exists so it's a conscious choice.

## Step 2: Propose Changes

Prepare a proposal covering:

- **Intent:** Add, modify, or remove. (Just one — if multiple, run them as separate changes.)
- **What changes:** Which components/modules are affected and how
- **Technical approach:** What you'll actually do (new files, modified files, deleted files, patterns used)
- **Impact:** What else this touches:
  - **Source:** integration points and any callers / consumers of changed behaviour
  - **Tests:** which existing tests need updating or removing; which new tests are needed
  - **Docs:** **list each `plan.md` that needs updating by path** (the one for this feature, plus any sibling features whose plans reference behaviour you're changing or removing). Don't bury this under "documentation" — name the files.
  - **UI:** if the change introduces, removes, or restructures any screen/view/component, name which sections of `docs/ui.md` will be created or updated (navigation, screens, layout grammar, interaction patterns, visual language). If `docs/ui.md` does not yet exist and the change introduces UI, this is the first UI in the project — Step 6 will create the file with the sections this change requires. Write `none` if the change is pure under-the-hood code.
  - **Module integration:** does this shift what the module's integration test must assert? If yes, the test itself likely needs updating — flag it here so the Step 6 `Next move:` can point to `/b-integration <module>`.
- **Scope impact:** Does this change what's in scope, change a non-goal, or add/remove/reword a success criterion in `scope.md`? Merely *satisfying* an existing criterion is not scope impact — criteria carry no status and are not updated when work lands.
- **Decision impact:** List any accepted ADR loaded in Step 1 that this change *touches* — i.e. the change either confirms it (no action needed), contradicts it (must supersede), narrows it (a narrowing ADR — the old decision stays `accepted`), or surfaces it as drifted from the code (the ADR is stale and should be superseded). If no ADRs are touched, write `none`. Also note if this change introduces a new cross-cutting decision that does not yet have an ADR — flag it here so the reconcile step can write one.
- **Acceptance criteria:** How we'll know this works. Be specific:
  - Tests to write, update, or remove (with brief description of what each verifies)
  - Manual verification steps if applicable
  - Edge cases to consider
- **What you won't change:** Explicitly note anything adjacent that you're leaving alone

Mark your recommended approach if there are alternatives.

## Gate: Confirm or Adjust

Present the proposal to the user at an operator gate. Frame it as:

"Here's what I propose to change and how I'll verify it works. Confirm to proceed, or tell me what to adjust."

Include the acceptance criteria in the question — these are part of the agreement, not an afterthought. The choices are: **confirm** (proceed as proposed), **adjust** (free-form changes — revise and re-present the gate), or **cancel**.

**Do not write any code until the user confirms.** Stop and wait; proceed only on an explicit applicable answer — silence or an unrelated reply is not acceptance.

## Step 3: Write the Plan

After the user confirms at the gate, write `plan.md` *before* any code is touched. The plan is the durable record of intent: if the session crashes mid-implementation, this file plus `git status` is what makes recovery possible. Most of `plan.md`'s content is plannable — the proposal you just got confirmed names it. Write that content now; only the retrospective tail (final test counts, implementation footnotes worth keeping, the completion stamp) is deferred to Step 6.

**For add intent:** create `docs/modules/<module>/<feature>/plan.md` with the sections the feature warrants:

- **Purpose** — what the feature does, what it does *not* do (from the proposal's intent and "What you won't change").
- **Components** — a file table from the proposal's "Technical approach": each file by path with a one-line purpose. This is the spine of the recovery anchor.
- **Schema / API surface / Access model** — if the feature introduces a table, API, or access boundary, document the shape now. The proposal already named these.
- **Configuration** — env vars, settings, or dependency mounts the feature requires (write `No new env vars.` if none).
- **Integration points** — which other modules this feature consumes from or exposes to.
- **Testing** — the acceptance criteria from the gate expressed as test *categories* (e.g. "CRUD round-trip", "non-owner returns 404", "FK ON DELETE RESTRICT"). Specific counts ("12 cases") and pass/fail evidence are filled in at Step 6.
- **Implementation trajectory** (multi-session features only) — phase plan; compress earlier phases to one-paragraph précis as they complete.

**For modify intent:** rewrite the affected sections of the existing `plan.md` to reflect the *intended end state*. Delete claims that no longer hold; the doc represents current state, not history. The file becomes briefly aspirational (reflects the change before the code does) — this is intentional. It is the recovery anchor.

**For remove intent:** no plan.md work at this step; the file is deleted in Step 6.

The plan written here is what survives a crash. Implementation footnotes that emerge during Step 4 (a workaround for a specific bug, a hand-edited migration, a non-obvious cast) and the `Confirmed YYYY-MM-DD` stamp are appended at Step 6.

## Step 4: Implement (delegated)

After plan.md is written, implementation runs in a **fresh `bower-implementer` subagent**, not in this context. The isolated context is the point: this conversation carries the orientation and proposal history, and none of it is needed to execute the approved plan — the plan is the contract. Do not implement inline when delegation is available.

1. **Assemble the spawn packet.** Pass paths for on-disk content, values only for conversation-only content:
   - The approved `plan.md` path. (For **remove** intent, where Step 3 wrote nothing: the existing `plan.md` of the feature being removed, plus the confirmed list of files to delete.)
   - The intent (add / modify / remove).
   - The **acceptance criteria verbatim**, including any amendments made at the gate — these exist only in this conversation, so they go by value.
   - The "What you won't change" list from the proposal.
   - The feature's `status.md` path and the module's `module-status.md` path (orientation only).
   - The paths of the Step 1 ADRs that constrain implementation, each with a one-line reason.
   - The names of the relevant `docs/architecture.md` sections (not the whole file).
   - A pointer to `docs/constitution.md`'s testing section (runner command, fixtures, verified-for-✓ rules).
   - The project root.
2. **Delegate to `bower-implementer`** with the packet. It implements, writes and runs tests, and returns an implementation report with fixed sections: `## Outcome`, `## Changed files`, `## Acceptance mapping`, `## Test run`, `## Divergences`, `## Implementation footnotes`, `## Doc implications`.
3. **Branch on the report's `## Outcome`:**
   - **COMPLETE** — proceed to Step 5, carrying the report.
   - **DIVERGED-STOPPED** — the implementer hit a significant divergence and stopped with a coherent tree. Present the divergence to the user at an operator gate — this is the re-gate. On their decision, amend `plan.md` to the agreed direction yourself, then delegate to a fresh `bower-implementer` with the amended plan plus the previous report's `## Changed files` as resume context. (Subagents are one-shot; the changed-files list plus the working tree is the continuation state — the same recovery discipline as a crashed session.)
   - **BLOCKED** — an environment or tooling failure. Surface it to the user verbatim; do not silently retry.
4. **Fallback — delegation unavailable.** This is the caller's move, per *Runtime bindings → Delegation*: state one deliberate line — "Subagent unavailable; implementing inline (expect higher context usage)." — then implement, test, and handle divergence yourself under the same rules the implementer follows (minor divergence: update `plan.md` and continue; significant: stop and re-gate with the user), and construct the same report sections before Step 5, with `Context: inline` at the top of the report — Steps 5 and 6 consume one shape regardless of path.

## Step 5: Acceptance Reconciliation

Before marking the feature done, produce an explicit reconciliation of every acceptance criterion agreed at the gate. Start from the report's `## Acceptance mapping` — verify it, don't re-derive it. If any PASS line looks thin (a vague test name, a count that doesn't match the criteria), re-run the named test command once to confirm. Each criterion maps to evidence:

```
- <criterion> — test: <path::name> — PASS
- <criterion> — test: <none written> — MISSING
- <criterion> — manual: "<check description>" — PENDING USER
```

Handling:

- **MISSING** is a blocker. Either write the test, or return to the user at an operator gate to renegotiate the criterion. Do not proceed with MISSING items.
- **PENDING USER** — present the manual checks to the user at a batch gate, collecting an explicit disposition per check: confirmed (mark PASS), failed (treat as a bug and fix before proceeding), or deferred ("I'll check later" — leave as PENDING USER and mark the feature 🚧 rather than ✓, see Step 6). Do not act on any check's answer until every check has one.

**Decision reconciliation.** After acceptance criteria are reconciled, review the **Decision impact** noted at the gate — and additionally check the report's `## Divergences` and `## Doc implications` for ADR touches that weren't visible at the gate. For each touched ADR:

- **Confirmed** (change implements the decision as recorded) — no action.
- **Contradicted / drifted** (change violates an accepted ADR, or the ADR was already stale relative to the code) — invoke `/b-adr` to write a new ADR superseding the old one. Pass the rationale and the ADR-ID being superseded in the description.
- **Narrowed** (change scopes an exception without invalidating the original) — invoke `/b-adr` to write a narrowing ADR. Pass the rationale and the ADR-ID being narrowed. The new ADR carries `narrows: [ADR-NNNN]`, the old one gains `narrowed-by` and keeps `status: accepted`.
- **New cross-cutting decision** (change introduces a commitment that didn't have an ADR) — invoke `/b-adr` to record it.

Skip only if no Decision impact was identified at the gate (Step 2 listed it as `none`). Otherwise this is not optional — silent decision drift is exactly what the ADR mechanism exists to prevent.

If the user rejects the drafted ADR at `/b-adr`'s gate, treat that as a request to redraft with their adjustments, not as permission to skip. If they want to abandon ADR creation entirely, return to this reconciliation step and re-classify the impact (likely "confirmed" rather than "new decision"). Complete any ADR work before continuing to Step 6.

**Constitution reconciliation.** If the implementation report carries a `## Constitution contradictions` section with entries, handle each one here — before Step 6, and never inside it. `docs/constitution.md` is human-owned, so this is not a reconcile you perform; it is a consent request the user answers.

For each entry, print the evidence in full and unparaphrased:

```
docs/constitution.md:41 says, verbatim:
  "Every module boundary is covered by a contract test, run in CI on every PR."

The implementer found: no contract tests exist; .github/workflows/ci.yml:18 runs
only `pytest tests/unit`. This feature's tests were written against the unit
runner instead.
```

Then ask at an operator gate whether to edit the file, offering: correct the claim to match reality · move it under `## Not yet in force` (it was an aspiration) · leave it alone. Only on an explicit instruction to change it do you edit `constitution.md` — that instruction is what makes the edit *prompted*, which ownership permits. Silence, a deferral, or "noted" all mean leave it.

Three rules that are the point of the step:

- **Verbatim and located, always.** Quote the line and give `docs/constitution.md:NN` so the user can open the file and read it in context. A summary of the contradiction invites a rubber-stamp; the objective is to get the human into the doc.
- **Never fold this into Step 6.** Step 6 is agent-owned doc maintenance that runs without a gate. A human-owned doc must not be edited on that path, even when the correction looks obvious.
- **Never bury it.** Do not reduce a contradiction to a line in the handoff summary because the feature otherwise passed. A false convention that survives this pass will mislead the next fresh context exactly as it misled this one, and nothing else in the framework is looking for it.

If the user declines the edit, that is a legitimate outcome — record nothing, change nothing, and move on. Their file, their call.

## Step 6: Update Documentation

The exact set of documents to touch depends on the intent. Common to all intents: `status.md` is rewritten from scratch, `module-status.md` build-order markers reflect reality, and `scope.md` is updated if the change shifted scope.

**Completed plans describe the system, not the build.** When finalising `plan.md` (add and modify intents), keep purpose, the current behavioural contract, the component map, integration points, and testing *categories*. Compress dated counts and implementation history aggressively — the resumption record and git hold those. A footnote earns its place only when a future reader would otherwise have to dig it out of git. If the plan reads like a changelog, trim it back to current state.

**For add intent:**

1. Finalise `plan.md`. The bulk of the file already exists from Step 3 — this step appends the retrospective tail, drawn from the implementation report:
   - Update the **Testing** section with final test counts from the report's `## Test run` and any test names worth surfacing (e.g. "12 cases against per-test schema").
   - Append any **implementation footnotes worth keeping** from the report's `## Implementation footnotes`: workarounds for specific bugs, hand-edited migrations, non-obvious casts at boundaries — the kind of detail a future reader would otherwise have to dig out of git. Skip if nothing surprising came up.
   - Add a closing line: `Confirmed YYYY-MM-DD` (today's date) once acceptance criteria reconcile. This line is the visible completion flag; a `plan.md` without it is not done.
2. Append the new feature to `module-status.md` `## Build order`. Place it where its dependencies dictate; if it has none, append to the end. Mark ✓ if all criteria PASS, 🚧 if PENDING USER.
3. Refresh `## Module integration` `Notes:` if the new feature widens what the integration test must assert. Do not flip the marker.

**For modify intent:**

1. Finalise `plan.md`. The intended-end-state edits already landed in Step 3. This step appends the retrospective tail, drawn from the implementation report:
   - Update the **Testing** section with final test counts (from `## Test run`) for any new/changed tests.
   - Append implementation footnotes worth keeping (from `## Implementation footnotes`).
   - Refresh or add the `Confirmed YYYY-MM-DD` line.
   - If during Step 4 the implementer diverged from the Step 3 plan, the plan should already reflect reality (minor divergences are edited in flight and listed under `## Divergences`) — verify and tidy any stale fragments.
2. Update each sibling `plan.md` listed in the Step 2 Impact section — fix outbound references to the changed behaviour. Cross-reference the report's `## Changed files` and `## Doc implications` for sibling plans the proposal missed; update those too and note it in the resumption summary.
3. Refresh `## Module integration` `Notes:` if the test's assertions need to shift (the report's `## Doc implications` flags this). If yes, the `Next move:` below points to `/b-integration` so the test itself gets updated.
4. If the feature is multi-session, update `## Implementation trajectory` in `plan.md`: compress the just-completed phase into a one-paragraph précis (why-focused, not steps); leave future phases detailed.

**For remove intent:**

1. Delete the feature's `plan.md` and `status.md` files; remove its directory under `docs/modules/<module>/<feature>/`.
2. Remove the feature from `module-status.md` `## Build order`.
3. Update each sibling `plan.md` listed in the Step 2 Impact section — strip references to the removed behaviour.
4. Refresh `## Module integration` `Notes:` if the test's assertions need to shrink.
5. Update `architecture.md` only if the removed thing was named there as a public surface. If you find yourself rewriting architecture, stop — this isn't a `/b-feature` change. Recommend `/b-design`.

**All intents:**

6. **`docs/ui.md`** — if Step 2's Impact section listed UI sections to update, reconcile now:
   - If `docs/ui.md` exists, update affected sections to reflect the new state (current-state doc, not history).
   - If it does not exist *and* this change introduced UI (the project's first interface scaffolding), create `docs/ui.md` with only the sections this change requires. Stay at invariant-level: navigation map, screen inventory, layout grammar, interaction patterns, visual-language pointers. Pixel-level detail belongs in code, not the doc.
   - If Step 2 listed UI impact as `none`, skip.
7. Rewrite this feature's `status.md` from scratch — never append to the previous contents. Which form you write depends on the marker this feature is about to carry in Step 9 (schema: `_bower/framework-reference.md`, "status.md — Resumption Framing"). (Skip this for remove — the file is gone; resumption guidance lives in the next-move handoff below.)

   **If the feature lands ✓** — every agreed criterion PASS, nothing PENDING USER — write the **terminal form**: the marker, a `## Verification` section (date, what was run, what passed, plus a `Qualification:` line if the evidence carries a standing caveat), and `## Next move` → `(none — complete)`. ~50 words. Compress, don't delete — `## Verification` is the only durable record that the criteria were exercised. A `Qualification:` is **not** a `Pending verification:` line: the first bounds evidence that *was* gathered, the second names evidence that wasn't, and a ✓ feature carrying the second is a false-completeness error.

   **If the feature lands anything else** — 🚧 with PENDING USER items, or 🟡/🔴 — write the **live form**: current state, next move, `Pending verification:` listing the deferred checks. ≤150 words.

   The stored `Next move:` is **a literal slash command, not prose**, and it may only name work on *this* feature. Exactly one of:

   - `Run /b-feature <this feature>` — the deferred checks or the broken thing need another pass on this feature.
   - `(none — complete)` — the feature is ✓.

   It does **not** point at the next feature in the build order, at `/b-integration`, at `/b-review`, or at the next module. Those are project-scoped, they go stale the moment anything else lands, and nothing rewrites every feature's `status.md` to correct them. They belong in the printed handoff below, which is transient by construction.

8. Update `scope.md` only if the change shifted the scope boundary, changed a non-goal, or added/removed/reworded a success criterion. Do **not** record that a criterion is now met — criteria have no status field, and achievement is derived from module completion by `/b-recap`. If a criterion is deleted, delete it outright; scope carries no history.
9. Update `module-status.md`: update the `## Build order` marker for this feature. Use ✓ only if all criteria are PASS; use 🚧 if manual checks remain PENDING USER; use 🟡 or 🔴 if something is broken. Do **not** flip the `## Module integration` marker here — that belongs to `/b-integration`.

   **Then annotate any downstream entry whose scope this change absorbed.** If the implementation report's `## Doc implications` names a later build-order feature whose scope now partly exists — or you can see for yourself that it does — append a single clause to *that* entry: who absorbed what, then `Remaining:` and what is left to build. This is the one case where reconcile writes an entry other than its own.

   ```
   7. framing-probe-personas — ⏸ (scope reduced by feature 3: persona receives
      framing per ADR-0014; and feature 5: framing-target annotations.
      Remaining: the curated catalogue definitions.)
   ```

   Do this only when scope genuinely moved — not for every dependency touched — and keep it to one line, since `module-status.md`'s ~250-word budget is shared with the integration notes. Do not edit the downstream feature's `plan.md`: it does not exist yet for an unbuilt feature, and where it does, rewriting a plan outside its own gate is not this step's business. The build-order line is the durable place, because it is in the next pass's orientation set. If the absorption leaves nothing to build, write `Remaining: none — verify and close via /b-feature <name>` and leave the marker ⏸; do not promote it to ✓ on another feature's passing criteria.
10. Run `/b-index` if module status markers changed. Do **not** hand-edit `docs/index.md` as an alternative — its status is derived from the markers you just wrote, and prose appended there has no writer that ever compacts it (see *Status is never curated* in `b-index.md`). If `/b-index` is not invokable, leave the index to the next regeneration; the markers you wrote in `module-status.md` are the durable record.
11. **Tick the routed finding, if this change discharged one.** If Step 1.10 loaded an open `route:/b-feature` item and the drift it named is now gone, tick that box and append the completion note, exactly as Step 1.10 specifies. Do it here, last — after acceptance reconciled and the docs landed. A tick written earlier is a claim about work that had not happened yet. If the drift is **not** gone (the gate narrowed the change, the operator cut scope, the finding turned out to be wrong about the code), leave the box open and say so in the Step 7 handoff. The disposition is not yours to make: in a review plan it is `/b-review`'s, and in a queue it is the operator's — a won't-fix is a decision either way, and re-classification follows a design run, not a narrowed feature change.
12. **Out-of-scope drift — offer to queue it.** If this run surfaced a real problem you were not invoked to fix — a sibling plan that disagrees with its code, something the implementation report raised under `## Divergences` or `## Doc implications`, a second instance of the bug you just fixed elsewhere — do not fix it, and do not let it die in the console. Offer at an operator gate to record it in `docs/modules/<module>/findings.md`, one item per drift, and write nothing unless they say yes: a silent append is tracked work the operator never agreed to.

    On confirmation, create the file from the template in `_bower/framework-reference.md` → *Findings queue* if it does not exist, number `Q<n>` from the file's existing high-water mark, and write the full line **now** — including the three-line `Location:` / `Drift:` / `Resolution:` brief, while the evidence is still in front of you. The brief is the entire handoff to whoever picks the item up in a fresh context; a line written later from memory is the note-to-self the queue exists to avoid. Put the item in the module that owns the drifted code, which is not always the module you were changing.

## Step 7: Handoff

Emit a single handoff block. This is where the **project-scoped** next move lives — what the operator should do next given everything that is now true, not just what is true of this feature. It is printed and transient by design: it goes stale as soon as anything else lands, which is exactly why it is not written into a file.

```
<feature> in <module>: <✓ | 🚧 pending verification | 🟡/🔴>

Next move:
  - <one of:>
    Run /b-feature <name>                      (next ⏸ feature in the module's build order)
    Run /b-feature <this feature>              (this feature's PENDING USER checks or a 🟡/🔴 fix)
    Run /b-integration <module>                (the test's assertions shifted, or this was the
                                                last non-✓ entry and integration is still ⏸/🚧)
    Run /b-review <module>          (optional)  (this change completed the module — every feature ✓
                                                and integration ✓; see the note below)
    Run /b-module <name>                       (next module, if small and well-specified)
    Run /b-design                              (the change revealed an architectural shift; rare,
                                                usually surfaced earlier)
    Run /b-recap                               (next steps depend on user judgement)
    (none — project genuinely done)
```

Pick exactly one — **except** when this change discharged a routed finding from a module's `review-plan.md` (Step 1.10). Then the next move is `/b-review <reviewed-module>`, with the finding ID. This is not a bookkeeping trip: you have already ticked the box, so the review is where the *remaining* findings get mediated and where closeout becomes available if yours was the last open item. Say which finding you ticked and whether anything else in that plan is still open, so the operator knows whether they are resuming work or closing a review. The reviewed module is the one whose plan holds the finding, which for a cross-module finding is *not* the module you just changed — naming the changed module here sends the operator to a review that does not exist. If you left the finding **un**ticked (Step 6.11), say that instead, and say why: `/b-review` is then the command that decides between won't-fix and re-classification.

**A `findings.md` item is different — there is no review to resume.** Ticking a `Q<n>` opens nothing and closes nothing, so pick the normal next move from the list above. Say in one line which queue item you discharged and how many remain open in that file, or that you deleted the file because that was the last one.

When it is `/b-review <module>`, frame the review as optional — a small project may reasonably skip it — but name the command so it is one keystroke away, and add one clause that it is resumable: a review opens a state (`Review: 🚧`) and re-running `/b-review <module>` picks up mediation rather than re-diagnosing, so the findings need not be dealt with in one sitting.
