---
name: b-upgrade
description: Upgrade the project to the current framework version by walking the migration notes in _bower/changes.md.
---
<!-- GENERATED FILE — do not edit. Source: skills-src/commands/b-upgrade.md. Regenerate: node scripts/build-adapters.cjs -->

# Bower Upgrade

You are running the Bower framework upgrade workflow in a **project** (not in the framework repo itself). This command:

1. Clones the Bower framework repo into a temp directory.
2. Runs its `scripts/scaffold.sh` (or `scaffold.ps1`) against this project to refresh the framework footprint: `_bower/`, `.claude/agents` + `.claude/commands`, `.agents/skills/b-*`, and `.codex/agents/bower-*`.
3. Walks each intermediate version's migration notes in order, applying them step-by-step and bumping `_bower/VERSION` after each.

Artifacts jump to the latest framework version in one scaffold pass; only `VERSION` moves step-by-step as migrations apply. This is intentional — see `_bower/changes.md` for the per-version migration notes that drive each step.

The request (the user's optional argument): the request as given in the message that invoked this skill.

## Important Behavioural Rules

- **Refuse to run on a dirty working tree.** If `git status --porcelain` returns anything, abort and tell the user to commit or stash first. The whole upgrade is recoverable via `git reset --hard` only if there's a clean baseline to return to.
- **Walk versions sequentially.** Apply migration N's notes, finish it (bump VERSION, optionally commit), then start migration N+1. Never read multiple versions' notes into a single plan — each step's plan is derived from exactly one version's section in `_bower/changes.md`.
- **Migration notes can be empty or "none".** Many versions have no migration work. Acknowledge and proceed.
- **Self-assess at the end.** This data isn't structured, so we don't have a deterministic validator. After all steps, write a candid paragraph on how confident you are that each migration landed correctly — what was clean, what required judgement, what the user should eyeball. The user decides whether to `git reset --hard` based on your assessment.
- **You are running in the project, not the framework repo.** Do not edit the cloned framework. Edit project files only.

## Step 1: Preconditions

1. Run `git status --porcelain`. If the output is non-empty, stop. Tell the user the upgrade requires a clean working tree (so `git reset --hard` remains a valid escape) and recommend `git stash` or a commit. Do not proceed.
2. Read `_bower/VERSION` from the project. If the file is missing, the project predates the VERSION convention — ask the user at an operator gate (binding: `_bower/framework.md` → *Runtime bindings*) what version their project is currently on (offer the versions from the heading lists you gather in Step 3 — those cover both the current-era changelog and the archive). Stop and wait for their answer before proceeding.
3. Read `_bower/SOURCE` from the project for the framework repo URL. If missing, ask the user at an operator gate for the framework repo URL (default suggestion: `https://github.com/ANU-HDRH/bower-framework.git`).

## Step 2: Clone the framework

Clone shallow into a unique temp directory:

```
git clone --depth 1 <SOURCE_URL> /tmp/bower-upgrade-$$
```

(Use `mktemp -d` or a timestamped path if `$$` isn't available — the path just needs to be unique and writable.) Remember the path; you'll need to clean it up at the end.

If the clone fails (network, auth, bad URL), surface the error to the user and stop.

## Step 3: Determine the upgrade plan

1. Read `<clone>/_bower/VERSION` — this is the new version.
2. List the version headings — **do not read `changes.md` whole.** It is the source of truth for migration notes, but you only need the heading list at this point, and you will read individual sections one at a time in Step 6:

   ```
   grep -n '^## v[0-9]' <clone>/_bower/changes.md
   ```

   This gives each version and its starting line number. Keep the line numbers — Step 6a uses them to read exactly one version's section.
3. Compare:
   - If `new == old`: tell the user "Already at v<old>" and stop. Clean up the temp dir.
   - If `new < old` (project is newer than framework remote — possible if the user is on a fork or a dev branch): stop with a confused message; do not proceed.
   - If `new > old`: continue.
4. From the heading list, take the ordered `vX.Y` versions strictly above `old` and up to and including `new`. This is the list of migration steps. E.g. project at v0.10, framework at v0.13 → steps = [0.11, 0.12, 0.13].
5. **If any step version is absent from the heading list, it is archived.** Versions at or below v0.19 live in `<clone>/docs/changes-archive.md`, which is not scaffolded into projects. Run `grep -n '^## v[0-9]' <clone>/docs/changes-archive.md` to get its heading list too, and note for each step which of the two files carries it. If a step version appears in neither file, stop and tell the user — the version is unaccounted for and guessing at its migration is worse than not upgrading.

## Step 4: Decide commit cadence (only if multi-step)

If the step list contains more than one version, ask at an operator gate:

> The upgrade spans N version steps (v0.X → v0.Y → ...). Commit between each step, or do all steps and commit at the end?

Options:
- **Commit between each step** — Each version's changes land as a discrete commit (`bower: migrate vX.Y → vX.Z`). Easier to bisect, easier to partially `git reset` if one step misbehaves.
- **Commit at the end** — One commit covers the whole upgrade. Simpler history.

If the list is a single step, skip this question — the user can commit when they're satisfied.

## Step 5: Run the scaffold script

### 5a. Check whether this runtime can run the scaffold at all

The scaffold writes into `.agents/` and `.codex/`, which some runtimes protect from workspace writes (Codex's `workspace-write` sandbox mounts both read-only, with no approval prompt — the write simply fails). Decide the path **before invoking the scaffold**: never run it in-sandbox hoping to recover, because a partial run refreshes `_bower/` and `.claude/` and then dies at the protected trees, leaving the runtime adapters on different framework versions.

Probe first, and probe the way the scaffold's own preflight does: **a directory that does not exist yet is judged by its nearest existing ancestor**, which is where the `mkdir` would land. This matters on exactly the upgrade that needs it most — a project scaffolded before the adapter trees existed has no `.agents/` or `.codex/` at all, and *absent is not protected*. A probe that writes straight into the directory fails on absence too, which would send every first upgrade down the operator-run path on a runtime that could have run the scaffold itself.

```
for d in .agents/skills .codex/agents; do
  p="$d"; while [ ! -d "$p" ]; do p="$(dirname "$p")"; done
  if ( : > "$p/.bower-write-probe" ) 2>/dev/null; then rm -f "$p/.bower-write-probe"
  else echo "PROTECTED: $d"; fi
done
```

No `PROTECTED:` line → Step 5c. Any `PROTECTED:` line → Step 5b.

### 5b. Protected paths: hand the scaffold to the operator

If the runtime offers a way to request escalated execution for a single command, you may request it for the exact scaffold command — a runtime permission request, which the operator may freely deny. If no escalation path exists, or it is denied, do **not** attempt any part of the scaffold. Print the exact command for the operator to run themselves in a terminal outside this runtime's sandbox:

```
bash <clone>/scripts/scaffold.sh <project-root>
```

(On Windows: `powershell -File <clone>\scripts\scaffold.ps1 <project-root>`.)

Tell them the clone must stay in place until this is done, wait for their confirmation that the scaffold ran (an operator gate — their explicit word, not an assumption), and verify before continuing to Step 6. Verify against *state, not a diff*: check that the footprint is at the new version — `.agents/skills/b-upgrade/SKILL.md` exists, `.codex/agents/bower-*.toml` are present, the project's `_bower/changes.md` carries the new version's `## v<new>` heading. A scaffold run over a footprint some of which was already current changes nothing, and reading "nothing changed" as "it did not run" would strand a correct upgrade. If they decline to run it, abort the upgrade honestly: no migration has been applied, `_bower/VERSION` is untouched, and the clone path is reported for manual cleanup. Never report a partial upgrade as complete.

### 5c. Run the scaffold

```
bash <clone>/scripts/scaffold.sh <project-root>
```

(On Windows, run `scaffold.ps1` instead.)

This refreshes `_bower/` (except `VERSION` and `SOURCE`, which the scaffold preserves) and the runtime command/agent surfaces (`.claude/agents`, `.claude/commands`, `.agents/skills/b-*`, `.codex/agents/bower-*`). It also prunes any framework files the framework no longer ships, printing a `removed (retired upstream)` line for each — note these for the Step 7 summary; they need no other action. The project's `_bower/VERSION` is still at the *old* value at this point — that's intentional. You own VERSION writes from here on.

**Note:** The scaffold just rewrote this workflow's own definition (`.claude/commands/b-upgrade.md` and `.agents/skills/b-upgrade/SKILL.md`). The new version takes effect on the next `/b-upgrade` invocation; this run continues with the instructions already in your context.

## Step 6: Walk migration steps

For each version in the step list, in order, oldest first:

### 6a. Extract migration notes for this version

Read **only this version's section** — not the whole changelog. Use the heading line numbers from Step 3: the section runs from this version's `## v<X.Y>` line to the line before the next `## v<X.Y>` heading. For the oldest entry in a file, it runs to the `## Earlier versions` pointer if the file has one, otherwise to end of file. **Read only that line range**, by whatever means this runtime offers for reading part of a file — never the whole changelog:

- **Current-era versions (v0.20 and above)** are in the project's now-updated `_bower/changes.md`.
- **Archived versions (v0.19 and below)** are in `<clone>/docs/changes-archive.md`, which the scaffold does not copy into projects. Read them from the clone. The project's `_bower/changes.md` carries a version index covering them, but not their bodies.

Either way the result is the version's full entry — what changed, why, and the migration notes. Reading one section at a time is deliberate: it keeps the migration you're applying the only one in context, and it means the changelog's total size never bounds an upgrade.

Identify the migration content within that entry. Contributors write it under a `### Migration` subheading or a `**Migration notes**` bold paragraph (older entries). If the section is absent, "none", or describes no project-side work, treat the step as a no-op — just bump VERSION (and optionally commit) and continue.

### 6b. Plan

Read any project files the migration notes reference (e.g. `docs/architecture.md`, `docs/modules/*/module-status.md`). Produce a concrete plan:

- Exact files you'll edit or create.
- For each file, the specific change in plain language (not a diff — the user is reading this to decide, not to review syntax).
- Any judgement calls you're making (the notes were written for a model audience but still leave room for interpretation — name those calls).

### 6c. Gate

Present the plan at an operator gate. Frame as: "Here's the plan for migration v<X.Y>. Confirm to apply, or tell me what to adjust."

Options:
- **Apply this plan** — proceed to execution.
- **Adjust** — user gives free-text feedback; revise and re-gate.
- **Skip this step** — apply no changes for this version but still bump VERSION (use sparingly; the user is overriding the migration notes).
- **Abort upgrade** — stop now. Tell the user the temp clone path so they can clean it up, and remind them `git reset --hard` reverses any committed steps.

### 6d. Execute

Apply the edits. Edit project files directly. Do not edit the cloned framework.

### 6e. Bump VERSION

Overwrite `_bower/VERSION` with this version's number (just the number, no `v` prefix, with a trailing newline to match the framework's format).

### 6f. Optional commit

If the user chose "commit between each step" in Step 4, commit now:

```
git add -A
git commit -m "bower: migrate v<old> → v<new>"
```

(Use the actual old/new strings.) If the user chose "commit at the end" or this is a single-step upgrade, do not commit yet.

## Step 7: Final summary and self-assessment

After all steps complete:

1. **Clean up** the temp clone directory (`rm -rf <clone>`).
2. **Emit a self-assessment.** Be candid. For each step:
   - What you applied.
   - What was mechanical vs. what required judgement.
   - Anything the user should sanity-check by eye (a file you weren't sure about, a backfill where the source data was thin, a decision the notes left to your discretion).
3. **Emit the handoff block** with the literal commands for what to do next:

```
Bower upgrade complete: v<old> → v<new>

Self-assessment:
  <candid paragraph per step or overall>

Next move:
  - If everything looks right: commit (if you chose end-of-run commits) and continue your work.
  - If something looks wrong: `git reset --hard <baseline-ref>` to undo, then investigate.
  - Start a new session before further Bower work — this upgrade rewrote instruction
    and skill files, and a running session must not be assumed to have reloaded them
    (binding: _bower/framework.md → Runtime bindings → Sessions).
```

<critical_constraints>
## What NOT To Do

- Do not run if `git status --porcelain` is non-empty
- Do not read more than one version's migration notes into a single plan — walk them strictly in order
- Do not edit files in the cloned framework repo — it is read-only reference; edit the project only
- Do not auto-commit if the user chose "commit at the end" or didn't see Step 4's question
- Do not silently skip a step whose migration notes are non-trivial — if you can't interpret them, ask at an operator gate rather than guessing
- Do not bump VERSION before applying the step's migrations — the bump signals the migration landed
- Do not run the scaffold in-sandbox when the runtime protects `.agents/` or `.codex/` — a partial run leaves the runtime adapters on different framework versions; probe first (Step 5a) and hand the command to the operator (Step 5b)
- Do not report a partial or operator-declined upgrade as complete — if the scaffold did not run, no migration happened and VERSION is untouched
- Do not claim the running session has reloaded the files this upgrade rewrote — hand off to a new session for further Bower work
- Do not leave the temp clone directory behind
- Do not claim a clean migration if any part required substantial judgement — the self-assessment is for the user to decide whether to `git reset`, and an over-confident assessment defeats the safety mechanism
- Do not emit free-prose next moves — use literal shell/slash commands in the handoff
</critical_constraints>
