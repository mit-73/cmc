// ══════════════════════════════════════════
// COMPARE / DIFF MODE renderers
// ══════════════════════════════════════════

// ── Dispatcher ──

async function renderCompareProject(el, idA, idB) {
  var tab = currentTab;
  if (tab === 'trends') {
    el.innerHTML = '<div class="empty-state"><div class="icon">📈</div><p>Switch to the Trends tab in normal mode to see historical data.</p></div>';
    return;
  }
  var handlers = {
    overview: cmpProjectOverview,
    hotspots: cmpProjectHotspots,
    techdebt: cmpProjectTechDebt,
    distributions: cmpProjectDistributions,
    dependencies: cmpProjectDependencies,
    duplication: cmpProjectDuplication,
  };
  var fn = handlers[tab];
  if (fn) await fn(el, idA, idB);
  else el.innerHTML = '<div class="empty-state"><p>Tab not implemented for compare</p></div>';
}

async function renderCompareModule(el, idA, idB, mod) {
  var tab = currentTab;
  if (tab === 'trends') {
    el.innerHTML = '<div class="empty-state"><div class="icon">📈</div><p>Switch to the Trends tab in normal mode.</p></div>';
    return;
  }
  var handlers = {
    overview: cmpModuleOverview,
    hotspots: cmpModuleHotspots,
    techdebt: cmpModuleTechDebt,
    distributions: cmpModuleDistributions,
    dependencies: cmpModuleDependencies,
    duplication: cmpModuleDuplication,
  };
  var fn = handlers[tab];
  if (fn) await fn(el, idA, idB, mod);
  else el.innerHTML = '<div class="empty-state"><p>Tab not implemented for compare</p></div>';
}

// ── Helper: module duplication filter ──

function modDupFilter(mod) {
  return function (p) {
    return p.block_a.path.startsWith(mod + '/') || p.block_a.path.includes('/' + mod + '/') ||
      p.block_b.path.startsWith(mod + '/') || p.block_b.path.includes('/' + mod + '/');
  };
}

function dupPairKey(p) {
  return p.block_a.path + ':' + p.block_a.line_start + '-' + p.block_b.path + ':' + p.block_b.line_start;
}

// ══════════════════════════
// Compare: Project
// ══════════════════════════

async function cmpProjectOverview(el, idA, idB) {
  var r = await Promise.all([
    loadFrom(idA, 'project_summary.json'), loadFrom(idB, 'project_summary.json'),
    loadFrom(idA, 'technical_debt.json'), loadFrom(idB, 'technical_debt.json'),
    loadFrom(idA, 'ratings.json'), loadFrom(idB, 'ratings.json'),
    loadFrom(idA, 'duplication.json'), loadFrom(idB, 'duplication.json'),
  ]);
  var psA = r[0], psB = r[1], tdA = r[2], tdB = r[3], ratA = r[4], ratB = r[5], dupA = r[6], dupB = r[7];
  if (!psA || !psB) { el.innerHTML = noData(); return; }

  var html = compareHeader(idA, idB);
  var metrics = [
    { label: 'Modules', a: psA.modules_count, b: psB.modules_count, dir: 'neutral' },
    { label: 'Files', a: psA.files_count, b: psB.files_count, dir: 'neutral' },
    { label: 'Classes', a: psA.classes_count, b: psB.classes_count, dir: 'neutral' },
    { label: 'Functions', a: psA.functions_count, b: psB.functions_count, dir: 'neutral' },
    { label: 'LOC', a: psA.loc_total, b: psB.loc_total, dir: 'neutral' },
    { label: 'SLOC', a: psA.sloc_total, b: psB.sloc_total, dir: 'neutral' },
  ];
  if (tdA && tdB) {
    metrics.push({ label: 'TD (hours)', a: tdA.total_hours, b: tdB.total_hours, dir: 'lower' });
    metrics.push({ label: 'TD/KLOC', a: tdA.total_td_per_loc, b: tdB.total_td_per_loc, dir: 'lower' });
  }
  if (dupA && dupB) metrics.push({ label: 'Duplication %', a: dupA.duplication_pct, b: dupB.duplication_pct, dir: 'lower' });
  var violA = psA.violations ? Object.values(psA.violations).reduce(function (s, v) { return s + (v || 0); }, 0) : 0;
  var violB = psB.violations ? Object.values(psB.violations).reduce(function (s, v) { return s + (v || 0); }, 0) : 0;
  if (violA || violB) metrics.push({ label: 'Violations', a: violA, b: violB, dir: 'lower' });
  html += '<div class="diff-grid">';
  metrics.forEach(function (m) { html += diffCard(m.label, m.a, m.b, m.dir); });
  html += '</div>';

  html += violationsDiffSection(psA.violations, psB.violations);

  if (psA.metrics_summary && psB.metrics_summary) {
    html += '<div class="section"><div class="section-title"><span class="icon">📈</span>Metrics Summary Comparison</div>';
    html += metricsSummaryDiffTable(psA.metrics_summary, psB.metrics_summary);
    html += '</div>';
  }

  if (ratA && ratA.modules && ratB && ratB.modules) {
    var mapA = {}; ratA.modules.forEach(function (m) { mapA[m.module] = m; });
    var mapB = {}; ratB.modules.forEach(function (m) { mapB[m.module] = m; });
    var allMods = {}; Object.keys(mapA).forEach(function (k) { allMods[k] = 1; }); Object.keys(mapB).forEach(function (k) { allMods[k] = 1; });
    html += '<div class="section"><div class="section-title"><span class="icon">🏆</span>Module Ratings Comparison</div>';
    html += '<div class="table-wrap scroll-y"><table><thead><tr><th>Module</th><th>Grade A→B</th><th>Score A</th><th>Score B</th><th>Δ Score</th></tr></thead><tbody>';
    Object.keys(allMods).sort().forEach(function (mod) {
      var a = mapA[mod] || { score: 0, grade: '—' }, b = mapB[mod] || { score: 0, grade: '—' };
      var gc = a.grade === b.grade
        ? '<span class="grade grade-' + b.grade + '">' + b.grade + '</span>'
        : '<span class="grade grade-' + a.grade + '">' + a.grade + '</span> → <span class="grade grade-' + b.grade + '">' + b.grade + '</span>';
      html += '<tr><td><a href="#" onclick="setScope(\'' + mod + '\');return false">' + mod + '</a></td><td>' + gc + '</td>';
      html += deltaCell(a.score, b.score, 'higher');
      html += '</tr>';
    });
    html += '</tbody></table></div></div>';
  }
  el.innerHTML = html;
}

async function cmpProjectHotspots(el, idA, idB) {
  var r = await Promise.all([
    loadFrom(idA, 'risk_hotspots.json'), loadFrom(idB, 'risk_hotspots.json'),
    loadFrom(idA, 'hotspots.json'), loadFrom(idB, 'hotspots.json'),
  ]);
  var riskA = r[0], riskB = r[1], hsA = r[2], hsB = r[3];
  var html = compareHeader(idA, idB);

  if (riskA && riskA.hotspots && riskB && riskB.hotspots) {
    html += '<div class="diff-grid">';
    html += diffCard('Risk Hotspot Count', riskA.count, riskB.count, 'lower');
    html += '</div>';
    var mapA = {}; riskA.hotspots.forEach(function (h) { mapA[h.path] = h; });
    html += '<div class="section"><div class="section-title"><span class="icon">🔥</span>Risk Hotspots — Current (B) with Δ from (A)</div>';
    html += '<div class="table-wrap scroll-y"><table><thead><tr><th>#</th><th>File</th><th>Module</th><th>Risk B</th><th>Risk A</th><th>Δ Risk</th><th>Churn B</th><th>CC Max B</th><th>TD B</th><th>Status</th></tr></thead><tbody>';
    riskB.hotspots.forEach(function (h, i) {
      var prev = mapA[h.path];
      var rA = prev ? prev.risk_score : 0;
      var d = h.risk_score - rA;
      var cls = deltaClass(d, 'lower');
      var ind = !prev ? '🆕' : (Math.abs(d) < 0.0001 ? '⚪' : (d < 0 ? '🟢' : '🔴'));
      html += '<tr><td>' + (i + 1) + '</td><td title="' + h.path + '">' + shortPath(h.path) + '</td><td><a href="#" onclick="setScope(\'' + h.module + '\');return false">' + h.module + '</a></td>';
      html += '<td><strong>' + h.risk_score.toFixed(4) + '</strong></td><td>' + n(rA) + '</td><td class="' + cls + '">' + (d > 0 ? '+' : '') + n(d) + '</td>';
      html += '<td>' + h.churn + '</td><td>' + h.cc_max + '</td><td>' + fmt(h.td_minutes) + '</td><td>' + ind + '</td></tr>';
    });
    html += '</tbody></table></div></div>';
  }

  if (hsA && hsB && hsA.by_cyclomatic_complexity && hsB.by_cyclomatic_complexity)
    html += cmpFuncList('🔴 Top by CC', hsA.by_cyclomatic_complexity, hsB.by_cyclomatic_complexity, 'cyclo', 'lower');
  if (hsA && hsB && hsA.by_lowest_maintainability && hsB.by_lowest_maintainability)
    html += cmpFuncList('🟡 Top by Lowest MI', hsA.by_lowest_maintainability, hsB.by_lowest_maintainability, 'mi', 'higher');
  if (hsA && hsB && hsA.by_weighted_methods && hsB.by_weighted_methods)
    html += cmpClassList('🟠 Top by WMC', hsA.by_weighted_methods, hsB.by_weighted_methods, 'wmc', 'lower');
  if (hsA && hsB && hsA.by_coupling && hsB.by_coupling)
    html += cmpClassList('🔵 Top by CBO', hsA.by_coupling, hsB.by_coupling, 'cbo', 'lower');
  if (hsA && hsB && hsA.by_lowest_cohesion && hsB.by_lowest_cohesion)
    html += cmpClassList('🟣 Top by Lowest TCC', hsA.by_lowest_cohesion, hsB.by_lowest_cohesion, 'tcc', 'higher');
  if (hsA && hsB && hsA.by_technical_debt && hsB.by_technical_debt)
    html += cmpFileList('⏱️ Top by TD', hsA.by_technical_debt, hsB.by_technical_debt, 'technical_debt_minutes', 'lower');
  if (!html || html === compareHeader(idA, idB)) html += noData();
  el.innerHTML = html;
}

async function cmpProjectTechDebt(el, idA, idB) {
  var r = await Promise.all([
    loadFrom(idA, 'technical_debt.json'), loadFrom(idB, 'technical_debt.json'),
    loadFrom(idA, 'hotspots.json'), loadFrom(idB, 'hotspots.json'),
  ]);
  var tdA = r[0], tdB = r[1], hsA = r[2], hsB = r[3];
  if (!tdA || !tdB) { el.innerHTML = noData(); return; }
  var html = compareHeader(idA, idB);

  html += '<div class="diff-grid">';
  html += diffCard('Total TD (days)', tdA.total_days, tdB.total_days, 'lower');
  html += diffCard('Total TD (hours)', tdA.total_hours, tdB.total_hours, 'lower');
  html += diffCard('TD/KLOC (min)', tdA.total_td_per_loc, tdB.total_td_per_loc, 'lower');
  html += diffCard('Total LOC', tdA.total_loc, tdB.total_loc, 'neutral');
  html += '</div>';

  if (tdA.by_module && tdB.by_module) {
    var mapA = {}; tdA.by_module.forEach(function (m) { mapA[m.module] = m; });
    var mapB = {}; tdB.by_module.forEach(function (m) { mapB[m.module] = m; });
    var allMods = {}; Object.keys(mapA).forEach(function (k) { allMods[k] = 1; }); Object.keys(mapB).forEach(function (k) { allMods[k] = 1; });
    html += '<div class="section"><div class="section-title"><span class="icon">📦</span>Tech Debt by Module</div>';
    html += '<div class="table-wrap scroll-y"><table><thead><tr><th>Module</th><th>TD A (h)</th><th>TD B (h)</th><th>Δ hours</th><th>TD/KLOC A</th><th>TD/KLOC B</th><th>Δ TD/KLOC</th><th>LOC A</th><th>LOC B</th><th>Δ LOC</th></tr></thead><tbody>';
    Object.keys(allMods).sort().forEach(function (mod) {
      var a = mapA[mod] || { total_hours: 0, td_per_loc: 0, loc: 0 }, b = mapB[mod] || { total_hours: 0, td_per_loc: 0, loc: 0 };
      html += '<tr><td><a href="#" onclick="setScope(\'' + mod + '\');return false">' + mod + '</a></td>';
      html += deltaCell(a.total_hours, b.total_hours, 'lower');
      html += deltaCell(a.td_per_loc, b.td_per_loc, 'lower');
      html += deltaCell(a.loc, b.loc, 'neutral');
      html += '</tr>';
    });
    html += '</tbody></table></div></div>';
  }

  if (tdA.top_files && tdB.top_files)
    html += cmpFileList('📄 Top Files by TD', tdA.top_files, tdB.top_files, 'technical_debt_minutes', 'lower');
  if (tdA.top_functions && tdB.top_functions)
    html += cmpFuncList('⚙️ Top Functions by TD', tdA.top_functions, tdB.top_functions, 'technical_debt_minutes', 'lower');
  if (tdA.top_classes && tdB.top_classes)
    html += cmpClassList('🏗️ Top Classes by TD', tdA.top_classes, tdB.top_classes, 'technical_debt_minutes', 'lower');
  el.innerHTML = html;
}

async function cmpProjectDistributions(el, idA, idB) {
  var r = await Promise.all([
    loadFrom(idA, 'distributions.json'), loadFrom(idB, 'distributions.json'),
  ]);
  var distA = r[0], distB = r[1];
  if (!distA || !distB || !distA.distributions || !distB.distributions) { el.innerHTML = noData(); return; }
  var html = compareHeader(idA, idB);

  html += '<div class="chart-grid">';
  var chartIdx = 0;
  for (var key in distB.distributions) {
    var dA = distA.distributions[key], dB = distB.distributions[key];
    if (!dA || !dB) continue;
    html += '<div class="chart-card"><h3>' + dB.metric_name + '</h3><canvas id="chartCmpDist' + chartIdx + '"></canvas></div>';
    chartIdx++;
  }
  html += '</div>';
  el.innerHTML = html;

  chartIdx = 0;
  for (var key2 in distB.distributions) {
    var dA2 = distA.distributions[key2], dB2 = distB.distributions[key2];
    if (!dA2 || !dB2) continue;
    createGroupedBarChart('chartCmpDist' + chartIdx,
      dB2.buckets.map(function (b) { return b.label; }),
      dA2.buckets.map(function (b) { return b.count; }),
      dB2.buckets.map(function (b) { return b.count; }),
      'A', 'B');
    chartIdx++;
  }
}

async function cmpProjectDependencies(el, idA, idB) {
  var r = await Promise.all([
    loadFrom(idA, 'dsm.json'), loadFrom(idB, 'dsm.json'),
    loadFrom(idA, 'graph_import.json'), loadFrom(idB, 'graph_import.json'),
  ]);
  var dsmA = r[0], dsmB = r[1], gA = r[2], gB = r[3];
  if (!dsmA && !dsmB && !gA && !gB) { el.innerHTML = noData(); return; }
  var html = compareHeader(idA, idB);

  if (dsmA && dsmB && dsmA.matrix && dsmB.matrix) {
    html += '<div class="diff-grid">';
    if (dsmA.total_imports != null && dsmB.total_imports != null)
      html += diffCard('Total Imports', dsmA.total_imports, dsmB.total_imports, 'lower');
    html += '</div>';
    var allMods = dsmB.modules;
    var idxA = {}; (dsmA.modules || []).forEach(function (m, i) { idxA[m] = i; });
    html += '<div class="section"><div class="section-title"><span class="icon">🔲</span>DSM Diff (B − A)</div>';
    html += '<div class="section-subtitle">Green = fewer imports, Red = more imports</div>';
    html += '<div class="dsm-wrap"><table class="dsm-table"><thead><tr><th></th>';
    allMods.forEach(function (m) { html += '<th title="' + m + '" style="writing-mode:vertical-lr;transform:rotate(180deg);max-width:30px">' + m.substring(0, 12) + '</th>'; });
    html += '</tr></thead><tbody>';
    allMods.forEach(function (m, i) {
      html += '<tr><th style="text-align:right">' + m + '</th>';
      allMods.forEach(function (m2, j) {
        if (i === j) { html += '<td class="dsm-self">—</td>'; return; }
        var vB = dsmB.matrix[i][j];
        var iA = idxA[m], jA = idxA[m2];
        var vA = (iA !== undefined && jA !== undefined && dsmA.matrix[iA]) ? dsmA.matrix[iA][jA] : 0;
        var d = vB - vA;
        if (d === 0 && vB === 0) html += '<td class="dsm-val" style="color:var(--text-dim)">·</td>';
        else if (d === 0) html += '<td class="dsm-val" title="' + m + '→' + m2 + ': ' + vB + ' (no change)">' + vB + '</td>';
        else {
          var bg = d > 0 ? 'rgba(248,81,73,0.3)' : 'rgba(63,185,80,0.3)';
          html += '<td class="dsm-val" style="background:' + bg + '" title="' + m + '→' + m2 + ': ' + vA + '→' + vB + ' (Δ' + (d > 0 ? '+' : '') + d + ')">' + vB + '<br><small style="color:' + (d > 0 ? 'var(--red)' : 'var(--green)') + '">' + (d > 0 ? '+' : '') + d + '</small></td>';
        }
      });
      html += '</tr>';
    });
    html += '</tbody></table></div></div>';

    // Cycles diff
    var cyclesA = dsmA.cycles || [], cyclesB = dsmB.cycles || [];
    if (cyclesA.length || cyclesB.length) {
      var ckA = {}; cyclesA.forEach(function (c) { ckA[c.from + '→' + c.to] = 1; });
      var ckB = {}; cyclesB.forEach(function (c) { ckB[c.from + '→' + c.to] = 1; });
      var newCycles = cyclesB.filter(function (c) { return !ckA[c.from + '→' + c.to]; });
      var removedCycles = cyclesA.filter(function (c) { return !ckB[c.from + '→' + c.to]; });
      html += '<div class="diff-grid">';
      html += diffCard('Dependency Cycles', cyclesA.length, cyclesB.length, 'lower');
      html += '</div>';
      if (newCycles.length) {
        html += '<div class="section"><div class="section-title"><span class="icon">🆕</span>New Cycles <span class="badge badge-red">' + newCycles.length + '</span></div>';
        html += '<div class="table-wrap"><table><thead><tr><th>#</th><th>From</th><th>To</th></tr></thead><tbody>';
        newCycles.forEach(function (c, i) { html += '<tr><td>' + (i + 1) + '</td><td>' + c.from + '</td><td>' + c.to + '</td></tr>'; });
        html += '</tbody></table></div></div>';
      }
      if (removedCycles.length) {
        html += '<div class="section"><div class="section-title"><span class="icon">✅</span>Removed Cycles <span class="badge badge-green">' + removedCycles.length + '</span></div>';
        html += '<div class="table-wrap"><table><thead><tr><th>#</th><th>From</th><th>To</th></tr></thead><tbody>';
        removedCycles.forEach(function (c, i) { html += '<tr><td>' + (i + 1) + '</td><td>' + c.from + '</td><td>' + c.to + '</td></tr>'; });
        html += '</tbody></table></div></div>';
      }
      if (!newCycles.length && !removedCycles.length)
        html += '<div class="section-subtitle">No cycle changes between snapshots.</div>';
    }
  }

  if (gA && gB && gA.edges && gB.edges) {
    var edgeKeyA = {}; gA.edges.forEach(function (e) { edgeKeyA[e.from_node + '→' + e.to_node] = e.weight || 1; });
    var edgeKeyB = {}; gB.edges.forEach(function (e) { edgeKeyB[e.from_node + '→' + e.to_node] = e.weight || 1; });
    var allEdges = {}; Object.keys(edgeKeyA).forEach(function (k) { allEdges[k] = 1; }); Object.keys(edgeKeyB).forEach(function (k) { allEdges[k] = 1; });
    var changed = Object.keys(allEdges).filter(function (k) { return (edgeKeyA[k] || 0) !== (edgeKeyB[k] || 0); }).sort();
    if (changed.length) {
      html += '<div class="section"><div class="section-title"><span class="icon">🕸️</span>Changed Import Edges (' + changed.length + ')</div>';
      html += '<div class="table-wrap scroll-y"><table><thead><tr><th>From→To</th><th>Weight A</th><th>Weight B</th><th>Δ</th><th>Status</th></tr></thead><tbody>';
      changed.forEach(function (k) {
        var wA = edgeKeyA[k] || 0, wB = edgeKeyB[k] || 0;
        var d = wB - wA;
        var ind = wA === 0 ? '🆕' : wB === 0 ? '🗑️' : (d > 0 ? '🔴' : '🟢');
        html += '<tr><td>' + k + '</td><td>' + wA + '</td><td>' + wB + '</td><td class="' + (d > 0 ? 'delta-bad' : 'delta-good') + '">' + (d > 0 ? '+' : '') + d + '</td><td>' + ind + '</td></tr>';
      });
      html += '</tbody></table></div></div>';
    } else {
      html += '<div class="section-subtitle">No import edge changes between snapshots.</div>';
    }
  }
  el.innerHTML = html;
}

async function cmpProjectDuplication(el, idA, idB) {
  var r = await Promise.all([
    loadFrom(idA, 'duplication.json'), loadFrom(idB, 'duplication.json'),
  ]);
  var dupA = r[0], dupB = r[1];
  if (!dupA || !dupB) { el.innerHTML = noData(); return; }
  var html = compareHeader(idA, idB);

  html += '<div class="diff-grid">';
  html += diffCard('Files Analyzed', dupA.total_files, dupB.total_files, 'neutral');
  html += diffCard('Total Tokens', dupA.total_tokens, dupB.total_tokens, 'neutral');
  html += diffCard('Duplicated Tokens', dupA.duplicated_tokens, dupB.duplicated_tokens, 'lower');
  html += diffCard('Duplication %', dupA.duplication_pct, dupB.duplication_pct, 'lower');
  html += diffCard('Duplicate Pairs', dupA.duplicate_pairs_count, dupB.duplicate_pairs_count, 'lower');
  if (dupA.files_with_duplicates != null && dupB.files_with_duplicates != null)
    html += diffCard('Files with Dups', dupA.files_with_duplicates, dupB.files_with_duplicates, 'lower');
  html += '</div>';

  if (dupA.duplicate_pairs && dupB.duplicate_pairs) {
    var setA = {}; dupA.duplicate_pairs.forEach(function (p) { setA[dupPairKey(p)] = p; });
    var setB = {}; dupB.duplicate_pairs.forEach(function (p) { setB[dupPairKey(p)] = p; });
    var newPairs = dupB.duplicate_pairs.filter(function (p) { return !setA[dupPairKey(p)]; });
    var removedPairs = dupA.duplicate_pairs.filter(function (p) { return !setB[dupPairKey(p)]; });

    if (newPairs.length) {
      html += '<div class="section"><div class="section-title"><span class="icon">🆕</span>New Duplicate Pairs <span class="badge badge-red">' + newPairs.length + '</span></div>';
      html += dupPairTable(newPairs.slice(0, 50));
      if (newPairs.length > 50) html += '<div class="section-subtitle">Showing 50 of ' + newPairs.length + '</div>';
      html += '</div>';
    }
    if (removedPairs.length) {
      html += '<div class="section"><div class="section-title"><span class="icon">✅</span>Removed Duplicate Pairs <span class="badge badge-green">' + removedPairs.length + '</span></div>';
      html += dupPairTable(removedPairs.slice(0, 50));
      if (removedPairs.length > 50) html += '<div class="section-subtitle">Showing 50 of ' + removedPairs.length + '</div>';
      html += '</div>';
    }
    if (!newPairs.length && !removedPairs.length)
      html += '<div class="section-subtitle">No duplicate pair changes between snapshots.</div>';
  }
  el.innerHTML = html;
}

// ══════════════════════════
// Compare: Module
// ══════════════════════════

async function cmpModuleOverview(el, idA, idB, mod) {
  var r = await Promise.all([
    loadFrom(idA, 'modules/' + mod + '_summary.json'), loadFrom(idB, 'modules/' + mod + '_summary.json'),
    loadFrom(idA, 'ratings.json'), loadFrom(idB, 'ratings.json'),
    loadFrom(idA, 'modules/' + mod + '_package_analysis.json'), loadFrom(idB, 'modules/' + mod + '_package_analysis.json'),
    loadFrom(idA, 'technical_debt.json'), loadFrom(idB, 'technical_debt.json'),
  ]);
  var sumA = r[0], sumB = r[1], ratA = r[2], ratB = r[3], pkgA = r[4], pkgB = r[5], tdA = r[6], tdB = r[7];
  if (!sumA || !sumB) { el.innerHTML = noData('Module "' + mod + '"'); return; }
  var html = compareHeader(idA, idB);

  var infoA = ratA && ratA.modules ? ratA.modules.find(function (m) { return m.module === mod; }) : null;
  var infoB = ratB && ratB.modules ? ratB.modules.find(function (m) { return m.module === mod; }) : null;
  if (infoA && infoB && infoA.grade !== infoB.grade)
    html += '<div style="margin-bottom:16px;font-size:18px">Grade: <span class="grade grade-' + infoA.grade + '" style="font-size:16px;padding:4px 10px">' + infoA.grade + '</span> → <span class="grade grade-' + infoB.grade + '" style="font-size:16px;padding:4px 10px">' + infoB.grade + '</span></div>';

  html += '<div class="diff-grid">';
  if (infoA && infoB) html += diffCard('Score', infoA.score, infoB.score, 'higher');
  html += diffCard('Files', sumA.files_count, sumB.files_count, 'neutral');
  html += diffCard('Classes', sumA.classes_count, sumB.classes_count, 'neutral');
  html += diffCard('Functions', sumA.functions_count, sumB.functions_count, 'neutral');
  html += diffCard('LOC', sumA.loc_total, sumB.loc_total, 'neutral');
  html += diffCard('SLOC', sumA.sloc_total, sumB.sloc_total, 'neutral');
  // Tech Debt diff cards from summary or global technical_debt.json
  var modTdA = sumA.technical_debt, modTdB = sumB.technical_debt;
  if (!modTdA && tdA && tdA.by_module) modTdA = tdA.by_module.find(function (m) { return m.module === mod; });
  if (!modTdB && tdB && tdB.by_module) modTdB = tdB.by_module.find(function (m) { return m.module === mod; });
  if (modTdA && modTdB) {
    html += diffCard('Tech Debt (days)', modTdA.total_days || 0, modTdB.total_days || 0, 'lower');
    var tdpA = modTdA.td_per_loc != null ? modTdA.td_per_loc : (modTdA.total_td_per_loc || 0);
    var tdpB = modTdB.td_per_loc != null ? modTdB.td_per_loc : (modTdB.total_td_per_loc || 0);
    html += diffCard('TD/KLOC (min)', tdpA, tdpB, 'lower');
  }
  html += '</div>';

  html += violationsDiffSection(sumA.violations, sumB.violations);

  if (sumA.metrics_summary && sumB.metrics_summary) {
    html += '<div class="section"><div class="section-title"><span class="icon">📈</span>Metrics Summary Comparison</div>';
    html += metricsSummaryDiffTable(sumA.metrics_summary, sumB.metrics_summary);
    html += '</div>';
  }

  if (pkgA && pkgB && pkgA.directory_structure && pkgB.directory_structure) {
    var dirMapA = {}; pkgA.directory_structure.forEach(function (d) { dirMapA[d.path] = d; });
    html += '<div class="section"><div class="section-title"><span class="icon">📁</span>Directory Structure Changes</div>';
    html += '<div class="table-wrap scroll-y"><table><thead><tr><th>Path</th><th>Files A</th><th>Files B</th><th>Δ</th><th>LOC A</th><th>LOC B</th><th>Δ LOC</th></tr></thead><tbody>';
    pkgB.directory_structure.forEach(function (d) {
      var a = dirMapA[d.path] || { file_count: 0, total_loc: 0 };
      html += '<tr><td>' + d.path + '</td>';
      html += deltaCell(a.file_count, d.file_count, 'neutral');
      html += deltaCell(a.total_loc, d.total_loc, 'neutral');
      html += '</tr>';
    });
    html += '</tbody></table></div></div>';
  }
  el.innerHTML = html;
}

async function cmpModuleHotspots(el, idA, idB, mod) {
  var r = await Promise.all([
    loadFrom(idA, 'raw/function_metrics.json'), loadFrom(idB, 'raw/function_metrics.json'),
    loadFrom(idA, 'raw/class_metrics.json'), loadFrom(idB, 'raw/class_metrics.json'),
  ]);
  var fA = r[0], fB = r[1], cA = r[2], cB = r[3];
  var html = compareHeader(idA, idB);

  if (fA && fB && fA.functions && fB.functions) {
    var mfA = fA.functions.filter(function (f) { return f.module === mod; }).sort(function (a, b) { return b.cyclo - a.cyclo; }).slice(0, 20);
    var mfB = fB.functions.filter(function (f) { return f.module === mod; }).sort(function (a, b) { return b.cyclo - a.cyclo; }).slice(0, 20);
    if (mfB.length) html += cmpFuncList('🔴 Top by CC', mfA, mfB, 'cyclo', 'lower');

    var miA = fA.functions.filter(function (f) { return f.module === mod; }).sort(function (a, b) { return a.mi - b.mi; }).slice(0, 20);
    var miB = fB.functions.filter(function (f) { return f.module === mod; }).sort(function (a, b) { return a.mi - b.mi; }).slice(0, 20);
    if (miB.length) html += cmpFuncList('🟡 Top by Lowest MI', miA, miB, 'mi', 'higher');

    var wmfpA = fA.functions.filter(function (f) { return f.module === mod; }).sort(function (a, b) { return b.wmfp - a.wmfp; }).slice(0, 20);
    var wmfpB = fB.functions.filter(function (f) { return f.module === mod; }).sort(function (a, b) { return b.wmfp - a.wmfp; }).slice(0, 20);
    if (wmfpB.length) html += cmpFuncList('🟠 Top Functions by WMFP', wmfpA, wmfpB, 'wmfp', 'lower');
  }

  if (cA && cB && cA.classes && cB.classes) {
    var mcWmcA = cA.classes.filter(function (c) { return c.module === mod; }).sort(function (a, b) { return b.wmc - a.wmc; }).slice(0, 20);
    var mcWmcB = cB.classes.filter(function (c) { return c.module === mod; }).sort(function (a, b) { return b.wmc - a.wmc; }).slice(0, 20);
    if (mcWmcB.length) html += cmpClassList('🔵 Top Classes by WMC', mcWmcA, mcWmcB, 'wmc', 'lower');

    var mcCboA = cA.classes.filter(function (c) { return c.module === mod; }).sort(function (a, b) { return b.cbo - a.cbo; }).slice(0, 20);
    var mcCboB = cB.classes.filter(function (c) { return c.module === mod; }).sort(function (a, b) { return b.cbo - a.cbo; }).slice(0, 20);
    if (mcCboB.length) html += cmpClassList('🟣 Top Classes by CBO', mcCboA, mcCboB, 'cbo', 'lower');
  }
  if (!html || html === compareHeader(idA, idB)) html += noData();
  el.innerHTML = html;
}

async function cmpModuleTechDebt(el, idA, idB, mod) {
  var r = await Promise.all([
    loadFrom(idA, 'technical_debt.json'), loadFrom(idB, 'technical_debt.json'),
    loadFrom(idA, 'raw/file_metrics.json'), loadFrom(idB, 'raw/file_metrics.json'),
    loadFrom(idA, 'raw/function_metrics.json'), loadFrom(idB, 'raw/function_metrics.json'),
    loadFrom(idA, 'raw/class_metrics.json'), loadFrom(idB, 'raw/class_metrics.json'),
  ]);
  var tdA = r[0], tdB = r[1], filesA = r[2], filesB = r[3], funcsA = r[4], funcsB = r[5], classesA = r[6], classesB = r[7];
  var html = compareHeader(idA, idB);

  if (tdA && tdB && tdA.by_module && tdB.by_module) {
    var mA = tdA.by_module.find(function (m) { return m.module === mod; }) || { total_hours: 0, td_per_loc: 0, loc: 0, total_days: 0 };
    var mB = tdB.by_module.find(function (m) { return m.module === mod; }) || { total_hours: 0, td_per_loc: 0, loc: 0, total_days: 0 };
    html += '<div class="diff-grid">';
    html += diffCard('Module TD (hours)', mA.total_hours, mB.total_hours, 'lower');
    html += diffCard('TD/KLOC (min)', mA.td_per_loc, mB.td_per_loc, 'lower');
    html += diffCard('Module LOC', mA.loc, mB.loc, 'neutral');
    html += '</div>';
  }
  if (filesA && filesB && filesA.files && filesB.files) {
    var mfA = filesA.files.filter(function (f) { return f.module === mod; }).sort(function (a, b) { return b.technical_debt_minutes - a.technical_debt_minutes; }).slice(0, 20);
    var mfB = filesB.files.filter(function (f) { return f.module === mod; }).sort(function (a, b) { return b.technical_debt_minutes - a.technical_debt_minutes; }).slice(0, 20);
    if (mfB.length) html += cmpFileList('📄 Top Files by TD', mfA, mfB, 'technical_debt_minutes', 'lower');
  }
  if (funcsA && funcsB && funcsA.functions && funcsB.functions) {
    var ffA = funcsA.functions.filter(function (f) { return f.module === mod; }).sort(function (a, b) { return b.technical_debt_minutes - a.technical_debt_minutes; }).slice(0, 20);
    var ffB = funcsB.functions.filter(function (f) { return f.module === mod; }).sort(function (a, b) { return b.technical_debt_minutes - a.technical_debt_minutes; }).slice(0, 20);
    if (ffB.length) html += cmpFuncList('⚙️ Top Functions by TD', ffA, ffB, 'technical_debt_minutes', 'lower');
  }
  if (classesA && classesB && classesA.classes && classesB.classes) {
    var ccA = classesA.classes.filter(function (c) { return c.module === mod; }).sort(function (a, b) { return b.technical_debt_minutes - a.technical_debt_minutes; }).slice(0, 20);
    var ccB = classesB.classes.filter(function (c) { return c.module === mod; }).sort(function (a, b) { return b.technical_debt_minutes - a.technical_debt_minutes; }).slice(0, 20);
    if (ccB.length) html += cmpClassList('🏗️ Top Classes by TD', ccA, ccB, 'technical_debt_minutes', 'lower');
  }
  el.innerHTML = html;
}

async function cmpModuleDistributions(el, idA, idB, mod) {
  var r = await Promise.all([
    loadFrom(idA, 'raw/function_metrics.json'), loadFrom(idB, 'raw/function_metrics.json'),
  ]);
  var fA = r[0], fB = r[1];
  if (!fA || !fB) { el.innerHTML = noData(); return; }
  var mfA = (fA.functions || []).filter(function (f) { return f.module === mod; });
  var mfB = (fB.functions || []).filter(function (f) { return f.module === mod; });
  var html = compareHeader(idA, idB);
  html += '<div class="section-subtitle">A: ' + fmt(mfA.length) + ' functions, B: ' + fmt(mfB.length) + ' functions</div>';

  // Use all distributions for compare
  var cmpDists = DISTRIBUTION_BUCKETS;

  html += '<div class="chart-grid">';
  var idx = 0;
  for (var name in cmpDists) {
    html += '<div class="chart-card"><h3>' + name + '</h3><canvas id="chartCmpModDist' + idx + '"></canvas></div>';
    idx++;
  }
  html += '</div>';
  el.innerHTML = html;

  idx = 0;
  for (var name2 in cmpDists) {
    var d = cmpDists[name2];
    var vA = mfA.map(function (f) { return f[d.key]; });
    var vB = mfB.map(function (f) { return f[d.key]; });
    var labels = d.buckets.map(function (b) { return b[2]; });
    createGroupedBarChart('chartCmpModDist' + idx, labels, bucketize(vA, d.buckets), bucketize(vB, d.buckets), 'A', 'B');
    idx++;
  }
}

async function cmpModuleDependencies(el, idA, idB, mod) {
  var r = await Promise.all([
    loadFrom(idA, 'dsm.json'), loadFrom(idB, 'dsm.json'),
    loadFrom(idA, 'modules/' + mod + '_package_analysis.json'), loadFrom(idB, 'modules/' + mod + '_package_analysis.json'),
  ]);
  var dsmA = r[0], dsmB = r[1], pkgA = r[2], pkgB = r[3];
  var html = compareHeader(idA, idB);

  if (dsmA && dsmB && dsmA.matrix && dsmB.matrix) {
    var iA = dsmA.modules.indexOf(mod), iB = dsmB.modules.indexOf(mod);
    if (iA >= 0 && iB >= 0) {
      var outB = [], inB = [];
      dsmB.modules.forEach(function (m, j) {
        if (m === mod) return;
        var jA = dsmA.modules.indexOf(m);
        var oB = dsmB.matrix[iB][j], oA = jA >= 0 ? dsmA.matrix[iA][jA] : 0;
        var ibB_val = dsmB.matrix[j][iB], ibA_val = (jA >= 0) ? dsmA.matrix[jA][iA] : 0;
        if (oB > 0 || oA > 0) outB.push({ module: m, b: oB, a: oA, d: oB - oA });
        if (ibB_val > 0 || ibA_val > 0) inB.push({ module: m, b: ibB_val, a: ibA_val, d: ibB_val - ibA_val });
      });
      outB.sort(function (a, b) { return b.b - a.b; });
      inB.sort(function (a, b) { return b.b - a.b; });
      html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px">';
      html += '<div class="section"><div class="section-title">Outgoing imports</div><div class="table-wrap"><table><thead><tr><th>Module</th><th>A</th><th>B</th><th>Δ</th></tr></thead><tbody>';
      outB.forEach(function (d) { html += '<tr><td><a href="#" onclick="setScope(\'' + d.module + '\');return false">' + d.module + '</a></td><td>' + d.a + '</td><td>' + d.b + '</td><td class="' + deltaClass(d.d, 'lower') + '">' + (d.d > 0 ? '+' : '') + d.d + '</td></tr>'; });
      html += '</tbody></table></div></div>';
      html += '<div class="section"><div class="section-title">Incoming imports</div><div class="table-wrap"><table><thead><tr><th>Module</th><th>A</th><th>B</th><th>Δ</th></tr></thead><tbody>';
      inB.forEach(function (d) { html += '<tr><td><a href="#" onclick="setScope(\'' + d.module + '\');return false">' + d.module + '</a></td><td>' + d.a + '</td><td>' + d.b + '</td><td class="' + deltaClass(d.d, 'lower') + '">' + (d.d > 0 ? '+' : '') + d.d + '</td></tr>'; });
      html += '</tbody></table></div></div>';
      html += '</div>';
    }
  }

  // Import Statistics diff
  if (pkgA && pkgB && pkgA.import_statistics && pkgB.import_statistics) {
    var isMapA = {}; pkgA.import_statistics.forEach(function (s) { isMapA[s.package_name] = s.count; });
    var isMapB = {}; pkgB.import_statistics.forEach(function (s) { isMapB[s.package_name] = s.count; });
    var allPkgs = {};
    Object.keys(isMapA).forEach(function (k) { allPkgs[k] = 1; });
    Object.keys(isMapB).forEach(function (k) { allPkgs[k] = 1; });
    html += '<div class="section"><div class="section-title"><span class="icon">📊</span>Import Statistics Comparison</div>';
    html += '<div class="table-wrap scroll-y"><table><thead><tr><th>Package</th><th>Count A</th><th>Count B</th><th>Δ</th></tr></thead><tbody>';
    Object.keys(allPkgs).sort().forEach(function (pkg) {
      var a = isMapA[pkg] || 0, b = isMapB[pkg] || 0;
      html += '<tr><td>' + pkg + '</td>';
      html += deltaCell(a, b, 'lower');
      html += '</tr>';
    });
    html += '</tbody></table></div></div>';
  }

  // Cross-Package Imports diff
  if (pkgA && pkgB) {
    var xpA = pkgA.cross_package_imports || [], xpB = pkgB.cross_package_imports || [];
    if (xpA.length || xpB.length) {
      function xpKey(imp) { return (imp.file_path || '') + ':' + (imp.line_number || '') + ':' + (imp.import_uri || ''); }
      var xpSetA = {}; xpA.forEach(function (imp) { xpSetA[xpKey(imp)] = 1; });
      var xpSetB = {}; xpB.forEach(function (imp) { xpSetB[xpKey(imp)] = 1; });
      var newXP = xpB.filter(function (imp) { return !xpSetA[xpKey(imp)]; });
      var remXP = xpA.filter(function (imp) { return !xpSetB[xpKey(imp)]; });
      html += '<div class="diff-grid">';
      html += diffCard('Cross-Package Imports', xpA.length, xpB.length, 'lower');
      html += '</div>';
      if (newXP.length) {
        html += '<div class="section"><div class="section-title"><span class="icon">🆕</span>New Cross-Package Imports <span class="badge badge-red">' + newXP.length + '</span></div>';
        html += '<div class="table-wrap scroll-y"><table><thead><tr><th>#</th><th>File</th><th>Line</th><th>Package</th><th>Import URI</th></tr></thead><tbody>';
        newXP.slice(0, 50).forEach(function (imp, i) {
          html += '<tr><td>' + (i + 1) + '</td><td title="' + imp.file_path + '">' + shortPath(imp.file_path) + '</td><td>' + imp.line_number + '</td><td>' + imp.imported_package + '</td><td style="font-size:12px;word-break:break-all">' + imp.import_uri + '</td></tr>';
        });
        html += '</tbody></table></div></div>';
      }
      if (remXP.length) {
        html += '<div class="section"><div class="section-title"><span class="icon">✅</span>Removed Cross-Package Imports <span class="badge badge-green">' + remXP.length + '</span></div>';
        html += '<div class="table-wrap scroll-y"><table><thead><tr><th>#</th><th>File</th><th>Line</th><th>Package</th><th>Import URI</th></tr></thead><tbody>';
        remXP.slice(0, 50).forEach(function (imp, i) {
          html += '<tr><td>' + (i + 1) + '</td><td title="' + imp.file_path + '">' + shortPath(imp.file_path) + '</td><td>' + imp.line_number + '</td><td>' + imp.imported_package + '</td><td style="font-size:12px;word-break:break-all">' + imp.import_uri + '</td></tr>';
        });
        html += '</tbody></table></div></div>';
      }
    }
  }

  // Shotgun Surgery Candidates diff
  if (pkgA && pkgB) {
    var ssA = pkgA.shotgun_surgery_candidates || [], ssB = pkgB.shotgun_surgery_candidates || [];
    if (ssA.length || ssB.length) {
      var ssMapA = {}; ssA.forEach(function (s) { ssMapA[s.relative_path] = s.usage_count; });
      var ssMapB = {}; ssB.forEach(function (s) { ssMapB[s.relative_path] = s.usage_count; });
      var allSS = {};
      Object.keys(ssMapA).forEach(function (k) { allSS[k] = 1; });
      Object.keys(ssMapB).forEach(function (k) { allSS[k] = 1; });
      html += '<div class="section"><div class="section-title"><span class="icon">🔗</span>Shotgun Surgery Candidates Comparison</div>';
      html += '<div class="table-wrap scroll-y"><table><thead><tr><th>Path</th><th>Usage A</th><th>Usage B</th><th>Δ</th></tr></thead><tbody>';
      Object.keys(allSS).sort().forEach(function (path) {
        var a = ssMapA[path] || 0, b = ssMapB[path] || 0;
        html += '<tr><td>' + path + '</td>';
        html += deltaCell(a, b, 'lower');
        html += '</tr>';
      });
      html += '</tbody></table></div></div>';
    }
  }

  // Git Hotspots diff
  if (pkgA && pkgB) {
    var ghA = pkgA.git_hotspots || [], ghB = pkgB.git_hotspots || [];
    if (ghA.length || ghB.length) {
      var ghMapA = {}; ghA.forEach(function (v) { ghMapA[v.file_path] = v.commit_count; });
      var ghMapB = {}; ghB.forEach(function (v) { ghMapB[v.file_path] = v.commit_count; });
      var allGH = {};
      Object.keys(ghMapA).forEach(function (k) { allGH[k] = 1; });
      Object.keys(ghMapB).forEach(function (k) { allGH[k] = 1; });
      html += '<div class="section"><div class="section-title"><span class="icon">⚠️</span>Git Hotspots Comparison</div>';
      html += '<div class="table-wrap scroll-y"><table><thead><tr><th>Path</th><th>Commits A</th><th>Commits B</th><th>Δ</th></tr></thead><tbody>';
      Object.keys(allGH).sort().forEach(function (path) {
        var a = ghMapA[path] || 0, b = ghMapB[path] || 0;
        html += '<tr><td title="' + path + '">' + shortPath(path) + '</td>';
        html += deltaCell(a, b, 'lower');
        html += '</tr>';
      });
      html += '</tbody></table></div></div>';
    }
  }

  el.innerHTML = html;
}

async function cmpModuleDuplication(el, idA, idB, mod) {
  var r = await Promise.all([
    loadFrom(idA, 'duplication.json'), loadFrom(idB, 'duplication.json'),
  ]);
  var dupA = r[0], dupB = r[1];
  if (!dupA || !dupB) { el.innerHTML = noData(); return; }
  var html = compareHeader(idA, idB);

  var filter = modDupFilter(mod);
  var pairsA = (dupA.duplicate_pairs || []).filter(filter);
  var pairsB = (dupB.duplicate_pairs || []).filter(filter);
  var tokA = pairsA.reduce(function (s, p) { return s + p.token_count; }, 0);
  var tokB = pairsB.reduce(function (s, p) { return s + p.token_count; }, 0);

  html += '<div class="diff-grid">';
  html += diffCard('Module Dup Pairs', pairsA.length, pairsB.length, 'lower');
  html += diffCard('Duplicated Tokens', tokA, tokB, 'lower');
  html += '</div>';

  var setA = {}; pairsA.forEach(function (p) { setA[dupPairKey(p)] = 1; });
  var setB = {}; pairsB.forEach(function (p) { setB[dupPairKey(p)] = 1; });
  var newP = pairsB.filter(function (p) { return !setA[dupPairKey(p)]; });
  var remP = pairsA.filter(function (p) { return !setB[dupPairKey(p)]; });
  if (newP.length) html += '<div class="section"><div class="section-title"><span class="icon">🆕</span>New Pairs <span class="badge badge-red">' + newP.length + '</span></div>' + dupPairTable(newP.slice(0, 30)) + '</div>';
  if (remP.length) html += '<div class="section"><div class="section-title"><span class="icon">✅</span>Removed Pairs <span class="badge badge-green">' + remP.length + '</span></div>' + dupPairTable(remP.slice(0, 30)) + '</div>';
  if (!newP.length && !remP.length) html += '<div class="section-subtitle">No duplication changes for this module.</div>';
  el.innerHTML = html;
}
