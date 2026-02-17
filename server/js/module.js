// ══════════════════════════════════════════
// MODULE SCOPE renderers
// ══════════════════════════════════════════

async function renderModule(el, mod) {
  var handlers = {
    overview: renderModuleOverview,
    hotspots: renderModuleHotspots,
    techdebt: renderModuleTechDebt,
    distributions: renderModuleDistributions,
    dependencies: renderModuleDependencies,
    duplication: renderModuleDuplication,
    trends: renderModuleTrends,
  };
  var fn = handlers[currentTab];
  if (fn) await fn(el, mod);
  else el.innerHTML = '<div class="empty-state"><p>Tab not implemented</p></div>';
}

async function renderModuleOverview(el, mod) {
  var summary = await load('mod_' + mod + '_summary', 'modules/' + mod + '_summary.json');
  if (!summary) { el.innerHTML = noData('Module "' + mod + '"'); return; }
  var gradeMap = DC._gradeMap || {};
  var info = gradeMap[mod];

  var html = '<div class="kpi-grid">';
  if (info) html += kpi('Grade', '<span class="grade grade-' + info.grade + '" style="font-size:20px;width:32px;height:32px;line-height:32px">' + info.grade + '</span>', '🏆', 'Score: ' + info.score.toFixed(1));
  html += kpi('Files', fmt(summary.files_count), '📄');
  html += kpi('Classes', fmt(summary.classes_count), '🏗️');
  html += kpi('Functions', fmt(summary.functions_count), '⚙️');
  html += kpi('LOC', fmt(summary.loc_total), '📏');
  html += kpi('SLOC', fmt(summary.sloc_total), '📐');
  if (summary.technical_debt) {
    html += kpi('Tech Debt', (summary.technical_debt.total_days || 0).toFixed(1) + 'd', '⏱️',
      (summary.technical_debt.total_hours || 0).toFixed(0) + ' hours');
    if (summary.technical_debt.td_per_loc != null)
      html += kpi('TD/KLOC', (summary.technical_debt.td_per_loc).toFixed(0) + ' min', '📊');
  }
  html += '</div>';

  html += violationsSection(summary.violations);

  if (summary.metrics_summary) {
    html += '<div class="section"><div class="section-title"><span class="icon">📈</span>Metrics Summary</div>';
    html += metricsSummaryTable(summary.metrics_summary, METRIC_LABELS_SHORT);
    html += '</div>';
  }

  var pkg = await load('mod_' + mod + '_pkg', 'modules/' + mod + '_package_analysis.json');
  if (pkg && pkg.directory_structure) {
    html += '<div class="section"><div class="section-title"><span class="icon">📁</span>Directory Structure</div>';
    html += '<div class="table-wrap scroll-y"><table><thead><tr><th>Path</th><th>Files</th><th>LOC</th></tr></thead><tbody>';
    pkg.directory_structure.forEach(function (d) {
      var depth = (d.path.match(/\//g) || []).length;
      var indent = '&nbsp;'.repeat(depth * 3);
      html += '<tr><td>' + indent + (d.path.split('/').pop() || d.path) + '</td><td>' + d.file_count + '</td><td>' + fmt(d.total_loc) + '</td></tr>';
    });
    html += '</tbody></table></div></div>';
  }
  el.innerHTML = html;
}

async function renderModuleHotspots(el, mod) {
  var results = await Promise.all([
    load('raw_functions', 'raw/function_metrics.json'),
    load('raw_classes', 'raw/class_metrics.json'),
  ]);
  var funcs = results[0], classes = results[1];
  var html = '';

  if (funcs && funcs.functions) {
    var modFuncs = funcs.functions.filter(function (f) { return f.module === mod; });
    var byCC = modFuncs.slice().sort(function (a, b) { return b.cyclo - a.cyclo; }).slice(0, 20);
    if (byCC.length) html += '<div class="section"><div class="section-title"><span class="icon">🔴</span>Top Functions by CC</div>' + funcTable(byCC, false) + '</div>';
    var byMI = modFuncs.slice().sort(function (a, b) { return a.mi - b.mi; }).slice(0, 20);
    if (byMI.length) html += '<div class="section"><div class="section-title"><span class="icon">🟡</span>Top Functions by Lowest MI</div>' + funcTable(byMI, false) + '</div>';
    var byWMFP = modFuncs.slice().sort(function (a, b) { return b.wmfp - a.wmfp; }).slice(0, 20);
    if (byWMFP.length) html += '<div class="section"><div class="section-title"><span class="icon">🟠</span>Top Functions by WMFP</div>' + funcTable(byWMFP, false) + '</div>';
  }
  if (classes && classes.classes) {
    var modClasses = classes.classes.filter(function (c) { return c.module === mod; });
    var byWMC = modClasses.slice().sort(function (a, b) { return b.wmc - a.wmc; }).slice(0, 20);
    if (byWMC.length) html += '<div class="section"><div class="section-title"><span class="icon">🔵</span>Top Classes by WMC</div>' + classTable(byWMC, false) + '</div>';
    var byCBO = modClasses.slice().sort(function (a, b) { return b.cbo - a.cbo; }).slice(0, 20);
    if (byCBO.length) html += '<div class="section"><div class="section-title"><span class="icon">🟣</span>Top Classes by CBO</div>' + classTable(byCBO, false) + '</div>';
  }
  if (!html) html = noData('No hotspot data for "' + mod + '"');
  el.innerHTML = html;
}

async function renderModuleTechDebt(el, mod) {
  var results = await Promise.all([
    load('technical_debt', 'technical_debt.json'),
    load('raw_functions', 'raw/function_metrics.json'),
    load('raw_classes', 'raw/class_metrics.json'),
    load('raw_files', 'raw/file_metrics.json'),
  ]);
  var td = results[0], funcs = results[1], classes = results[2], files = results[3];
  var html = '';

  if (td && td.by_module) {
    var modTd = td.by_module.find(function (m) { return m.module === mod; });
    if (modTd) {
      html += '<div class="kpi-grid">';
      html += kpi('Module TD', modTd.total_days.toFixed(1) + ' days', '⏱️', modTd.total_hours.toFixed(0) + ' hours');
      html += kpi('TD / KLOC', modTd.td_per_loc.toFixed(0) + ' min', '📊');
      html += kpi('Module LOC', fmt(modTd.loc), '📏');
      html += '</div>';
    }
  }
  if (files && files.files) {
    var modFiles = files.files.filter(function (f) { return f.module === mod; }).sort(function (a, b) { return b.technical_debt_minutes - a.technical_debt_minutes; }).slice(0, 30);
    if (modFiles.length) html += '<div class="section"><div class="section-title"><span class="icon">📄</span>Top Files by TD</div>' + fileTable(modFiles, false) + '</div>';
  }
  if (funcs && funcs.functions) {
    var modFuncs = funcs.functions.filter(function (f) { return f.module === mod; }).sort(function (a, b) { return b.technical_debt_minutes - a.technical_debt_minutes; }).slice(0, 30);
    if (modFuncs.length) html += '<div class="section"><div class="section-title"><span class="icon">⚙️</span>Top Functions by TD</div>' + funcTable(modFuncs, false) + '</div>';
  }
  if (classes && classes.classes) {
    var modClasses = classes.classes.filter(function (c) { return c.module === mod; }).sort(function (a, b) { return b.technical_debt_minutes - a.technical_debt_minutes; }).slice(0, 30);
    if (modClasses.length) html += '<div class="section"><div class="section-title"><span class="icon">🏗️</span>Top Classes by TD</div>' + classTable(modClasses, false) + '</div>';
  }
  if (!html) html = noData('No tech debt data for "' + mod + '"');
  el.innerHTML = html;
}

async function renderModuleDistributions(el, mod) {
  var funcs = await load('raw_functions', 'raw/function_metrics.json');
  if (!funcs || !funcs.functions) { el.innerHTML = noData(); return; }
  var modFuncs = funcs.functions.filter(function (f) { return f.module === mod; });
  if (!modFuncs.length) { el.innerHTML = noData('No function data for "' + mod + '"'); return; }

  var html = '<div class="section-subtitle">' + fmt(modFuncs.length) + ' functions in module</div><div class="chart-grid">';
  var idx = 0;
  for (var name in DISTRIBUTION_BUCKETS) {
    html += '<div class="chart-card"><h3>' + name + ' (n=' + fmt(modFuncs.length) + ')</h3><canvas id="chartModDist' + idx + '"></canvas></div>';
    idx++;
  }
  html += '</div>';
  el.innerHTML = html;

  idx = 0;
  for (var name2 in DISTRIBUTION_BUCKETS) {
    var d = DISTRIBUTION_BUCKETS[name2];
    var values = modFuncs.map(function (f) { return f[d.key]; });
    var dlabels = d.buckets.map(function (b) { return b[2]; });
    var counts = bucketize(values, d.buckets);
    var pcts = counts.map(function (c) { return ((c / modFuncs.length) * 100).toFixed(1) + '%'; });
    createBarChart('chartModDist' + idx, dlabels, counts, 'Count', 'vertical', pcts);
    idx++;
  }
}

async function renderModuleDependencies(el, mod) {
  var pkg = await load('mod_' + mod + '_pkg', 'modules/' + mod + '_package_analysis.json');
  if (!pkg) { el.innerHTML = noData('No package analysis for "' + mod + '"'); return; }
  var html = '';

  var dsm = await load('dsm', 'dsm.json');
  if (dsm && dsm.matrix && dsm.modules) {
    var dsmIdx = dsm.modules.indexOf(mod);
    if (dsmIdx >= 0) {
      var imports = dsm.matrix[dsmIdx];
      var importedBy = dsm.modules.map(function (_, j) { return dsm.matrix[j][dsmIdx]; });
      var outgoing = [], incoming = [];
      dsm.modules.forEach(function (m, j) {
        if (j !== dsmIdx && imports[j] > 0) outgoing.push({ module: m, count: imports[j] });
        if (j !== dsmIdx && importedBy[j] > 0) incoming.push({ module: m, count: importedBy[j] });
      });
      outgoing.sort(function (a, b) { return b.count - a.count; });
      incoming.sort(function (a, b) { return b.count - a.count; });

      if (outgoing.length || incoming.length) {
        html += '<div class="section"><div class="section-title"><span class="icon">🔲</span>Module Dependencies (DSM)</div>';
        html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">';
        html += '<div><h4 style="color:var(--text-muted);margin-bottom:8px">Depends on (outgoing)</h4>';
        if (outgoing.length) {
          html += '<div class="table-wrap"><table><thead><tr><th>Module</th><th>Imports</th></tr></thead><tbody>';
          outgoing.forEach(function (d) { html += '<tr><td><a href="#" onclick="setScope(\'' + d.module + '\');return false">' + d.module + '</a></td><td>' + d.count + '</td></tr>'; });
          html += '</tbody></table></div>';
        } else html += '<div class="section-subtitle">None</div>';
        html += '</div>';
        html += '<div><h4 style="color:var(--text-muted);margin-bottom:8px">Used by (incoming)</h4>';
        if (incoming.length) {
          html += '<div class="table-wrap"><table><thead><tr><th>Module</th><th>Imports</th></tr></thead><tbody>';
          incoming.forEach(function (d) { html += '<tr><td><a href="#" onclick="setScope(\'' + d.module + '\');return false">' + d.module + '</a></td><td>' + d.count + '</td></tr>'; });
          html += '</tbody></table></div>';
        } else html += '<div class="section-subtitle">None</div>';
        html += '</div></div></div>';
      }
    }
  }

  if (pkg.import_statistics && pkg.import_statistics.length) {
    html += '<div class="section"><div class="section-title"><span class="icon">📊</span>Import Statistics</div>';
    html += '<div class="table-wrap scroll-y"><table><thead><tr><th>#</th><th>Package</th><th>Import Count</th></tr></thead><tbody>';
    pkg.import_statistics.slice().sort(function (a, b) { return b.count - a.count; }).forEach(function (s, i) {
      html += '<tr><td>' + (i + 1) + '</td><td>' + s.package_name + '</td><td>' + s.count + '</td></tr>';
    });
    html += '</tbody></table></div></div>';
  }

  if (pkg.cross_package_imports && pkg.cross_package_imports.length) {
    html += '<div class="section"><div class="section-title"><span class="icon">📦</span>Cross-Package Imports <span class="badge badge-red">' + pkg.cross_package_imports.length + '</span></div>';
    html += '<div class="section-subtitle">Imports from other packages — potential coupling issues</div>';
    html += '<div class="table-wrap scroll-y"><table><thead><tr><th>#</th><th>File</th><th>Line</th><th>Imported Package</th><th>Import URI</th></tr></thead><tbody>';
    pkg.cross_package_imports.slice(0, 100).forEach(function (imp, i) {
      html += '<tr><td>' + (i + 1) + '</td><td title="' + imp.file_path + '">' + shortPath(imp.file_path) + '</td><td>' + imp.line_number + '</td><td>' + imp.imported_package + '</td><td style="font-size:12px;word-break:break-all">' + imp.import_uri + '</td></tr>';
    });
    html += '</tbody></table></div>';
    if (pkg.cross_package_imports.length > 100)
      html += '<div class="section-subtitle">Showing 100 of ' + pkg.cross_package_imports.length + '</div>';
    html += '</div>';
  }

  if (pkg.shotgun_surgery_candidates && pkg.shotgun_surgery_candidates.length) {
    html += '<div class="section"><div class="section-title"><span class="icon">🔗</span>Shotgun surgery candidates</div>';
    html += '<div class="table-wrap scroll-y"><table><thead><tr><th>Path</th><th>Usage count</th></tr></thead><tbody>';
    pkg.shotgun_surgery_candidates.forEach(function (imp) {
      html += '<tr><td>' + (imp.relative_path || '—') + '</td><td>' + (imp.usage_count || '—') + '</td></tr>';
    });
    html += '</tbody></table></div></div>';
  }
  if (pkg.git_hotspots && pkg.git_hotspots.length) {
    html += '<div class="section"><div class="section-title"><span class="icon">⚠️</span>Git hotspots</div>';
    html += '<div class="table-wrap scroll-y"><table><thead><tr><th>Path</th><th>Commit count</th></tr></thead><tbody>';
    pkg.git_hotspots.forEach(function (v) {
      html += '<tr><td>' + (v.file_path || '—') + '</td><td>' + (v.commit_count || '—') + '</td></tr>';
    });
    html += '</tbody></table></div></div>';
  }

  if (!html) html = '<div class="empty-state"><div class="icon">📁</div><p>No dependency data</p></div>';
  el.innerHTML = html;
}

async function renderModuleDuplication(el, mod) {
  var dup = await load('duplication', 'duplication.json');
  if (!dup || !dup.duplicate_pairs) { el.innerHTML = noData(); return; }
  var modPairs = dup.duplicate_pairs.filter(function (p) {
    return p.block_a.path.startsWith(mod + '/') || p.block_a.path.includes('/' + mod + '/') ||
      p.block_b.path.startsWith(mod + '/') || p.block_b.path.includes('/' + mod + '/');
  });

  var html = '<div class="kpi-grid">';
  html += kpi('Module Dup Pairs', fmt(modPairs.length), '🔗');
  var totalTokens = modPairs.reduce(function (s, p) { return s + p.token_count; }, 0);
  html += kpi('Duplicated Tokens', fmt(totalTokens), '📋');
  html += '</div>';

  if (modPairs.length) {
    html += '<div class="section"><div class="section-title"><span class="icon">📋</span>Duplicate Pairs</div>';
    html += dupPairTable(modPairs.slice(0, 100));
    if (modPairs.length > 100) html += '<div class="section-subtitle">Showing 100 of ' + modPairs.length + '</div>';
    html += '</div>';
  } else {
    html += '<div class="empty-state"><div class="icon">✅</div><p>No duplicates in this module</p></div>';
  }
  el.innerHTML = html;
}

async function renderModuleTrends(el, mod) {
  if (!snapshotIndex || !snapshotIndex.snapshots.length) {
    el.innerHTML = '<div class="empty-state"><div class="icon">📈</div><p>No trend data for "' + mod + '"</p></div>';
    return;
  }
  var delta = await load('delta', 'delta.json');
  var html = '';

  if (delta && delta.module_deltas && delta.module_deltas[mod]) {
    var md = delta.module_deltas[mod];
    html += '<div class="section"><div class="section-title"><span class="icon">📊</span>Module Delta</div>';
    html += '<div class="section-subtitle">Baseline: ' + fmtDate(delta.baseline) + ' → Current: ' + fmtDate(delta.current) + '</div>';
    html += '<div class="table-wrap"><table><thead><tr><th>Metric</th><th>Before</th><th>After</th><th>Delta</th><th>Change %</th><th>Status</th></tr></thead><tbody>';
    md.forEach(function (d) {
      var cls = d.delta > 0 ? 'delta-pos' : d.delta < 0 ? 'delta-neg' : 'delta-zero';
      html += '<tr><td>' + d.metric + '</td><td>' + n(d.before) + '</td><td>' + n(d.after) + '</td><td class="' + cls + '">' + (d.delta > 0 ? '+' : '') + n(d.delta) + '</td><td class="' + cls + '">' + (d.pct_change > 0 ? '+' : '') + n(d.pct_change) + '%</td><td>' + d.indicator + '</td></tr>';
    });
    html += '</tbody></table></div></div>';
  }

  if (snapshotIndex.snapshots.length > 1) {
    html += '<div class="section"><div class="section-title"><span class="icon">📈</span>Module History</div>';
    html += '<div class="chart-grid">';
    html += '<div class="chart-card"><h3>LOC over time</h3><canvas id="chartModHistLoc"></canvas></div>';
    html += '<div class="chart-card"><h3>TD (min) over time</h3><canvas id="chartModHistTd"></canvas></div>';
    html += '<div class="chart-card"><h3>Score over time</h3><canvas id="chartModHistScore"></canvas></div>';
    html += '<div class="chart-card"><h3>Functions over time</h3><canvas id="chartModHistFuncs"></canvas></div>';
    html += '</div></div>';
    el.innerHTML = html;

    var dataPoints = [];
    for (var i = 0; i < snapshotIndex.snapshots.length; i++) {
      var sid = snapshotIndex.snapshots[i].id;
      var r = await Promise.all([
        loadFrom(sid, 'metadata.json'),
        loadFrom(sid, 'modules/' + mod + '_summary.json'),
        loadFrom(sid, 'ratings.json'),
        loadFrom(sid, 'technical_debt.json'),
      ]);
      var meta = r[0], summary = r[1], ratings = r[2], td = r[3];
      if (!meta || !summary) continue;
      var modRating = ratings && ratings.modules ? ratings.modules.find(function (m) { return m.module === mod; }) : null;
      var modTd = td && td.by_module ? td.by_module.find(function (m) { return m.module === mod; }) : null;
      dataPoints.push({
        timestamp: meta.generated_at,
        loc: summary.loc_total, sloc: summary.sloc_total,
        files: summary.files_count, functions: summary.functions_count,
        td_minutes: modTd ? modTd.total_minutes : 0,
        score: modRating ? modRating.score : null,
      });
    }
    dataPoints.sort(function (a, b) { return new Date(a.timestamp) - new Date(b.timestamp); });
    var labels = dataPoints.map(function (d) { return new Date(d.timestamp).toLocaleDateString(); });
    createLineChart('chartModHistLoc', labels, dataPoints.map(function (d) { return d.loc; }), 'LOC');
    createLineChart('chartModHistTd', labels, dataPoints.map(function (d) { return d.td_minutes; }), 'TD (min)');
    createLineChart('chartModHistScore', labels, dataPoints.map(function (d) { return d.score; }), 'Score');
    createLineChart('chartModHistFuncs', labels, dataPoints.map(function (d) { return d.functions; }), 'Functions');
  } else {
    if (!html) html = '<div class="empty-state"><div class="icon">📈</div><p>No trend data for "' + mod + '"</p></div>';
    el.innerHTML = html;
  }
}
