---
name: b-analysis
description: Read-only change brief from the bower-analyst subagent — what does a proposed change imply across the project?
---
<!-- GENERATED FILE — do not edit. Source: skills-src/commands/b-analysis.md. Regenerate: node scripts/build-adapters.cjs -->

# Bower Analysis

You are running the Bower analysis workflow. This is a **strictly read-only, advisory** command that produces a Bower **change brief** for a proposed change against the current project — useful as a standalone inspection tool, and as a sanity check before running `/b-design` to execute the change.

You do **not** write files, run git, invoke downstream commands, or confirm/gate. You delegate to the `bower-analyst` subagent, receive its brief, and emit it verbatim.

The request (the user's change description): the request as given in the message that invoked this skill.

## Process

### Step 1 — Confirm input

If the request is empty or missing, ask the user for a change description and stop — end the turn and wait. Do not proceed without one.

### Step 2 — Delegate to the analyst

Delegate to the `bower-analyst` subagent (binding: `_bower/framework.md` → *Runtime bindings*) and wait for its brief. The prompt to the subagent must include:

- The change description verbatim.
- The project root (the current working directory).
- An instruction to produce the brief per `_bower/brief-schema.md`.

Shape:

```
Produce a Bower change brief for the proposed change below. Conform exactly to the schema in _bower/brief-schema.md.

Project root: <cwd>

Change description:
<verbatim description>
```

Do **not** attempt the analysis in the main context while delegation is available. The subagent exists precisely so the analysis happens in isolated context, against a focused prompt; running it inline defeats the purpose. If this runtime cannot delegate, that is the one exception: you — the calling workflow — follow `bower-analyst`'s definition inline, say so in one line, and mark the emitted brief `Context: inline`.

### Step 3 — Emit the brief

The subagent's final message is the brief. Emit it to the user verbatim — do not summarise, paraphrase, abridge, reorder, or interpret. The brief is the output; anything else is noise.

### Step 4 — Handoff

After the brief, emit a single short handoff block:

```
Brief produced. The `## Considered and ruled out` and `## Ambiguities and assumptions` sections are the primary audit surfaces — read them carefully.

Next move:
  - To execute this brief: /b-design <change description>
  - To refine and re-analyse: /b-analysis <revised description>
```
