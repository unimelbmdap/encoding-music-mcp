---
name: b-review
description: Fresh-eyes review of a completed module via the bower-reviewer subagent; reconciles owned drift behind one triage gate and routes the rest.
---
<!-- GENERATED FILE — do not edit. Source: skills-src/commands/b-review.md. Regenerate: node scripts/build-adapters.cjs -->

# Bower Module Review

You are running the Bower module-review workflow. This reviews **one completed (or near-complete) module** with fresh eyes, surfaces where the build diverged from what the docs, decisions, and rest of the module say it should be, and reconciles the divergences it can resolve itself — routing the rest to the commands that own them.

The review exists because a sequential, feature-at-a-time build systematically misses properties that only become visible once the module is whole: whether the tests cover the *interactions* between features, whether the docs still match the code, whether features built weeks apart answer the same question the same way. The implementing agent had every rationalisation for the current code in context; this command gets a fresh pair of eyes by delegating diagnosis to the read-only `bower-reviewer` subagent.

The request (the target module): the request as given in the message that invoked this skill.

## Important Behavioural Rules

- **Diagnosis is read-only; the apply is bounded.** The `bower-reviewer` subagent surveys and reports — it never writes. This command *acts*, but only on the **owned** reconciliation classes (`inline-reconcile`, `test-backfill`, `status-fix`, `adr-supersede`). Everything else is routed to `/b-feature` or `/b-design` as a literal-command next move. The command never makes a behavioural or architectural change itself.
- **Review is a state, not a single pass.** `## Module review`'s `Review:` marker in `module-status.md` goes ⏸ → 🚧 at the triage gate and 🚧 → ✓ only at closeout, when every accepted finding carries a disposition. Between those points the module is *in review*, the plan is on disk, and the operator can leave and come back across as many sessions as the work takes. Re-invoking `/b-review <module>` while the marker is 🚧 **resumes mediation** — it never re-diagnoses.
- **The plan tracks every accepted finding, owned and routed alike.** `docs/modules/<module>/review-plan.md` holds one `## Findings` checklist. Owned/routed decides *who acts*, not what is tracked. This is what stops a pile of `/b-feature` findings scrolling off the console with no record. A plan is written whenever there is at least one accepted finding, **including a routed-only review**. Routed items additionally carry the reviewer's `Location`/`Drift`/`Resolution` verbatim (Step 3) — they are deferred into a fresh context, so the plan line is their entire handoff.
- **A finding is discharged when its drift is gone, not when a command has run.** The two coincide for `/b-feature` and come apart for `/b-design`, which produces a decision rather than a change. Ticks are verified against the code.
- **You are not the only writer of a tick, and you are the only auditor of one.** A `route:/b-feature` item is normally ticked by the command that discharged it, which appends a completion note (`— done YYYY-MM-DD via /b-feature <slug>`). That is the right owner for a task list, and it is self-certification at the moment it happens — so a tick you *find* is a claim, never a fact, and the closeout audit is the framework's only independent check on it. Everything else in the plan is still yours alone: briefs, `[~]` dispositions, re-classification, the `Review:` marker, and the plan's deletion.
- **The plan is also the recovery anchor.** It is written *before* any reconciliation is applied, so a mid-apply crash leaves that file plus `git status` as the resumption material — same discipline as `/b-feature`'s post-gate `plan.md` write. It is transient: deleted at closeout, when the `Review: ✓` marker replaces it as the durable record.
- **One gate to start, one to close.** The triage gate authorises the work; the closeout gate confirms the review is finished. You do not re-gate each item in between, except that `adr-supersede` items run through `/b-adr`, whose own gate fires.
- **No findings log survives closeout.** What was fixed is in the commits; what was not was an operator decision. Do not write a findings history anywhere. The record is `Review: ✓ <date> (<N> of <N> features)` and nothing more.
- **Out-of-band volume is safe here by construction.** A review fix pass batches only changes that are *individually* ad-hoc-safe under existing framework rules: doc↔code reconciles (gate-free living-doc maintenance), test backfill for already-agreed behaviour, status-marker corrections, and ADR supersessions (gated by `/b-adr`). The one unsafe category — boundary erosion — is tracked in the plan but always routed to `/b-design` and never actioned here. The hard-redirect rule still holds.
- **Literal-command handoff.** Every routed finding and every "next move" names the exact slash command to type next, never free prose.

## Step 0: State Check

Before anything else, determine which mode you're in:

Confirm the module exists (`docs/modules/<module>/module-status.md` is present). If it does not, stop and say so — recommend `/b-recap` to find the right module name.

Read that file's `## Module review` section and check for `docs/modules/<module>/review-plan.md`. The pair decides the mode:

| `Review:` | plan on disk | mode |
|---|---|---|
| 🚧 | yes | **Resume mediation** — skip Steps 1–2, go to Step 5 against the plan's undisposed items |
| ⏸ or ✓ | no | **Fresh review** — proceed to Step 1 |
| 🚧 | **no** | **Broken state** — see below |
| ⏸ or ✓ | **yes** | **Broken state** — see below |

Re-diagnosing while a plan is open would discard in-progress work and re-derive findings the operator has already triaged; the open plan means mediation is already owed.

**If `## Module review` is missing entirely**, the project predates the section. Treat the module as never reviewed, say so in one line, and write `## Module review` with `Review: ⏸` before proceeding — do not infer a past review from git history or from prose elsewhere in the file.

**Broken state.** The marker and the plan are two sides of one fact, so a disagreement means a prior run died mid-flight or something hand-edited one of them. Do not guess. State what you found and ask the operator which to trust: the plan is the substantive artifact, so `🚧` + no plan is normally *"that review was lost — start fresh"*, and a plan present under `⏸`/`✓` is normally *"the marker was never set or was closed early — resume mediation and set it to 🚧"*. Act only on their answer.

Review is most valuable when the module is complete (all features ✓, integration ✓), but it does not hard-require completion; if the module is mid-build, note that the review will find expected gaps and let the operator decide whether to proceed.

## Step 1: Diagnose (delegate)

Delegate to the `bower-reviewer` subagent (binding: `_bower/framework.md` → *Runtime bindings*) and wait for its report. Pass it the module name and the project root. The subagent reads the module's `module-status.md`, each feature's `plan.md`/`status.md`, the constitution's testing conventions, the `## Software architecture` entry, the ADRs touching the module, and the code — then returns a **review report** conforming to `_bower/review-schema.md`.

Do not re-derive the review yourself or second-guess the subagent's findings inline. Its isolation is the point — it sees the code without the implementer's context. Your job is to consume the report, gate it, and execute against it.

**Fallback — delegation unavailable.** This is the caller's move: follow `bower-reviewer`'s definition inline, say so in one line, and mark the report `Context: inline`. Announce the degradation again at the triage gate — "diagnosis ran inline; adversarial freshness is degraded" — because the operator deciding there is entitled to weigh the findings accordingly.

## Step 2: Present the Findings

**Always print this block before the triage gate, in full, in this session.** The gate's options are meaningless to an operator who has not seen the findings: "confirm to action all owned items" is a blank cheque, and "let me deselect some" is impossible to answer about items nobody has read. This is a hard precondition on the gate, not a narrative step — printing a count and going straight to the question is the failure it exists to prevent.

Print the report's findings to the operator as a readable, numbered block — grouped by dimension, ordered by severity, each showing the drift (the two things that disagree), the proposed resolution, and the class. Include the `## Considered and ruled out` and `## Observations (not actionable)` sections — the negative space is how the operator judges whether the review was thorough, and the observations carry signal (e.g. an ADR whose commitments weren't visible from the index) that doesn't become an action.

Separate the findings visually into:

- **Owned reconciliations** — `inline-reconcile`, `test-backfill`, `status-fix`, `adr-supersede`. These are what this command actions itself.
- **Routed** — `route:/b-feature`, `route:/b-design`. These need another command's gate; you surface them, the operator runs them. They are still *tracked* in the plan.

Print the report's `## Constitution contradictions` section too, **separately from both groups and unabridged** — verbatim quote, `docs/constitution.md:NN`, the contradicting evidence, and which findings leaned on the claim. It is neither owned nor routed: `constitution.md` is human-owned, so it gets its own consent gate below and never enters the plan.

**Pre-review findings.** Read `docs/modules/<module>/findings.md` if it exists — the module's findings queue, holding drift recorded outside review (spec: `_bower/framework-reference.md` → *Findings queue*). Print its open items in their own group, labelled **pre-review findings**, after the reviewer's. They were not diagnosed by this review; they are candidates for absorption into it, and the operator decides at the triage gate. Say so plainly, and note where the reviewer's own findings expand on or contradict one — that is the most useful thing you can tell the operator about them, and it is the reason absorption exists rather than the two files simply coexisting.

This printed block is transient triage material. The operator reads it here, and the plan (next step) is what makes it survive the session — say so if the finding count is large, because the console is not the record.

## Gate: Triage (batch gate)

Triage collects a disposition for the review as a whole — and, when the operator wants finer control, per finding.

**Never present this gate until Step 2's numbered findings block has been printed in this session.** If you are resuming, recovering, or otherwise arrived here without having printed it, print it first — the operator cannot deselect findings they have not read, and a confirmation given without them is not informed consent.

Present one operator gate framing it as:

"I found N owned reconciliations and M routed findings in module `<module>`. Confirm to open the review — I'll write the plan, apply the owned items, and leave the routed ones tracked for you to run. Or tell me which findings to drop, or cancel."

Offer the disposition choices (*Open the review and action all owned items* / *Let me deselect some* / *Cancel — just show me the report*). If the operator chooses to deselect, the walk that follows is a **batch gate** (binding: *Runtime bindings → Batch gates*): collect an explicit keep/drop disposition per finding, and act on none of them until the full set is confirmed; the kept findings become the plan.

Routed findings are **not** informational at this gate — accepting them puts them in the checklist, where they hold the review open until run or won't-fixed. Say that plainly when asking, so the operator understands they are agreeing to tracked work, not just reading a list. A review whose findings are *all* routed is a normal outcome and still opens a review.

**Pre-review findings are absorbed at this gate, or not at all.** If Step 2 printed queued items, the confirmation here also authorises moving the accepted ones into the plan — say so in the question, and offer them per item if the operator is deselecting. An absorbed item is renumbered into the `F` sequence, its brief carried verbatim, and removed from the queue in Step 3; from then on the plan's copy is the one that counts, and the review holds it open. An item left unabsorbed stays in the queue untouched, which is a legitimate answer rather than a deferral — the queue holds nothing open and loses nothing by keeping it. This is the only crossing between the two files, and it runs in one direction: a review never pushes a finding down into the queue.

**Do not write the plan, set the marker, or apply anything until the operator confirms.** If they cancel, emit the findings and observations as a read-only handoff, leave `Review:` untouched, and stop — a cancelled triage means no review was opened.

## Gate: Constitution consent (only if contradictions were reported)

If the report's `## Constitution contradictions` section has entries, ask about them at a **second, separate** operator gate — never merged into the triage question above, because the triage question authorises *this command* to act, and this one authorises an edit to a file the command does not own.

Per contradiction, restate the verbatim quote and its `docs/constitution.md:NN` before asking, so the operator can open the file and read the line in context rather than trusting a summary. Offer: correct the claim to match reality · move it under `## Not yet in force` (it was an aspiration) · leave it alone. Edit `docs/constitution.md` only on an explicit instruction to do so — that makes the edit prompted, which ownership permits. Anything else means leave the file untouched.

This gate runs even when the operator cancelled the triage gate, and even when every dimension came back clean: a false constitution is worth surfacing on its own, and it is the one thing here nothing else in the framework is looking for.

**A corrected constitution can invalidate findings that were measured against it.** If an accepted reconciliation's `Bearing:` names a claim the operator just corrected, say so and re-confirm that item before it goes in the plan — the bar it was judged against has moved.

## Step 3: Write the Plan

After confirmation, if there is at least one accepted finding **of any class**, write `docs/modules/<module>/review-plan.md` *before* applying anything:

```markdown
# Review plan: <module>

Open review, diagnosed YYYY-MM-DD against 5 features. **Not living documentation** — this file is deleted at closeout, when `module-status.md`'s `Review: ✓` becomes the record. While it exists the module is in review (`Review: 🚧`): `/b-recap` summarises it and the docs viewer makes its findings readable. A command handed a routed finding ticks that one box on discharge, appending `— done <date> via <command>`; every other edit here, and the disposal of any item, belongs to `/b-review <module>` alone, which re-verifies each routed tick against the code before closing.

Dispositions: `[ ]` open · `[x]` resolved · `[~]` won't fix (operator decision, with date).

## Findings

- [ ] F3 — token-refresh/plan.md stale on TTL — inline-reconcile — docs/modules/<module>/token-refresh/plan.md:24
- [ ] F1 — ADR-0007 names Redis; code uses in-process — adr-supersede — /b-adr supersede ADR-0007
- [ ] F4 — backfill expired-token refresh test — test-backfill — src/auth/__tests__/refresh.test.ts
- [ ] F5 — session-revoke ✓ with pending verification — status-fix — docs/modules/<module>/session-revoke/status.md
- [ ] F2 — non-owner 404 vs 403 — route:/b-feature — Run /b-feature modify <module> non-owner-response-consistency according to F2 in docs/modules/<module>/review-plan.md
  - Location: src/auth/login.ts:48 vs src/auth/refresh.ts:61
  - Drift: login returns 404 for a session that isn't the caller's; refresh returns 403 for the equivalent case. Two features, two answers to one question.
  - Resolution: Pick one (404 hides existence, 403 admits it); apply to both. Behavioural change with an acceptance criterion, not a doc reconcile.
- [ ] F7 — session store reaches into billing tables — route:/b-design — Run /b-design session-store-billing-boundary according to F7 in docs/modules/<module>/review-plan.md
  - Location: src/auth/session.ts:88 imports src/billing/repository/internal.ts
  - Drift: auth's module boundary admits only the billing module's public surface; session.ts reads billing's repository internals directly to resolve a plan tier.
  - Resolution: Architectural — the tier lookup belongs behind a billing-owned interface, or the concern belongs in a different module. /b-design decides which.
- [ ] F6 — consolidate JWT helper tests — route:/b-feature — Run /b-feature modify billing consolidate-jwt-helper-tests according to F6 in docs/modules/<module>/review-plan.md
  - Location: src/auth/__tests__/login.test.ts:70, refresh.test.ts:55
  - Drift: both suites carry near-identical unit tests for the shared decodeJwt helper. Redundant; the helper deserves one home.
  - Resolution: Consolidate into one suite. Low priority — the operator may decline.

## Observations (not actionable)

- (from the report's Observations section, or "None.")
```

Shape rules:

- **One `## Findings` checklist, owned and routed together**, each line carrying its class so the reader knows who acts. Order owned-first — those get actioned in this pass — but do not split them into separate sections; a routed item in a second section stops being tracked work, which is the failure this shape fixes.
- **A routed item names the exact command to run**, including its target module when the fix belongs to a *different* module than the one under review (F6 above). A cross-module finding stays in *this* module's plan — the plan is a review artifact, not a work queue — so the target must be explicit or the reader loses it. **`route:/b-design` items get a slug too** — a bare `/b-design` is not a runnable instruction, and it leaves the operator inventing the change description that Stage 0 hands the analyst.
- **The command ends `according to F<n> in <path-to-this-plan>`**, and that clause is part of the command, not a note beside it. The whole line is meant to be copied and run verbatim: the request is narrative, and `/b-feature` and `/b-design` read a finding reference in it as an explicit selector that beats every other match. Written any other way — a parenthetical, a second line, a bare `F6` — it depends on the operator reassembling two pieces, and the one that gets dropped is the one that carries the evidence. **The path is required, not decorative:** finding IDs are module-local, so `F6` alone does not identify a finding, and a routed item's command is most often run in a session that has never opened this plan.
- **Every routed item carries a three-line brief**, indented beneath it: `Location:`, `Drift:`, `Resolution:`, copied *verbatim* from the report's finding. **All three, each non-empty** — they do different jobs and none substitutes for another: where to look, what disagrees with what, what to do about it. A location-only brief is worse than none, because it looks like a handoff while still leaving the receiving session to infer why the file matters. Never write a bare label to fill the shape; if a field is genuinely unavailable, say so in the field rather than leaving it blank. Do not summarise them — the report is gone after this pass and these lines are the only surviving evidence. **Owned items do not get a brief** and must not be given one: they are actioned in this same pass with the report still in context, so the brief would be write-only weight in a file that is otherwise deleted within the hour.

  The asymmetry is the point. A routed item is deferred to a later session, in a fresh context, run by a command that was not present at diagnosis. Its one line has to survive being the whole handoff. Without the brief, the receiving command re-derives the finding from code — which costs a survey, may reach a different conclusion, and may fail to reproduce the finding at all and tick it as looked-at-and-fine.

  Sub-bullets are indented and carry **no checkbox** — one checkbox per finding, or `/b-recap`'s and the viewer's disposition counts double-count. Keep each to one line; if `Drift:` needs a paragraph, the finding should have been split.
- **A ticked routed item may carry a completion note**, appended after the pointer as `— done YYYY-MM-DD via <command>`. You do not write it — the discharging command does — but it is part of the line schema, so preserve it on any item you edit, and read it as provenance when auditing the tick. It names who to attribute the claim to; it is not evidence the drift is gone.
- **Record the diagnosis date and the roster count** in the preamble. The count is the length of `## Build order` right now, and it is what gets written into `Review: ✓ (N of N features)` at closeout.
- `## Observations` is advisory, rides along so an interrupted session sees the whole picture, and never blocks closeout.

**Absorbed pre-review findings enter the plan here, and leave the queue in the same pass.** Give each one the next free `F<n>` — never carry its `Q<n>` across, since IDs are per-file and a `Q` inside a review plan breaks the plan's own reference form — and rewrite its command's trailing clause to `according to F<n> in docs/modules/<module>/review-plan.md`. Copy `Location:` / `Drift:` / `Resolution:` **verbatim**, whatever the item's class: the no-brief-for-owned-items rule above is about not *writing* a brief at diagnosis, and stripping one that already exists destroys evidence nothing can reconstruct. Then remove the item from `docs/modules/<module>/findings.md`, and delete that file if it is now empty.

Do both halves together. An item left in both files is tracked twice and will be discharged twice; an item that left the queue without arriving in the plan is simply lost. Say in one line which items you absorbed and what the queue has left.

Then set the marker: write `Review: 🚧` in `module-status.md`'s `## Module review` section. Plan and marker go together — if you wrote one, write the other, in the same pass.

If there are **no** accepted findings (the module is clean, or the operator dropped everything), do not write a plan or marker yet. Retain the diagnosis-time roster count and go straight to the closeout gate with zero findings. A clean review is still a completed review, and it is the case where recording the fact matters most — there is no other evidence it happened.

## Step 4: (reserved — numbering aligns Apply with the rest of the family)

## Step 5: Mediate

Walk the `## Findings` checklist. Tick each box as it is disposed of — **update the file as you go, not in a batch at the end**; the plan's value is that it is accurate at the moment a session dies.

**Owned items — action them now.** For each open owned item, in any order:

- **`inline-reconcile`** — edit the stale `plan.md` / `status.md` line to match the code. This is living-doc maintenance; no further gate. Tick the box.
- **`status-fix`** — correct the dishonest marker. If the fix is "flip ✓ to 🚧 because a manual check is pending," do that. If it's "the manual check actually passes," confirm with the operator (it's a real verification) before flipping to ✓ and clearing the `Pending verification:` line. Whenever a feature ends this step at ✓, leave its `status.md` in the **terminal form** — marker, `## Verification`, `## Next move` → `(none — complete)` — which also discharges a finding about a forward-pointing next move on a finished feature. Tick the box.
- **`test-backfill`** — write the test for the already-agreed behaviour and run it. If it passes, tick the box. **If writing the test reveals the code is actually wrong**, do not paper over it: re-classify the item in place to `route:/b-feature`, leave it open, and note it — a behavioural defect needs the propose-confirm gate, not a silent fix here. The item now holds the review open, which is correct.
- **`adr-supersede`** — invoke `/b-adr` with the ADR-ID and the rationale. The class covers supersede *or narrow*: `/b-adr`'s supersede-vs-narrow test decides whether the drifted ADR is replaced or kept `accepted` with an exception carved out, and either outcome resolves the finding. Its own gate fires. On success, tick the box. If the operator rejects the draft at `/b-adr`'s gate, treat it as a request to redraft, not to skip; if they abandon ADR work entirely, leave the item open (or `[~]` if they call it won't-fix) rather than deleting it silently.

If implementation reveals the report was wrong about a finding (the drift doesn't actually exist), don't force the reconcile — mark it `[~]` with `report was wrong: <why>` and move on.

**Routed items — do not action them.** In a single session that usually means you present them and stop. The operator runs the routed command, which ticks its own box on discharge; re-invoking `/b-review <module>` is for the findings that are still open and for closeout, not for per-finding bookkeeping. Boundary erosion (`route:/b-design`) is never actioned here under any circumstances, and a design run never ticks — see the re-classification rule below.

**An item you find already `[x]` is left alone here.** It was ticked by the command that discharged it, and the closeout gate audits every routed tick against the code before the plan is deleted. Checking it twice buys nothing; checking it *only* here would put the audit before any later tick rather than after all of them.

**A routed item is ticked when the drift it names is gone — not when the command it names has run.** Those are the same thing for `/b-feature`, which implements, and they are *not* the same thing for `/b-design`, which decides. A design run ends with an ADR and, usually, implementation work that nothing schedules: the decision has landed, the drift has not moved. So before ticking any routed item, open the `Location:` from its brief and confirm the disagreement is actually gone. This is one targeted read per item, not a re-review — the brief exists precisely so it is cheap. Never tick on the operator's report that they ran something, and never on seeing related-looking changes in the tree.

**When a `route:/b-design` item's decision has landed but its code has not, re-classify in place.** Same finding, same `F<n>`, same unticked box: replace the class with `route:/b-feature` and the command with the implementation command, and rewrite the brief so the design output is carried forward — `Location:` still names the offending code, `Resolution:` becomes *implement ADR-00NN's decision here*, and `Drift:` names the accepted ADR as the side the code now contradicts. Tell the operator you did it and why. The finding keeps its number deliberately: they may be holding a handoff that names it, and a renumber loses the thread.

This mirrors the `test-backfill` rule above — a class is a claim about who can discharge the finding, and when that claim turns out to be wrong the finding is re-classed and stays open rather than being disposed of on a technicality. The escape is unchanged: if the operator decides the implementation is not worth doing, that is a `[~]` won't-fix, which is a decision rather than an oversight.

**On a resumed review, check the briefs before presenting.** If an open routed item is missing any of `Location:`/`Drift:`/`Resolution:`, or carries one as a bare label with no value — the plan predates v0.32, or was hand-edited — say so once, naming the items. A partial brief needs saying as much as an absent one; it is the case that looks finished.

Do **not** offer to write the missing fields yourself. A resumed review does not re-diagnose, so you have no reviewer report either — reconstructing a brief here means reading code to infer what the finding meant, which is a review performed with less context than `bower-reviewer` had and outside its isolation. Offer the operator the two real options instead: carry on without briefs (the commands still run; whoever discharges a finding re-derives it, as before v0.32), or discard and re-diagnose — delete `review-plan.md`, set `Review: ⏸`, and run `/b-review <module>` fresh. Name the cost of the second: a reviewer run, and any `[~]` won't-fix decisions come back to be declined again. Never delete the plan without their agreement.

**Won't-fix.** Any item can be disposed of as `[~]` on an operator decision, routed items included. Record it as `[~] F6 — <gist> — won't fix (operator, YYYY-MM-DD)`. You may *propose* a won't-fix when an item has become moot, but never mark one unprompted — it discharges work the operator agreed to at the triage gate. Won't-fix needs no further record anywhere; the decision dies with the plan by design.

## Gate: Closeout

When every item in `## Findings` carries a disposition (`[x]` or `[~]`), the review is finishable — but **verify the routed ticks before offering the gate.** Closeout deletes the plan, so this is the last moment any of it is recoverable. For each `[x]` routed item, read the `Location:` from its brief and confirm the drift is gone. Owned items were applied by this command and need no re-check; `[~]` items are decisions, not claims about code.

**This is the framework's only independent check on a routed tick, and the whole reason the tick may be delegated.** Most routed ticks are written by the command that discharged the finding, in a context nothing here can see, at the moment it declared its own work complete. A completion note (`— done 2026-08-10 via /b-feature <slug>`) is provenance, not evidence: it tells you which command and which date to attribute the claim to, and says nothing about whether the drift is gone. Older ticks may also have been made under the pre-v0.34 rule, or by an operator answering "yes, I ran it." Read the code in every case.

**A legacy plan has no briefs, and that does not block closeout.** A plan written before v0.32 gives a routed tick no `Location:` to check, and re-deriving one here is the hand-reconstruction this command refuses to do. Locate the code from the finding's gist if the gist makes it unambiguous; where it does not, the item is **unverifiable, not failed** — do not untick it, and do not invent a location to check. Count those separately in the gate line and name them, so the operator can eyeball the ones nothing confirmed: `routed ticks: 3 verified, 2 unverifiable (F5, F9 — no brief; plan predates v0.32)`. They may still close the review; an unverifiable tick is the cost of the plan's age, and holding a review open forever over it helps nobody.

Report the result as a line in the gate, always — `routed ticks verified: 5 of 5` — because an unstated check is indistinguishable from a skipped one. If a tick is checked and does not hold, do not present the gate: untick that item, re-classify it if the reason is a `route:/b-design` decision whose code never landed, say plainly what you found, and report progress instead. A review that reopens at the closeout gate has just done its job.

Present one operator gate:

"All N findings in module `<module>` are disposed of (`<x> resolved, <y> won't fix`). Close the review? I'll delete the plan and record `Review: ✓ <today>`."

Offer: *Close the review* / *Keep it open — more to do* / *Show me the plan first*. Closing is the operator's call, not yours: they may know of related work still landing.

**A clean review (zero accepted findings, arriving here straight from Step 3) has no plan and no marker.** Phrase the gate as: "The review of `<module>` found nothing to act on. Record it? I'll write `Review: ✓ <today> (<N> of <N> features)`." Offer *Record it* / *Don't record — treat as never reviewed*. On confirmation, run only step 3 below with the roster count retained from Step 3 — steps 1, 2, and 4 have nothing to do (no markers changed, no plan exists to delete).

**If any item is still open, do not present this gate.** Report progress instead (`3 of 7 findings disposed`), leave `Review: 🚧` and the plan in place, and emit the Step 6 handoff naming what remains. An unfinished review is a perfectly good place to stop — that is the whole point of the state.

On confirmation:

1. If any status marker changed, run `/b-index` so module status reflects reality. If `/b-index` is not invokable, correct the module-level marker in `module-status.md` and leave `docs/index.md` to the next regeneration — never hand-edit the index, whose status is derived from those markers (see *Status is never curated* in `b-index.md`).
2. If a reconcile changed a feature's resumption picture, refresh that feature's `status.md` accordingly (≤150 words, current-state).
3. Write `Review: ✓ YYYY-MM-DD (<N> of <N> features)` in `module-status.md`'s `## Module review`, using today's date and the diagnosis-time roster count — from the plan's preamble when a plan exists, or the count retained from Step 3 for a clean review — **not** a recount of `## Build order` now. The snapshot answers *what was reviewed*, and if routed `/b-feature` work added features during mediation, those features were not part of this review. The review will therefore sometimes read as slightly stale the moment it closes; that is honest.
4. **Delete `docs/modules/<module>/review-plan.md`.** Its job is done, and `Review: ✓` is now the record. Leaving it would both rot and put the module in a broken state (`✓` with a plan on disk).

Steps 3 and 4 are one unit — never do one without the other. (A clean review is not an exception: it has no plan, so step 4 is vacuously done, not skipped.)

## Step 6: Handoff

Emit a single handoff block. State the review state explicitly — the operator needs to know whether they can walk away and whether coming back means `/b-review` again.

```
Module <module>: Review 🚧 in review — 3 of 7 findings disposed
                 (or: Review ✓ closed YYYY-MM-DD — 5 of 5 features)

Resolved this pass:
  - <one line per disposed item, or "(none)">

Still open — tracked in review-plan.md:
  - Run /b-feature modify <module> <slug> according to F1 in docs/modules/<module>/review-plan.md
  - Run /b-design <slug> according to F7 in docs/modules/<module>/review-plan.md
  - (none — all findings disposed)

Constitution:
  - <docs/constitution.md:NN — corrected | moved to "Not yet in force" |
     left as-is at the operator's request>, or "(none reported)"

Observations:
  - <non-actionable note, or "(none)">

Next move:
  - <the single most important open command, or:>
    Run /b-review <module>                        (resume mediation, nothing else owed)
    Run /b-recap                                  (orient before deciding)
    (none — module reviewed clean and closed)
```

**Print the command exactly as the plan carries it — reference included, on one line.** These are copied and run verbatim, and the reference is what makes the receiving command load the evidence instead of re-deriving it from code. Do not shorten it to fit the column, and do not move it to a second line: a two-line handoff is a one-line paste plus a dropped clause. Reproduce the gist as a trailing comment only if it fits; the reference is the part that cannot be lost.

When the review is still open, say in one line that `/b-review <module>` resumes it and does not re-analyse — that is not obvious from the outside, and an operator who thinks resuming means re-running the reviewer will keep the findings in a text editor instead.

Pick exactly one recommended next move. A `route:/b-design` finding (boundary erosion) outranks everything — if one exists, it is the next move, because architectural drift is the one thing the framework will not let accumulate.

## Resuming mediation

When Step 0 found `Review: 🚧` with a plan on disk, you skipped diagnosis. Read the plan, then run Step 5 against its open `## Findings` items exactly as above — including the routed ones, which you tick only once you have checked the code and found the drift gone, never on the operator's report that a command landed — then the closeout gate if everything is disposed of, then the Step 6 handoff.

Do **not** re-spawn the reviewer. The findings were already gated when the plan was written, and re-diagnosing would replace triaged work with a fresh derivation the operator never agreed to. If the operator wants a *fresh* review rather than a resume, the current review has to close first (or they delete the plan and reset the marker themselves); say so rather than running both. Re-diagnosis is also how the routed items get lost — the exact failure the plan exists to prevent.
