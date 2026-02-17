// ══════════════════════════════════════════
// Shared helpers, formatters, and HTML builders
// ══════════════════════════════════════════

// ── Metric label maps (shared across project/module/compare views) ──

const METRIC_LABELS_FULL = {
  cyclo: 'Cyclomatic Complexity', halvol: 'Halstead Volume', mi: 'Maintainability Index',
  mnl: 'Max Nesting Level', nop: 'Parameters', cbo: 'CBO', dit: 'DIT', nom: 'NOM',
  rfc: 'RFC', tcc: 'TCC', wmc: 'WMC', woc: 'WOC', noi: 'Imports', noei: 'External Imports',
  loc_function: 'Func LOC', sloc_function: 'Func SLOC', wmfp: 'WMFP', fpy_function: 'FPY (Function)',
  noam: 'Accessors (NOAM)', noii: 'Inherited Interfaces (NOII)', noom: 'Overridden Methods (NOOM)',
  fpy_class: 'FPY (Class)', wmfp_file: 'WMFP (File)', wmfp_density: 'WMFP Density', fpy_file: 'FPY (File)',
};

const METRIC_LABELS_SHORT = {
  cyclo: 'CC', halvol: 'Halstead Vol', mi: 'MI', mnl: 'Max Nesting', nop: 'Params',
  loc_function: 'Func LOC', sloc_function: 'Func SLOC', wmfp: 'WMFP', fpy_function: 'FPY(Func)',
  cbo: 'CBO', dit: 'DIT', nom: 'NOM', rfc: 'RFC', tcc: 'TCC', wmc: 'WMC', woc: 'WOC',
  noi: 'Imports', noei: 'Ext Imports',
  noam: 'NOAM', noii: 'NOII', noom: 'NOOM',
  fpy_class: 'FPY(Class)', wmfp_file: 'WMFP(File)', wmfp_density: 'WMFP Dens', fpy_file: 'FPY(File)',
};

const COL_LABELS = {
  cyclo: 'CC', mi: 'MI', loc: 'LOC', sloc: 'SLOC', halstead_volume: 'H.Vol',
  wmfp: 'WMFP', fpy: 'FPY', technical_debt_minutes: 'TD(min)', cbo: 'CBO', wmc: 'WMC',
  tcc: 'TCC', rfc: 'RFC', nom: 'NOM', dit: 'DIT', woc: 'WOC', td_per_loc: 'TD/LOC',
  cyclo_sum: 'CC Σ', cyclo_avg: 'CC Avg', mi_avg: 'MI Avg',
  number_of_parameters: 'Params', max_nesting_level: 'Nest',
  noam: 'NOAM', noii: 'NOII', noom: 'NOOM',
  halstead_volume_avg: 'H.Vol Avg', mi_min: 'MI Min', cyclo_max: 'CC Max',
  noi: 'Imports', noei: 'Ext Imports',
  wmfp_density: 'WMFP Dens', dead_code_estimate: 'Dead Code',
  hardcoded_strings: 'Hardcoded Str', magic_numbers: 'Magic Num',
  static_members: 'Static Memb',
};

// ── Distribution bucket configs (shared between module & compare views) ──

const DISTRIBUTION_BUCKETS = {
  'Cyclomatic Complexity': { key: 'cyclo',   buckets: [[0,2,'1'],[2,6,'2-5'],[6,11,'6-10'],[11,21,'11-20'],[21,51,'21-50'],[51,Infinity,'>50']] },
  'Maintainability Index':  { key: 'mi',     buckets: [[0,20,'<20'],[20,40,'20-40'],[40,60,'40-60'],[60,80,'60-80'],[80,101,'80-100']] },
  'Function LOC':            { key: 'loc',    buckets: [[0,11,'1-10'],[11,31,'11-30'],[31,61,'31-60'],[61,101,'61-100'],[101,Infinity,'>100']] },
  'Max Nesting Level':       { key: 'max_nesting_level', buckets: [[0,1,'0'],[1,2,'1'],[2,3,'2'],[3,4,'3'],[4,5,'4'],[5,Infinity,'5+']] },
  'Parameters':              { key: 'number_of_parameters', buckets: [[0,1,'0'],[1,2,'1'],[2,3,'2'],[3,4,'3'],[4,6,'4-5'],[6,Infinity,'6+']] },
};

// ── Formatters ──

function fmt(v) {
  if (v == null) return '—';
  return typeof v === 'number' ? v.toLocaleString() : v;
}

function n(v) {
  if (v == null) return '—';
  return typeof v === 'number' ? (Number.isInteger(v) ? v.toLocaleString() : v.toFixed(2)) : v;
}

function shortPath(p) {
  if (!p) return '—';
  var parts = p.split('/');
  return parts.length > 3 ? '…/' + parts.slice(-2).join('/') : p;
}

function fmtDate(d) {
  if (!d) return '—';
  try { return new Date(d).toLocaleString(); } catch (e) { return d; }
}

function colLabel(c) { return COL_LABELS[c] || c; }

// ── HTML snippets ──

function noData(ctx) {
  return '<div class="empty-state"><div class="icon">📭</div>' +
    '<p>No data available' + (ctx ? ' for ' + ctx : '') +
    '. Run <code style="color:var(--accent)">cmc serve</code> to start.</p></div>';
}

function kpi(label, value, icon, sub) {
  return '<div class="kpi-card"><div class="label">' + (icon || '') + ' ' + label +
    '</div><div class="value">' + value + '</div>' +
    (sub ? '<div class="sub">' + sub + '</div>' : '') + '</div>';
}

function spinnerHtml() {
  return '<div class="content loading"><div class="spinner"></div></div>';
}

// ── Table builders ──

function funcTable(items, showModLink) {
  var h = '<div class="table-wrap scroll-y"><table><thead><tr>' +
    '<th>#</th><th>Function</th><th>Class</th><th>File</th>';
  if (showModLink) h += '<th>Module</th>';
  h += '<th>CC</th><th>MI</th><th>LOC</th><th>WMFP</th><th>FPY</th><th>TD(min)</th></tr></thead><tbody>';
  items.forEach(function (f, i) {
    h += '<tr><td>' + (i + 1) + '</td><td>' + (f.function_name || '—') +
      '</td><td>' + (f.class_name || '—') +
      '</td><td title="' + f.path + ':' + f.line_start + '">' + shortPath(f.path) + '</td>';
    if (showModLink) h += '<td><a href="#" onclick="setScope(\'' + f.module + '\');return false">' + f.module + '</a></td>';
    h += '<td>' + f.cyclo + '</td><td>' + n(f.mi) + '</td><td>' + f.loc +
      '</td><td>' + n(f.wmfp) + '</td><td>' + n(f.fpy) +
      '</td><td>' + fmt(f.technical_debt_minutes) + '</td></tr>';
  });
  return h + '</tbody></table></div>';
}

function classTable(items, showModLink) {
  var h = '<div class="table-wrap scroll-y"><table><thead><tr>' +
    '<th>#</th><th>Class</th><th>File</th>';
  if (showModLink) h += '<th>Module</th>';
  h += '<th>WMC</th><th>CBO</th><th>RFC</th><th>NOM</th><th>TCC</th><th>DIT</th><th>LOC</th><th>TD(min)</th></tr></thead><tbody>';
  items.forEach(function (c, i) {
    h += '<tr><td>' + (i + 1) + '</td><td>' + (c.class_name || '—') +
      '</td><td title="' + c.path + ':' + c.line_start + '">' + shortPath(c.path) + '</td>';
    if (showModLink) h += '<td><a href="#" onclick="setScope(\'' + c.module + '\');return false">' + c.module + '</a></td>';
    h += '<td>' + c.wmc + '</td><td>' + c.cbo + '</td><td>' + c.rfc +
      '</td><td>' + c.nom + '</td><td>' + n(c.tcc) + '</td><td>' + c.dit +
      '</td><td>' + c.loc + '</td><td>' + fmt(c.technical_debt_minutes) + '</td></tr>';
  });
  return h + '</tbody></table></div>';
}

function fileTable(items, showModLink) {
  var h = '<div class="table-wrap scroll-y"><table><thead><tr><th>#</th><th>File</th>';
  if (showModLink) h += '<th>Module</th>';
  h += '<th>TD(min)</th><th>TD/LOC</th><th>CC Σ</th><th>MI Avg</th><th>LOC</th><th>FPY</th></tr></thead><tbody>';
  items.forEach(function (f, i) {
    h += '<tr><td>' + (i + 1) + '</td><td title="' + f.path + '">' + shortPath(f.path) + '</td>';
    if (showModLink) h += '<td><a href="#" onclick="setScope(\'' + f.module + '\');return false">' + f.module + '</a></td>';
    h += '<td>' + fmt(f.technical_debt_minutes) + '</td><td>' + n(f.td_per_loc) +
      '</td><td>' + f.cyclo_sum + '</td><td>' + n(f.mi_avg) +
      '</td><td>' + f.loc + '</td><td>' + n(f.fpy) + '</td></tr>';
  });
  return h + '</tbody></table></div>';
}

function dupPairTable(pairs) {
  var h = '<div class="table-wrap scroll-y"><table><thead><tr>' +
    '<th>#</th><th>File A</th><th>Lines A</th><th>File B</th><th>Lines B</th><th>Tokens</th><th>Lines</th>' +
    '</tr></thead><tbody>';
  pairs.forEach(function (p, i) {
    h += '<tr><td>' + (i + 1) + '</td>' +
      '<td title="' + p.block_a.path + '">' + shortPath(p.block_a.path) + '</td>' +
      '<td>' + p.block_a.line_start + '-' + p.block_a.line_end + '</td>' +
      '<td title="' + p.block_b.path + '">' + shortPath(p.block_b.path) + '</td>' +
      '<td>' + p.block_b.line_start + '-' + p.block_b.line_end + '</td>' +
      '<td>' + p.token_count + '</td><td>' + p.line_count + '</td></tr>';
  });
  return h + '</tbody></table></div>';
}

// ── Metrics summary table (used in overview & compare) ──

function metricsSummaryTable(ms, labelMap) {
  var labels = labelMap || METRIC_LABELS_SHORT;
  var h = '<div class="table-wrap"><table><thead><tr>' +
    '<th>Metric</th><th>Mean</th><th>Median</th><th>P90</th><th>Min</th><th>Max</th><th>Std Dev</th>' +
    '</tr></thead><tbody>';
  for (var k in ms) {
    var v = ms[k];
    if (!v || v.mean === undefined) continue;
    h += '<tr><td>' + (labels[k] || k) + '</td><td>' + n(v.mean) + '</td><td>' + n(v.median) +
      '</td><td>' + n(v.p90) + '</td><td>' + n(v.min_val) + '</td><td>' + n(v.max_val) +
      '</td><td>' + n(v.std_dev) + '</td></tr>';
  }
  return h + '</tbody></table></div>';
}

// ── Diff / delta helpers ──

function diffCard(label, before, after, direction) {
  var d = after - before;
  var pct = before !== 0 ? ((d / before) * 100) : 0;
  var cls = 'delta-neutral', indicator = '⚪';
  if (Math.abs(d) >= 0.01) {
    if (direction === 'higher') {
      cls = d > 0 ? 'delta-good' : 'delta-bad';
      indicator = d > 0 ? '🟢' : '🔴';
    } else if (direction === 'lower') {
      cls = d < 0 ? 'delta-good' : 'delta-bad';
      indicator = d < 0 ? '🟢' : '🔴';
    }
  }
  var sign = d > 0 ? '+' : '';
  return '<div class="diff-card">' +
    '<div class="label">' + label + ' ' + indicator + '</div>' +
    '<div class="values"><span class="before">' + n(before) + '</span>' +
    '<span class="after">' + n(after) + '</span></div>' +
    '<div class="' + cls + '" style="font-size:13px;margin-top:4px">' +
    sign + n(d) + ' (' + sign + pct.toFixed(1) + '%)</div></div>';
}

function deltaCell(before, after, direction) {
  var d = after - before;
  var cls = 'delta-neutral';
  if (Math.abs(d) >= 0.01) {
    if (direction === 'higher') cls = d > 0 ? 'delta-good' : 'delta-bad';
    else if (direction === 'lower') cls = d < 0 ? 'delta-good' : 'delta-bad';
  }
  var sign = d > 0 ? '+' : '';
  return '<td>' + n(before) + '</td><td>' + n(after) + '</td><td class="' + cls + '">' + sign + n(d) + '</td>';
}

function deltaClass(delta, direction) {
  if (Math.abs(delta) < 0.01) return 'delta-neutral';
  if (direction === 'higher') return delta > 0 ? 'delta-good' : 'delta-bad';
  if (direction === 'lower') return delta < 0 ? 'delta-good' : 'delta-bad';
  return 'delta-neutral';
}

function metricsSummaryDiffTable(msA, msB) {
  var h = '<div class="table-wrap"><table><thead><tr>' +
    '<th>Metric</th><th>Mean A</th><th>Mean B</th><th>Δ Mean</th>' +
    '<th>P90 A</th><th>P90 B</th><th>Δ P90</th>' +
    '<th>Max A</th><th>Max B</th><th>Δ Max</th></tr></thead><tbody>';
  var keys = Object.keys(msB);
  keys.forEach(function (k) {
    var a = msA[k], b = msB[k];
    if (!b || b.mean === undefined) return;
    if (!a) a = { mean: 0, p90: 0, max_val: 0 };
    var dir = (k === 'mi' || k === 'tcc' || k === 'fpy_function' || k === 'woc') ? 'higher' : 'lower';
    var dMean = b.mean - (a.mean || 0), dP90 = b.p90 - (a.p90 || 0), dMax = (b.max_val || 0) - (a.max_val || 0);
    h += '<tr><td>' + (METRIC_LABELS_SHORT[k] || k) + '</td>';
    h += '<td>' + n(a.mean) + '</td><td>' + n(b.mean) + '</td><td class="' + deltaClass(dMean, dir) + '">' + (dMean > 0 ? '+' : '') + n(dMean) + '</td>';
    h += '<td>' + n(a.p90) + '</td><td>' + n(b.p90) + '</td><td class="' + deltaClass(dP90, dir) + '">' + (dP90 > 0 ? '+' : '') + n(dP90) + '</td>';
    h += '<td>' + n(a.max_val) + '</td><td>' + n(b.max_val) + '</td><td class="' + deltaClass(dMax, dir) + '">' + (dMax > 0 ? '+' : '') + n(dMax) + '</td>';
    h += '</tr>';
  });
  return h + '</tbody></table></div>';
}

// ── Compare list builders (func / file) ──

function cmpFuncList(title, listA, listB, sortKey, dir) {
  var mapA = {};
  listA.forEach(function (f, i) {
    mapA[(f.path || '') + ':' + (f.line_start || '') + ':' + (f.function_name || '')] = { rank: i + 1, val: f[sortKey] };
  });
  var h = '<div class="section"><div class="section-title">' + title + ' — Current (B) vs (A)</div>';
  h += '<div class="table-wrap scroll-y"><table><thead><tr>' +
    '<th>#B</th><th>#A</th><th>Function</th><th>Class</th><th>Module</th>' +
    '<th>Val B</th><th>Val A</th><th>Δ</th><th>Status</th></tr></thead><tbody>';
  listB.forEach(function (f, i) {
    var key = (f.path || '') + ':' + (f.line_start || '') + ':' + (f.function_name || '');
    var prev = mapA[key];
    var valB = f[sortKey] || 0, valA = prev ? prev.val : 0;
    var d = valB - valA;
    var cls = deltaClass(d, dir);
    var ind = !prev ? '🆕' : (Math.abs(d) < 0.01 ? '⚪' : (dir === 'lower' ? (d < 0 ? '🟢' : '🔴') : (d > 0 ? '🟢' : '🔴')));
    var rankA = prev ? '#' + prev.rank : '—';
    h += '<tr><td>' + (i + 1) + '</td><td>' + rankA + '</td><td>' + (f.function_name || '—') +
      '</td><td>' + (f.class_name || '—') +
      '</td><td><a href="#" onclick="setScope(\'' + f.module + '\');return false">' + f.module + '</a></td>';
    h += '<td>' + n(valB) + '</td><td>' + n(valA) + '</td><td class="' + cls + '">' + (d > 0 ? '+' : '') + n(d) + '</td><td>' + ind + '</td></tr>';
  });
  h += '</tbody></table></div></div>';
  return h;
}

function cmpFileList(title, listA, listB, sortKey, dir) {
  var mapA = {};
  listA.forEach(function (f, i) { mapA[f.path] = { rank: i + 1, val: f[sortKey] }; });
  var h = '<div class="section"><div class="section-title">' + title + ' — B vs A</div>';
  h += '<div class="table-wrap scroll-y"><table><thead><tr>' +
    '<th>#B</th><th>#A</th><th>File</th><th>Module</th>' +
    '<th>Val B</th><th>Val A</th><th>Δ</th><th>Status</th></tr></thead><tbody>';
  listB.slice(0, 30).forEach(function (f, i) {
    var prev = mapA[f.path];
    var valB = f[sortKey] || 0, valA = prev ? prev.val : 0;
    var d = valB - valA;
    var cls = deltaClass(d, dir);
    var ind = !prev ? '🆕' : (Math.abs(d) < 0.01 ? '⚪' : (dir === 'lower' ? (d < 0 ? '🟢' : '🔴') : (d > 0 ? '🟢' : '🔴')));
    h += '<tr><td>' + (i + 1) + '</td><td>' + (prev ? '#' + prev.rank : '—') +
      '</td><td title="' + f.path + '">' + shortPath(f.path) +
      '</td><td><a href="#" onclick="setScope(\'' + (f.module || '') + '\');return false">' + (f.module || '—') + '</a></td>';
    h += '<td>' + n(valB) + '</td><td>' + n(valA) + '</td><td class="' + cls + '">' + (d > 0 ? '+' : '') + n(d) + '</td><td>' + ind + '</td></tr>';
  });
  h += '</tbody></table></div></div>';
  return h;
}

// ── Compare list builder: class ──

function cmpClassList(title, listA, listB, sortKey, dir) {
  var mapA = {};
  listA.forEach(function (c, i) {
    mapA[(c.path || '') + ':' + (c.line_start || '') + ':' + (c.class_name || '')] = { rank: i + 1, val: c[sortKey] };
  });
  var h = '<div class="section"><div class="section-title">' + title + ' — Current (B) vs (A)</div>';
  h += '<div class="table-wrap scroll-y"><table><thead><tr>' +
    '<th>#B</th><th>#A</th><th>Class</th><th>File</th><th>Module</th>' +
    '<th>Val B</th><th>Val A</th><th>Δ</th><th>Status</th></tr></thead><tbody>';
  listB.forEach(function (c, i) {
    var key = (c.path || '') + ':' + (c.line_start || '') + ':' + (c.class_name || '');
    var prev = mapA[key];
    var valB = c[sortKey] || 0, valA = prev ? prev.val : 0;
    var d = valB - valA;
    var cls = deltaClass(d, dir);
    var ind = !prev ? '🆕' : (Math.abs(d) < 0.01 ? '⚪' : (dir === 'lower' ? (d < 0 ? '🟢' : '🔴') : (d > 0 ? '🟢' : '🔴')));
    var rankA = prev ? '#' + prev.rank : '—';
    h += '<tr><td>' + (i + 1) + '</td><td>' + rankA + '</td><td>' + (c.class_name || '—') +
      '</td><td title="' + c.path + ':' + c.line_start + '">' + shortPath(c.path) +
      '</td><td><a href="#" onclick="setScope(\'' + c.module + '\');return false">' + c.module + '</a></td>';
    h += '<td>' + n(valB) + '</td><td>' + n(valA) + '</td><td class="' + cls + '">' + (d > 0 ? '+' : '') + n(d) + '</td><td>' + ind + '</td></tr>';
  });
  h += '</tbody></table></div></div>';
  return h;
}

// ── Violations diff section ──

function violationsDiffSection(violA, violB) {
  if (!violA && !violB) return '';
  violA = violA || {};
  violB = violB || {};
  var allKeys = {};
  Object.keys(violA).forEach(function (k) { allKeys[k] = 1; });
  Object.keys(violB).forEach(function (k) { allKeys[k] = 1; });
  var keys = Object.keys(allKeys);
  if (!keys.length) return '';
  var totalA = Object.values(violA).reduce(function (s, v) { return s + (v || 0); }, 0);
  var totalB = Object.values(violB).reduce(function (s, v) { return s + (v || 0); }, 0);
  if (totalA === 0 && totalB === 0) return '';
  var html = '<div class="section"><div class="section-title"><span class="icon">⚠️</span>Violations Comparison</div>';
  html += '<div class="table-wrap"><table><thead><tr><th>Violation</th><th>A</th><th>B</th><th>Δ</th></tr></thead><tbody>';
  keys.sort().forEach(function (k) {
    var a = violA[k] || 0, b = violB[k] || 0;
    if (a === 0 && b === 0) return;
    var d = b - a;
    var label = VIOLATION_LABELS[k] || k;
    html += '<tr><td>' + label + '</td>';
    html += deltaCell(a, b, 'lower');
    html += '</tr>';
  });
  html += '<tr style="font-weight:bold"><td>Total</td>';
  html += deltaCell(totalA, totalB, 'lower');
  html += '</tr>';
  html += '</tbody></table></div></div>';
  return html;
}

// ── Bucket distribution helper ──

function bucketize(values, buckets) {
  return buckets.map(function (b) {
    return values.filter(function (v) { return v >= b[0] && v < b[1]; }).length;
  });
}

// ── Violations table ──

var VIOLATION_LABELS = {
  cyclo_high: '⚠️ High Complexity',
  cyclo_very_high: '🔴 Very High Complexity',
  mi_poor: '🟡 Poor Maintainability',
  mnl_critical: '📐 Critical Nesting',
  god_classes: '🏗️ God Classes',
  low_cohesion: '🔗 Low Cohesion',
  high_coupling: '🔌 High Coupling',
  excessive_params: '📋 Excessive Params',
  excessive_imports: '📦 Excessive Imports',
  magic_numbers_high: '🔢 Magic Numbers',
  hardcoded_strings_high: '📝 Hardcoded Strings',
  potential_dead_code: '💀 Potential Dead Code',
};

function violationsSection(violations) {
  if (!violations) return '';
  var total = Object.values(violations).reduce(function (s, v) { return s + (v || 0); }, 0);
  if (total === 0) return '';
  var html = '<div class="section"><div class="section-title"><span class="icon">⚠️</span>Violations <span class="badge badge-red">' + total + '</span></div>';
  html += '<div class="kpi-grid">';
  for (var key in violations) {
    var count = violations[key];
    if (count > 0) {
      var label = VIOLATION_LABELS[key] || key;
      html += kpi(label.replace(/^[^\s]+\s/, ''), count, label.split(' ')[0]);
    }
  }
  html += '</div></div>';
  return html;
}
