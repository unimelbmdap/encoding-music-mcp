# Bower Review Report — Schema

The review report is the structured artifact produced by the **bower-reviewer** subagent at the start of `/b-review`. It is the authoritative answer to *what did we actually build in this module, and where does it diverge from what the docs, the decisions, and the rest of the module say it should be?*

`/b-review` executes against the report: it gates the findings with the operator, writes **every** accepted finding to a `review-plan.md` checklist, applies the owned ones itself, and leaves the routed ones tracked until the operator runs the commands that own them. Diagnosis opens a review state (`Review: 🚧`) that closes only when every finding is disposed of.

A review is **module-scoped**. The reviewer surveys one module's features, its plans and status files, the ADRs that touch it, and its code. It does not review the whole project — that breadth belongs to `/b-recap` (orientation) and `/b-analysis` (forward-looking change impact). Review looks *down* into one finished module and *backward* at what was built.

## Where reports are used

- `/b-review <module>` — invokes `bower-reviewer` internally, presents the findings at a triage gate, writes the accepted findings to `docs/modules/<module>/review-plan.md`, applies the owned ones, and tracks the routed ones until closeout.

There is no read-only "print the report and stop" entry point, the way `/b-analysis` is for the change brief. A review that surfaced findings and did nothing with them would be a report that rots — exactly the artifact Bower avoids. The findings are consumed immediately into a plan or a routed handoff; they are not preserved as a standalone document.

Because the report is discarded, **the `Location` / `Drift` / `Resolution` lines of any `route:*` finding are copied verbatim into `review-plan.md`** beneath that finding's checklist line. Write those three fields knowing they may be read months later, in a fresh context, by `/b-feature` or `/b-design` rather than by the operator: locate both sides exactly, and make `Resolution:` say what to do, not that something should be done. Owned findings are actioned in the same pass and are not copied.

## The six dimensions

The reviewer is deliberately scoped to what a sequential, feature-at-a-time implementation **systematically cannot see** — properties that only become visible once the module is whole. It is not a linter, a style checker, a security audit, or a performance profiler; those are owned by tools and by `/security-review`, and adding them would cost the lightweight axis without buying anything the implementer couldn't already get.

Every finding belongs to exactly one of these dimensions:

1. **Test coverage (whole-module).** Tests written per-feature optimise locally. At module completion: are the *interactions between features* tested, not just each feature in isolation? Are whole categories missing (error paths, boundary conditions)? Is there redundancy (several features re-testing the same shared helper)? Does the module-integration test actually assert the boundary concern, or merely smoke-test?
2. **Spec ↔ code drift (bidirectional).** Either the implementation wandered from the feature's `plan.md` / the acceptance contract, **or** `plan.md` / `status.md` is stale against the code. Both are the map and the territory disagreeing. The direction matters for the resolution: stale doc → reconcile the doc; code violates an agreed criterion → a behavioural fix.
3. **Cross-feature consistency.** Sequentially-built features drift: feature 1 returns 404 for a non-owner, feature 3 returns 403; naming, error-handling shapes, and return conventions diverge. No single-feature pass can see this; a whole-module pass can.
4. **Status honesty.** Are the markers truthful? Anything ✓ that still has a `Pending verification:` line? Is the floor-not-sum rule observed (a module is the worst of its feature markers and its integration marker)? Is each ✓ feature's `status.md` in its **terminal form** — marker, `## Verification`, `Next move: (none — complete)` — rather than still carrying a live resumption snapshot or a `Next move:` pointing at other work? A forward-pointing next move on a finished feature is `status-fix`, and the file compresses as part of the fix.
5. **ADR drift.** Accepted ADRs that touch this module but now contradict the code. This is "code is truth, ADR is hypothesis" turned from a passive posture into an active check. **Drift only** — the reviewer does not flag ADRs for being verbose or over-scoped: bodies are immutable, and prose length is not a supersede-worthy reason. If a bundled ADR's commitments were hard to recover because the index shows only titles, that is a legitimate finding (it is the failure signal the deferred ADR-index improvement waits on), but it is reported as an observation, not as an actionable plan item.
6. **Boundary integrity.** Does the module still integration-test cleanly in isolation, or have back-channels to other modules crept in? This is the DAG-in-positive-form test from `rationale.md`. Boundary erosion is **architectural** — it enters the plan as tracked work, but is always routed to `/b-design` and never actioned by `/b-review`.

## Resolution class

Every finding carries a **class** that determines what `/b-review` does with it. This is the critical field — it is how the command separates what it owns from what it routes.

| Class | Meaning | What `/b-review` does |
|---|---|---|
| `inline-reconcile` | A `plan.md` / `status.md` line that flatly contradicts the code; the doc is stale, the code is fine. | Applies inline (living-doc maintenance, already gate-free). Owned plan item. |
| `test-backfill` | A missing test for *already-built, already-agreed* behaviour — closing a coverage gap, not driving new behaviour. | Writes the test inline and runs it. Owned plan item. If writing it reveals the code is actually wrong, the finding is re-classed `route:/b-feature`. |
| `status-fix` | A dishonest marker (✓ with pending verification, floor-not-sum violation). | Corrects the marker inline; `/b-index` is re-run at the end. Owned plan item. |
| `adr-supersede` | An accepted ADR contradicted by the code. | Invokes `/b-adr` to supersede (its own gate fires). Owned plan item. |
| `route:/b-feature` | A behavioural fix or consistency change beyond a doc reconcile — needs the propose-confirm-acceptance gate. | **Routed**, not owned. Tracked as a plan item naming the command to run; never applied by `/b-review`. |
| `route:/b-design` | Boundary erosion / architectural drift. | **Routed**, not owned. Tracked as a plan item; the hard-redirect rule applies — `/b-review` refuses to action it. |

**Owned** classes (`inline-reconcile`, `test-backfill`, `status-fix`, `adr-supersede`) are the ones `/b-review` can resolve itself, because each is individually ad-hoc-safe under existing framework rules. **Routed** classes (`route:/b-feature`, `route:/b-design`) require another command's gate.

The distinction governs **who acts**, not what is tracked: every accepted finding of either kind goes in the one `## Findings` checklist in `review-plan.md`, and holds the review open (`Review: 🚧` in `module-status.md`) until it is resolved or explicitly won't-fixed. A routed item is ticked when **the drift it names is gone**, verified against the code — not when the command it names has run. Those coincide for `/b-feature`, which implements, and come apart for `/b-design`, which only decides. A report whose findings are entirely routed is a normal outcome and still opens a review — it does not mean there is nothing to track.

## Schema

A report is a single markdown document with the sections below, in order, with these exact headers. Every section is present; an empty findings list still carries the section with `Status: clean`.

### Header

```
# Review report: <module-name>

Generated by bower-reviewer on YYYY-MM-DD against <project-root>.
Module: <module-name>
```

An optional line `Context: inline` may follow the `Generated by` line. It is written **only by the calling command** (`/b-review`) when the runtime could not delegate and the caller followed the reviewer's definition inline — it records that the diagnosis lacks fresh-context isolation, and `/b-review` restates that degradation at the triage gate. A genuinely delegated reviewer never writes this line; absence means the report was produced in an isolated context.

### `## Summary`

Scannable one-line-per-dimension overview. Six lines, one per dimension, each either `clean` or a phrase naming the finding count and gist. This is the section the operator uses to gate; everything below is the supporting evidence.

```
- Test coverage: 2 findings (missing error-path coverage; redundant helper tests)
- Spec ↔ code drift: 1 finding (auth/plan.md stale on token TTL)
- Cross-feature consistency: 1 finding (404 vs 403 for non-owner)
- Status honesty: clean
- ADR drift: 1 finding (ADR-0007 names Redis; code uses in-process cache)
- Boundary integrity: clean
```

### `## Inputs read`

Audit trail of what the reviewer consulted: the module's `module-status.md`, each feature's `plan.md` and `status.md`, the ADRs loaded in full (and a count of those scanned via index but not loaded), and the source files read. Helps the operator spot a finding that rests on a file the reviewer didn't actually open.

### `## Findings`

A numbered list of findings, ordered by severity (high → low), then by dimension. Each finding:

```
### F1 — <short title>

Dimension: <one of the six dimension names>
Severity: high | medium | low
Location: <repo-relative file:line, or doc path — exact>
Drift: <the gap, stated as two things that disagree. "plan.md says X; code does Y." Not "X looks wrong.">
Resolution: <the proposed fix, concretely>
Class: <one of the six resolution classes>
Command: <literal slash command for adr-supersede and route:* classes; "inline (this pass)" for inline-reconcile / test-backfill / status-fix>
```

Rules for findings:

- **Drift is stated as a disagreement between two named things**, with both sides located. A finding that can't name what disagrees with what is an opinion, not a drift — leave it out.
- **Severity is for ordering and triage only.** It does not branch behaviour: a high-severity `inline-reconcile` is still just a checklist item. Reserve `high` for findings that mislead a future reader or hide a real defect; `low` for cosmetic drift.
- **Paths and IDs are exact.** `docs/modules/auth/token-refresh/plan.md:24`, `ADR-0007` — never "the auth plan" or "the caching ADR."
- **One finding, one resolution, one class.** If a single observation implies both a doc reconcile and a behavioural fix, split it into two findings.

### `## Considered and ruled out`

Negative-space audit, parallel to the change brief's section of the same name. The reviewer lists dimensions, features, or ADRs it examined and found clean — each with a one-line reason. **An empty list is suspicious**: it suggests the reviewer skimmed rather than surveyed. "Checked feature-3 against feature-1's error-handling — consistent" is the shape. This section is the operator's primary check that the review was thorough, not that it found nothing.

### `## Constitution contradictions`

Claims in `docs/constitution.md` that the module survey contradicted. **This section sits outside the six dimensions and outside the resolution-class machinery** — deliberately, because its resolution is categorically different: `constitution.md` is human-owned, so the fix is never an owned reconcile, never a routed command, and never enters `review-plan.md`. It is a consent request the *user* answers.

The reviewer already reads the constitution as the **yardstick** for the test-coverage and status-honesty dimensions. That is exactly where a false yardstick does most damage — every finding measured against it inherits the error — so "the yardstick itself is wrong" has to be reportable. Each entry:

```
- Claim: "<verbatim quote>" — docs/constitution.md:NN
  Found: <the contradicting evidence, with exact path:line or command + result>
  Bearing: <which dimension or finding relied on this claim, or "none — noticed in passing">
```

Rules:

- **Verbatim and located, both sides.** The calling command shows this to the user so they can open the file and read the line themselves; a paraphrase invites a rubber-stamp and defeats the point.
- **Only what this module's survey actually contradicted.** This is not a general audit of the constitution — do not go looking. If the survey didn't touch a claim, it isn't reportable here.
- **`## Not yet in force` is not a contradiction.** Anything under that heading already declares itself untrue; treat it as non-existent and never report it.
- **Never propose the edit as a finding.** No dimension, no class, no `Command:` line. If a *finding* depended on the false claim, keep the finding and cross-reference it in `Bearing:` — the operator may want to re-judge it once the constitution is corrected.

If there are none, the section reads `None.`

### `## Observations (not actionable)`

Findings worth surfacing that have no owned or routed resolution — most commonly an ADR whose commitments were hard to recover from a title-only index row (the deferred ADR-index-summary signal), or a smell that doesn't yet rise to a boundary-erosion finding. These are copied into the plan's non-blocking `## Observations` section so an interrupted review retains the report's context, and printed in the handoff; they never become checklist items or hold the review open. If there are none, the section reads `None.`

## Schema rules

- **Every section is present**, even when empty (`Status: clean`, `None.`).
- **No prose between sections.** The report is structured data; commentary belongs inside sections.
- **The reviewer is read-only.** It surveys and reports; it never writes, edits, or commits. Acting on the report is the calling command's job, behind the triage gate.
- **`clean` is a first-class outcome.** A dimension with no findings is a positive assertion that the reviewer checked and found no drift — not a sign it didn't look. The `## Considered and ruled out` section is where that diligence is evidenced.
- **No new design.** The reviewer reports drift against what already exists; it does not propose new features, new modules, or new architecture. A finding whose resolution is "build something new" is out of scope — the reviewer notes it as an observation and lets the operator decide whether to run `/b-feature` or `/b-design`.

## Worked example

The module below is **fictional** — a small `auth` module used purely to illustrate the schema. Do not pattern-match real project content against the names, ADR IDs, or feature structures here.

```markdown
# Review report: auth

Generated by bower-reviewer on 2026-05-29 against /home/user/projects/acme.
Module: auth

## Summary

- Test coverage: 2 findings (no expired-token path test; login + refresh both re-test the same JWT helper)
- Spec ↔ code drift: 1 finding (token-refresh/plan.md stale on TTL)
- Cross-feature consistency: 1 finding (non-owner returns 404 in login, 403 in refresh)
- Status honesty: 1 finding (session-revoke marked ✓ with a Pending verification line)
- ADR drift: 1 finding (ADR-0007 names Redis session store; code uses in-process)
- Boundary integrity: clean

## Inputs read

Module:
  - docs/modules/auth/module-status.md
Feature plans + status (loaded in full):
  - docs/modules/auth/login/{plan,status}.md
  - docs/modules/auth/token-refresh/{plan,status}.md
  - docs/modules/auth/session-revoke/{plan,status}.md
ADRs (loaded in full):
  - ADR-0007 — session store (relevant; drifted)
  - 4 other ADRs scanned via docs/adr/index.md, not loaded
Source:
  - src/auth/login.ts, src/auth/refresh.ts, src/auth/session.ts
  - src/auth/__tests__/*.test.ts

## Findings

### F1 — ADR-0007 names Redis; code uses an in-process session store

Dimension: ADR drift
Severity: high
Location: docs/adr/0007-session-store.md vs src/auth/session.ts:12
Drift: ADR-0007 (accepted) records "sessions are stored in Redis with a 30-minute TTL"; src/auth/session.ts uses an in-process Map with no external store. The decision drifted; the ADR is the stale one.
Resolution: Supersede ADR-0007 with a new ADR recording the in-process store decision and its rationale (single-instance deployment, Redis dependency dropped).
Class: adr-supersede
Command: /b-adr supersede ADR-0007 — in-process session store replaces Redis

### F2 — Non-owner access returns 404 in login, 403 in refresh

Dimension: Cross-feature consistency
Severity: medium
Location: src/auth/login.ts:48 vs src/auth/refresh.ts:61
Drift: login returns 404 for a session that isn't the caller's; refresh returns 403 for the equivalent case. Two features, two answers to one question.
Resolution: Pick one (404 hides existence, 403 admits it); apply to both. This is a behavioural change with an acceptance criterion, not a doc reconcile.
Class: route:/b-feature
Command: /b-feature modify auth non-owner-response-consistency

### F3 — token-refresh/plan.md states a 15-minute TTL; code uses 60 minutes

Dimension: Spec ↔ code drift
Severity: medium
Location: docs/modules/auth/token-refresh/plan.md:24 vs src/auth/refresh.ts:30
Drift: plan.md says "access tokens expire after 15 minutes"; the code sets 3600s. The doc is stale; the code is the intended current behaviour (confirmed against the most recent change).
Resolution: Reconcile plan.md to 60 minutes.
Class: inline-reconcile
Command: inline (this pass)

### F4 — No test for the expired-token refresh path

Dimension: Test coverage (whole-module)
Severity: medium
Location: src/auth/__tests__/refresh.test.ts
Drift: refresh.ts handles an expired refresh token (returns 401, clears the session), but no test exercises that branch — it was agreed in the acceptance criteria and built, just never covered.
Resolution: Backfill a test asserting expired-token → 401 + session cleared.
Class: test-backfill
Command: inline (this pass)

### F5 — session-revoke is marked ✓ but carries a Pending verification line

Dimension: Status honesty
Severity: low
Location: docs/modules/auth/session-revoke/status.md
Drift: status.md ends with "Pending verification: manual check that revoke invalidates active sessions" yet module-status.md marks the feature ✓. The floor-not-sum rule says it should be 🚧.
Resolution: Either confirm the manual check now (flip to ✓) or mark the feature 🚧. Surface to the operator at the gate.
Class: status-fix
Command: inline (this pass)

### F6 — login and token-refresh both re-test decodeJwt directly

Dimension: Test coverage (whole-module)
Severity: low
Location: src/auth/__tests__/login.test.ts:70, refresh.test.ts:55
Drift: both suites have near-identical unit tests for the shared decodeJwt helper. Redundant; the helper deserves one home.
Resolution: Consolidate the helper's tests into one suite. Low priority — note it; the operator may decline.
Class: route:/b-feature
Command: /b-feature modify auth consolidate-jwt-helper-tests

## Considered and ruled out

- Checked session-revoke against login/refresh for the non-owner-response inconsistency (F2) — revoke uses 404, consistent with login; the split is only login+refresh vs refresh.
- Reviewed ADR-0003 (password hashing) against src/auth — code matches the ADR; no drift.
- Checked the module-integration test (docs/modules/auth/module-status.md) — it exercises login→refresh→revoke end-to-end and asserts the cross-feature session lifecycle; the boundary concern is genuinely covered, not smoke-tested.

## Constitution contradictions

- Claim: "Every module boundary is covered by a contract test, run in CI on every PR." — docs/constitution.md:41
  Found: no contract tests exist for any module; .github/workflows/ci.yml:18 runs only `pytest tests/unit`. The auth module-integration test at tests/integration/test_auth.py is the module's sole boundary test and is not invoked by CI.
  Bearing: F4 and F6 were judged against this claim — the coverage bar it sets is not the bar this project actually holds.

## Observations (not actionable)

None.
```

In that example the constitution asserted a *state of the world* ("every module boundary is covered", "run in CI on every PR") rather than a rule, and it was false. Written normatively — "module boundaries should be covered by a contract test; `✓` requires one" — it could only ever have been *unmet*, which surfaces as work rather than as a phantom guarantee two findings were then measured against. The `## Not yet in force` heading in `_bower/framework-reference.md` is where the aspirational half belongs.
