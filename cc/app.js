// Command Center. All content is read at runtime from .colaberry/*.json.
// The only data in this file is SAMPLE, shown in Sample mode and always labelled.
const TABS = [
  ['overview', 'Overview'], ['outcomes', 'Outcomes'], ['users', 'Users and use case'],
  ['guardrails', 'Guardrails'], ['systems', 'Systems'], ['projects', 'Project management'],
  ['agents', 'AI agents'], ['knowledge', 'Knowledge base'], ['data', 'Data model'],
];

const SAMPLE = {
  plan: {
    project: { name: 'Sample Project', descriptor: 'Made-up example' },
    schedule: { build_start: '2026-09-01', build_end: '2026-10-01', demo_day: '2026-10-08', demo_release_key: 'r0' },
    derived: {
      measures: [{ id: 'M-1', statement: 'Sample: reduce time to publish a video' }],
      roles: ['sample editor', 'sample reviewer'],
      guardrails: [{ id: 'REQ-S1', statement: 'Sample: a human approves everything before publishing' }],
      systems: ['Sample Video Site'],
    },
    releases: [
      { key: 'r0', title: 'Sample release one', starts_on: '2026-09-01', ends_on: '2026-09-20', story_ids: ['S-1', 'S-2'], is_demo_target: true },
      { key: 'r1', title: 'Sample release two', starts_on: '2026-09-21', ends_on: '2026-10-01', story_ids: ['S-3'], is_demo_target: false },
    ],
    requirements: [
      { id: 'REQ-S1', statement: 'Sample: a human approves everything before publishing', kind: 'SAFE', priority: 'must', fulfilled_by: ['S-2'] },
      { id: 'REQ-S2', statement: 'Sample: generate ideas', kind: 'FUNC', priority: 'must', fulfilled_by: ['S-1'] },
      { id: 'REQ-S3', statement: 'Sample: an uncovered requirement', kind: 'FUNC', priority: 'must', fulfilled_by: [] },
    ],
    stories: [
      { id: 'S-1', title: 'Sample story one', release: 'r0', narrative: 'As a sample editor, I want ideas, so that I save time.', due_on: '2026-09-15', due_baseline_on: '2026-09-10', owner: 'Sample owner', acceptance_criteria: ['Sample criterion'] },
      { id: 'S-2', title: 'Sample story two', release: 'r0', narrative: 'As a sample reviewer, I want to approve, so that nothing slips out.', due_on: '2026-09-20', due_baseline_on: '2026-09-20', owner: 'Sample owner', acceptance_criteria: ['Sample criterion'] },
      { id: 'S-3', title: 'Sample story three', release: 'r1', narrative: 'As a sample editor, I want reports.', due_on: '2026-10-01', due_baseline_on: '2026-10-01', owner: 'Other owner', acceptance_criteria: [] },
    ],
    agents: [],
  },
  progress: {
    totals: { stories_verified: 1, stories_total: 3, criteria_passed: 1, criteria_total: 2, points_awarded: 5 },
    stories: [
      { id: 'S-1', verification: { state: 'verified', commit: 'sample0', points: 5 } },
      { id: 'S-2', verification: { state: 'in_progress' } },
      { id: 'S-3', verification: { state: 'not_started' } },
    ],
  },
  manifest: { generated_at: new Date().toISOString() },
};

const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const safe = (f, d) => { try { return f(); } catch { return d; } };
let mode = safe(() => localStorage.getItem('cc-mode'), null) || 'real';
let real = { plan: null, progress: null, manifest: null, model: null, errors: [] };

async function load() {
  for (const k of ['plan', 'progress', 'manifest']) {
    try {
      const r = await fetch(`.colaberry/${k}.json`, { cache: 'no-store' });
      if (!r.ok) throw new Error(r.status);
      real[k] = await r.json();
    } catch (e) { real.errors.push(`.colaberry/${k}.json`); }
  }
  normalise(real.plan);
  try { real.model = await (await fetch('cc/datamodel.json')).json(); } catch { /* optional */ }
}
// The real plan names some fields differently from the sample; accept both, never invent values.
function normalise(plan) {
  if (!plan) return;
  (plan.releases || []).forEach((r) => { r.title ??= r.name; });
  (plan.stories || []).forEach((st) => { st.acceptance_criteria ??= st.acceptance; st.owner ??= st.owner_agent; });
}
// Stories present in progress but not in the plan (e.g. STORY-000, the Command Center itself).
const extraStories = () => (D().progress?.stories || []).filter((x) => !stories().some((s) => s.id === x.id))
  .map((x) => ({ id: x.id, title: x.id === 'STORY-000' ? 'Build the Command Center' : '(progress only)', release: x.release, narrative: 'Tracked in progress.json only; not part of the plan.', acceptance_criteria: (x.criteria || []).map((c) => c.text), progressOnly: true }));
const D = () => (mode === 'sample' ? SAMPLE : real);

// ---- helpers over the data ----
const planOf = () => D().plan || {};
const derived = () => planOf().derived || {};
const stories = () => planOf().stories || [];
const reqs = () => planOf().requirements || [];
const stateOf = (id) => {
  const s = (D().progress?.stories || []).find((x) => x.id === id);
  return s?.verification?.state || 'not_started';
};
const verOf = (id) => (D().progress?.stories || []).find((x) => x.id === id)?.verification || {};
const roleName = (r) => (typeof r === 'string' ? r : r.name || r.role || r.id || JSON.stringify(r));
const tag = () => (mode === 'sample' ? '<span class="tag">SAMPLE</span>' : '');
const card = (k, v, s, href) => `<a class="card ${mode === 'sample' ? 'sample' : ''}" href="${href}"><div class="k">${esc(k)}${tag()}</div><div class="v">${v}</div><div class="s">${esc(s)}</div></a>`;
const empty = (m) => `<div class="empty">${m}</div>`;
const back = (tab, label) => `<a class="back" href="#/${tab}">← ${esc(label)}</a>`;
const table = (head, rows) => `<div class="scroll"><table><tr>${head.map((h) => `<th>${esc(h)}</th>`).join('')}</tr>${rows.join('')}</table></div>`;
const tr = (cells) => `<tr>${cells.map((c) => `<td>${c}</td>`).join('')}</tr>`;
const link = (href, t) => `<a href="${href}">${esc(t)}</a>`;
const needData = () => !D().plan || !D().progress;

function asOf() {
  const m = D().manifest, el = $('#asof');
  el.className = 'asof';
  if (!m || !m.generated_at) {
    el.className = 'asof warn';
    el.textContent = 'Data as of: unknown — manifest not found. Sync from the portal to refresh.';
    return;
  }
  const t = new Date(m.generated_at), days = (Date.now() - t) / 864e5;
  const abs = t.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
  const n = Math.floor(days);
  let txt = `Data as of ${abs} (${days < 1 ? 'today' : n + ' day' + (n === 1 ? '' : 's') + ' ago'})`;
  if (days > 7) { el.classList.add('warn'); txt += ' — over a week old, sync from the portal to refresh'; }
  el.textContent = txt + (mode === 'sample' ? ' · sample' : '');
}

function notSynced() {
  return empty(`<b>Data not synced yet.</b> Missing: ${real.errors.map(esc).join(', ')}.<br>The platform writes these files when you sync. Nothing is shown until it does — no numbers are invented.<br>(If you opened this file directly, serve it over http, e.g. <code>python -m http.server</code>.)`);
}

// ---- 1 Overview ----
function overview(detail) {
  const { plan, progress } = D();
  if (detail) return overviewDetail(detail);
  let h = '<h1>Overview</h1>';
  if (!plan || !progress) return h + notSynced();
  const p = plan.project || {}, s = plan.schedule || {}, t = progress.totals || {};
  h += `<p class="lead">${esc(p.name || 'Unnamed project')}${p.descriptor ? ' — ' + esc(p.descriptor) : ''}</p><div class="grid">`;
  h += card('Stories verified', `${esc(t.stories_verified ?? '–')} of ${esc(t.stories_total ?? '–')}`, 'from progress.totals', '#/overview/stories');
  h += card('Criteria passed', `${esc(t.criteria_passed ?? '–')} of ${esc(t.criteria_total ?? '–')}`, 'from progress.totals', '#/overview/criteria');
  h += card('Points awarded', esc(t.points_awarded ?? '–'), 'from progress.totals', '#/overview/points');
  h += card('Demo release', esc(s.demo_release_key || 'Not set'), s.demo_day ? `Demo day ${s.demo_day}` : 'no demo day in plan', '#/overview/schedule');
  h += card('Build window', esc(s.build_start && s.build_end ? `${s.build_start} → ${s.build_end}` : 'Not scheduled'), (s.build_start ? 'from plan.schedule' : 'plan.schedule is empty'), '#/overview/schedule');
  h += card('Live systems', 'Not checked', 'nothing here can confirm a connection', '#/overview/live');
  return h + '</div>';
}
function overviewDetail(which) {
  const titles = { stories: 'Stories verified', criteria: 'Criteria passed', points: 'Points awarded', schedule: 'Schedule', live: 'What is live' };
  let h = back('overview', 'Overview') + `<h1>${esc(titles[which] || which)}</h1>`;
  if (needData()) return h + notSynced();
  if (which === 'schedule' && !Object.keys(planOf().schedule || {}).length) return h + empty('The plan carries no schedule (no build window, demo day or demo release). Nothing is invented; it appears here once the plan has one.');
  if (which === 'schedule') return h + `<table>${Object.entries(planOf().schedule || {}).map(([k, v]) => `<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join('')}</table>`;
  if (which === 'live') return h + empty('<span class="dot"></span>Not checked from here. Connection status is a fact about the running system, which these files cannot report. See the Systems tab.');
  const rows = [...stories(), ...extraStories()].map((st) => tr([link(`#/projects/${st.id}`, st.id), esc(st.title), esc(st.release ?? '—'), esc(stateOf(st.id)), esc(verOf(st.id).points ?? '')]));
  return h + (rows.length ? table(['ID', 'Title', 'Release', 'State', 'Points'], rows) : empty('No stories in the plan.'));
}

// ---- 2 Outcomes ----
function outcomes(id) {
  const ms = derived().measures || [];
  if (id) {
    const m = ms.find((x) => x.id === id);
    return back('outcomes', 'Outcomes') + `<h1>${esc(id)}</h1>` + (m ? `<p>${esc(m.statement)}</p>${empty('No numeric target, baseline or current value has been recorded for this measure. Nothing is shown rather than a guess.')}` : empty('No such measure in the plan.'));
  }
  let h = '<h1>Outcomes</h1><p class="lead">The numbers this has to move.</p>';
  if (needData()) return h + notSynced();
  h += empty('The plan carries no numeric target yet, so no measure shows a value. A card per measure appears below when the plan has any.') ;
  return h + `<div class="grid" style="margin-top:12px">${ms.map((m) => card(m.id, 'No target', m.statement, `#/outcomes/${m.id}`)).join('')}</div>`;
}

// ---- 3 Users ----
function users(id) {
  const roles = derived().roles || [];
  if (id) {
    const name = decodeURIComponent(id);
    const own = stories().filter((s) => (s.narrative || '').toLowerCase().includes(name.toLowerCase()));
    return back('users', 'Users') + `<h1>${esc(name)}</h1>` + (own.length ? table(['Story', 'Narrative'], own.map((s) => tr([link(`#/projects/${s.id}`, s.id), esc(s.narrative)]))) : empty('No story narrative names this role.'));
  }
  let h = '<h1>Users and use case</h1><p class="lead">Who this is for, from the roles in your stories.</p>';
  if (needData()) return h + notSynced();
  if (!roles.length) return h + empty('No roles in the plan yet.');
  return h + `<div class="grid">${roles.map((r) => { const n = roleName(r); const c = stories().filter((s) => (s.narrative || '').toLowerCase().includes(n.toLowerCase())).length; return card('Role', esc(n), `${c} stories`, `#/users/${encodeURIComponent(n)}`); }).join('')}</div>`;
}

// ---- 4 Guardrails ----
function verdict(id) {
  const req = reqs().find((r) => r.id === id);
  const ids = req?.fulfilled_by || [];
  if (!ids.length) return ['No story enforces this yet — a promise made and not yet kept.', false];
  const bad = ids.filter((s) => stateOf(s) !== 'verified');
  return bad.length ? [`A promise made and not yet kept: ${bad.join(', ')} not verified.`, false] : [`Enforced: ${ids.join(', ')} verified.`, true];
}
function guardrails(id) {
  const gs = derived().guardrails || [];
  if (id) {
    const g = gs.find((x) => x.id === id);
    if (!g) return back('guardrails', 'Guardrails') + empty('No such guardrail.');
    const ids = reqs().find((r) => r.id === id)?.fulfilled_by || [];
    return back('guardrails', 'Guardrails') + `<h1>${esc(id)}</h1><p>${esc(g.statement)}</p><p><b>${esc(verdict(id)[0])}</b></p>` +
      (ids.length ? table(['Story', 'Title', 'State'], ids.map((s) => tr([link(`#/projects/${s}`, s), esc(stories().find((x) => x.id === s)?.title), esc(stateOf(s))]))) : empty('No stories are linked to this requirement.'));
  }
  let h = '<h1>Guardrails</h1><p class="lead">What must never happen.</p>';
  if (needData()) return h + notSynced();
  if (!gs.length) return h + empty('No SAFE requirement in the plan — worth fixing before building further.');
  return h + `<div class="grid">${gs.map((g) => { const [t, ok] = verdict(g.id); return card(g.id, ok ? 'Enforced' : 'Not yet kept', g.statement + ' — ' + t, `#/guardrails/${g.id}`); }).join('')}</div>`;
}

// ---- 5 Systems ----
function systems(name) {
  const ss = derived().systems || [];
  if (name) {
    const n = decodeURIComponent(name);
    return back('systems', 'Systems') + `<h1>${esc(n)}</h1><p><span class="dot"></span>Not checked from here · last checked: never</p>` + empty('This repo only knows the name. Whether it is connected is a fact about the running system; the indicator stays grey until that system reports.');
  }
  let h = '<h1>Systems</h1><p class="lead">What this connects to.</p>';
  if (needData()) return h + notSynced();
  if (!ss.length) return h + empty('No systems named in the plan.');
  return h + table(['System', 'Status', 'Last checked'], ss.map((s) => tr([link(`#/systems/${encodeURIComponent(roleName(s))}`, roleName(s)), '<span class="dot"></span>not checked from here', 'never'])));
}

// ---- 6 Project management ----
const day = (s) => Date.parse(s) / 864e5;
function projects(id) {
  if (id) {
    const st = stories().find((s) => s.id === id) || extraStories().find((s) => s.id === id);
    if (!st) return back('projects', 'Project management') + empty('No such story in the plan.');
    const v = verOf(id);
    const crit = progressCriteria(id);
    return back('projects', 'Project management') + `<h1>${esc(st.id)} — ${esc(st.title)}</h1><p>${esc(st.narrative)}</p>` +
      `<table><tr><th>Release</th><td>${esc(st.release ?? '—')}</td></tr><tr><th>Due (current)</th><td>${esc(st.due_on || 'not set in plan')}</td></tr><tr><th>Due (first given)</th><td>${esc(st.due_baseline_on || 'not set in plan')}</td></tr><tr><th>State</th><td>${esc(stateOf(id))}</td></tr><tr><th>Commit</th><td>${esc(v.commit || 'none')}</td></tr><tr><th>Points</th><td>${esc(v.points ?? 'none')}</td></tr></table>` +
      '<h2>Acceptance criteria</h2>' + ((st.acceptance_criteria || []).length ? `<ul>${(st.acceptance_criteria).map((c) => `<li>${esc(typeof c === 'string' ? c : c.text)}${crit(c)}</li>`).join('')}</ul>` : empty('No criteria in the plan.'));
  }
  let h = '<h1>Project management</h1>';
  if (needData()) return h + notSynced();
  const rel = planOf().releases || [], sc = planOf().schedule || {};
  const dated = rel.filter((r) => r.starts_on && r.ends_on);
  h += sc.build_start ? `<p class="lead">Build ${esc(sc.build_start)} → ${esc(sc.build_end)}; demo day ${esc(sc.demo_day)}. The week between build end and demo day is demo prep. Releases after the demo target are the roadmap.</p>` : empty('The plan carries no schedule or release dates, so there is no Gantt to draw. Releases are listed below by build week; no dates are invented.') + '<br>';
  if (dated.length) {
    const lo = Math.min(...dated.map((r) => day(r.starts_on)), sc.build_start ? day(sc.build_start) : Infinity);
    const hi = Math.max(...dated.map((r) => day(r.ends_on)), sc.demo_day ? day(sc.demo_day) : -Infinity);
    const span = Math.max(hi - lo, 1);
    h += '<div class="gantt">' + dated.map((r) => {
      const l = ((day(r.starts_on) - lo) / span) * 100, w = Math.max(((day(r.ends_on) - day(r.starts_on)) / span) * 100, 1.5);
      return `<div class="grow"><span class="glabel">${link(`#/projects/release/${r.key}`, r.key)} ${esc(r.title)}${r.is_demo_target ? ' <b>(demo target)</b>' : ' <i>(roadmap)</i>'}${tag()}</span><div class="gtrack"><div class="gbar ${r.is_demo_target ? 'demo' : ''}" style="left:${l}%;width:${w}%">${esc(r.starts_on)} → ${esc(r.ends_on)}</div></div></div>`;
    }).join('') + '</div>';
  } else if (rel.length) {
    h += table(['Release', 'Name', 'Weeks', 'Stories', 'Goal'], rel.map((r) => tr([link(`#/projects/release/${r.key}`, r.key), esc(r.title), `${esc(r.week_start ?? '?')}–${esc(r.week_end ?? '?')}`, (r.story_ids || []).length, esc(r.goal || '')])));
  } else h += empty('No releases in the plan.');
  const rows = stories().map((s) => {
    const slip = s.due_on && s.due_baseline_on ? Math.round(day(s.due_on) - day(s.due_baseline_on)) : null;
    return tr([link(`#/projects/${s.id}`, s.id), esc(s.title), esc(s.release), esc(s.due_on || 'not set'), esc(s.due_baseline_on || 'not set'), slip == null ? '—' : slip > 0 ? `<b>+${slip}d slipped</b>` : 'none', esc(stateOf(s.id))]);
  });
  return h + '<h2>Tasks</h2>' + (rows.length ? table(['ID', 'Task', 'Release', 'Due', 'First due', 'Slippage', 'State'], rows) : empty('No stories in the plan.'));
}
function progressCriteria(id) {
  const st = (D().progress?.stories || []).find((x) => x.id === id);
  const cs = st?.criteria || [];
  return (c) => { const t = typeof c === 'string' ? c : c.text; const m = cs.find((x) => x.text === t); return m ? (m.passed ? ' ✔' : ' ✘') : ''; };
}
function releaseDetail(key) {
  const r = (planOf().releases || []).find((x) => x.key === key);
  if (!r) return back('projects', 'Project management') + empty('No such release.');
  return back('projects', 'Project management') + `<h1>${esc(r.key)} — ${esc(r.title)}</h1><p>${r.starts_on ? esc(r.starts_on) + ' → ' + esc(r.ends_on) : 'no dates in plan (build weeks ' + esc(r.week_start ?? '?') + '–' + esc(r.week_end ?? '?') + ')'}${r.is_demo_target ? ' · demo target' : ''}</p>${r.goal ? `<p><b>Goal:</b> ${esc(r.goal)}</p>` : ''}${r.demo ? `<p><b>Demo:</b> ${esc(r.demo)}</p>` : ''}` +
    table(['Story', 'Title', 'State'], (r.story_ids || []).map((s) => tr([link(`#/projects/${s}`, s), esc(stories().find((x) => x.id === s)?.title), esc(stateOf(s))])));
}

// ---- 7 Agents ----
const OWNER = (s) => s.owner || s.owner_name || s.owned_by || s.agent || null;
function agentCards() {
  const ag = planOf().agents || [];
  if (ag.length) return { scoped: true, list: ag.map((a) => ({ name: a.name, a, owns: a.owns || [] })) };
  const by = {};
  stories().forEach((s) => { const o = OWNER(s); if (o) (by[o] ||= []).push(s.id); });
  return { scoped: false, list: Object.entries(by).map(([name, owns]) => ({ name, a: null, owns })) };
}
function agents(name) {
  const { scoped, list } = agentCards();
  if (name) {
    const n = decodeURIComponent(name), x = list.find((l) => l.name === n);
    if (!x) return back('agents', 'AI agents') + empty('No such agent or owner.');
    const a = x.a || {};
    const row = (k, v) => `<tr><th>${k}</th><td>${v}</td></tr>`;
    return back('agents', 'AI agents') + `<h1>${esc(n)}</h1><table>` +
      (scoped ? row('Purpose', esc(a.purpose)) + row('Trigger', esc(`${a.trigger_type || ''} ${a.trigger || ''}`)) + row('Autonomy', esc(a.autonomy_level)) + row('Approval gates', esc(JSON.stringify(a.approval_gates ?? '')))
        + row('Escalation', esc(JSON.stringify(a.escalation_rules ?? ''))) + row('Inputs / outputs', esc(JSON.stringify([a.inputs, a.outputs]))) : '') +
      row('Skills', (a.skills || []).length ? esc(a.skills.join(', ')) : 'no skills registered yet') + row('Runs', 'no runs recorded') +
      row('Owns', x.owns.map((s) => link(`#/projects/${s}`, s)).join(', ') || 'nothing') + '</table>';
  }
  let h = '<h1>AI agents</h1>';
  if (needData()) return h + notSynced();
  if (!list.length) return h + empty('No agents in the plan and no story owners to show. Nothing is invented.');
  if (!scoped) h += '<div class="banner">The plan has no scoped agent roster yet. These are <b>story owners</b>, not scoped AI agents — a job title is not an agent.</div>';
  return h + `<div class="grid">${list.map((x) => card(scoped ? 'Agent' : 'Owner', esc(x.name), `${x.owns.length} stories · no runs recorded · no skills registered yet`, `#/agents/${encodeURIComponent(x.name)}`)).join('')}</div>`;
}

// ---- 8 Knowledge base ----
let notes = safe(() => JSON.parse(localStorage.getItem('cc-notes') || '[]'), []);
function knowledge(id, extra) {
  if (id === 'req') {
    const r = reqs().find((x) => x.id === extra);
    if (!r) return back('knowledge', 'Knowledge base') + empty('No such requirement.');
    return back('knowledge', 'Knowledge base') + `<h1>${esc(r.id)}</h1><p>${esc(r.statement)}</p><p>${esc(r.kind)} · ${esc(r.priority)} · ${esc(r.cluster || 'no cluster')}</p>` +
      ((r.fulfilled_by || []).length ? table(['Story', 'State'], r.fulfilled_by.map((s) => tr([link(`#/projects/${s}`, s), esc(stateOf(s))]))) : empty('Not fulfilled by any story.'));
  }
  let h = '<h1>Knowledge base</h1>';
  if (needData()) return h + notSynced();
  h += '<h2>Traceability</h2>' + table(['Requirement', 'Kind', 'Priority', 'Stories', 'Verified?'], reqs().map((r) => {
    const f = r.fulfilled_by || [], gap = !f.length;
    const ok = f.length && f.every((s) => stateOf(s) === 'verified');
    return tr([link(`#/knowledge/req/${r.id}`, r.id) + ' ' + esc(r.statement), esc(r.kind), esc(r.priority), gap ? (r.priority === 'must' ? '<b>GAP — none</b>' : 'none') : f.map((s) => link(`#/projects/${s}`, s)).join(', '), gap ? 'no' : ok ? 'yes' : 'not yet']);
  }));
  h += `<h2>Notes ${tag()}</h2><p class="lead">Kept in this browser only.</p><div id="notes">${notes.map((n) => `<p>• ${esc(n)}</p>`).join('') || empty('No notes yet.')}</div><form id="nf"><input id="ni" placeholder="Add a note"><button>Add</button></form>`;
  h += `<h2>Ask the data</h2><div id="chat" class="chat"></div><form id="cf"><input id="ci" placeholder="Ask about requirements, stories, roles, systems…"><button>Ask</button></form>`;
  return h;
}
function answer(q) {
  const words = q.toLowerCase().split(/\W+/).filter((w) => w.length > 2 && !['the', 'what', 'which', 'and', 'for', 'how', 'who', 'are', 'does'].includes(w));
  const hay = [];
  reqs().forEach((r) => hay.push([`${r.id}: ${r.statement} (${r.kind}, ${r.priority}; stories: ${(r.fulfilled_by || []).join(', ') || 'none'})`, 'Knowledge base']));
  stories().forEach((s) => hay.push([`${s.id}: ${s.title} — ${s.release}, due ${s.due_on}, ${stateOf(s.id)}`, 'Project management']));
  (derived().guardrails || []).forEach((g) => hay.push([`${g.id}: ${g.statement} — ${verdict(g.id)[0]}`, 'Guardrails']));
  (derived().roles || []).forEach((r) => hay.push([`Role: ${roleName(r)}`, 'Users and use case']));
  (derived().systems || []).forEach((s) => hay.push([`System: ${roleName(s)} — not checked from here`, 'Systems']));
  (derived().measures || []).forEach((m) => hay.push([`${m.id}: ${m.statement} — no target set`, 'Outcomes']));
  (planOf().releases || []).forEach((r) => hay.push([`Release ${r.key}: ${r.title}, ${r.starts_on} → ${r.ends_on}`, 'Project management']));
  const hits = hay.map(([t, tab]) => [words.filter((w) => t.toLowerCase().includes(w)).length, t, tab]).filter((x) => x[0] > 0).sort((a, b) => b[0] - a[0]).slice(0, 4);
  if (!words.length || !hits.length) return "I can't answer that from this project's data.";
  return hits.map((h) => `${h[1]}  [from: ${h[2]}]`).join('\n');
}
function knowledgeWire() {
  const nf = $('#nf'), cf = $('#cf');
  if (nf) nf.onsubmit = (e) => { e.preventDefault(); const v = $('#ni').value.trim(); if (!v) return; notes.push(v); safe(() => localStorage.setItem('cc-notes', JSON.stringify(notes))); render(); };
  if (cf) cf.onsubmit = (e) => { e.preventDefault(); const q = $('#ci').value.trim(); if (!q) return; $('#chat').innerHTML += `<p><b>You:</b> ${esc(q)}</p><p style="white-space:pre-wrap"><b>Answer${mode === 'sample' ? ' (sample data)' : ''}:</b> ${esc(answer(q))}</p>`; $('#ci').value = ''; };
}

// ---- 9 Data model ----
function dataModel(name) {
  const m = real.model;
  let h = '<h1>Data model</h1>';
  if (!m) return h + empty('No proposed model found (cc/datamodel.json).');
  if (name) {
    const t = m.tables.find((x) => x.name === name);
    if (!t) return back('data', 'Data model') + empty('No such table.');
    return back('data', 'Data model') + `<h1>${esc(t.name)}</h1><p>Derived from ${t.from.map((r) => link(`#/knowledge/req/${r}`, r)).join(', ')}</p><h2>Fields</h2><ul>${t.fields.map((f) => `<li>${esc(f)}</li>`).join('')}</ul><h2>Relationships</h2>` + (t.relations.length ? `<ul>${t.relations.map((f) => `<li>${esc(f)}</li>`).join('')}</ul>` : empty('None yet.'));
  }
  return h + '<div class="banner"><b>Proposal only.</b> No tables exist anywhere yet. Review this model before anything is created.</div><div class="grid">' +
    m.tables.map((t) => card('Table', esc(t.name), `${t.fields.length} fields · from ${t.from.join(', ')}`, `#/data/${t.name}`)).join('') + '</div>';
}

function render() {
  const [, tab = 'overview', a, b] = (location.hash || '#/overview').split('/');
  const cur = TABS.find((t) => t[0] === tab) || TABS[0];
  $('#tabs').innerHTML = TABS.map(([id, label]) => `<a href="#/${id}" class="${id === cur[0] ? 'on' : ''}">${label}</a>`).join('');
  asOf();
  $('#sample-banner').hidden = mode !== 'sample';
  const p = planOf().project;
  $('#proj-name').textContent = p?.name || 'Command Center';
  $('#proj-desc').textContent = p?.descriptor || '';
  const fn = { overview: () => overview(a), outcomes: () => outcomes(a), users: () => users(a), guardrails: () => guardrails(a), systems: () => systems(a),
    projects: () => (a === 'release' ? releaseDetail(b) : projects(a)), agents: () => agents(a), knowledge: () => knowledge(a, b), data: () => dataModel(a) }[cur[0]];
  $('#view').innerHTML = fn();
  knowledgeWire();
}

$('#mode').value = mode;
$('#mode').onchange = (e) => { mode = e.target.value; safe(() => localStorage.setItem('cc-mode', mode)); render(); };
window.addEventListener('hashchange', render);
load().then(render);
