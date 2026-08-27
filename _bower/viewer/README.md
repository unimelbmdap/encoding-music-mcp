# Bower docs viewer

A local web view of a Bower project's `docs/` tree: project state, the module
graph, derived success criteria, ADRs, per-feature plans and status — plus a
drift report comparing what the docs claim against what is actually on disk.

Read-only. It never writes to `docs/`.

It ships inside `_bower/`, so the scaffold script copies it and `/b-upgrade`
refreshes it in the same pass that migrates the docs it reads — the tool and the
schemas it parses can never drift more than one commit apart. Commit it along
with the rest of `_bower/`; there is nothing local or generated about it.

## Run it

```bash
node _bower/viewer/serve.cjs            # http://localhost:4173
node _bower/viewer/serve.cjs --port 8080
node _bower/viewer/serve.cjs --host 0.0.0.0        # also reachable on your subnet
node _bower/viewer/serve.cjs --root ../other-proj  # another Bower project
node _bower/viewer/serve.cjs --build graph.json    # emit the graph, no server
```

Edits under `docs/` re-extract and push a live reload. Add `?static=1` to the
URL to skip the live connection (used for headless capture).

Binds loopback by default. The graph embeds every document body — including
whatever `docs/operations/` says about where credentials live — so exposing it
to your subnet is opt-in via `--host 0.0.0.0`.

Runs on `node` or `bun`, with **no dependencies**. Files are `.cjs` so the host
project's `package.json` (`"type": "module"` or not) cannot affect them.

## Layout

```
lib/md.cjs        markdown structure parsing — frontmatter, sections, tables
lib/extract.cjs   docs/ → graph.json. Pure: no DOM, no vscode API, no npm
serve.cjs         static server + fs.watch + SSE live reload
web/              the client: index.html, style.css, app.js, vendored marked
```

`extract.cjs` and `web/` are shell-agnostic on purpose. The client reaches its
container through one narrow interface (`HOST` at the top of `app.js`:
`openFile`, `graphUrl`, `eventsUrl`), so a VS Code extension can swap the
implementation without touching any view code. `serve.cjs` is the only
browser-specific piece.

## Schema contract

**This is the table to check when you change a Bower document schema.** The
viewer parses those schemas, so a schema change can break it — and the break is
silent, producing plausible-looking wrong findings rather than a crash. Every
convention the extractor depends on is listed here against the section that
defines it. Changing a row means changing `lib/extract.cjs` and
`tools/viewer-test/fixture/` in the same commit.

| Convention | Defined in | Yields |
|---|---|---|
| `## Software architecture` `### <module>` blocks — purpose, data concern, depends on, consumed by | `framework.md` Core Principles; `/b-design` Stage 3 | the module graph and its edges |
| `## Build order` entries and markers — **the module's only feature roster** | `framework-reference.md` → *module-status.md — Integration and Build Order* | build order, per-feature markers |
| `## Build order` pull-forward annotation, incl. the `Remaining:` clause | same section, *Pull-forward annotation* | what is actually left to build |
| `## Module integration` `Test:` / `Notes:` lines | same section | integration marker and test path |
| Module status rollup — worst across features **and** integration | same section, *Module-level status is a floor* | derived module status |
| `status.md` leading marker, `## Next move`, `Pending verification:` | `framework-reference.md` → *status.md — Resumption Framing* | feature state, next moves, honesty checks |
| `status.md` terminal form at ✓ — `## Verification` (+ `Qualification:`), `Next move: (none — complete)`; a stored next move is feature-scoped | same section, *Terminal form* | `next-move-on-complete`; the next-moves panel excludes ✓ features |
| `## Success criteria` bullets + `Delivered by:` clauses, **no status field** | `framework-reference.md` → *scope.md — Boundary, Not Tracker* | derived criteria satisfaction |
| `plan.md` `## Components` table | `/b-feature` Step 6 | the file → feature index |
| ADR frontmatter: `status`, `scope`, `modules`, `topics` | `framework-reference.md` → *ADRs* | facets, applicability |
| ADR frontmatter: `supersedes` / `superseded-by` | same section, *Lifecycle* | supersession chains and symmetry checks |
| ADR frontmatter: `narrows` / `narrowed-by`, target stays `accepted` | same section, *Narrowing* | narrowing pairs and their checks |
| `constitution.md` `## Not yet in force` | `framework-reference.md` → *constitution.md — Normative Shape* | separates aspiration from rule |
| `docs/index.md` 🌱 banner + `docs/adoption-ledger.md` | `framework-reference.md` → *Adoption phase* | phase detection; suppresses per-feature status warnings |
| `## Module review` `Review:` line — marker, date, `(N of N features)` snapshot | `framework-reference.md` → *module-status.md — Integration and Build Order* | review state, derived staleness, the lifecycle panel |
| `docs/modules/<m>/review-plan.md` `## Findings` checklist — `[ ]` / `[x]` / `[~]` | `framework-reference.md` → *Module Review* | in-review banner, disposed/total counts, marker↔plan agreement |
| `review-plan.md` finding line — `F<n> — <gist> — <class> — <pointer>`, optionally `— done YYYY-MM-DD via <command>` on a ticked routed item, the closed class vocabulary, the preamble's date and roster count, `## Observations` | `/b-review` Step 3 (the plan shape); the tick grant in `framework-reference.md` → *Module Review* | the review page: what each finding is, who owns it, where it points, and who ticked it. The completion note is split off the pointer — the pointer is a command meant to be copied verbatim |
| `review-plan.md` routed-finding brief — indented, checkbox-free `- Location:` / `- Drift:` / `- Resolution:` sub-bullets under a `route:*` item, all three required and non-empty | `/b-review` Step 3 (shape rules) | the brief shown under its finding; the incomplete-brief check. Indentation is load-bearing: a brief line matching the checkbox pattern would inflate the disposed/total counts |
| `review-plan.md` anything else — indented prose under a finding, sections beyond `## Findings` / `## Observations` | — (operator material, not schema) | carried through and rendered: links to the plan resolve to the review page rather than a raw view, so the page must never show less than the file |
| `docs/modules/<m>/findings.md` — the findings queue: same line and brief shape as a routed review finding, IDs `Q<n>`, no marker pairs with it | `framework-reference.md` → *Findings queue* | the `findings-queue-empty` check (a queue with no open items is residue). The file is rendered as a routed page by the loose-file rule below, not parsed into a structured view. Nothing links to it — the route exists so the queue is readable in the rail, the file index and search, and so that a stale link from before it drained resolves rather than reading dead |
| Any other loose `.md` at a module root | — (deliberately open) | a routed page, mirroring the central-docs sweep. A closed whitelist here is what made `findings.md` render as a dead link on a real project while the drift report reported nothing — `broken-link` tests existence, the renderer tests routability |
| `docs/index.md` Modules table markers | `/b-index` | each module's *declared* status, compared with the derived one |
| Repo-root-based doc links (`/docs/…`) | `framework.md` Working Conventions | backlinks; broken- and relative-link checks |
| `git log -- docs` | — | recency (optional; degrades if absent) |

Nothing outside this table is guessed at. Feature→feature edges in particular
are deliberately absent: `## Integration points` is prose. Module→module edges
from `architecture.md` are complete, so the graph does not suffer for it.

`lib/extract.cjs` declares `SCHEMA_VERSION` — the framework version whose
schemas it parses. It is compared against the target project's `_bower/VERSION`,
and a mismatch is reported in the UI rather than silently misread. Bump it when
a row above changes.

## The drift checks

The reason to open this more than once. Each compares two documents, or a
document against the filesystem.

**Errors — a contradiction.** Two documents cannot both be right.

- a build-order marker disagrees with that feature's own `status.md`
- a feature is ✓ while its `status.md` still lists pending verification
- a success criterion is delivered by a module that does not exist
- an ADR supersession or narrowing is recorded on only one of the two ADRs
- an ADR names a module that does not exist
- an accepted ADR also carries `superseded-by`
- an ADR claims both `narrows` and `supersedes` on one target
- a **narrowed** ADR is not `accepted` — narrowing leaves its target in force, so
  this is the exact defect the field exists to prevent: live policy marked dead

**Warnings — something to reconcile.** Not automatically a defect.

- a built feature's plan lists a `Components` file that is not on disk
- a build-order entry past ⏸ has no docs directory
- a `## Build order` has numbered entries but none parse — the roster would
  otherwise read as empty and cascade into per-feature findings with one cause
- `docs/index.md` declares a module status the feature markers do not roll up to
- `architecture.md` still lists a module's features (v0.26 moved the roster)
- a success criterion has no `Delivered by:` clause, or still carries a marker
- a doc link does not resolve
- the adoption ledger is empty but the 🌱 banner is still up
- a module is `Review: 🚧` with no `review-plan.md` on disk — a review was opened
  and its findings are gone
- a `review-plan.md` exists but `Review:` is not 🚧 — the marker was never set, or
  the review closed without deleting the plan. `/b-review` writes the two
  together, which is what makes either direction detectable at all
- a table cell holds a paragraph of prose — a formatter then aligns every sibling
  row out to match it, and on a real project one 15,000-character cell became
  75kB of padding in `docs/index.md`, on the orientation read-path of nearly
  every command. Ordinary column alignment costs a few kB and is not reported.

**Info — a convention note.** Three concern review state. An open routed finding
whose `Location`/`Drift`/`Resolution` brief is absent **or incomplete**: the
command that eventually discharges it — `/b-feature` or `/b-design`, in a session
that never saw the review report — would start from the one-line gist alone,
which is the gap v0.32 closed. All three fields are required and must be
non-empty, because they do different jobs: where to look, what disagrees with
what, and what to do about it. A location-only brief is the worse case, not a
lesser one — it looks like a handoff while still forcing the re-derivation the
brief exists to prevent. It is version-gated rather than tripwire-guarded, since on a pre-v0.32
project every routed finding is briefless by construction and that is history,
not drift. The other two: a closed review whose
roster snapshot is smaller than the build order is now (features exist that the
review never saw — derived, since nothing invalidates a review), and a
`module-status.md` with no `## Module review` section at all. The second fires on
every module of a project that has not run the v0.29 migration, so it is
deliberately exempt from the obsolescence tripwire below — universality is the
signal there, not decay.

Also including two aimed at the viewer itself:
`schema-version-skew` when it and the project disagree about the framework
version, and `check-may-be-obsolete` when a check fires on *every* candidate.
That second one is a tripwire for this tool's own decay — a check matching
everything is more often testing a dropped convention than finding a defect in
every instance, which is precisely how the v0.26 roster change turned this
report into 48 false warnings on a real project.

A `warn` is a prompt to look, not a verdict. The module-status divergence in
particular can be a deliberate human judgement the mechanical rollup cannot make.

## Module status rollup

A module's status is the worst marker across its features and its integration
test — but ⏸ is read as *not started* rather than as a severity, so a module
that is part built and part planned rolls up to 🚧, and only an entirely
untouched module is ⏸. That is what `framework-reference.md`'s own worked example
describes: all features ✓ with `## Module integration` still ⏸ surfaces as 🚧.
Where the rollup disagrees with `docs/index.md`, both are shown and the
difference is reported rather than silently resolved.

**Review is not in that rollup.** A module page shows a *Lifecycle* panel with
three separate axes — build, integration, review — because `/b-review` is
optional framework work. Folding its marker into the worst-of derivation would
silently make it mandatory and would knock every complete-but-unreviewed module
off ✓. So the review state sits beside the status marker and never inside it: a
module can be ✓ and never reviewed, or mid-build with a review open, and both are
honest. Review staleness is derived the same way `/b-recap` derives it — the
`(N of N features)` snapshot against the current build order — so it catches
features *added* since the review, not features modified in place.

**An open review has a page.** While `review-plan.md` is on disk the review lane
is a link (`#/review/<module>`, also where the in-review banner goes), and that
page shows the `## Findings` checklist itself: each finding's disposition, its
gist, its class, and where it points — a file, openable, or the literal command
that discharges it. A count of disposed findings is not something an operator can
act on; the findings are. The page exists only as long as the plan does, which is
correct — at closeout the plan is deleted and `Review: ✓` is the whole record.

## Keeping it honest when the framework changes

The viewer reads Bower's document schemas, so it is coupled to them by
construction. Four things hold that coupling, in increasing order of teeth:

1. **The contributor rule** in the framework repo's `AGENTS.md`: a change to a
   document schema checks this README's Schema contract table.
2. **The table itself**, which names the defining section verbatim — so the
   section you are editing is greppable from the framework repo root.
3. **`node tools/viewer-test/run.cjs`** — fixtures containing one instance of
   every drift condition, plus a conformant module that must produce *zero*
   findings. The negative assertion is the one that matters: the expected set of
   finding kinds is exact, so a check that starts firing on correct docs fails
   the run. Not scaffolded into projects; it lives in the framework repo.
4. **`scripts/release.sh` runs that test** and aborts on failure, so a framework
   version cannot be released with the viewer misreading it.

Before shipping a framework change that touched a schema, also point the viewer
at a real project — `--root ../some-project` — and read the drift page. The
fixtures prove each check is *correct*; only a real project proves the parser
survives real data (a hundred-plus distinct plan section names, megabytes of doc
body, real git history). Neither substitutes for the other.

## Not built yet

The VS Code extension. The pieces it needs — reverse file→feature lookup,
per-file ADR context, the drift checks as live diagnostics in the Problems
panel — all come from `extract.cjs` unchanged; only a new shell is required.

The viewer is deliberately **human-facing only**: no `/b-*` command consumes its
output, and agents read `docs/` directly as they always have. Wiring the drift
checks into `/b-review` is recorded in `_bower/roadmap.md` with its revisit
trigger; doing it would make this tool's output a contract, which is a larger
commitment than a reading surface.
