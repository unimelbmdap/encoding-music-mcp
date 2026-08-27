'use strict';
// Bower docs → graph.json
//
// Reads a Bower project's docs/ tree and emits a single structured graph.
// Pure and dependency-free: no DOM, no vscode API, no npm. The web shell and a
// future VS Code extension both consume this identical output.
//
// EVERY document convention this file parses is listed in the viewer README's
// "Schema contract" table, against the framework-reference.md section that
// defines it. If you change a schema here, change that table in the same commit
// — the table is how the next framework change finds this file.

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const M = require('./md.cjs');

// The framework version whose document schemas this extractor was written
// against. Compared with the target project's _bower/VERSION so a viewer
// pointed at a project on another version says so, rather than quietly
// misreading it. Bump when a framework change alters what is parsed here.
const SCHEMA_VERSION = '0.34';

// ---------------------------------------------------------------- helpers

const read = (p) => fs.readFileSync(p, 'utf8');
const exists = (p) => fs.existsSync(p);
const isDir = (p) => exists(p) && fs.statSync(p).isDirectory();
const lsDirs = (p) =>
  isDir(p)
    ? fs
        .readdirSync(p, { withFileTypes: true })
        .filter((e) => e.isDirectory())
        .map((e) => e.name)
        .sort()
    : [];
const lsFiles = (p) =>
  isDir(p)
    ? fs
        .readdirSync(p, { withFileTypes: true })
        .filter((e) => e.isFile())
        .map((e) => e.name)
        .sort()
    : [];

// Document ownership, per _bower/framework.md's Document Authority table.
function ownershipOf(rel) {
  const base = path.basename(rel);
  if (base === 'constitution.md' || base === 'problem-space.md') return 'human-owned';
  if (base === 'index.md') return 'agent-owned (derived)';
  if (base === 'status.md' || base === 'module-status.md') return 'agent-owned';
  if (base === 'adoption-ledger.md' || base === 'review-plan.md' || base === 'findings.md')
    return 'agent-owned (transient)';
  if (base === 'plan.md') return 'co-authored';
  if (['architecture.md', 'ui.md', 'scope.md'].includes(base)) return 'co-authored';
  if (rel.startsWith('docs/adr/')) return 'body immutable once accepted';
  if (rel.startsWith('docs/reference/')) return 'vendored (read-only)';
  return 'unclassified';
}

// A `review-plan.md` finding line, per /b-review's plan shape:
//   `- [ ] F3 — <gist> — <class> — <pointer>`
// The class vocabulary is closed (see b-review.md), which is what makes the rest
// unambiguous: whatever precedes the class is the gist, whatever follows it is
// where the work is. Parsing is best-effort by design — a line that does not fit
// keeps its raw text and is shown as written, because the plan is operator prose
// first and a machine-readable checklist second.
const REVIEW_OWNED = ['inline-reconcile', 'test-backfill', 'status-fix', 'adr-supersede'];
// A routed finding's brief, per /b-review Step 3. All three are required — see
// the check in the module loop for why a partial brief is worse than none.
const BRIEF_FIELDS = ['location', 'drift', 'resolution'];
const isReviewClass = (s) => REVIEW_OWNED.includes(s) || /^route:\/b-[a-z-]+$/.test(s);

function parseFinding(text) {
  const out = {
    text,
    id: null,
    gist: text,
    class: null,
    routed: false,
    brief: null,
    annotations: null,
    pointer: null,
    pointerKind: null,
    pointerFile: null,
    pointerLine: null,
    note: null,
    completion: null,
  };
  const parts = text.split(/\s+[—–]\s+/).map((s) => s.trim());
  let i = 0;
  if (/^F\d+$/i.test(parts[0])) {
    out.id = parts[0].toUpperCase();
    i = 1;
  }
  const ci = parts.findIndex((p, n) => n >= i && isReviewClass(p));
  if (ci === -1) {
    out.gist = parts.slice(i).join(' — ') || text;
    return out;
  }
  out.class = parts[ci];
  out.routed = out.class.startsWith('route:');
  out.gist = parts.slice(i, ci).join(' — ') || text;
  // v0.34: the command that discharges a routed finding ticks it and appends a
  // completion note — `— done YYYY-MM-DD via /b-feature <slug>`. It is
  // provenance for the closeout audit, not part of the pointer, and the pointer
  // is a command meant to be copied and run verbatim: left glued on, the page's
  // copy would be the wrong text. Split it off before the pointer is parsed.
  let rest = parts.slice(ci + 1);
  // The date is required, not decorative: matching a bare `done …` segment would
  // let a pointer that merely starts with the word be eaten silently. A note
  // written without a date stays visibly in the pointer, which is the better
  // failure — wrong and visible beats swallowed.
  const di = rest.findIndex((p) => /^done\s+\d{4}-\d{2}-\d{2}\b/i.test(p));
  if (di !== -1) {
    out.completion = rest.slice(di).join(' — ');
    rest = rest.slice(0, di);
  }
  const tail = rest.join(' — ');
  if (!tail) return out;
  // A won't-fix disposition is recorded where a pointer would otherwise sit.
  if (/^won'?t fix\b/i.test(tail)) {
    out.note = tail;
    return out;
  }
  out.pointer = tail;
  if (/^(Run\s+)?\//.test(tail) && /\/b-/.test(tail)) out.pointerKind = 'command';
  else if (/^[\w./@-]+(:\d+)?$/.test(tail) && /[/.]/.test(tail)) {
    out.pointerKind = 'path';
    const m = /^(.*?)(?::(\d+))?$/.exec(tail);
    out.pointerFile = m[1];
    out.pointerLine = m[2] ? Number(m[2]) : null;
  } else out.pointerKind = 'text';
  return out;
}

// The five central docs, in reading order. Anything else at the root of docs/
// is appended after them, and every subdirectory is scanned — a project may
// grow its own, and an upstream tool should not need a code change to show it.
const CENTRAL_ORDER = ['index.md', 'scope.md', 'architecture.md', 'constitution.md', 'ui.md'];

// Documents Bower itself defines, writes, and reconciles — as against material
// the project keeps under docs/ for its own reasons. The distinction is worth
// surfacing: a reader should not have to guess whether a page is one the
// framework maintains, and no Bower convention applies to the project's own.
// ADRs and module docs are handled on their own paths, not here.
const BOWER_DOCS = new Set([
  'docs/index.md',
  'docs/scope.md',
  'docs/architecture.md',
  'docs/constitution.md',
  'docs/ui.md',
  'docs/design/problem-space.md',
  'docs/adoption-ledger.md',
]);
// Bower artifacts that live under docs/modules/<m>/ and so cannot be named by
// path. module-status.md, review-plan.md and the per-feature files are handled
// on their own walkers; findings.md rides the loose-file sweep, where without
// this it would land under "Project docs" as material the framework does not
// define — which it does.
const BOWER_MODULE_DOCS = new Set(['findings.md']);
const originOf = (rel) =>
  BOWER_DOCS.has(rel) ||
  (/^docs\/modules\/[^/]+\/[^/]+$/.test(rel) && BOWER_MODULE_DOCS.has(path.basename(rel)))
    ? 'bower'
    : 'project';

// ---------------------------------------------------------------- main

function extract(root) {
  const docsDir = path.join(root, 'docs');
  if (!isDir(docsDir)) {
    throw new Error(`No docs/ directory at ${root} — is this a Bower project?`);
  }

  const health = [];
  const flag = (severity, kind, message, rel, extra) =>
    health.push({ severity, kind, message, path: rel, ...(extra || {}) });

  // Obsolescence tripwire. A check that fires on *every* candidate is far more
  // likely to be testing a convention the framework has since dropped than to
  // have found a defect in every single instance — that is exactly how the
  // v0.26 features-roster removal turned this report into 48 false warnings.
  // Each check that scans a population registers its candidates here.
  const population = new Map();
  const candidate = (kind, fired) => {
    const s = population.get(kind) || { fired: 0, candidates: 0 };
    s.candidates++;
    if (fired) s.fired++;
    population.set(kind, s);
  };

  const linkSources = []; // { fromRel, fromLabel, fromRoute, target }
  const docRoutes = new Map(); // repo-rel path -> hash route

  // A table cell holding a paragraph of prose costs far more than it looks.
  // A markdown formatter aligns table columns by padding every cell to the
  // widest, so one oversized cell multiplies across every row: a five-row table
  // whose worst cell holds 15,000 characters becomes ~75kB of spaces. These
  // files sit on the orientation read-path of nearly every command, so every
  // agent pays for it on every session.
  //
  // The cell is the defect and the padding is its symptom, so the cell is what
  // is measured. Ordinary alignment of a Components table costs a few kB and is
  // exactly what a formatter is for — reporting that would be noise.
  const MAX_CELL = 1200;
  const checkTableCells = (rel, body) => {
    // Vendored material is read-only and not the project's to reformat.
    if (rel.startsWith('docs/reference/')) return;
    let worst = 0;
    for (const line of M.withoutFences(body).split('\n')) {
      const t = line.trim();
      if (!t.startsWith('|')) continue;
      for (const cell of t.replace(/^\||\|$/g, '').split('|')) {
        const n = cell.trim().length;
        if (n > worst) worst = n;
      }
    }
    if (worst <= MAX_CELL) return;
    const padding = body.length - body.replace(/ {3,}/g, ' ').length;
    const kb = (n) => `${Math.round(n / 1024)}kB`;
    flag(
      'warn',
      'oversized-table-cell',
      `A table cell holds ${worst.toLocaleString()} characters of prose. ` +
        (padding > 4096
          ? `A formatter has aligned the table to it, so ${kb(padding)} of this ${kb(body.length)} file is now padding — ` +
            `a cost every agent that orients on it pays. `
          : '') +
        `Move the prose into the body of a document and leave the cell a short value.`,
      rel,
      { worstCell: worst, padding, bytes: body.length },
    );
  };

  // ------------------------------------------------------------ framework version

  const versionFile = path.join(root, '_bower/VERSION');
  const projectVersion = exists(versionFile) ? read(versionFile).trim() : null;
  const schema = {
    viewerFor: SCHEMA_VERSION,
    projectVersion,
    match: projectVersion === null ? null : projectVersion === SCHEMA_VERSION,
  };
  // Routed-finding briefs arrived in v0.32; a plan written before that is not
  // drifted for lacking them. Unknown version → assume current, since the
  // scaffold always writes VERSION and its absence is already reported.
  // Segments, not parseFloat — "0.100" would otherwise read as 0.1 and turn
  // the gate off again ninety versions from now.
  const [vMaj, vMin] = (projectVersion || '').split('.').map(Number);
  const briefsExpected = projectVersion === null || vMaj > 0 || (vMaj === 0 && vMin >= 32);
  if (schema.match === false)
    flag(
      'info',
      'schema-version-skew',
      `This viewer parses framework v${SCHEMA_VERSION} document schemas; the project is on v${projectVersion}. ` +
        `Checks below may test conventions the project has not adopted, or miss ones it has.`,
      '_bower/VERSION',
    );

  // ------------------------------------------------------------ central docs

  const centralSpecs = [];
  const rootMd = lsFiles(docsDir);
  for (const f of CENTRAL_ORDER) if (rootMd.includes(f)) centralSpecs.push([f, 'central']);
  for (const f of rootMd) if (!CENTRAL_ORDER.includes(f)) centralSpecs.push([f, 'central']);
  for (const dir of lsDirs(docsDir)) {
    if (dir === 'adr' || dir === 'modules') continue; // both have dedicated structure
    for (const f of lsFiles(path.join(docsDir, dir))) centralSpecs.push([`${dir}/${f}`, dir]);
  }

  const docs = [];
  for (const [relDoc, kind] of centralSpecs) {
    const abs = path.join(docsDir, relDoc);
    if (!exists(abs)) continue;
    const rel = `docs/${relDoc}`;
    const id = relDoc.replace(/\.[^.]+$/, '');
    const ext = path.extname(relDoc).slice(1).toLowerCase();
    const renderable = ext === 'md';
    const body = read(abs);
    const title =
      (renderable && (/^#\s+(.*)$/m.exec(body) || [])[1]) || path.basename(relDoc, path.extname(relDoc));
    const route = `#/doc/${encodeURIComponent(id)}`;
    docRoutes.set(rel, route);
    docs.push({
      id,
      rel,
      kind,
      ext,
      renderable,
      title: title.trim(),
      origin: originOf(rel),
      ownership: ownershipOf(rel),
      bytes: Buffer.byteLength(body),
      headings: renderable ? M.headings(body) : [],
      body,
    });
    if (renderable) {
      checkTableCells(rel, body);
      for (const l of M.links(body))
        linkSources.push({ fromRel: rel, fromLabel: title.trim(), fromRoute: route, target: l.target });
    }
  }
  const docById = (id) => docs.find((d) => d.id === id);

  // ------------------------------------------------------------ ADRs

  const adrs = [];
  const adrDir = path.join(docsDir, 'adr');
  for (const f of lsFiles(adrDir)) {
    if (!/^\d{4}-.*\.md$/.test(f)) continue;
    const rel = `docs/adr/${f}`;
    const raw = read(path.join(adrDir, f));
    const { fm, body } = M.frontmatter(raw);
    const num = f.slice(0, 4);
    const id = fm.id || `ADR-${num}`;
    const route = `#/adr/${num}`;
    docRoutes.set(rel, route);
    const secs = M.sections(body);
    const adr = {
      id,
      num,
      slug: f.replace(/\.md$/, ''),
      rel,
      title: fm.title || (/^#\s+(.*)$/m.exec(body) || [])[1] || id,
      status: fm.status || 'unknown',
      date: fm.date || null,
      scope: fm.scope || null,
      modules: [].concat(fm.modules || []),
      topics: [].concat(fm.topics || []),
      supersedes: [].concat(fm.supersedes || []),
      supersededBy: [].concat(fm['superseded-by'] || []),
      narrows: [].concat(fm.narrows || []),
      narrowedBy: [].concat(fm['narrowed-by'] || []),
      ownership: ownershipOf(rel),
      sections: {
        context: secs['Context'] || '',
        decision: secs['Decision'] || '',
        consequences: secs['Consequences'] || '',
        alternatives: secs['Alternatives considered'] || '',
      },
      body,
    };
    adrs.push(adr);
    checkTableCells(rel, body);
    for (const l of M.links(body))
      linkSources.push({ fromRel: rel, fromLabel: id, fromRoute: route, target: l.target });
  }
  adrs.sort((a, b) => a.num.localeCompare(b.num));
  const adrById = new Map(adrs.map((a) => [a.id, a]));

  // ADR index doc (own route, distinct from the faceted view)
  const adrIndexAbs = path.join(adrDir, 'index.md');
  if (exists(adrIndexAbs)) {
    const rel = 'docs/adr/index.md';
    const body = read(adrIndexAbs);
    const route = '#/doc/adr-index';
    docRoutes.set(rel, route);
    docs.push({
      id: 'adr-index',
      rel,
      kind: 'central',
      ext: 'md',
      renderable: true,
      title: 'ADR Index',
      origin: 'bower',
      ownership: 'agent-owned (derived)',
      bytes: Buffer.byteLength(body),
      headings: M.headings(body),
      body,
    });
  }

  // ------------------------------------------------------------ architecture: the module graph

  const archDoc = docById('architecture');
  const archModules = new Map();
  let buildOrderRationale = '';
  if (archDoc) {
    const secs = M.sections(archDoc.body);
    const swa = secs['Software architecture'] || '';
    buildOrderRationale =
      (/\*\*Build-order rationale\.\*\*\s*([\s\S]*?)(?=\n###\s|\n\*\*|$)/.exec(swa) || [])[1] || '';
    const blocks = swa.split(/^###\s+/m).slice(1);
    let i = 0;
    for (const block of blocks) {
      const nl = block.indexOf('\n');
      const name = (nl === -1 ? block : block.slice(0, nl)).trim().replace(/`/g, '');
      const rest = nl === -1 ? '' : block.slice(nl);
      const field = (label) => {
        const re = new RegExp(`\\*\\*${label}\\.?\\*\\*\\s*([\\s\\S]*?)(?=\\n\\s*\\n\\*\\*|$)`);
        return ((re.exec(rest) || [])[1] || '').trim();
      };
      // v0.26 moved the feature roster out of architecture.md — a module's
      // `## Build order` is the only roster. A surviving list here is an
      // incomplete migration, so it is read as drift, never as the roster.
      const staleRoster = field('Features');
      archModules.set(name, {
        name,
        order: ++i,
        purpose: field('Purpose'),
        dataConcern: field('Data concern'),
        dependsOnRaw: field('Depends on'),
        consumedByRaw: field('Consumed by'),
        staleRoster: staleRoster ? M.backticked(staleRoster) : [],
        anchor: M.slugify(name),
      });
    }
  } else {
    flag('warn', 'missing-doc', 'docs/architecture.md not found — the module graph will be empty', 'docs');
  }

  const moduleNames = new Set([...archModules.keys(), ...lsDirs(path.join(docsDir, 'modules'))]);

  // Resolve dependency edges to known module names only (prose is not guessed at).
  const resolveModuleRefs = (text) => [...new Set(M.backticked(text).filter((n) => moduleNames.has(n)))];

  // docs/index.md's Modules table declares a status per module. It is derived
  // state that /b-index regenerates, so it can fall behind the module docs.
  const declaredStatus = new Map();
  const indexDoc = docById('index');
  if (indexDoc) {
    const t = M.firstTable(M.sections(indexDoc.body)['Modules'] || '');
    if (t) {
      for (const row of t.rows) {
        const nameCell = row.find((c) => /`[a-z0-9-]+`/i.test(c || ''));
        const name = nameCell ? M.backticked(nameCell)[0] : null;
        if (!name) continue;
        // A `Review:` clause is stripped before scanning: the review marker is
        // a separate axis (its own column per /b-index), but an index that
        // wrongly appended it inside the Status cell must not have its ✓ read
        // as the module's declared status — MARKERS checks ✓ first.
        const mk = row.map((c) => M.trailingMarker((c || '').replace(/Review:.*$/i, ''))).find(Boolean);
        if (mk) declaredStatus.set(name, mk);
      }
    }
  }

  // ------------------------------------------------------------ adoption phase

  // Per framework-reference.md "Adoption phase": the 🌱 banner in docs/index.md
  // *is* the phase flag, and the ledger is fetched only because the banner said
  // to. During adoption, observed features are marked 🚧 as-built and carry no
  // status.md by design — so the missing-status check must stand down, or it
  // fires once per feature on every freshly adopted project.
  const ledgerAbs = path.join(docsDir, 'adoption-ledger.md');
  const bannerPresent = !!(indexDoc && /🌱/.test(indexDoc.body));
  let adoption = null;
  if (bannerPresent || exists(ledgerAbs)) {
    const openItems = [];
    if (exists(ledgerAbs)) {
      for (const line of read(ledgerAbs).split('\n')) {
        const m = /^\s*[-*]\s+(.*)$/.exec(line);
        if (!m) continue;
        const [location, ...rest] = m[1].split('·');
        openItems.push({
          location: location.trim().replace(/`/g, ''),
          question: rest.join('·').trim(),
          raw: m[1].trim(),
        });
      }
    }
    adoption = {
      active: bannerPresent,
      hasLedger: exists(ledgerAbs),
      ledgerRel: exists(ledgerAbs) ? 'docs/adoption-ledger.md' : null,
      openItems,
    };
    // "No open questions ⇒ no phase" — an empty ledger already meets the exit
    // condition, so a banner over one is a contradiction the operator can close.
    if (bannerPresent && exists(ledgerAbs) && !openItems.length)
      flag(
        'warn',
        'adoption-exit-due',
        'The adoption ledger is empty but docs/index.md still shows the 🌱 banner — the exit condition is met; delete the banner.',
        'docs/index.md',
      );
    if (bannerPresent && !exists(ledgerAbs))
      flag(
        'warn',
        'adoption-ledger-missing',
        'docs/index.md shows the 🌱 adoption banner but docs/adoption-ledger.md does not exist.',
        'docs/index.md',
      );
  }

  // ------------------------------------------------------------ constitution

  // v0.23: a claim about what *exists* either lives under `## Not yet in force`
  // — where agents must treat it as non-existent — or must be verifiable from
  // the repo. The section is surfaced separately because it is the one part of
  // the doc that must not be read as fact.
  let constitution = null;
  const constDoc = docById('constitution');
  if (constDoc) {
    const nyif = M.sections(constDoc.body)['Not yet in force'] || '';
    constitution = {
      rel: constDoc.rel,
      route: docRoutes.get(constDoc.rel),
      notYetInForce: nyif,
      items: nyif
        .split('\n')
        .map((l) => (/^\s*[-*]\s+(.*)$/.exec(l) || [])[1])
        .filter(Boolean),
    };
  }

  // ------------------------------------------------------------ modules + features

  const modules = [];
  const features = [];
  const reviewPlans = [];
  const fileIndex = new Map(); // repo-rel source path -> [{module, feature, purpose, change}]

  for (const name of [...moduleNames].sort()) {
    const modDir = path.join(docsDir, 'modules', name);
    const arch = archModules.get(name) || null;
    const route = `#/module/${encodeURIComponent(name)}`;

    candidate('arch-module-missing', !arch && isDir(modDir));
    if (!arch && isDir(modDir)) {
      flag(
        'warn',
        'arch-module-missing',
        `docs/modules/${name}/ exists but architecture.md §"Software architecture" has no \`### ${name}\` block`,
        `docs/modules/${name}`,
      );
    }
    if (!isDir(modDir)) {
      flag(
        'warn',
        'module-dir-missing',
        `architecture.md declares module \`${name}\` but docs/modules/${name}/ does not exist`,
        'docs/architecture.md',
      );
    }
    candidate('arch-feature-roster', !!(arch && arch.staleRoster.length));
    if (arch && arch.staleRoster.length)
      flag(
        'warn',
        'arch-feature-roster',
        `architecture.md's \`### ${name}\` entry still lists features (${arch.staleRoster
          .map((f) => `\`${f}\``)
          .join(', ')}). Since v0.26 the module's \`## Build order\` is the only roster.`,
        'docs/architecture.md',
        { module: name },
      );

    // -- module-status.md
    const msRel = `docs/modules/${name}/module-status.md`;
    const msAbs = path.join(modDir, 'module-status.md');
    let integration = null;
    const buildOrder = [];
    let review = null;
    candidate('missing-module-status', !exists(msAbs));
    if (exists(msAbs)) {
      const body = read(msAbs);
      docRoutes.set(msRel, route);
      const secs = M.sections(body);
      const mi = secs['Module integration'] || '';
      const testLine = (/^\s*Test:\s*(.*)$/m.exec(mi) || [])[1] || '';
      integration = {
        marker: M.trailingMarker(testLine),
        test: testLine.replace(/—.*$/, '').replace(/`/g, '').trim(),
        testRaw: testLine.trim(),
        notes: (/^\s*Notes:\s*([\s\S]*)$/m.exec(mi) || [])[1] || '',
        rel: msRel,
      };
      // v0.29 review state. `Review: ⏸ | 🚧 | ✓ YYYY-MM-DD (N of N features)`.
      // Deliberately redundant with review-plan.md's existence so a crashed or
      // hand-edited review is a mechanical finding rather than something only a
      // reading agent would notice — same reasoning as ADR supersession symmetry.
      if ('Module review' in secs) {
        const reviewLine = (/^\s*Review:\s*(.*)$/m.exec(secs['Module review']) || [])[1] || '';
        const snap = /\((\d+)\s+of\s+\d+\s+features?\)/i.exec(reviewLine);
        review = {
          marker: M.trailingMarker(reviewLine),
          date: (/(\d{4}-\d{2}-\d{2})/.exec(reviewLine) || [])[1] || null,
          featureCount: snap ? Number(snap[1]) : null,
          raw: reviewLine.trim(),
          rel: msRel,
        };
      }

      const bo = secs['Build order'] || '';
      for (const line of bo.split('\n')) {
        const m = /^\s*(\d+)\.\s+`?([A-Za-z0-9._-]+)`?\s*(?:—|-)\s*(.*)$/.exec(line);
        if (!m) continue;
        const rest = m[3];
        // v0.22 pull-forward annotation: `⏸ (scope reduced by <feature>: <what
        // landed>. Remaining: <what is left>.)`. The `Remaining:` half is the
        // load-bearing part — it is what stops the next pass rebuilding what
        // already exists — so it is surfaced rather than parsed away.
        const annotation = (/\((scope reduced[\s\S]*)\)\s*$/i.exec(rest) || [])[1] || null;
        buildOrder.push({
          order: Number(m[1]),
          name: m[2],
          marker: M.trailingMarker(rest),
          annotation,
          remaining: annotation ? M.labelled(annotation, 'Remaining') : null,
        });
      }
      // A build order that fails to parse fails silently and cascades: the
      // roster reads as empty, every feature fires feature-not-in-build-order,
      // and the module rollup goes wrong — a wall of plausible findings with
      // one cause. Numbered entries that yield nothing are that cause, and the
      // obsolescence tripwire cannot see it, so it is flagged here directly.
      const numbered = bo.split('\n').filter((l) => /^\s*\d+\.\s/.test(l));
      if (numbered.length && !buildOrder.length)
        flag(
          'warn',
          'build-order-unparsed',
          `${name}'s \`## Build order\` has ${numbered.length} numbered ${numbered.length === 1 ? 'entry' : 'entries'} but none parse ` +
            `as \`N. \`feature\` — description\` (first: "${numbered[0].trim().slice(0, 80)}"). ` +
            `The roster reads as empty, so every finding below about this module's features shares this one cause.`,
          msRel,
          { module: name },
        );
      checkTableCells(msRel, body);
      for (const l of M.links(body))
        linkSources.push({
          fromRel: msRel,
          fromLabel: `${name} (module status)`,
          fromRoute: route,
          target: l.target,
        });
    } else {
      flag('warn', 'missing-module-status', `No module-status.md for module \`${name}\``, `docs/modules/${name}`);
    }

    // -- transient review plan (/b-review's recovery anchor)
    const rpAbs = path.join(modDir, 'review-plan.md');
    const planPresent = exists(rpAbs);
    if (planPresent) {
      const rpRel = `docs/modules/${name}/review-plan.md`;
      const body = read(rpAbs);
      // The plan gets its own page rather than resolving to the module: it is
      // the substance of an open review, and a link that lands on a lifecycle
      // badge instead of the findings answers a different question.
      const rpRoute = `#/review/${encodeURIComponent(name)}`;
      docRoutes.set(rpRel, rpRoute);
      const rpSecs = M.sections(body);
      // `[x]` resolved and `[~]` won't-fix both count as disposed of; only `[ ]`
      // holds the review open. Won't-fix is an operator decision recorded in the
      // plan and deliberately left no other trace.
      // Checkbox lines are the findings; indented label sub-bullets beneath one
      // are its brief (v0.32) and are attached to it rather than counted. Only
      // checkboxes dispose of anything, so a brief line that looked like an item
      // would inflate both the total and the "still open" count.
      const items = [];
      for (const line of (rpSecs['Findings'] || body).split('\n')) {
        const box = /^\s*[-*]\s+\[( |x|X|~)\]\s+(.*)$/.exec(line);
        if (box) {
          items.push({
            done: box[1] !== ' ',
            wontFix: box[1] === '~',
            ...parseFinding(box[2].trim()),
          });
          continue;
        }
        const sub = /^\s+[-*]\s+(Location|Drift|Resolution):\s*(.*)$/.exec(line);
        if (sub && items.length) {
          const it = items[items.length - 1];
          (it.brief || (it.brief = {}))[sub[1].toLowerCase()] = sub[2].trim();
          continue;
        }
        // Any other indented content under an item is operator prose — a
        // re-opened note, a caveat — and this page is the plan's only rendering
        // (links to it resolve here, not to a raw file view), so dropping it
        // would make the page a lossier read than the file. Kept verbatim and
        // shown under the finding. Indentation-gated so a malformed plan with
        // no ## Findings heading doesn't swallow its other sections into the
        // last item.
        if (/^\s+\S/.test(line) && items.length) {
          const it = items[items.length - 1];
          (it.annotations || (it.annotations = [])).push(line.trim().replace(/^[-*]\s+/, ''));
        }
      }
      // A label with nothing after it is not a field. Collapsing an all-empty
      // brief back to null keeps `brief` meaning "there is something here",
      // which is what the renderer and the check below both assume.
      for (const it of items)
        if (it.brief && !BRIEF_FIELDS.some((k) => it.brief[k])) it.brief = null;
      // A routed finding is deferred into a fresh session, so its Location/Drift/
      // Resolution brief is the whole handoff — without it the receiving command
      // re-derives the finding from code and may fail to reproduce it at all.
      // Version-gated rather than tripwire-guarded: on a pre-v0.32 project every
      // routed item is briefless by construction, which is history, not drift.
      // Exempt from the obsolescence tripwire, on the same grounds as
      // review-section-missing: a project that upgrades mid-review has a plan
      // where *every* routed finding is briefless, and universality there is the
      // signal rather than evidence this check has decayed.
      //
      // All three fields are required, not just the presence of a brief. They do
      // different jobs and none substitutes for another: `Location:` says where
      // to look, `Drift:` says what disagrees with what, `Resolution:` says what
      // to do about it. A location-only brief points a fresh session at a file
      // and leaves it to infer why — which is the re-derivation this exists to
      // prevent, only now wearing the appearance of a complete handoff.
      if (briefsExpected)
        for (const it of items) {
          if (!it.routed || it.done) continue;
          const absent = BRIEF_FIELDS.filter((k) => !(it.brief && it.brief[k]));
          if (!absent.length) continue;
          const which = it.brief
            ? `is missing ${absent.map((k) => `\`${k}\``).join(' and ')} from its brief`
            : 'carries no Location/Drift/Resolution brief';
          // Deliberately not "run /b-review to fix it": resuming a review does not
          // re-diagnose, so it cannot produce a brief, and hand-writing one is
          // the re-derivation the brief exists to prevent. The honest options are
          // to live with it or to discard the plan and diagnose afresh.
          flag(
            'info',
            'review-routed-no-brief',
            `${name}'s review finding ${it.id || 'in review-plan.md'} is routed to ${it.class.replace('route:', '')} ` +
              `but ${which}, so the command that discharges it has to re-derive that much from code. ` +
              `Resuming /b-review will not fill it in — a resume does not re-diagnose. Either accept it, ` +
              `or delete the plan, set Review: ⏸ and run /b-review ${name} for a fresh diagnosis.`,
            rpRel,
          );
        }
      // The preamble carries the diagnosis date and the roster count the closeout
      // will write into `Review: ✓` — both are the review's provenance, so they
      // belong on the page rather than only in the file.
      const preamble = body.replace(/^#[^\n]*\n/, '').split(/^##\s/m)[0];
      const obsKey = Object.keys(rpSecs).find((k) => /^Observations/.test(k));
      const observations = (obsKey ? rpSecs[obsKey] : '')
        .split('\n')
        .map((l) => (/^\s*[-*]\s+(.*)$/.exec(l) || [])[1])
        .filter((t) => t && !/^none\.?$/i.test(t.trim()))
        .map((t) => t.trim());
      // Sections beyond the two the schema names (a real review has written a
      // `## Constitution` consent record, for instance) are carried through and
      // rendered as-is. Same fidelity rule as the annotations above: the page
      // shows everything the file holds, or it is the poorer way to read it.
      const sections = Object.keys(rpSecs)
        .filter((k) => k !== 'Findings' && k !== obsKey)
        .map((k) => ({
          title: k,
          lines: rpSecs[k]
            .split('\n')
            .map((l) => l.trim().replace(/^[-*]\s+/, ''))
            .filter(Boolean),
        }))
        .filter((s) => s.lines.length);
      reviewPlans.push({
        module: name,
        rel: rpRel,
        route: rpRoute,
        moduleRoute: route,
        diagnosed: (/(\d{4}-\d{2}-\d{2})/.exec(preamble) || [])[1] || null,
        featureCount: Number((/against\s+(\d+)\s+features?/i.exec(preamble) || [])[1]) || null,
        observations,
        sections,
        items,
        open: items.filter((i) => !i.done).length,
        wontFix: items.filter((i) => i.wontFix).length,
        total: items.length,
      });
    }

    // -- findings queue (v0.34). Nothing pairs with it and it holds nothing
    // open, so there is exactly one mechanical fact worth reporting: an empty
    // one left on disk. Whoever disposes of the last item deletes the file, so
    // a queue with no open items is the residue of a half-finished drain — the
    // same shape of fact as a plan without its marker, and reported by /b-recap
    // on the same grounds.
    const fqAbs = path.join(modDir, 'findings.md');
    if (exists(fqAbs)) {
      const fqOpen = read(fqAbs)
        .split('\n')
        .filter((l) => /^\s*[-*]\s+\[ \]\s+/.test(l)).length;
      candidate('findings-queue-empty', fqOpen === 0);
      if (fqOpen === 0)
        flag(
          'warn',
          'findings-queue-empty',
          `${name}'s findings.md has no open items, so the queue is drained but the file was left behind — ` +
            `whoever disposed of the last item should have deleted it. Delete docs/modules/${name}/findings.md.`,
          `docs/modules/${name}/findings.md`,
          { module: name },
        );
    }

    // -- loose files at the module root. module-status.md and review-plan.md
    // have dedicated routes above; everything else here — findings.md, and
    // whatever a later version or a project itself invents — is registered as a
    // routed page, mirroring the central-docs sweep. The alternative was the
    // closed whitelist this replaces, under which a file present on disk and
    // correctly linked still rendered as a dead link, with the drift report
    // silently agreeing it was fine because it tests existence, not routability.
    for (const f of lsFiles(modDir)) {
      if (f === 'module-status.md' || f === 'review-plan.md') continue;
      const rel = `docs/modules/${name}/${f}`;
      const id = `modules/${name}/${f.replace(/\.[^.]+$/, '')}`;
      const ext = path.extname(f).slice(1).toLowerCase();
      const renderable = ext === 'md';
      const body = read(path.join(modDir, f));
      const title =
        (renderable && (/^#\s+(.*)$/m.exec(body) || [])[1]) || path.basename(f, path.extname(f));
      const docRoute = `#/doc/${encodeURIComponent(id)}`;
      docRoutes.set(rel, docRoute);
      docs.push({
        id,
        rel,
        kind: `modules/${name}`,
        ext,
        renderable,
        title: title.trim(),
        origin: originOf(rel),
        ownership: ownershipOf(rel),
        bytes: Buffer.byteLength(body),
        headings: renderable ? M.headings(body) : [],
        body,
      });
      if (renderable) {
        checkTableCells(rel, body);
        for (const l of M.links(body))
          linkSources.push({
            fromRel: rel,
            fromLabel: title.trim(),
            fromRoute: docRoute,
            target: l.target,
          });
      }
    }

    // -- v0.29 review state vs plan. The marker and the plan are written
    // together by /b-review, so a disagreement is mechanically detectable and
    // means a run died mid-flight or something was hand-edited.
    if (exists(msAbs)) {
      // Deliberately NOT registered with the obsolescence tripwire. Firing on
      // every module is this check's expected state on any project that has not
      // yet run the v0.29 migration — it is a version-boundary notice, not a
      // convention test, so universality here is the signal rather than decay.
      if (!review)
        flag(
          'info',
          'review-section-missing',
          `${name}'s module-status.md has no \`## Module review\` section, so its review state is unrecorded ` +
            `(a project predating v0.29 — the v0.29 migration adds it with \`Review: ⏸\`).`,
          msRel,
          { module: name },
        );

      candidate('review-open-no-plan', !!review && review.marker === '🚧' && !planPresent);
      if (review && review.marker === '🚧' && !planPresent)
        flag(
          'warn',
          'review-open-no-plan',
          `${name} is marked \`Review: 🚧\` but docs/modules/${name}/review-plan.md does not exist — ` +
            `a review was opened and its plan is gone, so the findings are lost. Run /b-review ${name} to resolve.`,
          msRel,
          { module: name },
        );

      const notOpen = planPresent && (!review || review.marker !== '🚧');
      candidate('review-plan-not-open', notOpen);
      if (notOpen)
        flag(
          'warn',
          'review-plan-not-open',
          `${name} has an open review-plan.md but \`Review:\` is ${review && review.marker ? review.marker : 'unset'}, not 🚧 — ` +
            `the marker was never set, or the review was closed without deleting the plan.`,
          msRel,
          { module: name },
        );

      // Staleness is derived, never stored: the snapshot count against the
      // roster now. Catches features *added* since the review, not features
      // modified in place — see framework-reference.md "Staleness is derived".
      const stale = !!review && review.marker === '✓' && review.featureCount !== null && buildOrder.length > review.featureCount;
      candidate('review-stale', stale);
      if (stale)
        flag(
          'info',
          'review-stale',
          `${name} was reviewed${review.date ? ` on ${review.date}` : ''} against ${review.featureCount} ` +
            `${review.featureCount === 1 ? 'feature' : 'features'}, but its build order now lists ${buildOrder.length} — ` +
            `${buildOrder.length - review.featureCount} added since, so the review does not cover them.`,
          msRel,
          { module: name },
        );
    }

    const featureDirs = lsDirs(modDir);
    const boByName = new Map(buildOrder.map((b) => [b.name, b]));
    const modFeatures = [];

    // A build-order entry with no docs directory is normal while ⏸ — the plan is
    // written at plan time. Once the entry is anything else, the docs must exist.
    for (const b of buildOrder) {
      const orphan = !featureDirs.includes(b.name) && !!b.marker && b.marker !== '⏸';
      candidate('build-order-orphan', orphan);
      if (orphan)
        flag(
          'warn',
          'build-order-orphan',
          `${name}'s build order marks \`${b.name}\` ${b.marker}, but docs/modules/${name}/${b.name}/ does not exist`,
          msRel,
          { module: name, feature: b.name },
        );
    }

    for (const fname of featureDirs) {
      const fRoute = `#/module/${encodeURIComponent(name)}/${encodeURIComponent(fname)}`;
      const planRel = `docs/modules/${name}/${fname}/plan.md`;
      const statusRel = `docs/modules/${name}/${fname}/status.md`;
      const planAbs = path.join(modDir, fname, 'plan.md');
      const statusAbs = path.join(modDir, fname, 'status.md');
      const bo = boByName.get(fname) || null;

      const feat = {
        module: name,
        name: fname,
        route: fRoute,
        order: bo ? bo.order : null,
        marker: bo ? bo.marker : null,
        annotation: bo ? bo.annotation : null,
        remaining: bo ? bo.remaining : null,
        inBuildOrder: !!bo,
        plan: null,
        status: null,
        components: [],
        adrs: [],
        integrationPoints: '',
        pendingVerification: null,
      };

      candidate('missing-plan', !exists(planAbs));
      if (exists(planAbs)) {
        const body = read(planAbs);
        docRoutes.set(planRel, fRoute);
        const secs = M.sections(body);
        feat.plan = {
          rel: planRel,
          ownership: ownershipOf(planRel),
          title: ((/^#\s+(.*)$/m.exec(body) || [])[1] || fname).trim(),
          preamble: M.firstParagraph(body.replace(/^#.*$/m, '')),
          purpose: M.firstParagraph(secs['Purpose'] || ''),
          headings: M.headings(body),
          sectionNames: secs._order || [],
          hasTrajectory: !!secs['Implementation trajectory'],
          body,
        };
        feat.integrationPoints = secs['Integration points'] || '';

        // Components table → the file index. This is the inverse lookup the
        // docs cannot answer today (they only go feature → file).
        const table = M.firstTable(secs['Components'] || '');
        candidate('no-components-table', !table);
        if (table) {
          for (const row of table.rows) {
            let cell = row[0] || '';
            // A cell may be a bare path, a backticked path, or a markdown link.
            const linked = /\[([^\]]*)\]\(([^)]*)\)/.exec(cell);
            if (linked) cell = linked[1];
            const file = cell.replace(/`/g, '').trim();
            if (!file || file.startsWith('|')) continue;
            const purpose = (row[1] || '').trim();
            const change = (/_\((new|modify|delete|remove)[^)]*\)_/i.exec(purpose) || [])[1] || null;
            // Only treat it as a path if it looks like one. Brace/glob patterns
            // (`deploy/env/{dev,staging}.tpl`) name a set, not a file.
            const isPattern = /[*?{}]/.test(file);
            const looksLikePath = file.includes('/') && !/\s/.test(file);
            const entry = { file, purpose, change, isPath: looksLikePath, isPattern, exists: null };
            if (looksLikePath && !isPattern) {
              entry.exists = exists(path.join(root, file));
              // Only a built feature's missing file is drift; a planned one's
              // components legitimately don't exist yet.
              const built = bo && bo.marker && bo.marker !== '⏸';
              if (!entry.exists && built && !/^remove|^delete/i.test(change || '')) {
                flag(
                  'warn',
                  'component-missing',
                  `${name}/${fname} plan lists \`${file}\`, which is not on disk`,
                  planRel,
                  { feature: fname, module: name, file },
                );
              }
              const list = fileIndex.get(file) || [];
              list.push({ module: name, feature: fname, purpose, change, route: fRoute });
              fileIndex.set(file, list);
            }
            feat.components.push(entry);
          }
        } else {
          flag('info', 'no-components-table', `${name}/${fname} plan has no parseable Components table`, planRel);
        }

        feat.adrs = M.adrRefs(body).filter((id) => adrById.has(id));
        checkTableCells(planRel, body);
        for (const l of M.links(body))
          linkSources.push({
            fromRel: planRel,
            fromLabel: `${name}/${fname} (plan)`,
            fromRoute: fRoute,
            target: l.target,
          });
      } else {
        flag('warn', 'missing-plan', `No plan.md for ${name}/${fname}`, `docs/modules/${name}/${fname}`);
      }

      // Adoption marks observed features 🚧 as-built and writes no status.md by
      // design, so a missing one is expected rather than drift while the phase
      // is open.
      const statusExpected = !(adoption && adoption.active);
      candidate('missing-status', statusExpected && !exists(statusAbs));
      if (exists(statusAbs)) {
        const body = read(statusAbs);
        docRoutes.set(statusRel, fRoute);
        const secs = M.sections(body);
        const marker = M.leadingMarker(body);
        // Two spellings in the wild: a `## Next move` section (canonical, and
        // what the terminal-form template writes) and an inline `Next move:` /
        // `**Next move:**` line in the body — the form every command's printed
        // handoff uses, so it is what a hand-written status.md tends to copy.
        // Reading only the section made the whole class invisible: a real
        // project had 20 stale forward-pointers none of which parsed.
        const nmBlock = secs['Next move'] || '';
        const nmLine = M.firstParagraph(nmBlock) || M.labelled(body, 'Next move', { anchored: true }) || '';
        // "Closed" is written `(none — <reason>)`, but projects reach it wrapped
        // in emphasis, backticks or bold, and a next move misread as live is
        // reported as drift — so strip decoration before asking.
        const isNone = /^\(?\s*none\b/i.test(nmLine.replace(/^[`*_\s]+/, ''));
        // framework-reference.md, "status.md — Resumption Framing": a
        // `Pending verification:` line lists acceptance criteria the operator
        // deferred. Specified as a line; projects also grow it as a section.
        const pv = M.labelled(body, 'Pending verification') || M.firstParagraph(secs['Pending verification'] || '');
        feat.pendingVerification = pv && !/^\s*(none|n\/a|—|-)\s*$/i.test(pv) ? pv : null;
        feat.status = {
          rel: statusRel,
          ownership: ownershipOf(statusRel),
          marker,
          headline: M.firstParagraph(body.replace(/^#.*$/m, '')),
          state: M.firstParagraph(secs['State'] || secs['Current state'] || ''),
          verification: (secs['Verification'] || '').trim(),
          nextMove: nmLine && !isNone ? nmLine : null,
          nextMoveNote: isNone ? nmLine : null,
          hasNextMoveSection: !!nmBlock,
          body,
        };
        candidate('status-no-marker', !marker);
        if (!marker) {
          flag(
            'info',
            'status-no-marker',
            `${name}/${fname} status.md opens without a status marker, so there is nothing to cross-check its build-order marker against`,
            statusRel,
          );
        } else if (bo && bo.marker && bo.marker !== marker) {
          flag(
            'error',
            'marker-disagreement',
            `${name}: build order says ${bo.marker} for \`${fname}\`, its status.md says ${marker}`,
            statusRel,
            { feature: fname, module: name },
          );
        }
        feat.adrs = [...new Set([...(feat.adrs || []), ...M.adrRefs(body).filter((id) => adrById.has(id))])];
        checkTableCells(statusRel, body);
        for (const l of M.links(body))
          linkSources.push({
            fromRel: statusRel,
            fromLabel: `${name}/${fname} (status)`,
            fromRoute: fRoute,
            target: l.target,
          });
      } else if (statusExpected) {
        flag('warn', 'missing-status', `No status.md for ${name}/${fname}`, `docs/modules/${name}/${fname}`);
      }

      if (!bo && exists(planAbs)) {
        flag(
          'warn',
          'feature-not-in-build-order',
          `${name}/${fname} has docs but does not appear in ${name}'s build order`,
          msRel,
        );
      }

      // Effective marker: build order is authoritative, status.md is the fallback.
      feat.effectiveMarker = feat.marker || (feat.status && feat.status.marker) || null;

      // "A feature with pending verification is marked 🚧 in module-status.md,
      // not ✓" — framework-reference.md, "status.md — Resumption Framing".
      // v0.30 terminal form: a ✓ feature's status.md compresses to marker +
      // `## Verification` + `Next move: (none — complete)`. A live next move on
      // a finished feature is the accrual this version removed — most often a
      // forward pointer at the *next* feature, written when this one completed
      // and never revisited, since no command rewrites another feature's file.
      // Judged against the status file's *own* marker, falling back to the
      // effective one: the question is whether this file matches the form its
      // own claim implies. A file that says 🚧 while the build order says ✓ is
      // internally consistent and already reported as `marker-disagreement` —
      // firing here too would double-report one lie, which is how a drift page
      // turns into noise.
      const fwd = feat.status && feat.status.nextMove;
      const selfMarker = (feat.status && feat.status.marker) || feat.effectiveMarker;
      candidate('next-move-on-complete', !!fwd && selfMarker === '✓');
      if (fwd && selfMarker === '✓')
        flag(
          'warn',
          'next-move-on-complete',
          `${name}/${fname} is ✓ but its status.md still carries a next move ("${fwd.slice(0, 90)}"). ` +
            `Since v0.30 a finished feature's status.md compresses to its terminal form — marker, ` +
            `\`## Verification\`, \`Next move: (none — complete)\`; a stored next move may only name work on its own feature.`,
          feat.status.rel,
          { feature: fname, module: name },
        );

      if (feat.pendingVerification && feat.effectiveMarker === '✓')
        flag(
          'error',
          'pending-verification-complete',
          `${name}/${fname} is marked ✓ but its status.md still lists pending verification: ${feat.pendingVerification}`,
          feat.status.rel,
          { feature: fname, module: name },
        );

      features.push(feat);
      modFeatures.push(feat);
    }

    // Module rollup: the worst marker across features + integration. ⏸ means
    // *not started* rather than a severity, so a module that is part built and
    // part planned rolls up to 🚧 — which is what framework-reference.md's own
    // worked example describes ("A module with all features ✓ but `## Module
    // integration` still ⏸ surfaces as 🚧"). Only an untouched module is ⏸.
    const markers = modFeatures
      .map((f) => f.effectiveMarker)
      .concat(integration ? [integration.marker] : [])
      .filter(Boolean);
    let rollup = null;
    if (markers.length) {
      const has = (mk) => markers.includes(mk);
      const allPlanned = markers.every((mk) => mk === '⏸');
      if (has('🔴')) rollup = '🔴';
      else if (has('🔧')) rollup = '🔧';
      else if (has('🟡')) rollup = '🟡';
      else if (has('🚧')) rollup = '🚧';
      else if (allPlanned) rollup = '⏸';
      else if (has('⏸')) rollup = '🚧';
      else rollup = '✓';
    }

    const declared = declaredStatus.get(name) || null;
    candidate('module-status-divergence', !!(declared && rollup && declared !== rollup));
    if (declared && rollup && declared !== rollup)
      flag(
        'warn',
        'module-status-divergence',
        `docs/index.md declares \`${name}\` ${declared}; its feature and integration markers roll up to ${rollup}`,
        'docs/index.md',
        { module: name },
      );

    modules.push({
      name,
      route,
      declaredStatus: declared,
      order: arch ? arch.order : 999,
      purpose: arch ? arch.purpose : '',
      dataConcern: arch ? arch.dataConcern : '',
      dependsOn: arch ? resolveModuleRefs(arch.dependsOnRaw) : [],
      dependsOnRaw: arch ? arch.dependsOnRaw : '',
      consumedBy: arch ? resolveModuleRefs(arch.consumedByRaw) : [],
      consumedByRaw: arch ? arch.consumedByRaw : '',
      archAnchor: arch ? arch.anchor : null,
      hasArch: !!arch,
      integration,
      review,
      buildOrder,
      featureNames: modFeatures.map((f) => f.name),
      status: rollup,
      complete: rollup === '✓',
      adrs: adrs.filter((a) => a.modules.includes(name)).map((a) => a.id),
      rel: exists(msAbs) ? msRel : null,
    });
  }
  modules.sort((a, b) => a.order - b.order || a.name.localeCompare(b.name));
  const moduleByName = new Map(modules.map((m) => [m.name, m]));

  // ------------------------------------------------------------ scope: derived criteria

  // v0.24: criteria carry no status field of any kind. Satisfaction is derived
  // — a criterion holds when every module in its `Delivered by:` clause is
  // complete (all features ✓ *and* the `## Module integration` marker ✓).
  // Nothing writes it down; /b-recap computes it on demand, and so does this.
  let scope = null;
  const scopeDoc = docById('scope');
  if (scopeDoc) {
    const block = M.sections(scopeDoc.body)['Success criteria'] || '';
    const criteria = M.criteria(block).map((c) => {
      const owners = c.deliveredBy.map((n) => ({ name: n, module: moduleByName.get(n) || null }));
      const unknown = owners.filter((o) => !o.module).map((o) => o.name);
      let satisfied = null;
      const blocking = [];
      if (owners.length && !unknown.length) {
        satisfied = true;
        for (const o of owners)
          if (!o.module.complete) {
            satisfied = false;
            blocking.push({ module: o.name, status: o.module.status, route: o.module.route });
          }
      }
      return {
        text: c.text.replace(/\s*[*_]*Delivered by[\s\S]*$/i, '').trim(),
        deliveredBy: c.deliveredBy,
        unknownModules: unknown,
        satisfied,
        blocking,
        carriesMarker: c.marker || null,
      };
    });

    for (const c of criteria) {
      // A criterion with no clause is underivable — report it; never infer a
      // module from the wording.
      candidate('criterion-no-owner', !c.deliveredBy.length);
      if (!c.deliveredBy.length)
        flag(
          'warn',
          'criterion-no-owner',
          `Success criterion has no \`Delivered by:\` clause, so its satisfaction cannot be derived: "${c.text.slice(0, 90)}${c.text.length > 90 ? '…' : ''}"`,
          scopeDoc.rel,
        );
      for (const u of c.unknownModules)
        flag(
          'error',
          'criterion-stale-pointer',
          `Success criterion is delivered by \`${u}\`, which is not a module in this project`,
          scopeDoc.rel,
        );
      if (c.carriesMarker)
        flag(
          'warn',
          'criterion-carries-status',
          `Success criterion carries a ${c.carriesMarker} status marker. Since v0.24 criteria hold no achievement state — it is derived from module completion.`,
          scopeDoc.rel,
        );
    }

    const derivable = criteria.filter((c) => c.satisfied !== null);
    scope = {
      rel: scopeDoc.rel,
      route: docRoutes.get(scopeDoc.rel),
      criteria,
      satisfied: derivable.filter((c) => c.satisfied).length,
      derivable: derivable.length,
      total: criteria.length,
    };
  }

  // ------------------------------------------------------------ ADR consistency

  for (const a of adrs) {
    for (const m of a.modules)
      if (!moduleNames.has(m))
        flag('error', 'adr-unknown-module', `${a.id} names module \`${m}\`, which does not exist`, a.rel);
    if (a.status === 'accepted' && a.supersededBy.length)
      flag(
        'error',
        'adr-status-conflict',
        `${a.id} is \`accepted\` but declares superseded-by ${a.supersededBy.join(', ')}`,
        a.rel,
      );
    if (a.status === 'superseded' && !a.supersededBy.length)
      flag('warn', 'adr-no-successor', `${a.id} is \`superseded\` but names no superseded-by`, a.rel);
    for (const t of a.supersedes) {
      const target = adrById.get(t);
      if (!target) flag('error', 'adr-dangling', `${a.id} supersedes unknown ${t}`, a.rel);
      else if (!target.supersededBy.includes(a.id))
        flag(
          'error',
          'adr-asymmetric',
          `${a.id} supersedes ${t}, but ${t} does not name ${a.id} in superseded-by`,
          target.rel,
        );
    }

    // v0.27 narrowing. Both sides are written in one commit by whichever command
    // created the new ADR, so a one-sided pair is an error rather than a partial
    // state. And `narrows` never changes the target's status — that is the whole
    // point of the field, so a narrowed ADR marked superseded is the exact
    // defect the field exists to prevent: live policy marked dead.
    for (const t of a.narrows) {
      const target = adrById.get(t);
      if (!target) {
        flag('error', 'adr-narrow-dangling', `${a.id} narrows unknown ${t}`, a.rel);
        continue;
      }
      if (!target.narrowedBy.includes(a.id))
        flag(
          'error',
          'adr-narrow-asymmetric',
          `${a.id} narrows ${t}, but ${t} does not name ${a.id} in narrowed-by`,
          target.rel,
        );
      if (a.supersedes.includes(t))
        flag(
          'error',
          'adr-narrow-and-supersede',
          `${a.id} claims both \`narrows\` and \`supersedes\` on ${t} — a decision is either scoped by an exception or replaced, not both`,
          a.rel,
        );
      if (target.status !== 'accepted')
        flag(
          'error',
          'narrowed-adr-not-accepted',
          `${a.id} narrows ${t}, but ${t} carries \`status: ${target.status}\` — narrowing leaves its target accepted, because the target's central commitment is still in force`,
          target.rel,
        );
    }
    for (const t of a.narrowedBy) {
      const source = adrById.get(t);
      if (!source) flag('error', 'adr-narrow-dangling', `${a.id} declares narrowed-by unknown ${t}`, a.rel);
      else if (!source.narrows.includes(a.id))
        flag(
          'error',
          'adr-narrow-asymmetric',
          `${a.id} declares narrowed-by ${t}, but ${t} does not name ${a.id} in narrows`,
          source.rel,
        );
    }

    candidate('adr-unclassified', a.status === 'accepted' && !a.scope);
    if (a.status === 'accepted' && !a.scope)
      flag(
        'info',
        'adr-unclassified',
        `${a.id} is accepted with no \`scope\` — treated as unclassified (pre-v0.20)`,
        a.rel,
      );
  }

  // ------------------------------------------------------------ backlinks

  const backlinks = new Map();
  for (const src of linkSources) {
    if (/^[a-z][a-z0-9+.-]*:/i.test(src.target)) continue; // external
    const fromDir = path.dirname(src.fromRel);
    const clean = src.target.split('#')[0];
    if (!clean) continue;
    // Doc links are repo-root-based (`/docs/adr/0008-…md`); a leading `/` resolves
    // from the repo root, not the linking file's directory. Relative targets are
    // still resolved for older docs and for links into vendored material.
    const rooted = clean.startsWith('/');
    const resolved = rooted
      ? path.posix.normalize(clean.slice(1))
      : path.posix.normalize(path.posix.join(fromDir, clean));
    if (resolved === src.fromRel) continue;
    const list = backlinks.get(resolved) || [];
    if (!list.some((e) => e.fromRel === src.fromRel))
      list.push({ fromRel: src.fromRel, label: src.fromLabel, route: src.fromRoute });
    backlinks.set(resolved, list);
    if (clean.endsWith('.md')) {
      const broken = !exists(path.join(root, resolved));
      candidate('broken-link', broken);
      if (broken) {
        flag('warn', 'broken-link', `Link to \`${clean}\` does not resolve (from ${src.fromRel})`, src.fromRel);
      } else {
        // v0.26: doc links are repo-root-based. A relative target resolves today
        // and breaks the moment either file moves.
        candidate('relative-doc-link', !rooted);
        if (!rooted)
          flag(
            'info',
            'relative-doc-link',
            `Link to \`${clean}\` is relative; since v0.26 doc links are repo-root-based (\`/${resolved}\`)`,
            src.fromRel,
          );
      }
    }
  }

  // ------------------------------------------------------------ git recency

  let recent = [];
  let gitAvailable = false;
  try {
    const SEP1 = '\u0001'; // escaped: a literal control byte here is too easy to lose in an edit
    const SEP2 = '\u0002';
    const out = execFileSync(
      'git',
      ['log', '-n', '400', '--date=short', '--format=%x01%ad%x02%s', '--name-only', '--', 'docs'],
      { cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] },
    );
    gitAvailable = true;
    const seen = new Map();
    let date = null;
    let subject = null;
    for (const line of out.split('\n')) {
      if (line.startsWith(SEP1)) {
        const parts = line.slice(SEP1.length).split(SEP2);
        date = parts[0] || null;
        subject = parts[1] || '';
        continue;
      }
      const p = line.trim();
      if (!p || !p.startsWith('docs/')) continue;
      if (!seen.has(p)) seen.set(p, { rel: p, date, subject });
    }
    recent = [...seen.values()].sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
  } catch {
    /* not a git repo, or git missing — recency is optional */
  }

  // ------------------------------------------------------------ project identity

  let projectName = path.basename(root);
  let tagline = '';
  if (indexDoc) {
    projectName = (indexDoc.title || projectName).replace(/\s*—.*$/, '').trim() || projectName;
    const t = M.firstTable(M.sections(indexDoc.body)['Status overview'] || '');
    if (t) {
      const row = t.rows.find((r) => /project/i.test(r[0] || ''));
      // Clamped: this becomes a one-line page subtitle, and a table cell holding
      // a paragraph would otherwise render as a wall of text under the title.
      // The oversized-table-cell check reports the underlying problem.
      if (row) {
        const full = (row[1] || '').trim();
        tagline = full.length > 200 ? `${full.slice(0, 197).replace(/\s+\S*$/, '')}…` : full;
      }
    }
  }

  // ------------------------------------------------------------ obsolescence tripwire

  for (const [kind, s] of population) {
    if (s.candidates < 3 || s.fired !== s.candidates) continue;
    flag(
      'info',
      'check-may-be-obsolete',
      `\`${kind}\` fired on all ${s.candidates} candidates. A check that matches everything is more often testing a ` +
        `convention the framework has dropped than finding ${s.candidates} real defects — verify it against ` +
        `framework v${projectVersion || 'unknown'} before acting on its findings.`,
      '_bower/viewer/lib/extract.cjs',
      { check: kind }, // not `kind` — that key is the finding's own kind
    );
  }

  // ------------------------------------------------------------ counts

  const tally = (arr) => {
    const t = {};
    for (const mk of arr) {
      const k = mk || 'unmarked';
      t[k] = (t[k] || 0) + 1;
    }
    return t;
  };

  // v0.30: a stored next move is *feature-scoped* — work on that feature, or
  // `(none — complete)`. So only an unfinished feature can have one outstanding,
  // and a ✓ feature's line is stale by construction rather than a work item
  // (flagged as `next-move-on-complete` above). Aggregating ✓ rows here is what
  // let a finished module's features keep calling for work that landed weeks
  // ago — the panel is labelled "outstanding", and for ✓ that was simply false.
  const nextMoves = features
    .filter((f) => f.status && f.status.nextMove && f.effectiveMarker !== '✓')
    .map((f) => ({
      module: f.module,
      feature: f.name,
      route: f.route,
      text: f.status.nextMove,
      command: (/`([^`]*\/b-[^`]*)`/.exec(f.status.nextMove) || [])[1] || null,
      marker: f.effectiveMarker,
    }));

  // The *project-scoped* next move, derived from markers rather than read out of
  // any file: no document owns "what should I do next overall", because every
  // landing changes it and nothing rewrites the per-feature files that used to
  // carry it. Same reasoning as index status prose being derived (v0.28).
  // Advisory and human-facing — /b-recap remains the authority an operator asks.
  // Build work only. Review is deliberately absent: `Review: ⏸` is *not*
  // outstanding work (framework-reference.md, "The review state is orthogonal
  // to completion"), so listing it here would quietly make an optional command
  // look owed — on a project with six finished modules it was six rows of nag.
  // An open review (`🚧`) is genuinely owed and already has its own banner.
  const ladder = [];
  for (const m of modules) {
    const nextFeature = (m.buildOrder || []).find((b) => b.marker !== '✓');
    if (nextFeature) {
      ladder.push({
        command: `/b-feature ${nextFeature.name}`,
        why: `next ${nextFeature.marker || 'unmarked'} entry in ${m.name}'s build order`,
        route: m.route,
      });
    } else if (!(m.integration && m.integration.marker === '✓')) {
      // A missing `## Module integration` section is the same owed work as a
      // non-✓ marker — all features done, boundary test not: /b-integration.
      ladder.push({
        command: `/b-integration ${m.name}`,
        why: `${m.name}'s features are all ✓ but its boundary test is ${(m.integration && m.integration.marker) || 'unmarked'}`,
        route: m.route,
      });
    }
  }

  return {
    generatedAt: new Date().toISOString(),
    root,
    project: { name: projectName, tagline },
    schema,
    frameworkVersion: projectVersion,
    markerMeta: M.MARKER_META,
    buildOrderRationale,
    docs,
    modules,
    features,
    adrs,
    scope,
    constitution,
    adoption,
    reviewPlans,
    nextMoves,
    ladder,
    backlinks: Object.fromEntries(backlinks),
    docRoutes: Object.fromEntries(docRoutes),
    fileIndex: Object.fromEntries([...fileIndex.entries()].sort((a, b) => a[0].localeCompare(b[0]))),
    recent,
    gitAvailable,
    health: health.sort((a, b) => {
      const w = { error: 0, warn: 1, info: 2 };
      return w[a.severity] - w[b.severity] || a.kind.localeCompare(b.kind);
    }),
    counts: {
      modules: modules.length,
      features: features.length,
      adrs: adrs.length,
      adrsAccepted: adrs.filter((a) => a.status === 'accepted').length,
      adrsSuperseded: adrs.filter((a) => a.status === 'superseded').length,
      adrsNarrowed: adrs.filter((a) => a.narrowedBy.length).length,
      moduleStatus: tally(modules.map((m) => m.status)),
      featureStatus: tally(features.map((f) => f.effectiveMarker)),
      health: tally(health.map((h) => h.severity)),
      indexedFiles: fileIndex.size,
      pendingVerification: features.filter((f) => f.pendingVerification).length,
    },
  };
}

module.exports = { extract, SCHEMA_VERSION };
