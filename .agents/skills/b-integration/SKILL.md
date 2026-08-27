---
name: b-integration
description: Build or update the integration test that exercises a module's boundary.
---
<!-- GENERATED FILE — do not edit. Source: skills-src/commands/b-integration.md. Regenerate: node scripts/build-adapters.cjs -->

# Bower Module Integration Test

You are running the Bower module-integration workflow. This builds the integration test that exercises a module's boundary, per the integration prose recorded in `module-status.md`. One gate before any code is written, mirroring `/b-feature`'s shape.

The request (the target module): the request as given in the message that invoked this skill.

## Important Behavioural Rules

- **One deliverable.** This command produces exactly one thing: a runnable integration test for the named module. Do not modify feature code, fix unrelated bugs, or expand scope; an architectural issue routes to `/b-design`.
- **Consult before building.** Present your proposal at an operator gate (binding: `_bower/framework.md` → *Runtime bindings*) and get explicit confirmation before writing any code.
- **Read first.** The module's `module-status.md` integration prose, every feature's `plan.md`, and `constitution.md`'s testing section are the foundation.
- **Acceptance is explicit.** What the test asserts is the contract. Manual checks (e.g. inspecting a generated artifact) are agreed at the gate too.
- **Literal-command handoff.** Every "next move" you emit names the exact slash command to type next, never free prose.

## Step 1: Understand Context

1. Read `docs/architecture.md` for system context.
2. Read `docs/scope.md` for current scope and any success criteria whose `Delivered by:` clause names this module — they say what the module-boundary behaviour is ultimately for.
3. Read `docs/modules/<module>/module-status.md` — the `## Module integration` section is the rubric you're implementing; the `## Build order` confirms which features participate.
4. Read each participating feature's `plan.md` to understand the data each contributes and the seams the test will exercise.
5. Read `docs/constitution.md` for test location, runner, fixture conventions, and any verification-required-for-✓ rules.
6. **Load relevant ADRs.** If `docs/adr/index.md` exists, read it and open accepted ADRs that (a) list this module under `modules`, (b) are cross-cutting (no `modules` field), or (c) have a title topically relevant to integration testing or the module's behaviour. The integration test should honour these decisions — e.g. an ADR mandating real-DB integration tests means no mock fixtures here.
7. Read source code at the module boundary to confirm the test will hit real seams, not mocked ones (unless the constitution says otherwise).

**Precondition check:** if any feature in the module's build order is not yet ✓ or 🚧 with passing automated criteria, surface this. The integration test can still be written, but it will fail until the underlying features are built. Recommend the user finish the missing features first via `/b-feature <name>` unless they confirm otherwise.

## Step 2: Propose the Test

Prepare a proposal covering:

- **File path** — concrete, e.g. `tests/integration/test_<module>_integration.py`. Match the project's test layout per `constitution.md`.
- **Harness shape** — fixtures, cassettes, temp directories, env setup. One short paragraph or bullet list.
- **Assertions** — the specific behaviours the test will verify at the module boundary. Map each back to the integration prose in `module-status.md` `## Module integration` `Notes:`.
- **Manual checks** — anything that can't be automated (e.g. "operator inspects the generated artifact for shape X"). Often empty.
- **Out of scope** — adjacent behaviours you're explicitly not covering, even if tempting.

Mark the recommended approach if there are alternatives (e.g. real DB vs. transactional fixture).

## Gate: Confirm or Adjust

Present the proposal at the operator gate. Frame it as:

"Here's the integration test I propose for module `<name>`: <file path>, <N> assertions, <manual checks if any>. Confirm to proceed, or tell me what to adjust."

Include the assertions and any manual checks — these are the agreement.

**Do not write any code until the user confirms.**

## Step 3: Implement

After confirmation:

1. Mark the module-integration marker 🚧 in `module-status.md` `## Module integration` `Test:` line.
2. Create the test file at the agreed path with the agreed harness and assertions.
3. Run the test. Confirm it passes.

If the test fails because of a real bug in the module (not a test-side issue), stop. Surface the failure to the user at an operator gate: a feature is broken at the boundary, which means a `/b-feature <name>` recovery cycle is the right next step, not papering over it here.

## Step 4: Acceptance Reconciliation

Reconcile every criterion agreed at the gate:

```
- <criterion> — test: <path::name> — PASS
- <criterion> — test: <none written> — MISSING
- <criterion> — manual: "<check description>" — PENDING USER
```

Handling:

- **MISSING** is a blocker. Either add the assertion or renegotiate at an operator gate. Do not proceed.
- **PENDING USER** — present the manual checks at a batch gate, one explicit disposition per check. PASS → mark ✓. Failure → treat as bug, fix, re-verify. Deferred → leave PENDING USER and mark the module-integration marker 🚧 (not ✓).

**ADR drift.** If writing the test surfaced a contradiction between an accepted ADR and the code or constitution (e.g. the ADR mandates real-DB but the harness uses an in-memory fixture), flag it in the handoff and recommend `/b-adr` to supersede before flipping the marker to ✓. Do not silently let the drift stand — that's exactly the rot the ADR mechanism exists to prevent.

## Step 5: Update Documentation

1. Update `module-status.md` `## Module integration`:
   - `Test:` line — set the path you wrote, and the marker (✓ if all PASS, 🚧 if PENDING USER, 🟡/🔴 if known issues).
   - `Notes:` line — refresh if the as-built test diverged from Stage 4's prose.
   - If `Pending verification:` items remain, add a line listing them under the `## Module integration` section.
2. Do **not** update `scope.md` to record that a criterion is now met — criteria carry no status, and `/b-recap` derives achievement from module completion (this test's ✓ is part of that derivation). Touch `scope.md` only in the rare case that building the test revealed the scope boundary or a criterion's wording to be wrong.
3. Run `/b-index` so the module-level marker reflects the new module-integration state.

## Step 6: Handoff

Emit a single handoff block. Always name the literal next command — never free prose:

```
Module integration for <module>: <✓ | 🚧 pending verification | 🟡/🔴>

Next move:
  - <one of:>
    Run /b-recap                               (orient and pick the next module/feature)
    Run /b-feature <name>                      (next ⏸ feature in the inter-module build order)
    Run /b-module <name>                       (next module, if small and well-specified)
    Run /b-integration <module>         (re-run after fixing PENDING USER items)
    (none — all modules ✓; project completion is /b-recap's call, which derives success-criteria satisfaction)
```

Pick exactly one recommended next command based on the project state you just observed. Mention at most one alternative on a second line.
