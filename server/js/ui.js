// ══════════════════════════════════════════
// UI orchestration: init, scope, tabs, render dispatch
// ══════════════════════════════════════════

async function init() {
  try {
    var r = await fetch('./index.json');
    if (!r.ok) throw new Error('index.json not found');
    snapshotIndex = await r.json();
  } catch {
    document.getElementById('content').innerHTML =
      '<div class="empty-state"><div class="icon">⚠️</div>' +
      '<p>Failed to load index.json.<br>Make sure the dashboard is opened via HTTP server:<br>' +
      '<code style="color:var(--accent)">cmc serve [PROJECT_ROOT]</code></p></div>';
    return;
  }

  if (!snapshotIndex.snapshots || !snapshotIndex.snapshots.length) {
    document.getElementById('content').innerHTML =
      '<div class="empty-state"><div class="icon">📭</div>' +
      '<p>No snapshots found. Run <code style="color:var(--accent)">cmc &lt;project&gt;</code> to generate metrics.</p></div>';
    return;
  }

  populateSnapshotSelects();
  var latest = snapshotIndex.snapshots[snapshotIndex.snapshots.length - 1];
  activeSnapshot = latest.id;
  document.getElementById('snapshotSelect').value = latest.id;

  if (snapshotIndex.snapshots.length >= 2) {
    document.getElementById('compareA').value = snapshotIndex.snapshots[snapshotIndex.snapshots.length - 2].id;
    document.getElementById('compareB').value = latest.id;
  }

  await loadSnapshotAndRender();
}

function populateSnapshotSelects() {
  var selects = ['snapshotSelect', 'compareA', 'compareB'];
  for (var si = 0; si < selects.length; si++) {
    var sel = document.getElementById(selects[si]);
    sel.innerHTML = '';
    for (var i = 0; i < snapshotIndex.snapshots.length; i++) {
      var s = snapshotIndex.snapshots[i];
      var opt = document.createElement('option');
      opt.value = s.id;
      var d = s.timestamp ? new Date(s.timestamp) : null;
      var dateStr = d ? d.toLocaleString() : s.id;
      var branch = s.git_branch ? ' (' + s.git_branch + ')' : '';
      var commit = s.git_commit ? ' #' + s.git_commit : '';
      opt.textContent = dateStr + branch + commit;
      sel.appendChild(opt);
    }
  }
}

async function onSnapshotChange(snapId) {
  activeSnapshot = snapId;
  compareMode = false;
  document.getElementById('btnCompare').classList.remove('active');
  document.getElementById('compareBar').classList.remove('visible');
  await loadSnapshotAndRender();
}

async function loadSnapshotAndRender() {
  var results = await Promise.all([
    load('metadata', 'metadata.json'),
    load('project_summary', 'project_summary.json'),
    load('ratings', 'ratings.json'),
  ]);
  var meta = results[0], summary = results[1], ratings = results[2];

  if (meta) {
    document.getElementById('headerMeta').textContent =
      'Generated: ' + new Date(meta.generated_at).toLocaleString() +
      ' · Parser: ' + meta.parser +
      (meta.config_version ? ' · Config: v' + meta.config_version : '') +
      ' · Duration: ' + meta.duration_seconds.toFixed(1) + 's' +
      ' · Modules: ' + meta.modules_analyzed.length;
    modules = meta.modules_analyzed.sort();
  }
  if (ratings && ratings.modules) {
    var gradeMap = {};
    ratings.modules.forEach(function (m) { gradeMap[m.module] = m; });
    DC._gradeMap = gradeMap;
  }
  buildScopeBar();
  render();
}

// ── Compare mode ──

function toggleCompare() {
  compareMode = !compareMode;
  document.getElementById('btnCompare').classList.toggle('active', compareMode);
  document.getElementById('compareBar').classList.toggle('visible', compareMode);
  if (!compareMode) render();
}

async function runCompare() {
  var idA = document.getElementById('compareA').value;
  var idB = document.getElementById('compareB').value;
  if (idA === idB) { alert('Select two different snapshots'); return; }
  compareMode = true;
  document.getElementById('btnCompare').classList.add('active');
  var el = document.getElementById('content');
  el.innerHTML = spinnerHtml();
  destroyCharts();
  try {
    if (currentScope === 'project') await renderCompareProject(el, idA, idB);
    else await renderCompareModule(el, idA, idB, currentScope);
  } catch (e) {
    el.innerHTML = '<div class="empty-state"><div class="icon">❌</div><p>Error: ' + e.message + '</p></div>';
    console.error(e);
  }
}

// ── Scope bar ──

function buildScopeBar() {
  var bar = document.getElementById('scopeBar');
  bar.querySelectorAll('.module-pill').forEach(function (p) { p.remove(); });
  var gradeMap = DC._gradeMap || {};
  modules.forEach(function (m) {
    var pill = document.createElement('div');
    pill.className = 'scope-pill module-pill' + (currentScope === m ? ' active' : '');
    pill.dataset.scope = m;
    pill.onclick = function () { setScope(m); };
    var info = gradeMap[m];
    if (info) {
      pill.innerHTML = '<span class="grade grade-' + info.grade + '">' + info.grade + '</span>' + m;
    } else {
      pill.textContent = m;
    }
    bar.appendChild(pill);
  });
}

function filterModules(q) {
  var lower = q.toLowerCase();
  document.querySelectorAll('.module-pill').forEach(function (p) {
    p.style.display = p.dataset.scope.toLowerCase().includes(lower) ? '' : 'none';
  });
}

function setScope(scope) {
  currentScope = scope;
  document.querySelectorAll('.scope-pill').forEach(function (p) {
    p.classList.toggle('active', p.dataset.scope === scope);
  });
  if (compareMode) runCompare(); else render();
}

function setTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.tab-btn').forEach(function (b) {
    b.classList.toggle('active', b.dataset.tab === tab);
  });
  if (compareMode) runCompare(); else render();
}

// ── Render dispatcher ──

async function render() {
  var el = document.getElementById('content');
  el.innerHTML = spinnerHtml();
  destroyCharts();
  try {
    if (currentScope === 'project') await renderProject(el);
    else await renderModule(el, currentScope);
  } catch (e) {
    el.innerHTML = '<div class="empty-state"><div class="icon">❌</div><p>Error: ' + e.message + '</p></div>';
    console.error(e);
  }
}

// ── Compare header ──

function compareHeader(idA, idB) {
  var sA = snapshotIndex.snapshots.find(function (s) { return s.id === idA; });
  var sB = snapshotIndex.snapshots.find(function (s) { return s.id === idB; });
  var nameA = sA && sA.timestamp ? new Date(sA.timestamp).toLocaleString() : idA;
  var nameB = sB && sB.timestamp ? new Date(sB.timestamp).toLocaleString() : idB;
  return '<div class="section"><div class="section-title"><span class="icon">⚖️</span>Comparison — ' +
    (currentScope === 'project' ? 'Project' : currentScope) + '</div>' +
    '<div class="section-subtitle">A: ' + nameA + ' → B: ' + nameB + '</div></div>';
}
