'use strict';
/* Bower docs viewer — browser shell.
   Talks to its host through a narrow interface (HOST), so a VS Code extension
   can swap the implementation without touching any view code. */

const HOST = {
  openFile: (p, line) => window.open(openHref(p, line), '_blank'),
  graphUrl: '/graph.json',
  eventsUrl: '/events',
};

let G = null;

function openHref(path, line = null) {
  const at = Number.isInteger(line) && line > 0 ? `&line=${line}` : '';
  return `/open?path=${encodeURIComponent(path)}${at}`;
}

// ─────────────────────────────────────────────────────────── utilities

const $ = (sel, el = document) => el.querySelector(sel);
const el = (tag, attrs = {}, ...kids) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === 'class') n.className = v;
    else if (k === 'html') n.innerHTML = v;
    else if (k.startsWith('on')) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v === true ? '' : v);
  }
  for (const kid of kids.flat()) {
    if (kid == null || kid === false) continue;
    n.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  return n;
};
const esc = (s) =>
  String(s ?? '').replace(
    /[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c],
  );

/** Inline `code` spans in plain metadata prose → real <code>. */
const ticks = (s) => esc(s).replace(/`([^`]+)`/g, '<code>$1</code>');

/** Flatten markdown to bare text, for one-line summaries in dense rows. */
const plain = (s) =>
  String(s ?? '')
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/[*_`]/g, '')
    .replace(/^\s*(State|Status):\s*/i, '')
    .replace(/^\s*[✓🚧⏸🟡🔴🔧]\s*(—|-|·)?\s*/u, '')
    .replace(/\s+/g, ' ')
    .trim();

/** Render a metadata fragment as inline markdown, so its links resolve. */
function inlineMd(text, sourceRel) {
  const host = renderMd(text || '', sourceRel, { stripH1: false });
  host.classList.add('md-inline');
  return host;
}

const markerMeta = (mk) =>
  (G && G.markerMeta && G.markerMeta[mk]) || { key: 'unmarked', label: 'No marker' };

function badge(mk, opts = {}) {
  const m = markerMeta(mk);
  return el(
    'span',
    { class: `mk mk-${m.key}`, title: m.label },
    el('span', { class: 'g' }, mk || '—'),
    opts.bare ? null : m.label.replace(/ and stable| but not started/, ''),
  );
}

const modByName = (n) => G.modules.find((m) => m.name === n);
const featOf = (mod, name) => G.features.find((f) => f.module === mod && f.name === name);
const adrByNum = (n) => G.adrs.find((a) => a.num === n);

function toast(msg) {
  const t = $('#toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.remove('show'), 2600);
}

// ─────────────────────────────────────────── markdown + link rewriting

function renderMd(markdown, sourceRel, { stripH1 = true } = {}) {
  let src = markdown || '';
  if (stripH1) src = src.replace(/^#\s+.*\n?/, '');
  const host = el('div', { class: 'md' });
  host.innerHTML = window.marked.parse(src, { mangle: false, headerIds: false });

  // Heading anchors, matching the slugs the extractor computed.
  const seen = new Map();
  for (const h of host.querySelectorAll('h1,h2,h3,h4')) {
    let slug = h.textContent
      .toLowerCase()
      .replace(/[^\w\s-]/g, '')
      .trim()
      .replace(/\s+/g, '-');
    if (seen.has(slug)) {
      const n = seen.get(slug) + 1;
      seen.set(slug, n);
      slug = `${slug}-${n}`;
    } else seen.set(slug, 0);
    h.id = slug;
  }

  // Rewrite doc links onto viewer routes. Targets are repo-root-based
  // (`/docs/adr/0008-…md`); a leading `/` resolves from the repo root rather
  // than the linking file's directory.
  const dir = sourceRel ? sourceRel.split('/').slice(0, -1).join('/') : '';
  for (const a of host.querySelectorAll('a[href]')) {
    const href = a.getAttribute('href');
    if (!href || /^[a-z][a-z0-9+.-]*:/i.test(href) || href.startsWith('#')) continue;
    const [rel, frag] = href.split('#');
    const resolved = rel.startsWith('/') ? normalise(rel.slice(1)) : normalise(`${dir}/${rel}`);
    const route = G.docRoutes[resolved];
    if (route) {
      a.setAttribute('href', frag ? `${route}#${frag}` : route);
      a.dataset.frag = frag || '';
    } else if (rel.endsWith('.md')) {
      a.classList.add('dead');
      a.title = `${resolved} does not resolve`;
      a.setAttribute('href', 'javascript:void 0');
    } else {
      a.setAttribute('href', `/open?path=${encodeURIComponent(resolved)}`);
      a.target = '_blank';
      a.title = `Open ${resolved}`;
    }
  }
  return host;
}

function normalise(p) {
  const out = [];
  for (const seg of p.split('/')) {
    if (!seg || seg === '.') continue;
    if (seg === '..') out.pop();
    else out.push(seg);
  }
  return out.join('/');
}

/**
 * The structured Components panel replaces the plan's own `## Components`
 * tables, so rendering both shows the same rows twice. Only the tables are
 * duplicated, though — prose in the section (a "Modified:" grouping, an
 * "unchanged because…" note) exists nowhere else and is kept. When nothing
 * but tables remains, the heading goes too; `removedHeading` tells the
 * caller to carry the `components` anchor on the panel instead.
 */
function withoutComponentsTables(md) {
  const lines = md.split('\n');
  const out = [];
  let fenced = false;
  let inSection = false;
  let headingAt = -1;
  let sectionHasProse = false;
  let removedHeading = false;
  const closeSection = () => {
    if (inSection && !sectionHasProse && headingAt !== -1) {
      out.splice(headingAt, 1);
      removedHeading = true;
    }
    inSection = false;
  };
  for (const line of lines) {
    if (/^\s*(```|~~~)/.test(line)) fenced = !fenced;
    if (!fenced && /^##\s/.test(line)) {
      closeSection();
      if (/^##\s+Components\s*$/.test(line)) {
        inSection = true;
        headingAt = out.length;
        sectionHasProse = false;
      }
    } else if (inSection && !fenced) {
      if (/^\s*\|/.test(line)) continue;
      if (line.trim()) sectionHasProse = true;
    }
    out.push(line);
  }
  closeSection();
  return { md: out.join('\n'), removedHeading };
}

/**
 * In-page table of contents. Anchors must carry the current route — a bare
 * `#slug` replaces the whole hash and routes to Not Found.
 */
function tocOf(headings, route, { min = 2, max = 3 } = {}) {
  const items = headings.filter((h) => h.depth >= min && h.depth <= max);
  if (items.length < 3) return null;
  return el(
    'div',
    {},
    el('div', { class: 'eyebrow' }, 'On this page'),
    el(
      'div',
      { class: 'toc' },
      items.map((h) =>
        el('a', { href: `${route || ''}#${h.slug}`, class: `d${h.depth}` }, h.text.replace(/`/g, '')),
      ),
    ),
  );
}

function backlinksOf(rel) {
  const list = (G.backlinks && G.backlinks[rel]) || [];
  if (!list.length) return null;
  return el(
    'div',
    {},
    el('div', { class: 'eyebrow' }, `Referenced by ${list.length}`),
    el(
      'div',
      { class: 'toc' },
      list.map((b) => el('a', { href: b.route }, b.label)),
    ),
  );
}

function sourceLink(rel) {
  return el(
    'div',
    {},
    el('div', { class: 'eyebrow' }, 'Source'),
    el(
      'div',
      { class: 'toc' },
      el('a', { href: `/open?path=${encodeURIComponent(rel)}`, target: '_blank' }, rel),
    ),
  );
}

// ───────────────────────────────────────────────── the build spine

/** Remove dependency edges implied by transitivity, so the true spine shows. */
function reduce(edges, names) {
  const adj = new Map(names.map((n) => [n, new Set()]));
  for (const [u, v] of edges) if (adj.has(u)) adj.get(u).add(v);
  const reaches = (from, to, skip) => {
    const seen = new Set();
    const stack = [...(adj.get(from) || [])].filter((n) => !(from === skip[0] && n === skip[1]));
    while (stack.length) {
      const n = stack.pop();
      if (n === to) return true;
      if (seen.has(n)) continue;
      seen.add(n);
      for (const m of adj.get(n) || []) stack.push(m);
    }
    return false;
  };
  return edges.filter(([u, v]) => !reaches(u, v, [u, v]));
}

function spine() {
  const mods = G.modules;
  if (!mods.length) return el('p', { class: 'muted' }, 'No modules found.');
  const order = new Map(mods.map((m, i) => [m.name, i]));

  const back = [];
  const fwd = [];
  for (const m of mods)
    for (const d of m.dependsOn) {
      if (!order.has(d)) continue;
      (order.get(d) < order.get(m.name) ? back : fwd).push([m.name, d]);
    }
  const backReduced = reduce(back, mods.map((m) => m.name));

  // Geometry
  const W = 60 + mods.length * 118;
  const boxW = 96;
  const boxH = 40;
  const midY = 132;
  const gap = (W - 60 - boxW) / Math.max(1, mods.length - 1);
  const cx = (n) => 30 + order.get(n) * gap + boxW / 2;

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'spine');
  svg.setAttribute('viewBox', `0 0 ${W} 224`);
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', 'Module build order and dependency edges');

  const ns = (tag, attrs = {}, text) => {
    const n = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [k, v] of Object.entries(attrs)) if (v != null) n.setAttribute(k, v);
    if (text != null) n.textContent = text;
    return n;
  };

  const arc = (a, b, above, cls) => {
    const x1 = cx(a);
    const x2 = cx(b);
    const span = Math.abs(x2 - x1);
    const y = above ? midY - boxH / 2 : midY + boxH / 2;
    const lift = Math.min(74, 20 + span * 0.28) * (above ? -1 : 1);
    const p = ns('path', {
      class: cls,
      d: `M ${x1} ${y} C ${x1} ${y + lift}, ${x2} ${y + lift}, ${x2} ${y}`,
    });
    p.dataset.a = a;
    p.dataset.b = b;
    return p;
  };

  const edgeLayer = ns('g');
  let i = 0;
  for (const [u, v] of backReduced) {
    const p = arc(u, v, true, 'edge');
    p.style.animationDelay = `${(i++ % 12) * 32}ms`;
    edgeLayer.append(p);
  }
  for (const [u, v] of fwd) {
    const p = arc(u, v, false, 'edge fwd');
    p.style.animationDelay = `${(i++ % 12) * 32}ms`;
    edgeLayer.append(p);
  }
  svg.append(edgeLayer);

  const statusColour = {
    complete: 'var(--euc)',
    wip: 'var(--ochre)',
    planned: 'var(--inert)',
    issues: 'var(--gold)',
    broken: 'var(--oxide)',
    revision: 'var(--violet)',
    unmarked: 'var(--ink-3)',
  };

  mods.forEach((m, idx) => {
    const x = 30 + idx * gap;
    const g = ns('g', { class: 'node-hit', role: 'link', tabindex: '0' });
    g.dataset.name = m.name;
    g.append(ns('rect', { class: 'node-box', x, y: midY - boxH / 2, width: boxW, height: boxH, rx: 2 }));
    // Status is carried by a solid left edge — colour, not an icon.
    g.append(
      ns('rect', {
        x,
        y: midY - boxH / 2,
        width: 3,
        height: boxH,
        fill: statusColour[markerMeta(m.status).key],
      }),
    );
    g.append(ns('text', { class: 'n-idx', x: x + 10, y: midY - 6 }, String(idx + 1).padStart(2, '0')));
    const label =
      m.name.length > 12 ? `${m.name.slice(0, 11)}…` : m.name;
    g.append(ns('text', { class: 'n-name', x: x + 10, y: midY + 12 }, label));
    const feats = G.features.filter((f) => f.module === m.name).length;
    g.append(
      ns(
        'text',
        { class: 'n-idx', x: x + boxW - 10, y: midY - 6, 'text-anchor': 'end' },
        feats ? `${feats}f` : '',
      ),
    );
    const title = ns('title', {}, `${m.name} — ${markerMeta(m.status).label}`);
    g.append(title);

    const go = () => (location.hash = m.route);
    g.addEventListener('click', go);
    g.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        go();
      }
    });
    g.addEventListener('mouseenter', () => light(m.name));
    g.addEventListener('focus', () => light(m.name));
    g.addEventListener('mouseleave', unlight);
    g.addEventListener('blur', unlight);
    svg.append(g);
  });

  // Hovering a module reveals every declared edge it participates in.
  function light(name) {
    svg.classList.add('dim');
    const all = [...back, ...fwd].filter(([u, v]) => u === name || v === name);
    const keep = new Set();
    for (const [u, v] of all) {
      keep.add(u);
      keep.add(v);
    }
    for (const p of svg.querySelectorAll('path.edge'))
      p.classList.toggle('lit', p.dataset.a === name || p.dataset.b === name);
    for (const n of svg.querySelectorAll('.node-hit'))
      n.classList.toggle('lit', keep.has(n.dataset.name));
  }
  function unlight() {
    svg.classList.remove('dim');
    for (const p of svg.querySelectorAll('path.edge')) p.classList.remove('lit');
    for (const n of svg.querySelectorAll('.node-hit')) n.classList.remove('lit');
  }

  return el(
    'div',
    {},
    el('div', { class: 'spine-wrap' }, svg),
    el(
      'div',
      { class: 'spine-key eyebrow' },
      el('span', {}, el('i', {}), 'depends on an earlier module'),
      el('span', {}, el('i', { class: 'fwd' }), 'depends on a later one — a cycle'),
      el('span', {}, 'hover a module for its full edge set'),
    ),
  );
}

// ───────────────────────────────────────────────────────────── views

function pageHead(crumbs, title, sub, { ident = false, aside = null } = {}) {
  return el(
    'header',
    { class: 'page-head' },
    el('div', { class: 'crumb eyebrow' }, crumbs),
    el('h1', { class: ident ? 'ident' : null }, title),
    sub ? el('p', { class: 'sub', html: ticks(sub) }) : null,
    aside,
  );
}

/**
 * Banners for project states that are themselves the next action — an open
 * adoption phase, an unapplied review plan, a viewer/project version skew.
 * All three are transient by design, so none of them gets a permanent home.
 */
function banners() {
  const out = [];
  const s = G.schema;
  if (s && s.match === false)
    out.push(
      el(
        'a',
        { class: 'banner warn', href: '#/health' },
        el('b', {}, 'Version skew'),
        ` This viewer parses framework v${s.viewerFor} schemas; the project is on v${s.projectVersion}. ` +
          `Re-run the scaffold, or read the drift checks with that in mind.`,
      ),
    );
  if (G.adoption && G.adoption.active)
    out.push(
      el(
        'a',
        { class: 'banner seed', href: '#/adoption' },
        el('b', {}, '🌱 Adoption in progress'),
        G.adoption.openItems.length
          ? ` ${G.adoption.openItems.length} unattributed choice${G.adoption.openItems.length === 1 ? '' : 's'} still open. ` +
            `Docs here were reconstructed from code — features marked 🚧 are as-built, not verified.`
          : ' The ledger is empty — the exit condition is met.',
      ),
    );
  for (const rp of G.reviewPlans || [])
    if (rp.open)
      out.push(
        el(
          'a',
          { class: 'banner warn', href: rp.route },
          el('b', {}, `In review · ${rp.module}`),
          ` ${rp.open} of ${rp.total} finding${rp.total === 1 ? '' : 's'} still open. ` +
            `Running /b-review ${rp.module} resumes mediation — it does not re-diagnose.`,
        ),
      );
  return out;
}

function viewOverview() {
  const c = G.counts;
  const fs = c.featureStatus || {};
  const h = c.health;
  const total = G.health.length;
  const severities = ['error', 'warn', 'info'].filter((s) => h[s]).map((s) => `${h[s]} ${s}`);

  // Equal-width grid tiles, each with a headline figure, a label, and its
  // breakdown on separate lines. The breakdown used to be one long
  // interpuncted string, which set the flex basis from content width and made
  // six tiles refuse to fit any screen.
  const tile = ({ value, label, lines = [], href, alert }) =>
    el(
      href ? 'a' : 'div',
      { class: `tile ${alert ? 'alert' : ''}`, href },
      el('b', {}, value),
      el('div', { class: 'tile-label' }, label),
      lines.filter(Boolean).length
        ? el(
            'div',
            { class: 'tile-lines' },
            lines.filter(Boolean).map((l) => el('div', {}, l)),
          )
        : null,
    );

  const modStatus = c.moduleStatus || {};
  const strip = el('div', { class: 'strip' }, [
    G.scope
      ? tile({
          value: `${G.scope.satisfied}/${G.scope.derivable}`,
          label: 'Criteria satisfied',
          lines: [
            G.scope.derivable < G.scope.total ? `${G.scope.total - G.scope.derivable} not derivable` : null,
          ],
          href: '#/scope',
        })
      : null,
    tile({
      value: c.modules,
      label: c.modules === 1 ? 'Module' : 'Modules',
      lines: [
        modStatus['✓'] ? `${modStatus['✓']} complete` : null,
        modStatus['🚧'] ? `${modStatus['🚧']} in development` : null,
        modStatus['⏸'] ? `${modStatus['⏸']} not started` : null,
      ],
      href: '#/modules',
    }),
    tile({
      value: c.features,
      label: c.features === 1 ? 'Feature' : 'Features',
      lines: [
        fs['✓'] ? `${fs['✓']} complete` : null,
        fs['🚧'] ? `${fs['🚧']} in development` : null,
        fs['⏸'] ? `${fs['⏸']} planned` : null,
        c.pendingVerification ? `${c.pendingVerification} awaiting checks` : null,
      ],
    }),
    tile({
      value: c.adrs,
      label: c.adrs === 1 ? 'Decision' : 'Decisions',
      lines: [
        `${c.adrsAccepted} accepted`,
        c.adrsSuperseded ? `${c.adrsSuperseded} superseded` : null,
        c.adrsNarrowed ? `${c.adrsNarrowed} narrowed` : null,
      ],
      href: '#/adrs',
    }),
    tile({
      value: c.indexedFiles,
      label: 'Files claimed',
      lines: ['by a feature plan'],
      href: '#/files',
    }),
    tile({
      value: total,
      label: 'Health findings',
      lines: total ? severities : ['nothing to reconcile'],
      href: '#/health',
      alert: !!h.error,
    }),
  ]);

  // Two kinds of next move, and they are not interchangeable. The stored ones
  // are feature-scoped and only exist while a feature is unfinished; the ladder
  // is project-scoped and *derived* from markers, because no file owns it (see
  // framework-reference.md, "status.md — Resumption Framing").
  const moveRows = [
    ...G.nextMoves.map((n) =>
      el(
        'a',
        { class: 'row', href: n.route },
        el('span', { class: 'ident' }, plain(n.command || n.text)),
        el('span', { class: 'note grow' }, `${n.module}/${n.feature}`),
      ),
    ),
    ...(G.ladder || []).map((l) =>
      el(
        'a',
        { class: 'row', href: l.route },
        el('span', { class: 'ident' }, l.command),
        el('span', { class: 'note grow' }, l.why),
      ),
    ),
  ];
  const moves = moveRows.length
    ? el('div', { class: 'rows' }, moveRows)
    : el('div', { class: 'panel-body' }, el('p', { class: 'muted' }, 'Nothing outstanding.'));

  const recent = G.recent.slice(0, 9);
  const recentRows = recent.length
    ? el(
        'div',
        { class: 'rows' },
        recent.map((r) => {
          const route = G.docRoutes[r.rel];
          return el(
            route ? 'a' : 'div',
            { class: 'row', href: route || null },
            el('span', { class: 'note', style: 'min-width:74px;color:var(--ink-3)' }, r.date),
            el('span', { class: 'ident grow', style: 'overflow:hidden;text-overflow:ellipsis' },
              r.rel.replace(/^docs\//, '')),
          );
        }),
      )
    : el(
        'div',
        { class: 'panel-body' },
        el('p', { class: 'muted' }, G.gitAvailable ? 'No recent doc changes.' : 'Git history unavailable.'),
      );

  return el(
    'div',
    {},
    pageHead(
      [el('span', {}, 'Bower'), el('span', {}, '·'), el('span', {}, 'Project state')],
      G.project.name,
      G.project.tagline,
    ),
    banners(),
    strip,
    el('section', { class: 'block' }, el('h2', {}, 'The build spine'), spine()),
    el(
      'div',
      { class: 'cols' },
      el(
        'div',
        { class: 'panel' },
        el(
          'div',
          { class: 'panel-head' },
          el('span', { class: 'eyebrow' }, 'Outstanding next moves'),
          el('span', { class: 'eyebrow' }, moveRows.length),
        ),
        moves,
      ),
      el(
        'div',
        { class: 'panel' },
        el(
          'div',
          { class: 'panel-head' },
          el('span', { class: 'eyebrow' }, 'Docs changed most recently'),
          el('a', { class: 'eyebrow', href: '#/modules' }, 'All modules →'),
        ),
        recentRows,
      ),
    ),
    el(
      'section',
      { class: 'block' },
      el('h2', {}, 'How this project is documented'),
      el(
        'div',
        { class: 'panel' },
        el(
          'div',
          { class: 'panel-body' },
          el('p', { class: 'muted', style: 'margin:0 0 12px' },
            'Bower keeps documentation as current state, not history. A module is a set of features ' +
              'sharing data concerns; each feature carries a plan (how it works) and a status ' +
              '(where it stands). Cross-cutting decisions live in ADRs, whose bodies are immutable — ' +
              'a reversal is a new ADR superseding the old.'),
          el(
            'div',
            { class: 'chips' },
            Object.entries(G.markerMeta).map(([mk, m]) =>
              el('span', { class: 'chip' }, `${mk}  ${m.label}`),
            ),
          ),
        ),
      ),
    ),
  );
}

function viewHealth() {
  const sev = { error: 0, warn: 1, info: 2 };
  const groups = {};
  for (const h of G.health) (groups[h.kind] = groups[h.kind] || []).push(h);
  const kinds = Object.keys(groups).sort(
    (a, b) => sev[groups[a][0].severity] - sev[groups[b][0].severity] || a.localeCompare(b),
  );

  const explain = {
    'adr-asymmetric': 'A supersession must be recorded on both ADRs in the same commit.',
    'adr-status-conflict': 'An ADR cannot be in force and superseded at once.',
    'adr-unknown-module': 'ADR frontmatter references exact module directory names.',
    'adr-no-successor': 'A superseded ADR must point at what replaced it.',
    'adr-unclassified': 'Pre-v0.20 ADRs carry no scope; they load on module or topic match only.',
    'adr-narrow-asymmetric': 'Narrowing is one write — both sides of the pair, or neither.',
    'adr-narrow-dangling': 'A narrowing pointer names an ADR that is not there.',
    'adr-narrow-and-supersede':
      'A decision either scopes an exception to an earlier one or replaces it. Claiming both marks live policy dead.',
    'narrowed-adr-not-accepted':
      'Narrowing leaves its target accepted — that is the whole point of the field. A narrowed ADR that is not accepted is the defect narrowing exists to prevent.',
    'broken-link': 'A link between docs does not resolve on disk.',
    'relative-doc-link': 'Doc links are repo-root-based. A relative target breaks the moment either file moves.',
    'component-missing': "A built feature's plan claims a file that is not there.",
    'arch-feature-roster':
      "architecture.md no longer holds a feature roster — the module's build order is the only one.",
    'marker-disagreement': 'Two documents report different status for the same feature.',
    'status-no-marker': 'No independent marker to cross-check the build-order marker against.',
    'feature-not-in-build-order': "The module's build order omits a feature that has docs.",
    'build-order-orphan': 'A build-order entry past ⏸ should have a docs directory.',
    'no-components-table': 'No parseable Components table, so its files are not indexed.',
    'pending-verification-complete':
      '✓ means the agreed criteria were verified. Deferred manual checks mean 🚧, not ✓.',
    'criterion-no-owner':
      'Without a Delivered by: clause a criterion cannot be derived — and its module is never guessed from the wording.',
    'criterion-stale-pointer': 'A criterion points at a module that no longer exists.',
    'criterion-carries-status':
      'Criteria hold no achievement state. Satisfaction is derived from module completion, never stored.',
    'adoption-exit-due': 'An empty ledger already meets the exit condition. Adoption is a phase you leave.',
    'adoption-ledger-missing': 'The banner told an agent to read a ledger that is not there.',
    'schema-version-skew': 'This viewer and the project disagree about which framework version they are on.',
    'oversized-table-cell':
      'A table cell holding a paragraph. A formatter aligns every sibling row out to match it, so the cost multiplies across a file agents read on every session.',
    'check-may-be-obsolete':
      'Aimed at the viewer, not the project: a check matching every candidate is usually testing a dropped convention.',
  };

  return el(
    'div',
    {},
    pageHead(
      [el('a', { href: '#/' }, 'Overview'), el('span', {}, '·'), el('span', {}, 'Health')],
      'Documentation health',
      'Drift checks: every one compares a document against another document, or against the ' +
        'files on disk. These are claims the docs make that the repository no longer supports. ' +
        'An `error` is a contradiction — two documents that cannot both be right. A `warn` is ' +
        'something to look at, not a verdict.',
    ),
    G.health.length === 0
      ? el('div', { class: 'panel' }, el('div', { class: 'panel-body' }, el('p', {}, 'No drift found.')))
      : kinds.map((kind) => {
          const items = groups[kind];
          return el(
            'section',
            { class: 'block' },
            el('h2', {}, `${kind.replace(/-/g, ' ')} · ${items.length}`),
            explain[kind]
              ? el('p', { class: 'muted', style: 'margin:-4px 0 12px;font-size:13.5px' }, explain[kind])
              : null,
            el(
              'div',
              { class: 'panel' },
              items.map((h) =>
                el(
                  'div',
                  { class: 'finding' },
                  el('div', { class: `sev sev-${h.severity}` }, h.severity),
                  el(
                    'div',
                    { class: 'msg' },
                    el('div', { html: ticks(h.message.replace(/\s*\(from [^)]*\)\s*$/, '')) }),
                    el(
                      'div',
                      { class: 'where' },
                      G.docRoutes[h.path]
                        ? el('a', { href: G.docRoutes[h.path] }, h.path)
                        : el('a', { href: `/open?path=${encodeURIComponent(h.path)}`, target: '_blank' }, h.path),
                    ),
                  ),
                ),
              ),
            ),
          );
        }),
  );
}

function viewScope() {
  if (!G.scope) return notFound('No docs/scope.md');
  const s = G.scope;
  const undecidable = s.criteria.filter((c) => c.satisfied === null);

  const row = (c) => {
    const mark = c.satisfied === null ? '?' : c.satisfied ? '✓' : '·';
    const cls = c.satisfied === null ? 'crit unknown' : c.satisfied ? 'crit met' : 'crit open';
    return el(
      'div',
      { class: cls },
      el('div', { class: 'crit-mark' }, mark),
      el(
        'div',
        { class: 'crit-body' },
        el('div', { class: 'crit-text' }, inlineMd(c.text, s.rel)),
        el(
          'div',
          { class: 'crit-meta' },
          c.deliveredBy.length
            ? el(
                'span',
                { class: 'chips' },
                c.deliveredBy.map((n) => {
                  const m = modByName(n);
                  const blocked = c.blocking.find((b) => b.module === n);
                  return m
                    ? el(
                        'a',
                        { class: `chip ${blocked ? 'blocking' : ''}`, href: m.route, title: markerMeta(m.status).label },
                        `${m.status || '—'} ${n}`,
                      )
                    : el('span', { class: 'chip gone', title: 'Not a module in this project' }, `${n} (missing)`);
                }),
              )
            : el('span', { class: 'eyebrow' }, 'no Delivered by: clause — not derivable'),
        ),
      ),
    );
  };

  return el(
    'div',
    {},
    pageHead(
      [el('a', { href: '#/' }, 'Overview'), el('span', {}, '·'), el('span', {}, 'Scope')],
      `${s.satisfied} of ${s.derivable} success criteria satisfied`,
      'Criteria carry no status field. A criterion holds when every module in its ' +
        '`Delivered by:` clause is complete — all features ✓ and the module-integration marker ✓. ' +
        'Derived here, exactly as `/b-recap` derives it; stored nowhere.',
    ),
    el(
      'div',
      { class: 'panel', style: 'margin-bottom:18px' },
      el(
        'div',
        { class: 'panel-head' },
        el('span', { class: 'eyebrow' }, 'Success criteria'),
        el(
          'span',
          { class: 'eyebrow' },
          undecidable.length ? `${undecidable.length} not derivable` : `${s.total} total`,
        ),
      ),
      el('div', { class: 'crits' }, s.criteria.map(row)),
    ),
    el('a', { class: 'eyebrow', href: s.route }, 'Read docs/scope.md in full →'),
  );
}

function viewAdoption() {
  const a = G.adoption;
  if (!a) return notFound('This project is not in an adoption phase');
  return el(
    'div',
    {},
    pageHead(
      [el('a', { href: '#/' }, 'Overview'), el('span', {}, '·'), el('span', {}, 'Adoption')],
      '🌱 Adoption phase',
      'These docs were reconstructed from an existing codebase. Every entry below is a ' +
        'cross-cutting choice found in the code whose rationale could not be attributed. ' +
        'Each has three exits — resolve to an ADR, remediate through `/b-feature` or `/b-design`, ' +
        'or dismiss — and all three delete the line. When the ledger empties, the banner goes.',
    ),
    !a.active
      ? el(
          'div',
          { class: 'panel', style: 'margin-bottom:18px' },
          el(
            'div',
            { class: 'panel-body' },
            el('p', { class: 'muted', style: 'margin:0' }, 'The banner is gone — the phase is closed.'),
          ),
        )
      : null,
    el(
      'div',
      { class: 'panel' },
      el(
        'div',
        { class: 'panel-head' },
        el('span', { class: 'eyebrow' }, 'Open questions'),
        el('span', { class: 'eyebrow' }, a.openItems.length),
      ),
      a.openItems.length
        ? el(
            'div',
            { class: 'rows' },
            a.openItems.map((it) =>
              el(
                'div',
                { class: 'row' },
                el('span', { class: 'ident', style: 'min-width:220px' }, it.location),
                el('span', { class: 'note grow' }, it.question || '—'),
              ),
            ),
          )
        : el(
            'div',
            { class: 'panel-body' },
            el('p', { class: 'muted', style: 'margin:0' }, 'Nothing open. The exit condition is met.'),
          ),
    ),
    a.ledgerRel ? el('a', { class: 'eyebrow', href: G.docRoutes[a.ledgerRel] || '#/' }, 'Read the ledger →') : null,
  );
}

/**
 * An open review is the one lifecycle state whose substance lives outside the
 * module's own documents: `review-plan.md` is transient and agent-owned, deleted
 * at closeout when `Review: ✓` becomes the record. It gets a page of its own
 * because "3 of 7 disposed" is not something an operator can act on — the
 * findings, their classes, and where each one points are.
 */
function viewReview(name) {
  const rp = (G.reviewPlans || []).find((p) => p.module === name);
  if (!rp)
    return notFound(
      `No open review for “${name}” — review-plan.md exists only while a review is open (Review: 🚧).`,
    );
  const m = modByName(name);
  const rv = m && m.review;
  const disposed = rp.total - rp.open;

  const disposition = (it) =>
    it.wontFix
      ? el('span', { class: 'tag wontfix' }, 'won’t fix')
      : it.done
        ? el('span', { class: 'tag done' }, 'resolved')
        : el('span', { class: 'tag pend' }, 'open');

  // A pointer is either a place in the tree or the literal command that
  // discharges the finding. Only the first is openable, and conflating them
  // would offer a link that goes nowhere.
  const pointerOf = (it) => {
    if (it.note) return el('span', { class: 'muted ptr', style: 'font-size:12.5px' }, it.note);
    if (!it.pointer) return null;
    if (it.pointerKind === 'path')
      return el(
        'a',
        {
          class: 'ident ptr',
          style: 'font-size:12px',
          href: openHref(it.pointerFile, it.pointerLine),
          target: '_blank',
          title: it.pointer,
        },
        it.pointer,
      );
    return el('code', { style: 'font-size:12px' }, it.pointer.replace(/^Run\s+/, ''));
  };

  return el(
    'div',
    {},
    pageHead(
      [
        el('a', { href: '#/' }, 'Overview'),
        el('span', {}, '·'),
        el('a', { href: '#/modules' }, 'Modules'),
        el('span', {}, '·'),
        el('a', { href: rp.moduleRoute }, name),
        el('span', {}, '·'),
        el('span', {}, 'Review'),
      ],
      `Review · ${name}`,
      (rp.diagnosed ? `Diagnosed ${rp.diagnosed}` : 'Open review') +
        (rp.featureCount !== null ? ` against ${rp.featureCount} feature${rp.featureCount === 1 ? '' : 's'}` : '') +
        `. \`/b-review ${name}\` resumes mediation — it does not re-diagnose. The plan is transient: ` +
        'it is deleted at closeout, when `Review: ✓` becomes the record.',
    ),
    // Plan and marker are two sides of one fact, written together. A page that
    // showed the findings without saying the pair disagrees would hide the more
    // urgent problem behind the less urgent one.
    !rv || rv.marker !== '🚧'
      ? el(
          'a',
          { class: 'strap', href: '#/health' },
          el('b', {}, 'Marker disagrees with the plan.'),
          ` This plan is on disk but the module's Review: marker is ${rv && rv.marker ? rv.marker : 'unset'}, not 🚧 — ` +
            'the marker was never set, or the review closed without deleting the plan. See Health →',
        )
      : null,
    el(
      'div',
      { class: 'panel' },
      el(
        'div',
        { class: 'panel-head' },
        el('span', { class: 'eyebrow' }, 'Findings'),
        el(
          'span',
          { class: 'eyebrow' },
          `${disposed} of ${rp.total} disposed${rp.wontFix ? ` · ${rp.wontFix} won’t fix` : ''}`,
        ),
      ),
      rp.total
        ? el(
            'div',
            { class: 'rows findings' },
            // Plan order is meaningful — /b-review writes owned findings first,
            // because those are the ones it actions in the pass — so it is kept.
            // Every row emits all five cells: `.rows.findings` is a grid whose
            // rows share column tracks, so a skipped cell would shift the rest.
            rp.items.flatMap((it, i) => {
              // A routed command carries its own `according to F<n> in <plan>`
              // reference so the operator can paste one line, which makes it far
              // too long for a `max-content` column — it would starve the gist
              // track. Commands drop to their own full-width row; a path pointer
              // is short and stays inline, where it reads as the finding's
              // location rather than as an instruction.
              const ptr = pointerOf(it);
              const inline = it.pointerKind === 'command' ? null : ptr;
              const subs = [];
              if (it.pointerKind === 'command' && ptr) subs.push(el('div', { class: 'row sub cmd' }, ptr));
              // The brief is the reviewer's Location/Drift/Resolution verbatim,
              // and after closeout deletes the report it is the only copy. It is
              // shown in full rather than folded away: a reader on this page is
              // deciding whether to act on the finding, which is the question the
              // brief answers.
              if (it.brief)
                subs.push(
                  el(
                    'div',
                    { class: 'row sub brief' },
                    // Same three fields as the extractor's BRIEF_FIELDS, in the
                    // order /b-review writes them. Renders what is present; a
                    // missing one is the health check's business, not a blank row.
                    ...['location', 'drift', 'resolution']
                      .filter((k) => it.brief[k])
                      .map((k) =>
                        el('div', {}, el('b', {}, `${k[0].toUpperCase()}${k.slice(1)}: `), plain(it.brief[k])),
                      ),
                  ),
                );
              // Free prose the operator (or an earlier /b-review) wrote under the
              // finding — a re-opened note, a caveat. This page is the plan's only
              // rendering, so what the file carries, the page shows.
              if (it.annotations)
                subs.push(
                  el('div', { class: 'row sub ann' }, ...it.annotations.map((n) => el('div', {}, plain(n)))),
                );
              // Only the group's last row draws the separator, so a finding and
              // its sub-rows read as one entry rather than three.
              if (subs.length) subs[subs.length - 1].className += ' last';
              return [
                el(
                  'div',
                  { class: subs.length ? 'row grouped' : 'row' },
                  el('span', { class: 'idx' }, it.id || String(i + 1)),
                  disposition(it),
                  el('span', { style: 'font-size:13px;color:var(--ink-2);min-width:0' }, plain(it.gist)),
                  it.class
                    ? el('span', { class: it.routed ? 'tag routed' : 'tag', title: it.routed ? 'Routed — another command owns this' : 'Owned — /b-review reconciles this itself' }, it.class)
                    : el('span'),
                  // v0.34: a routed finding is ticked by the command that
                  // discharged it, which leaves a completion note. Shown short,
                  // with the whole note on hover — it is provenance for the
                  // closeout audit, which still reads the code, not a claim the
                  // drift is gone. The routed pointer is a command and so has
                  // dropped to its own row, leaving this cell free.
                  inline ||
                    (it.completion
                      ? el(
                          'span',
                          { class: 'tag', title: `${it.completion} — provenance for the closeout audit, not evidence` },
                          (/^done\s+\d{4}-\d{2}-\d{2}/i.exec(it.completion) || [it.completion])[0],
                        )
                      : el('span')),
                ),
                ...subs,
              ];
            }),
          )
        : el(
            'div',
            { class: 'panel-body' },
            el('p', { class: 'muted', style: 'margin:0' }, 'The plan has no `## Findings` checklist.'),
          ),
    ),
    rp.observations.length
      ? el(
          'section',
          { class: 'block', style: 'margin-top:24px' },
          el('h2', {}, `Observations · ${rp.observations.length}`),
          el(
            'div',
            { class: 'panel' },
            el(
              'div',
              { class: 'rows' },
              rp.observations.map((o) =>
                el('div', { class: 'row' }, el('span', { class: 'grow', style: 'font-size:13px;color:var(--ink-3)' }, plain(o))),
              ),
            ),
          ),
        )
      : null,
    // Sections the schema doesn't name (a `## Constitution` consent record,
    // say) render the same way Observations do. Everything in the file appears
    // on this page — links to review-plan.md land here, not on a raw view.
    ...(rp.sections || []).map((s) =>
      el(
        'section',
        { class: 'block', style: 'margin-top:24px' },
        el('h2', {}, s.title),
        el(
          'div',
          { class: 'panel' },
          el(
            'div',
            { class: 'rows' },
            s.lines.map((t) =>
              el('div', { class: 'row' }, el('span', { class: 'grow', style: 'font-size:13px;color:var(--ink-3)' }, plain(t))),
            ),
          ),
        ),
      ),
    ),
    el(
      'a',
      { class: 'eyebrow', style: 'display:inline-block;margin-top:18px', href: `/open?path=${encodeURIComponent(rp.rel)}`, target: '_blank' },
      'Open review-plan.md →',
    ),
  );
}

function viewDoc(id) {
  const d = G.docs.find((x) => x.id === id);
  if (!d) return notFound(`No document “${id}”`);
  const route = G.docRoutes[d.rel] || `#/doc/${encodeURIComponent(id)}`;
  let body;
  if (d.ext === 'md') body = renderMd(d.body, d.rel);
  else if (d.ext === 'txt') body = el('pre', { class: 'pre-plain' }, d.body);
  else
    body = el(
      'div',
      { class: 'panel' },
      el(
        'div',
        { class: 'panel-body' },
        el('p', { class: 'muted' }, `${d.ext.toUpperCase()} file — not rendered here.`),
        el('a', { href: `/open?path=${encodeURIComponent(d.rel)}`, target: '_blank' }, `Open ${d.rel}`),
      ),
    );

  const kindLabel = {
    central: 'Core document',
    design: 'Design',
    operations: 'Operations',
    reference: 'Reference',
    reports: 'Report',
  };

  // The constitution is normative — it states rules, not facts. Anything under
  // `## Not yet in force` is an aspiration agents must treat as non-existent,
  // which is worth saying before the reader starts trusting the prose.
  const nyif =
    d.id === 'constitution' && G.constitution && G.constitution.items.length ? G.constitution.items : null;

  return el(
    'div',
    {},
    pageHead(
      [
        el('a', { href: '#/' }, 'Overview'),
        el('span', {}, '·'),
        el('span', {}, kindLabel[d.kind] || d.kind),
      ],
      d.title,
      null,
      {},
    ),
    // Project material carries no Bower convention, so say so before the reader
    // starts applying one.
    d.origin === 'project'
      ? el(
          'div',
          { class: 'strap project' },
          el('b', {}, 'Project document.'),
          ' Not part of Bower’s document set — the framework neither writes nor reconciles it, ' +
            'and none of its schemas or status conventions apply. Shown here so the project’s own ' +
            'material is reachable alongside the rest.',
        )
      : null,

    // A count and a jump, not a copy: the items are a few lines further down the
    // page in their own markdown, and duplicating them here loses the formatting
    // while doubling the reading.
    nyif
      ? el(
          'a',
          { class: 'strap nyif', href: `${route}#not-yet-in-force` },
          el('b', {}, `${nyif.length} rule${nyif.length === 1 ? '' : 's'} not yet in force.`),
          ' Intended, but not true of the repo today — agents treat them as non-existent, ' +
            'and no work is marked ✓ on their strength. Jump to the section →',
        )
      : null,
    el(
      'div',
      { class: 'split' },
      body,
      el(
        'aside',
        { class: 'aside' },
        el(
          'div',
          {},
          el('div', { class: 'eyebrow' }, 'Ownership'),
          el('div', { class: 'chips' }, el('span', { class: 'chip' }, d.ownership)),
        ),
        tocOf(d.headings, route),
        backlinksOf(d.rel),
        sourceLink(d.rel),
      ),
    ),
  );
}

function viewModules() {
  return el(
    'div',
    {},
    pageHead(
      [el('a', { href: '#/' }, 'Overview'), el('span', {}, '·'), el('span', {}, 'Modules')],
      'Module graph',
      G.buildOrderRationale ||
        'Modules in build order. Status is the worst marker across features and integration; review is a separate axis.',
    ),
    spine(),
    el(
      'div',
      { class: 'panel' },
      el(
        'div',
        { class: 'panel-head' },
        el('span', { class: 'eyebrow' }, 'Build order'),
        el('span', { class: 'eyebrow' }, `${G.modules.length} modules`),
      ),
      el(
        'div',
        { class: 'rows' },
        G.modules.map((m, i) =>
          el(
            'a',
            { class: 'row', href: m.route },
            el('span', { class: 'idx' }, String(i + 1).padStart(2, '0')),
            badge(m.status, { bare: true }),
            el('span', { class: 'ident', style: 'min-width:112px' }, m.name),
            el('span', { class: 'note grow' }, plain(m.purpose)),
            // Review is its own axis, sitting beside the status marker rather
            // than inside it — an unreviewed module is not thereby incomplete.
            m.review && m.review.marker
              ? el(
                  'span',
                  { class: 'eyebrow', title: `Review: ${m.review.raw}` },
                  `review ${m.review.marker}`,
                )
              : null,
          ),
        ),
      ),
    ),
  );
}

// A module moves build → integration → review, and until v0.29 only the first
// two were visible anywhere. The three stages are separate axes, not a single
// ladder: review is optional framework work and is deliberately *not* an input
// to the module's status rollup, so it is shown beside the rollup, never folded
// into it (framework-reference.md, "The review state is orthogonal to
// completion"). Staleness is derived here the same way /b-recap derives it.
function lifecycle(m) {
  const RANK = ['🔴', '🟡', '🚧', '⏸', '🔧', '✓'];
  // The Build stage counts against the `## Build order` — the module's only
  // feature roster — not against what has a docs directory. A ⏸ entry has no
  // directory until its plan is written, which is normal and deliberately not
  // flagged; deriving the stage from materialised features made a designed-but-
  // unbuilt module read "No features yet" in exactly the state where the roster
  // is the only thing there is to see.
  const feats = G.features.filter((f) => f.module === m.name);
  const markers = (m.buildOrder.length ? m.buildOrder.map((b) => b.marker) : feats.map((f) => f.marker)).filter(Boolean);
  const buildMk = markers.length
    ? RANK.find((r) => markers.includes(r)) || null
    : null;
  const done = markers.filter((k) => k === '✓').length;

  const rv = m.review;
  const rp = (G.reviewPlans || []).find((p) => p.module === m.name);
  const stale =
    rv && rv.marker === '✓' && rv.featureCount !== null && m.buildOrder.length > rv.featureCount
      ? `${m.buildOrder.length - rv.featureCount} feature${m.buildOrder.length - rv.featureCount === 1 ? '' : 's'} added since`
      : null;

  let reviewMk = rv ? rv.marker : null;
  let reviewDetail;
  if (!rv) reviewDetail = 'Not recorded — no “Module review” section (a project predating v0.29).';
  else if (rv.marker === '🚧')
    reviewDetail = rp
      ? `In review · ${rp.total - rp.open} of ${rp.total} findings disposed${rp.wontFix ? ` (${rp.wontFix} won't fix)` : ''}`
      : 'Marked in review, but no review-plan.md on disk.';
  else if (rv.marker === '✓')
    reviewDetail =
      `Reviewed${rv.date ? ` ${rv.date}` : ''}` +
      (rv.featureCount !== null ? ` against ${rv.featureCount} feature${rv.featureCount === 1 ? '' : 's'}` : '') +
      (stale ? ` · stale — ${stale}` : '');
  else reviewDetail = 'Never reviewed. /b-review is optional, and offered once the module is complete.';

  // The review stage is clickable while a plan is on disk: an open review has
  // findings behind it, and a count of them is not something to act on.
  const stage = (label, mk, detail, warn, href) =>
    el(
      href ? 'a' : 'div',
      { class: 'panel-head', style: 'gap:10px', href: href || null },
      badge(mk),
      el('span', { class: 'eyebrow' }, label),
      el('span', { class: warn ? 'shrunk' : 'muted', style: 'font-size:12.5px' }, detail),
      href ? el('span', { class: 'eyebrow' }, 'findings →') : null,
    );

  return el(
    'section',
    { class: 'block' },
    el('h2', {}, 'Lifecycle'),
    el(
      'div',
      { class: 'panel lifecycle' },
      stage(
        'Build',
        buildMk,
        markers.length ? `${done} of ${markers.length} features ✓` : 'No features yet.',
      ),
      stage(
        'Integration',
        m.integration ? m.integration.marker : null,
        m.integration ? m.integration.test || 'Test not yet defined.' : 'No module-integration section.',
      ),
      stage(
        'Review',
        reviewMk,
        reviewDetail,
        !!stale || (rv && rv.marker === '🚧' && !rp),
        rp ? rp.route : null,
      ),
    ),
  );
}

function viewModule(name) {
  const m = modByName(name);
  if (!m) return notFound(`No module “${name}”`);
  const feats = G.features.filter((f) => f.module === name);
  const byName = new Map(feats.map((f) => [f.name, f]));
  // Same rule as `lifecycle()`: the build order is the roster, so an entry with
  // no docs directory gets a placeholder row rather than being filtered out.
  // `.filter(Boolean)` here is what made an all-⏸ module render as empty — the
  // extractor knows those entries are legitimate and declines to flag them, and
  // "not drift" was implemented as "not present". A placeholder carries what the
  // build-order line holds and nothing else: no plan or status links, no drift
  // flags, no invented state.
  const ordered = m.buildOrder.length
    ? m.buildOrder.map(
        (b) =>
          byName.get(b.name) || {
            name: b.name,
            order: b.order,
            marker: b.marker,
            effectiveMarker: b.marker,
            annotation: b.annotation,
            remaining: b.remaining,
            docsOnDisk: false,
          },
      )
    : feats;
  const extra = feats.filter((f) => !ordered.includes(f));

  const depChips = (list, raw) =>
    list.length
      ? el(
          'div',
          { class: 'chips' },
          list.map((d) => el('a', { class: 'chip', href: `#/module/${encodeURIComponent(d)}` }, d)),
        )
      : el('p', { class: 'muted', style: 'margin:0' }, raw ? raw.replace(/\*/g, '') : 'Nothing.');

  return el(
    'div',
    {},
    pageHead(
      [
        el('a', { href: '#/' }, 'Overview'),
        el('span', {}, '·'),
        el('a', { href: '#/modules' }, 'Modules'),
        el('span', {}, '·'),
        el('span', {}, `#${m.order}`),
      ],
      name,
      m.purpose,
      {
        ident: true,
        aside: el(
          'div',
          { style: 'margin-top:14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap' },
          badge(m.status),
          m.declaredStatus && m.declaredStatus !== m.status
            ? el(
                'span',
                { class: 'eyebrow', title: 'The rollup derives from feature and integration markers' },
                'derived · ',
                el('a', { href: '#/health' }, `index.md declares ${m.declaredStatus}`),
              )
            : null,
        ),
      },
    ),
    el(
      'div',
      { class: 'panel', style: 'margin-bottom:18px' },
      el('div', { class: 'panel-head' }, el('span', { class: 'eyebrow' }, 'Data concern')),
      el(
        'div',
        { class: 'panel-body' },
        m.dataConcern
          ? inlineMd(m.dataConcern, 'docs/architecture.md')
          : el('p', { class: 'muted', style: 'margin:0' }, 'Not stated.'),
      ),
    ),
    el(
      'div',
      { class: 'cols' },
      el(
        'div',
        { class: 'panel' },
        el('div', { class: 'panel-head' }, el('span', { class: 'eyebrow' }, 'Depends on')),
        el('div', { class: 'panel-body' }, depChips(m.dependsOn, m.dependsOnRaw)),
      ),
      el(
        'div',
        { class: 'panel' },
        el('div', { class: 'panel-head' }, el('span', { class: 'eyebrow' }, 'Consumed by')),
        el('div', { class: 'panel-body' }, depChips(m.consumedBy, m.consumedByRaw)),
      ),
    ),
    el(
      'section',
      { class: 'block' },
      el('h2', {}, `Build order · ${ordered.length + extra.length} features`),
      el(
        'div',
        { class: 'panel' },
        el(
          'div',
          { class: 'rows' },
          [...ordered, ...extra].map((f, i) =>
            el(
              // A doc-less entry has nowhere to navigate to, so it is a div.
              // `a.row:hover` is the only anchor-specific styling, so the row
              // reads the same minus the affordance — which is accurate.
              f.docsOnDisk === false ? 'div' : 'a',
              { class: 'row', href: f.docsOnDisk === false ? null : f.route },
              el('span', { class: 'idx' }, String(f.order ?? i + 1).padStart(2, '0')),
              badge(f.effectiveMarker, { bare: true }),
              el('span', { class: 'ident', style: 'min-width:214px' }, f.name),
              el(
                'span',
                { class: 'note grow' },
                // A `Remaining:` clause wins over the plan's own summary: the
                // plan was written before another feature absorbed part of this
                // one's scope, so it overstates what is left to build.
                f.remaining
                  ? el('span', { class: 'shrunk' }, `Remaining: ${plain(f.remaining)}`)
                  : f.docsOnDisk === false
                    ? el('span', { class: 'muted' }, 'planned — no docs yet')
                    : plain((f.status && f.status.headline) || (f.plan && f.plan.purpose) || ''),
              ),
              f.pendingVerification ? el('span', { class: 'tag pend' }, 'checks pending') : null,
            ),
          ),
        ),
      ),
    ),
    lifecycle(m),
    m.integration
      ? el(
          'section',
          { class: 'block' },
          el('h2', {}, 'Module integration'),
          el(
            'div',
            { class: 'panel' },
            el(
              'div',
              { class: 'panel-head' },
              el(
                'span',
                { class: 'ident', style: 'font-size:12.5px' },
                m.integration.test || 'not yet defined',
              ),
              badge(m.integration.marker),
            ),
            el('div', { class: 'panel-body' }, renderMd(m.integration.notes, m.rel, { stripH1: false })),
          ),
        )
      : null,
    m.adrs.length
      ? el(
          'section',
          { class: 'block' },
          el('h2', {}, `Decisions constraining ${name} · ${m.adrs.length}`),
          el(
            'div',
            { class: 'panel' },
            el(
              'div',
              { class: 'rows' },
              m.adrs.map((id) => {
                const a = G.adrs.find((x) => x.id === id);
                return el(
                  'a',
                  { class: 'row', href: `#/adr/${a.num}` },
                  el('span', { class: 'idx', style: 'min-width:62px' }, a.id),
                  el('span', { class: 'note grow', style: 'color:var(--ink-2)' }, a.title),
                  el('span', { class: 'eyebrow' }, a.status),
                );
              }),
            ),
          ),
        )
      : null,
  );
}

function viewFeature(mod, name) {
  const f = featOf(mod, name);
  if (!f) return notFound(`No feature “${mod}/${name}”`);

  const compRows = f.components.map((c) => {
    const nameCell = c.isPath && !c.isPattern
      ? el('a', { href: `/open?path=${encodeURIComponent(c.file)}`, target: '_blank' }, c.file)
      : el('span', {}, c.file);
    return el(
      'tr',
      {},
      el(
        'td',
        { class: 'f' },
        nameCell,
        ' ',
        c.isPattern ? el('span', { class: 'tag pat' }, 'pattern') : null,
        c.exists === false ? el('span', { class: 'tag gone' }, 'missing') : null,
      ),
      el('td', { html: ticks(c.purpose) }),
    );
  });

  const stat = f.status;
  const plan = f.plan;
  // The structured panel above pretty-prints the plan's Components tables, so
  // the body renders without them; any prose in the section is kept.
  const planParts = plan && compRows.length ? withoutComponentsTables(plan.body) : null;

  return el(
    'div',
    {},
    pageHead(
      [
        el('a', { href: '#/modules' }, 'Modules'),
        el('span', {}, '·'),
        el('a', { href: `#/module/${encodeURIComponent(mod)}` }, mod),
        el('span', {}, '·'),
        el('span', {}, f.order ? `#${f.order}` : 'unordered'),
      ],
      name,
      plan ? plan.purpose || plan.preamble : null,
      { ident: true, aside: el('div', { style: 'margin-top:14px' }, badge(f.effectiveMarker)) },
    ),

    // The plan predates any absorption, so where a `Remaining:` clause exists it
    // is the contract for the next pass — said before the plan is shown.
    f.remaining || f.annotation
      ? el(
          'div',
          { class: 'panel shrunk-note', style: 'margin-bottom:18px' },
          el('div', { class: 'panel-head' }, el('span', { class: 'eyebrow' }, 'Scope reduced since planning')),
          el(
            'div',
            { class: 'panel-body' },
            f.remaining
              ? el('p', { style: 'margin:0 0 8px' }, el('b', {}, 'Remaining: '), plain(f.remaining))
              : null,
            el('p', { class: 'muted', style: 'margin:0;font-size:13px' }, plain(f.annotation || '')),
            el(
              'p',
              { class: 'muted', style: 'margin:8px 0 0;font-size:13px' },
              'The plan below was written before this absorption and overstates its own scope.',
            ),
          ),
        )
      : null,

    f.pendingVerification
      ? el(
          'div',
          { class: 'panel pending-note', style: 'margin-bottom:18px' },
          el('div', { class: 'panel-head' }, el('span', { class: 'eyebrow' }, 'Pending verification')),
          el(
            'div',
            { class: 'panel-body' },
            el('p', { style: 'margin:0' }, plain(f.pendingVerification)),
            el(
              'p',
              { class: 'muted', style: 'margin:8px 0 0;font-size:13px' },
              'Agreed criteria not yet checked. A feature with pending verification is 🚧, not ✓.',
            ),
          ),
        )
      : null,

    stat
      ? el(
          'section',
          { class: 'block' },
          el('h2', {}, 'Status'),
          el(
            'div',
            { class: 'panel' },
            el(
              'div',
              { class: 'panel-head' },
              el('span', { class: 'eyebrow' }, 'agent-owned · resumption snapshot'),
              stat.nextMove
                ? el('span', { class: 'ident', style: 'color:var(--bower)' }, plain(stat.nextMove))
                : null,
            ),
            el('div', { class: 'panel-body' }, renderMd(stat.body, stat.rel)),
          ),
        )
      : null,

    compRows.length
      ? el(
          'section',
          { class: 'block' },
          // Carries the `components` anchor when the plan body's own heading
          // was stripped below, so TOC and cross-document links still land.
          el('h2', { id: planParts && planParts.removedHeading ? 'components' : null }, `Components · ${compRows.length}`),
          el(
            'div',
            { class: 'panel' },
            el(
              'table',
              { class: 'data' },
              el('thead', {}, el('tr', {}, el('th', {}, 'File'), el('th', {}, 'Purpose'))),
              el('tbody', {}, compRows),
            ),
          ),
        )
      : null,

    plan
      ? el(
          'section',
          { class: 'block' },
          el('h2', {}, 'Plan'),
          el(
            'div',
            { class: 'split' },
            renderMd(planParts ? planParts.md : plan.body, plan.rel),
            el(
              'aside',
              { class: 'aside' },
              f.adrs.length
                ? el(
                    'div',
                    {},
                    el('div', { class: 'eyebrow' }, 'Decisions cited'),
                    el(
                      'div',
                      { class: 'chips' },
                      f.adrs.map((id) => {
                        const a = G.adrs.find((x) => x.id === id);
                        return el('a', { class: 'chip', href: `#/adr/${a.num}`, title: a.title }, id);
                      }),
                    ),
                  )
                : null,
              tocOf(plan.headings, f.route),
              backlinksOf(plan.rel),
              sourceLink(plan.rel),
              stat ? sourceLink(stat.rel) : null,
            ),
          ),
        )
      : null,
  );
}

let adrFilter = { status: 'accepted', scope: null, module: null, topic: null };

function viewAdrs() {
  const all = G.adrs;
  const uniq = (fn) => [...new Set(all.flatMap(fn))].filter(Boolean).sort();
  const shown = all.filter(
    (a) =>
      (!adrFilter.status || a.status === adrFilter.status) &&
      (!adrFilter.scope || a.scope === adrFilter.scope) &&
      (!adrFilter.module || a.modules.includes(adrFilter.module)) &&
      (!adrFilter.topic || a.topics.includes(adrFilter.topic)),
  );

  const facet = (label, key, values) =>
    el(
      'div',
      { style: 'margin-bottom:10px' },
      el('div', { class: 'eyebrow', style: 'margin-bottom:6px' }, label),
      el(
        'div',
        { class: 'chips' },
        el(
          'button',
          {
            class: `chip ${adrFilter[key] == null ? 'on' : ''}`,
            onclick: () => {
              adrFilter[key] = null;
              render();
            },
          },
          'any',
        ),
        values.map((v) =>
          el(
            'button',
            {
              class: `chip ${adrFilter[key] === v ? 'on' : ''}`,
              onclick: () => {
                adrFilter[key] = v;
                render();
              },
            },
            v,
          ),
        ),
      ),
    );

  return el(
    'div',
    {},
    pageHead(
      [el('a', { href: '#/' }, 'Overview'), el('span', {}, '·'), el('span', {}, 'Decisions')],
      'Architectural decisions',
      'Bodies are immutable once accepted. A reversal is a new ADR that *supersedes* the old; a decision ' +
        'that only scopes an exception *narrows* it, leaving the target accepted. And if an accepted ADR ' +
        'contradicts the code, the ADR is the stale one.',
    ),
    el(
      'div',
      { class: 'panel', style: 'margin-bottom:22px' },
      el(
        'div',
        { class: 'panel-body' },
        facet('Status', 'status', uniq((a) => [a.status])),
        facet('Scope', 'scope', uniq((a) => [a.scope])),
        facet('Module', 'module', uniq((a) => a.modules)),
        facet('Topic', 'topic', uniq((a) => a.topics)),
      ),
    ),
    el(
      'div',
      { class: 'panel' },
      el(
        'div',
        { class: 'panel-head' },
        el('span', { class: 'eyebrow' }, 'Matching decisions'),
        el('span', { class: 'eyebrow' }, `${shown.length} of ${all.length}`),
      ),
      el(
        'div',
        { class: 'rows' },
        shown.length
          ? shown.map((a) =>
              el(
                'a',
                { class: 'row', href: `#/adr/${a.num}` },
                el('span', { class: 'idx', style: 'min-width:60px' }, a.id),
                el('span', { class: 'grow' },
                  el('div', { style: 'color:var(--ink)' }, a.title),
                  el('div', { class: 'eyebrow', style: 'margin-top:3px' },
                    [a.scope || 'unclassified', a.modules.join(' · '), a.date].filter(Boolean).join('   ·   ')),
                ),
                // Relations, because a narrowed ADR is correctly still
                // `accepted` — without this the status column hides it.
                a.narrowedBy.length
                  ? el('span', { class: 'tag narrowed', title: `narrowed by ${a.narrowedBy.join(', ')}` }, 'narrowed')
                  : null,
                a.narrows.length
                  ? el('span', { class: 'tag narrows', title: `narrows ${a.narrows.join(', ')}` }, 'narrows')
                  : null,
                a.status !== 'accepted' ? el('span', { class: 'eyebrow' }, a.status) : null,
              ),
            )
          : el('div', { class: 'panel-body' }, el('p', { class: 'muted' }, 'No decisions match.')),
      ),
    ),
  );
}

function viewAdr(num) {
  const a = adrByNum(num);
  if (!a) return notFound(`No ADR ${num}`);
  const chain = (ids, label) =>
    ids.length
      ? el(
          'div',
          {},
          el('div', { class: 'eyebrow' }, label),
          el(
            'div',
            { class: 'chips' },
            ids.map((id) => {
              const t = G.adrs.find((x) => x.id === id);
              return t
                ? el('a', { class: 'chip', href: `#/adr/${t.num}`, title: t.title }, id)
                : el('span', { class: 'chip' }, `${id} (missing)`);
            }),
          ),
        )
      : null;

  return el(
    'div',
    {},
    pageHead(
      [
        el('a', { href: '#/adrs' }, 'Decisions'),
        el('span', {}, '·'),
        el('span', {}, a.id),
        el('span', {}, '·'),
        el('span', {}, a.status),
      ],
      a.title,
      null,
    ),
    el(
      'div',
      { class: 'split' },
      renderMd(a.body, a.rel),
      el(
        'aside',
        { class: 'aside' },
        el(
          'div',
          {},
          el('div', { class: 'eyebrow' }, 'Frontmatter'),
          el(
            'div',
            { class: 'chips' },
            el('span', { class: 'chip' }, a.status),
            a.scope ? el('span', { class: 'chip' }, `scope: ${a.scope}`) : null,
            a.date ? el('span', { class: 'chip' }, a.date) : null,
          ),
        ),
        a.modules.length
          ? el(
              'div',
              {},
              el('div', { class: 'eyebrow' }, 'Constrains'),
              el(
                'div',
                { class: 'chips' },
                a.modules.map((m) =>
                  el('a', { class: 'chip', href: `#/module/${encodeURIComponent(m)}` }, m),
                ),
              ),
            )
          : null,
        a.topics.length
          ? el(
              'div',
              {},
              el('div', { class: 'eyebrow' }, 'Topics'),
              el('div', { class: 'chips' }, a.topics.map((t) => el('span', { class: 'chip' }, t))),
            )
          : null,
        chain(a.supersedes, 'Supersedes'),
        chain(a.supersededBy, 'Superseded by'),
        // Narrowing leaves both sides accepted: the target's central commitment
        // stands and only the named exception is carved out of it.
        chain(a.narrows, 'Narrows — scopes an exception to'),
        chain(a.narrowedBy, 'Narrowed by — still in force, with an exception'),
        backlinksOf(a.rel),
        sourceLink(a.rel),
      ),
    ),
  );
}

function viewFiles() {
  const entries = Object.entries(G.fileIndex);
  return el(
    'div',
    {},
    pageHead(
      [el('a', { href: '#/' }, 'Overview'), el('span', {}, '·'), el('span', {}, 'Files')],
      'Which feature owns this file?',
      'Built by inverting every plan’s Components table. The docs only go feature → file; ' +
        'this is the direction they cannot answer.',
    ),
    el(
      'div',
      { class: 'panel' },
      el(
        'div',
        { class: 'panel-head' },
        el('input', {
          id: 'fq',
          type: 'search',
          placeholder: 'Filter paths…',
          value: viewFiles.q || '',
          style:
            'font:12.5px var(--f-mono);background:var(--surface-2);color:var(--ink);border:1px solid var(--line);border-radius:3px;padding:6px 9px;flex:1',
          oninput: (e) => {
            viewFiles.q = e.target.value;
            const box = $('#view');
            const sel = box.querySelector('table.data tbody');
            if (sel) sel.replaceWith(fileRows());
          },
        }),
        el('span', { class: 'eyebrow' }, `${entries.length} files`),
      ),
      el(
        'table',
        { class: 'data' },
        el('thead', {}, el('tr', {}, el('th', {}, 'Path'), el('th', {}, 'Claimed by'))),
        fileRows(),
      ),
    ),
  );

  function fileRows() {
    const qq = (viewFiles.q || '').toLowerCase();
    const rows = (qq ? entries.filter(([f]) => f.toLowerCase().includes(qq)) : entries).slice(0, 400);
    return el(
      'tbody',
      {},
      rows.map(([file, owners]) =>
        el(
          'tr',
          {},
          el(
            'td',
            { class: 'f' },
            el('a', { href: `/open?path=${encodeURIComponent(file)}`, target: '_blank' }, file),
          ),
          el(
            'td',
            {},
            el(
              'div',
              { class: 'chips' },
              owners.map((o) =>
                el(
                  'a',
                  { class: 'chip', href: o.route, title: o.purpose },
                  `${o.module}/${o.feature}`,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

function viewSearch(q) {
  const needle = (q || '').toLowerCase();
  const hits = [];
  if (needle.length >= 2) {
    const consider = (title, sub, route, body) => {
      const i = (body || '').toLowerCase().indexOf(needle);
      const inTitle = title.toLowerCase().includes(needle);
      if (i === -1 && !inTitle) return;
      let extract = '';
      if (i !== -1) {
        const from = Math.max(0, i - 70);
        extract = (from ? '…' : '') + body.slice(from, i + needle.length + 110).replace(/\s+/g, ' ') + '…';
      }
      hits.push({ title, sub, route, extract, rank: inTitle ? 0 : 1 });
    };
    for (const d of G.docs) consider(d.title, d.kind, `#/doc/${encodeURIComponent(d.id)}`, d.body);
    for (const a of G.adrs) consider(`${a.id} — ${a.title}`, 'decision', `#/adr/${a.num}`, a.body);
    for (const f of G.features) {
      const body = `${f.plan ? f.plan.body : ''}\n${f.status ? f.status.body : ''}`;
      consider(`${f.module}/${f.name}`, 'feature', f.route, body);
    }
    for (const m of G.modules)
      consider(m.name, 'module', m.route, `${m.purpose}\n${m.dataConcern}\n${m.integration ? m.integration.notes : ''}`);
    hits.sort((a, b) => a.rank - b.rank || a.title.localeCompare(b.title));
  }

  const hl = (s) => {
    if (!s) return '';
    const i = s.toLowerCase().indexOf(needle);
    if (i === -1) return esc(s);
    return `${esc(s.slice(0, i))}<mark>${esc(s.slice(i, i + needle.length))}</mark>${esc(s.slice(i + needle.length))}`;
  };

  return el(
    'div',
    {},
    pageHead(
      [el('a', { href: '#/' }, 'Overview'), el('span', {}, '·'), el('span', {}, 'Search')],
      needle.length < 2 ? 'Search' : `${hits.length} result${hits.length === 1 ? '' : 's'}`,
      needle.length < 2 ? 'Type at least two characters.' : `Matching “${q}” across every document.`,
    ),
    hits.length
      ? el(
          'div',
          { class: 'panel' },
          hits.slice(0, 80).map((h) =>
            el(
              'a',
              { class: 'hit', href: h.route },
              el('div', { class: 'h-t', html: hl(h.title) }),
              el('div', { class: 'eyebrow', style: 'margin-top:2px' }, h.sub),
              h.extract ? el('div', { class: 'h-x', html: hl(h.extract) }) : null,
            ),
          ),
        )
      : null,
  );
}

function notFound(msg) {
  return el(
    'div',
    {},
    pageHead([el('a', { href: '#/' }, 'Overview')], 'Not found', msg),
    el('a', { href: '#/' }, 'Back to the overview'),
  );
}

// ─────────────────────────────────────────────────────── rail + router

function buildRail() {
  const nav = $('#rail-nav');
  nav.textContent = '';
  $('#rail-project').textContent = G.project.name;

  const navLink = ({ href, name, idx, mk }) =>
    el(
      'a',
      { class: 'nav', href, 'data-href': href },
      idx ? el('span', { class: 'idx' }, idx) : null,
      mk ? el('span', { class: 'idx', title: markerMeta(mk).label }, mk) : null,
      el('span', { class: 'name' }, name),
    );

  const group = (label, items) =>
    el(
      'div',
      { class: 'nav-group' },
      label ? el('div', { class: 'eyebrow' }, label) : null,
      items.map(navLink),
    );

  const errs = G.health.length;
  nav.append(
    group('State', [
      { href: '#/', name: 'overview' },
      G.scope ? { href: '#/scope', name: `criteria · ${G.scope.satisfied}/${G.scope.derivable}` } : null,
      { href: '#/health', name: `health · ${errs}` },
      { href: '#/files', name: `files · ${G.counts.indexedFiles}` },
      G.adoption ? { href: '#/adoption', name: `adoption · ${G.adoption.openItems.length}` } : null,
    ].filter(Boolean)),
  );

  const doc = (id) => {
    const d = G.docs.find((x) => x.id === id);
    return d ? { href: `#/doc/${encodeURIComponent(id)}`, name: id.split('/').pop() } : null;
  };
  nav.append(
    group(
      'Core documents',
      ['index', 'scope', 'architecture', 'constitution', 'ui', 'design/problem-space']
        .map(doc)
        .filter(Boolean),
    ),
  );

  nav.append(
    group('Decisions', [
      { href: '#/adrs', name: `adrs · ${G.counts.adrs}` },
      ...(G.docs.some((d) => d.id === 'adr-index') ? [{ href: '#/doc/adr-index', name: 'adr/index' }] : []),
    ]),
  );

  nav.append(
    group(
      'Modules',
      G.modules.map((m, i) => ({
        href: m.route,
        name: m.name,
        idx: String(i + 1).padStart(2, '0'),
        mk: m.status,
      })),
    ),
  );

  // ── Everything above here is Bower's. Below the break is the project's own
  // material, which the framework neither writes nor reconciles. Folded by
  // folder so a project with a large docs/ tree does not bury the rail.
  const projectDocs = G.docs.filter((d) => d.origin === 'project');
  if (!projectDocs.length) return;

  const byFolder = new Map();
  for (const d of projectDocs) {
    const folder = d.id.includes('/') ? d.id.split('/').slice(0, -1).join('/') : '';
    if (!byFolder.has(folder)) byFolder.set(folder, []);
    byFolder.get(folder).push(d);
  }
  // Loose files at the root of docs/ first, then folders alphabetically.
  const folders = [...byFolder.keys()].sort((a, b) => (a === '' ? -1 : b === '' ? 1 : a.localeCompare(b)));

  nav.append(
    el(
      'div',
      { class: 'nav-break' },
      el('div', { class: 'eyebrow' }, 'Project docs'),
      el(
        'p',
        { class: 'nav-break-note' },
        'The project’s own material. No Bower schema or convention applies.',
      ),
    ),
  );

  const openKey = (folder) => `bower-nav-open:${folder}`;
  for (const folder of folders) {
    const items = byFolder.get(folder).map((d) => ({
      href: `#/doc/${encodeURIComponent(d.id)}`,
      name: d.id.split('/').pop(),
    }));
    // Loose root files are never folded — there is nothing to collapse into.
    if (folder === '') {
      nav.append(group(null, items));
      continue;
    }
    // Remember the fold state, and open regardless if the current page is inside.
    const active = items.some((i) => i.href === (location.hash || '#/'));
    const stored = localStorage.getItem(openKey(folder));
    const fold = el(
      'details',
      { class: 'nav-fold', open: active || stored === '1' || null },
      el(
        'summary',
        {},
        el('span', { class: 'name' }, folder),
        el('span', { class: 'count' }, items.length),
      ),
      el('div', { class: 'nav-group' }, items.map(navLink)),
    );
    fold.addEventListener('toggle', () => localStorage.setItem(openKey(folder), fold.open ? '1' : '0'));
    nav.append(fold);
  }
}

function markCurrent() {
  const h = location.hash || '#/';
  for (const a of document.querySelectorAll('a.nav')) {
    const href = a.dataset.href;
    a.toggleAttribute('aria-current', href === h);
    if (href === h) a.setAttribute('aria-current', 'page');
    else a.removeAttribute('aria-current');
  }
}

function render() {
  const hash = (location.hash || '#/').slice(1);
  // In-page anchors ride along as a second '#': `#/doc/constitution#some-heading`.
  // Strip the fragment before routing — the hashchange handler scrolls to it.
  const parts = hash.split('#')[0].split('/').filter(Boolean).map(decodeURIComponent);
  const box = $('#view');
  let node;

  if (parts.length === 0) node = viewOverview();
  else if (parts[0] === 'health') node = viewHealth();
  else if (parts[0] === 'scope') node = viewScope();
  else if (parts[0] === 'adoption') node = viewAdoption();
  else if (parts[0] === 'files') node = viewFiles();
  else if (parts[0] === 'modules') node = viewModules();
  else if (parts[0] === 'adrs') node = viewAdrs();
  else if (parts[0] === 'adr' && parts[1]) node = viewAdr(parts[1]);
  else if (parts[0] === 'doc' && parts[1]) node = viewDoc(parts.slice(1).join('/'));
  else if (parts[0] === 'review' && parts[1]) node = viewReview(parts[1]);
  else if (parts[0] === 'module' && parts[2]) node = viewFeature(parts[1], parts[2]);
  else if (parts[0] === 'module' && parts[1]) node = viewModule(parts[1]);
  else if (parts[0] === 'search') node = viewSearch(parts.slice(1).join('/'));
  else node = notFound(hash);

  box.textContent = '';
  box.append(node);
  markCurrent();
  document.title = `${G.project.name} — Bower`;
}

// ────────────────────────────────────────────────────────────── boot

async function load(firstRun) {
  const res = await fetch(HOST.graphUrl, { cache: 'no-store' });
  G = await res.json();
  $('#rev').textContent = `rev ${G.rev ?? 0}`;
  buildRail();
  if (firstRun) render();
  else {
    const y = window.scrollY;
    render();
    window.scrollTo(0, y);
  }
}

function wireTheme() {
  const btn = $('#theme');
  const label = () => {
    const explicit = document.documentElement.dataset.theme;
    const dark = explicit
      ? explicit === 'dark'
      : window.matchMedia('(prefers-color-scheme: dark)').matches;
    $('[data-theme-label]').textContent = dark ? 'Light' : 'Dark';
  };
  const saved = localStorage.getItem('bower-theme');
  if (saved) document.documentElement.dataset.theme = saved;
  label();
  btn.addEventListener('click', () => {
    const explicit = document.documentElement.dataset.theme;
    const dark = explicit
      ? explicit === 'dark'
      : window.matchMedia('(prefers-color-scheme: dark)').matches;
    const next = dark ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    localStorage.setItem('bower-theme', next);
    label();
  });
}

function wireSearch() {
  const input = $('#q');
  let t;
  input.addEventListener('input', () => {
    clearTimeout(t);
    t = setTimeout(() => {
      const v = input.value.trim();
      location.hash = v ? `#/search/${encodeURIComponent(v)}` : '#/';
    }, 200);
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === '/' && document.activeElement !== input) {
      e.preventDefault();
      input.focus();
      input.select();
    }
    if (e.key === 'Escape' && document.activeElement === input) {
      input.value = '';
      input.blur();
    }
  });
}

function wireLive() {
  // ?static=1 skips the live connection, so headless captures and any future
  // static export reach a settled page instead of an open stream.
  if (new URLSearchParams(location.search).has('static')) return;
  try {
    const es = new EventSource(HOST.eventsUrl);
    es.addEventListener('reload', async () => {
      await load(false);
      toast('docs changed — reloaded');
    });
    // The server re-extracted and failed; the graph on screen is the last
    // good one. Said plainly, rather than a "reloaded" toast over stale data.
    es.addEventListener('extract-error', (e) => {
      let msg = '';
      try {
        msg = JSON.parse(e.data);
      } catch {
        /* the message is a nicety; the warning is the point */
      }
      toast(`extract failed — showing the last good graph${msg ? `: ${msg}` : ''}`);
    });
  } catch {
    /* live reload is a nicety */
  }
}

// Expose the real view functions to the zero-dependency acceptance harness.
// Browser execution has no CommonJS `module`, so this branch costs the shell
// nothing and keeps renderer tests from becoming source-text assertions.
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    openHref,
    setGraphForTest: (graph) => {
      G = graph;
    },
    viewReview,
  };
} else {
  window.addEventListener('hashchange', () => {
    render();
    const frag = location.hash.split('#')[2];
    window.scrollTo(0, 0);
    if (frag) {
      const target = document.getElementById(frag);
      if (target) target.scrollIntoView();
    }
  });

  wireTheme();
  wireSearch();
  load(true)
    .then(wireLive)
    .catch((err) => {
      $('#view').textContent = '';
      $('#view').append(
        el('div', { class: 'panel' }, el('div', { class: 'panel-body' },
          el('p', {}, 'Could not load the graph.'),
          el('pre', { class: 'pre-plain' }, String(err)))),
      );
    });
}
