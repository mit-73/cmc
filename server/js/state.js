// ══════════════════════════════════════════
// Application state & data cache
// ══════════════════════════════════════════

var currentScope = 'project';
var currentTab = 'overview';
var modules = [];
var chartInstances = [];
var snapshotIndex = null;
var activeSnapshot = null;
var compareMode = false;

// Data cache keyed by "snapshotId:path"
var DC = {};

function destroyCharts() {
  chartInstances.forEach(function (c) { try { c.destroy(); } catch (e) { } });
  chartInstances = [];
}

// ── Unified data loader ──

function loadFromSnapshot(snapId, relPath) {
  var url = './history/' + snapId + '/' + relPath;
  var ck = snapId + ':' + relPath;
  if (DC[ck]) return Promise.resolve(DC[ck]);
  return fetch(url).then(function (r) {
    if (!r.ok) return null;
    return r.json().then(function (data) { DC[ck] = data; return data; });
  }).catch(function () { return null; });
}

// Convenience: load from active snapshot
function load(key, relPath) {
  return loadFromSnapshot(activeSnapshot, relPath);
}

// Alias kept for backward compat
var loadFrom = loadFromSnapshot;
