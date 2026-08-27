---
name: b-ui
description: Gated path for structural, underspecified UI changes — propose with alternatives, confirm, implement, reconcile docs/ui.md.
---
<!-- GENERATED FILE — do not edit. Source: skills-src/commands/b-ui.md. Regenerate: node scripts/build-adapters.cjs -->

# Bower UI Change

You are running the Bower UI change workflow — the gated path for **structural and underspecified** changes to the experience surface. Most UI work does not need this skill: visual tweaks, copy edits, and tightly-specified structural changes are handled out-of-band (the decision table lives in `_bower/framework.md` → *UI Changes — Paths and the Gate*; worked examples in `_bower/framework-reference.md`). Reach for `/b-ui` when the change touches navigation, screen composition, layout grammar, or interaction patterns **and** the request has branching choices the user should pick between.

This skill mirrors `/b-feature`'s propose-confirm-implement-reconcile shape, tuned for the experience surface: lighter reading list, proposal with alternatives, mock-up-or-description rather than component/caller analysis, reconciles `docs/ui.md` rather than feature plans alone.

The request (the user's description of the UI change): the request as given in the message that invoked this skill.

## Important Behavioural Rules

<lighter_path_check>
Before running this skill, ask whether it's the right shape for the request:

- **Visual-only** (move an icon, tweak colour, adjust spacing, change copy) → suggest dropping to ad-hoc work. No gate, no docs.
- **Structural but tightly specified** ("add a logout item to the user menu, opens a confirm modal") → suggest just doing it and reconciling `docs/ui.md`.
- **Structural with branching choices** → proceed with this skill.

The test for "branching choices": would you have to pick between ≥2 viable shapes (modal vs page, tabs vs accordion, drawer vs dropdown)? If yes, the gate earns its keep. If the operator already named the shape, it doesn't — invented alternatives are noise, not value. The operator can confirm to run the skill anyway, but offering the lighter path first is the right default.
</lighter_path_check>

- **Consult before building.** Present your proposal at an operator gate (binding: `_bower/framework.md` → *Runtime bindings*) — including at least two viable alternatives where the change has branching choices — and get explicit confirmation before writing code.
- **Read first.** Read `docs/ui.md` (or note its absence), the relevant feature plans, and the project's design-token / theme / style config. Skim the architecture's UI module entry.
- **Scope tightly.** Only propose what this request needs. Don't redesign adjacent screens.
- **Architecture is hard-redirected.** If the request introduces a new top-level navigation pattern, swaps the design system or UI framework, adopts new state-management for the UI layer, or otherwise crosses architectural boundaries, stop and recommend `/b-design`. Surface what's architectural and decline ad-hoc. The hard line is the same as elsewhere in the framework.
- **Capture invariants, not pixels.** `docs/ui.md` records navigation, layout grammar, interaction patterns, and visual-language pointers. Code remains the truth at the pixel level. If your proposed `ui.md` edit reads like a layout spec, you've gone too granular.
- **Literal-command handoff.** Every "next move" you emit names the exact slash command to type next.

## Step 1: Understand Context

1. Read `docs/ui.md` if it exists. If not, note this — your output may include initialising it.
2. Read `docs/architecture.md` for runtime context, especially the UI module's entry under `## Software architecture`.
3. Read the `plan.md` of any feature whose screens this change touches.
4. Read the project's style / theme / token config, whichever applies to the surface. For web: `tailwind.config.*`, `theme.{ts,js}`, `design-tokens.*`, CSS-in-JS theme files. For desktop GUI: QSS/stylesheet files, theme XML, or equivalents. For TUI: colour palette and typography conventions (often a Python module or config file). Skip if the project has no central style config.
5. **Load relevant ADRs.** If `docs/adr/index.md` exists, read it. Open any accepted ADR whose `modules` lists a UI-relevant module, that is cross-cutting (no `modules` field), or whose title is topically relevant to the change. Treat ADRs as constraints to confirm, not as ground truth — if an ADR contradicts current code, flag it at the gate.

## Step 2: Propose Changes (with options)

Prepare a proposal covering:

- **Intent:** what's being added, modified, or removed in the UI.
- **At least two viable alternatives** where the change has genuine branching choices (e.g. tab nav vs. accordion nav vs. modal nav for content navigation). For each: a short sketch (ASCII mock-up or bulleted layout description), what it commits the design to, what it leaves flexible. Mark one as **(Recommended)** with rationale, but make it clear the user chooses.

<branching_judgment>
"Genuine branching choices" means two or more viable shapes exist that you cannot pre-empt by reading `docs/ui.md` or the operator's wording. If they named a specific shape ("a modal"), the choice is already made — don't invent alternatives just to fill the gate. If they named only a goal ("user settings"), shapes are open and alternatives are real.

When alternatives are real, present 2-3 — not more. Each should commit the design to something distinguishable (not three flavours of the same answer). If you can only find one viable shape, surface this and ask the operator whether to proceed without alternatives or whether the request is actually a Path 2 (specified) change that doesn't need the gate.
</branching_judgment>
- **UI doc impact:** which sections of `docs/ui.md` will be created or updated (navigation map, screen inventory, layout grammar, interaction patterns), or "initialise `docs/ui.md`" if it doesn't yet exist.
- **Feature impact:** which feature `plan.md` files need updates, if any.
- **Decision impact:** any accepted ADRs this touches (confirms, contradicts, narrows, or surfaces as a new cross-cutting decision). Write `none` if no ADRs are touched.
- **Acceptance:** how we'll know it's right. UI work is usually manual ("does this look and feel right?"), occasionally automated (Playwright e2e for an interaction pattern, visual-regression for a layout that should not drift). Be specific.

## Gate: Confirm or Adjust

Present the proposal to the user at the operator gate. Frame as:

"Here are the options for this UI change. Pick one to proceed, or tell me what to adjust."

**Do not write any code until the user confirms.**

## Step 3: Implement

After confirmation:

1. Implement the chosen option.
2. Run any automated checks that apply (visual regression, e2e). If acceptance is purely manual, note it for Step 4.

## Step 4: Acceptance Reconciliation

For each acceptance criterion, map to evidence:

```
- <criterion> — automated: <path::name> — PASS
- <criterion> — manual: "<check description>" — PENDING USER
```

For PENDING USER manual checks, frame before asking — the operator does not yet have a screenshot tool (see `_bower/roadmap.md` — deferred), so compensate with description:

1. **State what changed visually** in one or two sentences. ("The dashboard now shows three tabs across the top: Inbox, Outbox, Archive. Clicking switches the panel below.")
2. **Name one or two specific things to look at.** ("Check the active tab indicator and the behaviour at narrow widths.")
3. **Then present the question** at an operator gate.

Without this framing the operator gets "does it look right?" with no anchor; with it, verification is productive in one round-trip. Mark per response. If the operator defers, leave as PENDING USER and reflect that in the docs in Step 5.

**Decision reconciliation.** Review each ADR flagged in Step 2's Decision impact:

- **Confirmed** — no action.
- **Contradicted / drifted** — invoke `/b-adr` to write a superseding ADR.
- **Narrowed** — invoke `/b-adr` to write a narrowing ADR. Pass the rationale and the ADR-ID being narrowed. The new ADR carries `narrows: [ADR-NNNN]`, the old one gains `narrowed-by` and keeps `status: accepted`.
- **New cross-cutting decision** — invoke `/b-adr` to record it.

Skip only if Step 2 listed Decision impact as `none`.

## Step 5: Update Documentation

1. **`docs/ui.md`** — the primary reconcile target.
   - If absent, create it with the sections relevant to this change. The doc grows as the UI grows; do not pre-emptively scaffold sections that don't yet apply.
   - If present, update affected sections to reflect the new state. The doc represents *current state*, not history.
   - Suggested sections (use what fits — do not invent empty headers): `## Navigation`, `## Screens`, `## Layout grammar`, `## Interaction patterns`, `## Visual language`.
   - Stay at invariant-level. Navigation map, screen inventory, layout patterns, interaction conventions — yes. Pixel coordinates, exact copy, component implementation details — no.
2. **Feature `plan.md`** — update any that the proposal listed.
3. **`module-status.md`** `## Module integration` `Notes:` — update if the change shifted what the module-boundary integration test must assert (rare for visual work; common when introducing a testable interaction pattern). Do not flip the marker.
4. **`scope.md`** — only if the change shifted the scope boundary, changed a non-goal, or added/removed/reworded a success criterion. Never to record a criterion as met: criteria carry no status. Most UI work does not touch scope at all.

`Next move:` is a literal slash command:

- `Run /b-ui <description>` — if this change revealed follow-up UI work that warrants the gate.
- `Run /b-feature <name>` — for the next non-UI feature in an affected module.
- `Run /b-integration <module>` — if a testable interaction pattern was introduced and the module's integration test needs updating.
- `(none — UI change complete)` — when there's no follow-up.

If during implementation you discover the approach needs to change significantly, stop and consult the user at an operator gate before continuing.
