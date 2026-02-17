// ══════════════════════════════════════════
// PROJECT SCOPE renderers
// ══════════════════════════════════════════

async function renderProject(el) {
  var handlers = {
    overview: renderProjectOverview,
    hotspots: renderProjectHotspots,
    techdebt: renderProjectTechDebt,
    distributions: renderProjectDistributions,
    dependencies: renderProjectDependencies,
    duplication: renderProjectDuplication,
    trends: renderProjectTrends,
  };
  var fn = handlers[currentTab];
  if (fn) await fn(el);
  else el.innerHTML = '<div class="empty-state"><p>Tab not implemented</p></div>';
}

async function renderProjectOverview(el) {
  var results = await Promise.all([
    load('project_summary', 'project_summary.json'),
    load('ratings', 'ratings.json'),
  ]);
  var summary = results[0], ratings = results[1];
  if (!summary) { el.innerHTML = noData(); return; }
  var td = await load('technical_debt', 'technical_debt.json');

  var html = '<div class="kpi-grid">';
  html += kpi('Modules', summary.modules_count, '📦');
  html += kpi('Files', fmt(summary.files_count), '📄');
  html += kpi('Classes', fmt(summary.classes_count), '🏗️');
  html += kpi('Functions', fmt(summary.functions_count), '⚙️');
  html += kpi('LOC', fmt(summary.loc_total), '📏');
  html += kpi('SLOC', fmt(summary.sloc_total), '📐');
  if (td) {
    html += kpi('Tech Debt', td.total_days.toFixed(0) + 'd', '⏱️', td.total_hours.toFixed(0) + ' hours');
    html += kpi('TD/KLOC', td.total_td_per_loc.toFixed(0) + ' min', '📊');
  }
  html += '</div>';

  html += violationsSection(summary.violations);

  if (summary.metrics_summary) {
    html += '<div class="section"><div class="section-title"><span class="icon">📈</span>Metrics Summary</div>';
    html += metricsSummaryTable(summary.metrics_summary, METRIC_LABELS_FULL);
    html += '</div>';
  }

  if (ratings && ratings.modules) {
    html += '<div class="section"><div class="section-title"><span class="icon">🏆</span>Module Ratings</div>';
    html += '<div class="table-wrap"><table><thead><tr><th>#</th><th>Module</th><th>Score</th><th>Grade</th></tr></thead><tbody>';
    ratings.modules.forEach(function (m, i) {
      html += '<tr><td>' + (i + 1) + '</td><td><a href="#" onclick="setScope(\'' + m.module + '\');return false">' + m.module + '</a></td><td>' + m.score.toFixed(1) + '</td><td><span class="grade grade-' + m.grade + '">' + m.grade + '</span></td></tr>';
    });
    html += '</tbody></table></div></div>';
  }
  el.innerHTML = html;
}

async function renderProjectHotspots(el) {
  var results = await Promise.all([
    load('hotspots', 'hotspots.json'),
    load('risk_hotspots', 'risk_hotspots.json'),
  ]);
  var hotspots = results[0], risk = results[1];
  if (!hotspots && !risk) { el.innerHTML = noData(); return; }
  var html = '';

  if (risk && risk.hotspots) {
    html += '<div class="section"><div class="section-title"><span class="icon">🔥</span>Risk Hotspots <span class="badge badge-red">' + risk.count + '</span></div>';
    html += '<div class="section-subtitle">Files ranked by churn × complexity</div>';
    html += '<div class="table-wrap scroll-y"><table><thead><tr><th>#</th><th>File</th><th>Module</th><th>Risk</th><th>Churn</th><th>Complexity</th><th>CC Max</th><th>CC Σ</th><th>TD (min)</th><th>LOC</th><th>MI Avg</th></tr></thead><tbody>';
    risk.hotspots.forEach(function (h, i) {
      html += '<tr><td>' + (i + 1) + '</td><td title="' + h.path + '">' + shortPath(h.path) + '</td><td><a href="#" onclick="setScope(\'' + h.module + '\');return false">' + h.module + '</a></td><td><strong>' + h.risk_score.toFixed(4) + '</strong></td><td>' + h.churn + '</td><td>' + h.complexity.toFixed(1) + '</td><td>' + h.cc_max + '</td><td>' + fmt(h.cc_sum) + '</td><td>' + fmt(h.td_minutes) + '</td><td>' + fmt(h.loc) + '</td><td>' + n(h.mi_avg) + '</td></tr>';
    });
    html += '</tbody></table></div></div>';
  }

  if (hotspots) {
    // Function-level hotspot categories
    var funcCats = [
      ['by_cyclomatic_complexity', '🔴 Top by CC'],
      ['by_lowest_maintainability', '🟡 Top by Lowest MI'],
    ];
    for (var fi = 0; fi < funcCats.length; fi++) {
      var items = hotspots[funcCats[fi][0]];
      if (items && items.length)
        html += '<div class="section"><div class="section-title">' + funcCats[fi][1] + '</div>' + funcTable(items, true) + '</div>';
    }

    // Class-level hotspot categories
    var classCats = [
      ['by_weighted_methods', '🟠 Top by WMC'],
      ['by_coupling', '🔵 Top by CBO'],
      ['by_lowest_cohesion', '🟣 Top by Lowest TCC'],
    ];
    for (var ci = 0; ci < classCats.length; ci++) {
      var items2 = hotspots[classCats[ci][0]];
      if (items2 && items2.length)
        html += '<div class="section"><div class="section-title">' + classCats[ci][1] + '</div>' + classTable(items2, true) + '</div>';
    }

    // File-level hotspot category
    if (hotspots.by_technical_debt && hotspots.by_technical_debt.length)
      html += '<div class="section"><div class="section-title">⏱️ Top by TD</div>' + fileTable(hotspots.by_technical_debt, true) + '</div>';
  }
  el.innerHTML = html;
}

async function renderProjectTechDebt(el) {
  var td = await load('technical_debt', 'technical_debt.json');
  if (!td) { el.innerHTML = noData(); return; }

  var html = '<div class="kpi-grid">';
  html += kpi('Total TD', td.total_days.toFixed(0) + ' days', '⏱️', td.total_hours.toFixed(0) + ' hours / ' + fmt(td.total_minutes) + ' min');
  html += kpi('TD / KLOC', td.total_td_per_loc.toFixed(0) + ' min', '📊');
  html += kpi('Total LOC', fmt(td.total_loc), '📏');
  html += '</div>';

  if (td.by_module && td.by_module.length)
    html += '<div class="chart-full"><h3>Tech Debt by Module (hours)</h3><canvas id="chartTdByModule"></canvas></div>';
  if (td.top_files && td.top_files.length)
    html += '<div class="section"><div class="section-title"><span class="icon">📄</span>Top Files by Tech Debt</div>' + fileTable(td.top_files, true) + '</div>';
  if (td.top_functions && td.top_functions.length)
    html += '<div class="section"><div class="section-title"><span class="icon">⚙️</span>Top Functions by Tech Debt</div>' + funcTable(td.top_functions, true) + '</div>';
  if (td.top_classes && td.top_classes.length)
    html += '<div class="section"><div class="section-title"><span class="icon">🏗️</span>Top Classes by Tech Debt</div>' + classTable(td.top_classes, true) + '</div>';

  el.innerHTML = html;

  if (td.by_module && td.by_module.length) {
    var sorted = td.by_module.slice().sort(function (a, b) { return b.total_hours - a.total_hours; });
    createBarChart('chartTdByModule', sorted.map(function (m) { return m.module; }), sorted.map(function (m) { return m.total_hours; }), 'TD (hours)', 'horizontal');
  }
}

async function renderProjectDistributions(el) {
  var dist = await load('distributions', 'distributions.json');
  if (!dist || !dist.distributions) { el.innerHTML = noData(); return; }

  var html = '<div class="chart-grid">';
  for (var key in dist.distributions) {
    var d = dist.distributions[key];
    html += '<div class="chart-card"><h3>' + d.metric_name + ' (n=' + fmt(d.total) + ')</h3><canvas id="chartDist_' + key + '"></canvas></div>';
  }
  html += '</div>';
  el.innerHTML = html;

  for (var key2 in dist.distributions) {
    var d2 = dist.distributions[key2];
    createBarChart('chartDist_' + key2,
      d2.buckets.map(function (b) { return b.label; }),
      d2.buckets.map(function (b) { return b.count; }),
      'Count', 'vertical',
      d2.buckets.map(function (b) { return b.pct.toFixed(1) + '%'; }));
  }
}

async function renderProjectDependencies(el) {
  var results = await Promise.all([load('dsm', 'dsm.json'), load('graph_import', 'graph_import.json')]);
  var dsm = results[0], graph = results[1];
  if (!dsm && !graph) { el.innerHTML = noData(); return; }
  var html = '';

  if (dsm && dsm.matrix) {
    html += '<div class="section"><div class="section-title"><span class="icon">🔲</span>DSM';
    if (dsm.total_imports != null) html += ' <span class="badge">' + fmt(dsm.total_imports) + ' imports</span>';
    html += '</div>';
    html += '<div class="section-subtitle">Cell (row→col) = imports from row to col</div>';
    html += '<div class="dsm-wrap"><table class="dsm-table"><thead><tr><th></th>';
    dsm.modules.forEach(function (m) { html += '<th title="' + m + '" style="writing-mode:vertical-lr;transform:rotate(180deg);max-width:30px">' + m.substring(0, 12) + '</th>'; });
    html += '</tr></thead><tbody>';
    dsm.modules.forEach(function (m, i) {
      html += '<tr><th style="text-align:right">' + m + '</th>';
      dsm.matrix[i].forEach(function (v, j) {
        if (i === j) html += '<td class="dsm-self">—</td>';
        else if (v > 0) {
          var heat = Math.min(v / 50, 1);
          html += '<td class="dsm-val" style="background:rgba(88,166,255,' + (0.1 + heat * 0.7) + ')" title="' + m + ' → ' + dsm.modules[j] + ': ' + v + '">' + v + '</td>';
        } else html += '<td class="dsm-val" style="color:var(--text-dim)">·</td>';
      });
      html += '</tr>';
    });
    html += '</tbody></table></div></div>';

    if (dsm.cycles && dsm.cycles.length) {
      html += '<div class="section"><div class="section-title"><span class="icon">🔄</span>Dependency Cycles <span class="badge badge-red">' + dsm.cycles.length + '</span></div>';
      html += '<div class="section-subtitle">Circular dependencies between modules — should be eliminated</div>';
      html += '<div class="table-wrap"><table><thead><tr><th>#</th><th>From</th><th>To</th></tr></thead><tbody>';
      dsm.cycles.forEach(function (c, i) {
        html += '<tr><td>' + (i + 1) + '</td><td>' + c.from + '</td><td>' + c.to + '</td></tr>';
      });
      html += '</tbody></table></div></div>';
    }
  }

  if (graph && graph.nodes && graph.edges) {
    html += '<div class="section"><div class="section-title"><span class="icon">🕸️</span>Import Graph</div>';
    html += '<div class="table-wrap scroll-y"><table><thead><tr><th>From</th><th>To</th><th>Weight</th><th>Type</th></tr></thead><tbody>';
    var edges = graph.edges.slice().sort(function (a, b) { return (b.weight || 1) - (a.weight || 1); });
    edges.forEach(function (e) { html += '<tr><td>' + e.from_node + '</td><td>' + e.to_node + '</td><td>' + (e.weight || 1) + '</td><td>' + (e.edge_type || '—') + '</td></tr>'; });
    html += '</tbody></table></div></div>';
  }
  el.innerHTML = html;
}

async function renderProjectDuplication(el) {
  var dup = await load('duplication', 'duplication.json');
  if (!dup) { el.innerHTML = noData(); return; }

  var html = '<div class="kpi-grid">';
  html += kpi('Files Analyzed', fmt(dup.total_files), '📄');
  html += kpi('Total Tokens', fmt(dup.total_tokens), '🔤');
  html += kpi('Duplicated Tokens', fmt(dup.duplicated_tokens), '📋');
  html += kpi('Duplication %', dup.duplication_pct.toFixed(2) + '%', '📊');
  html += kpi('Duplicate Pairs', fmt(dup.duplicate_pairs_count), '🔗');
  if (dup.files_with_duplicates != null)
    html += kpi('Files with Dups', fmt(dup.files_with_duplicates), '📁');
  html += '</div>';

  if (dup.duplicate_pairs && dup.duplicate_pairs.length) {
    html += '<div class="section"><div class="section-title"><span class="icon">📋</span>Duplicate Pairs</div>';
    html += dupPairTable(dup.duplicate_pairs.slice(0, 100));
    if (dup.duplicate_pairs.length > 100)
      html += '<div class="section-subtitle">Showing 100 of ' + dup.duplicate_pairs.length + ' pairs</div>';
    html += '</div>';
  }
  el.innerHTML = html;
}

async function renderProjectTrends(el) {
  if (!snapshotIndex || !snapshotIndex.snapshots.length) {
    el.innerHTML = '<div class="empty-state"><div class="icon">📈</div><p>No trend data. Run cmc multiple times to build history.</p></div>';
    return;
  }
  var delta = await load('delta', 'delta.json');
  var html = '';

  if (delta && delta.project_delta) {
    html += '<div class="section"><div class="section-title"><span class="icon">📊</span>Project Delta (vs previous)</div>';
    html += '<div class="section-subtitle">Baseline: ' + fmtDate(delta.baseline) + ' → Current: ' + fmtDate(delta.current) + '</div>';
    html += '<div class="table-wrap"><table><thead><tr><th>Metric</th><th>Before</th><th>After</th><th>Delta</th><th>Change %</th><th>Status</th></tr></thead><tbody>';
    delta.project_delta.forEach(function (d) {
      var cls = d.delta > 0 ? 'delta-pos' : d.delta < 0 ? 'delta-neg' : 'delta-zero';
      html += '<tr><td>' + d.metric + '</td><td>' + n(d.before) + '</td><td>' + n(d.after) + '</td><td class="' + cls + '">' + (d.delta > 0 ? '+' : '') + n(d.delta) + '</td><td class="' + cls + '">' + (d.pct_change > 0 ? '+' : '') + n(d.pct_change) + '%</td><td>' + d.indicator + '</td></tr>';
    });
    html += '</tbody></table></div></div>';
  }

  if (snapshotIndex.snapshots.length > 1) {
    html += '<div class="section"><div class="section-title"><span class="icon">📈</span>History Trends</div>';
    html += '<div class="section-subtitle">' + snapshotIndex.snapshots.length + ' snapshots</div>';
    html += '<div class="chart-grid">';
    html += '<div class="chart-card"><h3>LOC over time</h3><canvas id="chartHistLoc"></canvas></div>';
    html += '<div class="chart-card"><h3>Tech Debt (hours)</h3><canvas id="chartHistTd"></canvas></div>';
    html += '<div class="chart-card"><h3>Violations</h3><canvas id="chartHistViol"></canvas></div>';
    html += '<div class="chart-card"><h3>Duplication %</h3><canvas id="chartHistDup"></canvas></div>';
    html += '<div class="chart-card"><h3>Files</h3><canvas id="chartHistFiles"></canvas></div>';
    html += '<div class="chart-card"><h3>Modules</h3><canvas id="chartHistMods"></canvas></div>';
    html += '</div></div>';
    el.innerHTML = html;
    await renderHistoryCharts();
  } else {
    if (!html) html = '<div class="empty-state"><div class="icon">📈</div><p>Only one snapshot. Run cmc again to see trends.</p></div>';
    el.innerHTML = html;
  }
}

async function renderHistoryCharts() {
  var dataPoints = [];
  for (var i = 0; i < snapshotIndex.snapshots.length; i++) {
    var s = snapshotIndex.snapshots[i];
    var r = await Promise.all([
      loadFrom(s.id, 'metadata.json'),
      loadFrom(s.id, 'project_summary.json'),
      loadFrom(s.id, 'technical_debt.json'),
      loadFrom(s.id, 'duplication.json'),
    ]);
    var meta = r[0], ps = r[1], td = r[2], dup = r[3];
    if (!meta || !ps) continue;
    dataPoints.push({
      timestamp: meta.generated_at,
      loc: ps.loc_total, sloc: ps.sloc_total, files: ps.files_count,
      modules: ps.modules_count || (meta.modules_analyzed || []).length,
      td_hours: td ? td.total_hours : 0,
      td_per_kloc: td ? td.total_td_per_loc : 0,
      violations: ps.violations ? Object.values(ps.violations).reduce(function (s, v) { return s + (v || 0); }, 0) : 0,
      dup_pct: dup ? dup.duplication_pct : 0,
    });
  }
  if (!dataPoints.length) return;
  dataPoints.sort(function (a, b) { return new Date(a.timestamp) - new Date(b.timestamp); });
  var labels = dataPoints.map(function (d) { return new Date(d.timestamp).toLocaleDateString(); });
  createLineChart('chartHistLoc', labels, dataPoints.map(function (d) { return d.loc; }), 'LOC');
  createLineChart('chartHistTd', labels, dataPoints.map(function (d) { return d.td_hours; }), 'TD (h)');
  createLineChart('chartHistViol', labels, dataPoints.map(function (d) { return d.violations; }), 'Violations');
  createLineChart('chartHistDup', labels, dataPoints.map(function (d) { return d.dup_pct; }), 'Dup %');
  createLineChart('chartHistFiles', labels, dataPoints.map(function (d) { return d.files; }), 'Files');
  createLineChart('chartHistMods', labels, dataPoints.map(function (d) { return d.modules; }), 'Modules');
}
