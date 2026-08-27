---
description: Read-only orientation — where is this project, and what is the next move?
---
<!-- GENERATED FILE — do not edit. Source: skills-src/commands/b-recap.md. Regenerate: node scripts/build-adapters.cjs -->

# Bower Recap

You are running the Bower recap workflow. This is a **strictly read-only, advisory** orientation command. It answers one question: *where is this project, and what's the next move?*

You do **not** write files. You do **not** commit. You do **not** gate — you ask the operator nothing. You produce a single structured text block and stop.

## Inputs (read-only)

Read these and only these, and only if they exist. Trust the documents; do not infer project state from source code or run git:

1. `docs/index.md` — project-level structure and module status markers. Also note a leading `🌱 Adoption in progress` banner if present: the project is in the **adoption phase**, which changes how `🚧` features and the next action are read (see below).
2. `docs/scope.md` — current scope, non-goals, and the success criteria with their `Delivered by:` module clauses. The criteria carry **no** stored status; you derive it (see *Success criteria* below).
3. `docs/modules/**/module-status.md` — `## Build order`, `## Module integration`, and `## Module review` state for each module
4. `docs/modules/**/<feature>/status.md` — only for features currently at 🚧, 🟡, 🔴, or 🔧 (skip ✓ and ⏸). **A `🚧` feature with no `status.md` is an adopted-but-unverified feature, not an in-progress one** (adoption marks features as-built `🚧` and deliberately writes no `status.md`). Do not treat the missing file as an error or an omission — there is simply no session state to summarise; report it under *Adopted (unverified)*, not *Currently in progress*.
5. `docs/modules/**/review-plan.md` — check *existence* across all modules (one glob; you need it for every module, whatever its marker, to catch marker/plan disagreement). Read the file itself only for modules whose `Review:` marker is 🚧, to count disposed/total from its `## Findings` checklist (`[x]` and `[~]` both count as disposed) and to name the open items' commands. **Count checkbox lines only** — a routed finding carries indented `Location:` / `Drift:` / `Resolution:` sub-bullets that are not items and never affect the count. Ignore those briefs entirely; they are for the command that discharges the finding, not for orientation. Do not read the file for any other purpose — it is a transient work list, not project state.
6. `docs/modules/**/findings.md` — the per-module findings queue: drift recorded outside review, paired with no marker and holding nothing open. One glob for existence, then read each one that exists to count its open `[ ]` items and name their commands. **Count checkbox lines only** — every queue item carries indented `Location:` / `Drift:` / `Resolution:` sub-bullets, which are never items. Read it for nothing else; like `review-plan.md` it is a transient work list, not project state.
7. `docs/adoption-ledger.md` — only if the adoption banner is present. Count its open items (one bullet each) and note a couple of examples; do not otherwise read it line-by-line.

If `docs/index.md` does not exist, the project has not been designed yet. Say so in one line and recommend `/b-design`. Stop.

## Synthesis

From those inputs, compose:

- **Project name and one-line scope summary** — from `scope.md`
- **Adoption phase** — if the `🌱` banner is present, state it and the open-ledger count (e.g. "🌱 adoption phase — 6 open questions in adoption-ledger.md"). Omit this line entirely when there is no banner.
- **Progress overview** — per module, one line each, with status marker and brief state (e.g. "Module B: 🚧 2 of 4 features built"). During the adoption phase, a module's `🚧` reflects as-built-but-unverified features, so phrase it that way (e.g. "Module B: 🚧 4 features as-built, unverified") rather than implying active work.
- **Currently in progress** — any feature at 🚧 **that has a `status.md`**, with a one-line state from it. In the adoption phase, features at `🚧` with no `status.md` are *not* in progress — they belong under *Adopted (unverified)*. A feature whose `status.md` carries a `Pending verification:` line is code-complete and waiting on the operator, not being built: say so on its line (`awaiting verification`) so it is not read as active work, and see *Awaiting manual verification* below for the checks themselves.
- **Adopted (unverified)** — adoption-phase only: features at `🚧` with no `status.md` (as-built from existing code, not yet verified to the `✓` bar). List per module, or a one-line count if many. Omit this section when not in the adoption phase.
- **Degraded or blocked** — any feature at 🟡, 🔴, or 🔧 with the reason
- **Success criteria** — derived, never read from `scope.md`. A criterion is **satisfied** when every module named in its `*Delivered by:*` clause is complete: all features ✓ **and** the `## Module integration` marker ✓. Otherwise it is outstanding, and you name the modules holding it up. Report the count (`N of M satisfied`) and list the outstanding ones with their blocking modules. Three edge cases, all reported rather than guessed at:
  - A criterion with **no `Delivered by:` clause** (pre-v0.24 scope, or one the design left open) is *underivable* — list it as such, do not infer a module from the wording, and do not count it as satisfied.
  - A clause naming a module that **does not exist** under `docs/modules/` is a stale pointer — list it as such. It usually means a module was renamed or dissolved without `scope.md` being re-pointed.
  - During the adoption phase, `🚧` as-built features are not ✓, so criteria will read outstanding. That is correct — adopted code is unverified — but say so in one clause so it isn't read as missing work.
- **Recommended next action** — derived from build order *and* module-integration state. Always emitted as a literal slash command (or the explicit `(none — ...)` form), never as prose:
  - **Adoption phase takes precedence:** if the `🌱` banner is present, the next move is to drain the ledger, not to build — adopted features already exist in code. Emit the ledger as the next action: `Drain docs/adoption-ledger.md (N open) — per item: /b-adr (resolve), /b-feature or /b-design (remediate), or delete the line (dismiss); remove the banner when empty.` Do not recommend `/b-feature <name>` merely because features sit at `🚧` — that `🚧` is as-built, not in-progress.
  - **An open review holding a `/b-design` item outranks all build work.** If any module is `Review: 🚧` and its plan has an open `route:/b-design` finding, recommend `/b-design` — boundary erosion is the one thing the framework does not let accumulate. An open review holding only `/b-feature` items does *not* get this precedence; it competes normally below.
  - **Derive this, never copy it.** A feature's `status.md` may carry its own `## Next move` line, written by the run that last touched it. It is feature-scoped and can be stale — a feature awaiting manual verification holds one that points back at itself, since a stored next move retires at `✓` and pending verification pins the feature at `🚧`. Read the state and apply this ladder; never adopt a stored `## Next move` as the project's recommended action.
  - If a module has features in 🚧 **with a `status.md`** (genuine in-progress work), continue via `/b-feature <name>`. **A feature whose `status.md` carries a `Pending verification:` line does not qualify** — its code is done and the outstanding work is the operator's, so recommending `/b-feature` on it sends the workflow to build something already built. `framework-reference.md` pins such a feature at `🚧` by design, which makes the marker alone unable to tell the two states apart; the `Pending verification:` line is the discriminator. Skip it here and fall through to the rungs below.
  - **Pending verification is surfaced, not blocking.** A feature awaiting a manual check never becomes the recommended next action, and never suppresses one either — nothing about an outstanding operator check prevents building elsewhere. Emit the checks as an additional operator-action line above the recommendation, naming the feature and what the operator must do (e.g. `Operator action: verify cloudflare-config — 2 dashboard changes listed in its status.md`), then give the derived recommendation as normal.
  - Else, if a module is `Review: 🚧`, recommend continuing the review — `/b-review <module>` to resume mediation, or the specific open command if one dominates. Finishing an open review beats starting a new module.
  - Else, if a module has all features ✓ but its `## Module integration` `Test:` marker is ⏸ or 🚧, recommend `/b-integration <module>` — this is the residual case the rule was designed for.
  - Else, the first ⏸ feature in the first not-yet-complete module's build order. Recommend `/b-module <module>` if remaining features are few and unambiguous, else `/b-feature <feature>`.
  - If everything is ✓ (features and module integration) and every success criterion derives as satisfied, emit `(none — project complete)`. An underivable or stale-pointer criterion blocks this: emit `Reconcile docs/scope.md — <N> success criteria have no resolvable Delivered by: module` instead, since the project cannot be declared complete against criteria nothing owns. **An open findings queue blocks it too** — emit that queue's command instead. The queue never competes with the rungs above (deferred work does not outrank planned work), but a project with tracked drift left in it is not one to report as done.
- **Module integration state** — list any module where features are ✓ but the integration marker is ⏸/🚧/🟡/🔴, with the marker shown
- **Review state** — one line per module from its `## Module review` `Review:` marker. This is an **orthogonal axis**: never fold it into the module's status marker in the Progress overview, and never let it affect the success-criteria derivation — review is optional, so an unreviewed module is not thereby incomplete. Report:
  - `🚧 in review` — with the plan's disposed/total count and the open items' commands. This **is** outstanding work; it competes for the recommended next action.
  - `✓ reviewed <date>` — and derive staleness: compare the `(N of N features)` snapshot count against the module's current `## Build order` length. If the roster is now longer, say `stale — <k> features added since`. Never treat staleness as an error or recommend a re-review on the strength of it alone; it is information the operator acts on if they choose.
  - `⏸ never reviewed` — for complete modules only (all features ✓ and integration ✓), since that is the point at which review becomes available and useful. Do not report `⏸` on a mid-build module; it would be noise on every line of a young project.
  - **Missing `## Module review` section** — report as `review state not recorded` for that module, which means the project predates the section and has not run `/b-review` since. Do not infer a past review from anything else.
  - **Marker/plan disagreement** — `🚧` with no `review-plan.md`, or a plan present under `⏸`/`✓`. Report it as a broken review state with `Run /b-review <module>` to resolve; the two are written together, so a mismatch means a run died or something was hand-edited. Do not guess which side is right.
- **Findings queues** — one line per module that has a `findings.md`, with the open-item count and the commands. This is **not** review state: never fold it into the `Review:` line, the module's status marker, or the success-criteria derivation, because a queue holds nothing open and no module is incomplete for having one. It is real deferred work, so it surfaces here and blocks a `(none — project complete)` recommendation, but it never outranks a rung of the ladder below — the operator deferred these deliberately. Omit the section when no module has one. A `findings.md` that exists with **no open items** is a broken state — report it as `<module> — empty findings.md on disk (delete it)`, mirroring the marker/plan disagreement rule above: whoever disposed of the last item was supposed to delete the file.
- **Awaiting manual verification** — any feature whose `status.md` contains a `Pending verification:` line, with the checks listed
- **Open questions / blockers** — anything explicitly flagged in `status.md` files

## Output shape

Produce a single block resembling:

```
Project: <name>
Scope: <1-line summary>
Adoption: 🌱 adoption phase — <N> open questions in adoption-ledger.md   (omit line if no banner)

Progress:
  - Module A: ✓ complete
  - Module B: 🚧 2 of 4 features built (working: <feature>)
  - Module C: ⏸ not started

Currently in progress:
  - <module>/<feature> — <one-line state>
  - <module>/<feature> — awaiting verification, <one-line state>   (has a Pending verification: line)

Adopted (unverified):                          (adoption phase only; omit otherwise)
  - <module>/<feature> — as-built, not yet verified

Degraded / blocked:
  - (none) | <module>/<feature> — <reason>

Success criteria: <N> of <M> satisfied
  - outstanding: <criterion, abbreviated> — blocked on <module> (🚧)
  - unresolvable: <criterion, abbreviated> — no Delivered by: module   (omit line if none)

Module integration:
  - (none pending) | <module> — Test: <path or "not yet defined"> <marker>

Review state:
  - <module> — 🚧 in review, 3 of 7 findings disposed — Run /b-review <module>
  - <module> — ✓ reviewed 2026-07-12 (stale — 2 features added since)
  - <module> — ⏸ never reviewed (complete — Run /b-review <module>)
  - <module> — review state not recorded
  - (nothing to report)

Findings queues:                               (omit the section when no module has one)
  - <module> — 2 open — Run /b-feature modify <module> <slug> according to Q1 in docs/modules/<module>/findings.md
  - <module> — empty findings.md on disk (delete it)

Awaiting manual verification:
  - (none) | <module>/<feature> — <pending check>

Operator action:                               (omit unless something awaits manual verification)
  - verify <module>/<feature> — <what the operator must do, from its Pending verification: line>

Recommended next action:
  - <literal slash command, e.g. /b-feature <name>, /b-module <name>, /b-integration <module>, or "(none — project complete)">

Open questions:
  - (none) | <item from status.md>
```

Keep it tight. This is a dashboard, not a report.
