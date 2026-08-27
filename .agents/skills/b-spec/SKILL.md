---
name: b-spec
description: Export a single specification document from the project's Bower documentation, for readers outside the project.
---
<!-- GENERATED FILE — do not edit. Source: skills-src/commands/b-spec.md. Regenerate: node scripts/build-adapters.cjs -->

# Bower Spec Export

You are generating a single specification document from the project's Bower documentation. This document is for sharing with people outside the project — stakeholders, collaborators, reviewers, or other teams.

The request (optional scope or instructions from the user): the request as given in the message that invoked this skill.

## Step 1: Read Everything

1. Read `docs/architecture.md`
2. Read `docs/design/problem-space.md` (if it exists)
3. Read `docs/adr/index.md` and every accepted ADR in `docs/adr/` (if the directory exists). Skip superseded and deprecated ADRs — the spec presents *current* decisions.
4. Read `docs/index.md` to identify all modules and features
5. Read every `plan.md` across `docs/modules/`
6. Read every `module-status.md` for integration context

Note which files exist and which don't — the spec should only cover what's documented.

## Step 2: Determine Scope

Confirm what should be included at an operator gate (binding: `_bower/framework.md` → *Runtime bindings*). Present:

- The full list of modules and features you found
- Whether design context exists (problem-space.md, accepted ADRs)
- Your recommendation: full project spec, or a subset

Ask: "What should the spec cover? Everything, or specific modules/areas? And who's the audience — this affects the level of technical detail."

Wait for confirmation.

## Step 3: Synthesize

Write a single markdown document with this structure (adapt sections to what actually exists):

```
# [Project Name] — Specification

## Overview
[2-3 paragraphs: what this system does, why it exists, who it's for.
Drawn from architecture.md overview and problem-space.md.]

## Problem Context
[From problem-space.md: the problem, current alternatives, success criteria, scope.
Skip if no design/ docs exist.]

## Design Decisions
[Synthesised from accepted ADRs in docs/adr/. Present as narrative, not a raw
decision log — group related decisions, explain the reasoning chain, focus on
what the reader needs to make sense of the architecture. E.g. a paragraph
linking three related ADRs into a single technology-stack rationale, rather
than listing each ADR as its own bullet. Skip superseded and deprecated ADRs.
Skip the section entirely if no ADRs exist.]

## Architecture
[From architecture.md: components, data flow, technology stack, constraints.
Include extension points if relevant to the audience.]

## Modules

### [Module Name]
[From the module's entry in architecture.md `## Software architecture`:
what this group of features does together — its purpose and data concern.
From each feature's plan.md: purpose, how it works, key components,
integration points. Omit source locations, test paths, and internal
status tracking — the reader doesn't need those.]

[Repeat for each module in scope]

## Known Limitations
[Aggregate from plan.md known limitations sections.
Only include if substantive.]
```

## Step 4: Present

Write the spec to a file. Confirm the output path at an operator gate. Suggest `docs/spec.md` by default, but note that if this is a one-off export, the user might prefer a location outside `docs/` so it doesn't get treated as a living document.

<critical_constraints>
## Rules

- **Strip internal details.** Source file paths, test file paths, status markers, work-in-progress items, and deferred work are internal. Don't include them.
- **Narrative over template.** The output should read as a coherent document, not a concatenation of templates. Use transitions, combine related points, and cut redundancy.
- **Respect the audience.** If the user says it's for a non-technical stakeholder, reduce implementation detail. If it's for a technical reviewer, keep it.
- **Don't invent.** Only include what's in the documentation. If something is missing or thin, note the gap rather than filling it with assumptions.
- **Don't update project docs.** This command reads and exports. It doesn't modify any existing Bower documentation.
</critical_constraints>
