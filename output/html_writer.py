"""HTML dashboard generator.

Produces a self-contained HTML file with embedded Chart.js for interactive
visualization of metrics, ratings, distributions, DSM, risk hotspots,
and historical trends with diff/delta support.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..models import (
    ClassMetrics,
    FileMetrics,
    FunctionMetrics,
    ModuleSummary,
    ProjectSummary,
    StatsSummary,
)


def write_html_dashboard(
    project_summary: ProjectSummary,
    module_summaries: List[ModuleSummary],
    function_metrics: List[FunctionMetrics],
    class_metrics: List[ClassMetrics],
    file_metrics: List[FileMetrics],
    module_ratings: Dict[str, tuple],
    distributions: Dict[str, Any],
    risk_hotspots: List[Any],
    dsm_result: Optional[Any],
    duplication_result: Optional[Any],
    snapshot_delta: Optional[Any],
    history_snapshots: List[Any],
    output_dir: str,
) -> str:
    """Generate a self-contained HTML dashboard.

    Returns path to the written file.
    """
    path = os.path.join(output_dir, "dashboard.html")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Prepare data for embedding
    data = _build_dashboard_data(
        project_summary, module_summaries, function_metrics,
        class_metrics, file_metrics, module_ratings, distributions,
        risk_hotspots, dsm_result, duplication_result, snapshot_delta,
        history_snapshots,
    )

    html = _render_html(data)

    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)

    return path


def _build_dashboard_data(
    project_summary, module_summaries, function_metrics,
    class_metrics, file_metrics, module_ratings, distributions,
    risk_hotspots, dsm_result, duplication_result, snapshot_delta,
    history_snapshots,
) -> dict:
    """Build the JSON data blob to embed in the HTML."""
    ps = project_summary

    # Module comparison table
    module_table = []
    for ms in sorted(module_summaries, key=lambda m: m.technical_debt.total_minutes, reverse=True):
        score, grade = module_ratings.get(ms.module, (0.0, "—"))
        cc_stats = ms.metrics_summary.get("cyclo")
        mi_stats = ms.metrics_summary.get("mi")
        fpy_stats = ms.metrics_summary.get("fpy_function")
        module_table.append({
            "name": ms.module,
            "grade": grade,
            "score": round(score, 1),
            "files": ms.files_count,
            "classes": ms.classes_count,
            "functions": ms.functions_count,
            "loc": ms.loc_total,
            "sloc": ms.sloc_total,
            "cc_avg": round(cc_stats.mean, 2) if isinstance(cc_stats, StatsSummary) else 0,
            "mi_avg": round(mi_stats.mean, 2) if isinstance(mi_stats, StatsSummary) else 0,
            "fpy_avg": round(fpy_stats.mean, 3) if isinstance(fpy_stats, StatsSummary) else 0,
            "td_hours": round(ms.technical_debt.total_hours, 1),
            "td_minutes": round(ms.technical_debt.total_minutes, 0),
        })

    # Top function hotspots
    top_functions = sorted(function_metrics, key=lambda f: f.cyclo, reverse=True)[:20]
    fn_hotspots = [{
        "name": f.function_name,
        "class": f.class_name or "—",
        "module": f.module,
        "cc": f.cyclo,
        "mi": round(f.mi, 1),
        "loc": f.loc,
        "fpy": round(f.fpy, 2),
        "wmfp": round(f.wmfp, 2),
        "path": f.path,
        "line": f.line_start,
    } for f in top_functions]

    # Top class hotspots
    top_classes = sorted(class_metrics, key=lambda c: c.wmc, reverse=True)[:20]
    cls_hotspots = [{
        "name": c.class_name,
        "module": c.module,
        "wmc": c.wmc,
        "cbo": c.cbo,
        "rfc": c.rfc,
        "tcc": round(c.tcc, 3),
        "nom": c.nom,
        "loc": c.loc,
        "fpy": round(c.fpy, 2),
    } for c in top_classes]

    # Distribution data
    dist_data = {}
    for name, hist in distributions.items():
        dist_data[name] = {
            "title": hist.metric_name,
            "labels": [b.label for b in hist.buckets],
            "values": [b.count for b in hist.buckets],
            "pcts": [round(b.pct, 1) for b in hist.buckets],
        }

    # Violations
    v = ps.violations
    violations = {
        "cyclo_high": v.cyclo_high,
        "cyclo_very_high": v.cyclo_very_high,
        "mi_poor": v.mi_poor,
        "mnl_critical": v.mnl_critical,
        "god_classes": v.god_classes,
        "low_cohesion": v.low_cohesion,
        "high_coupling": v.high_coupling,
        "excessive_params": v.excessive_params,
        "excessive_imports": v.excessive_imports,
        "magic_numbers": v.magic_numbers_high,
        "hardcoded_strings": v.hardcoded_strings_high,
        "dead_code": v.potential_dead_code,
    }

    # Risk hotspots
    risk_data = []
    if risk_hotspots:
        for rh in risk_hotspots[:30]:
            risk_data.append(rh.to_dict() if hasattr(rh, 'to_dict') else rh)

    # DSM
    dsm_data = None
    if dsm_result:
        dsm_data = dsm_result.to_dict() if hasattr(dsm_result, 'to_dict') else dsm_result

    # Duplication
    dup_data = None
    if duplication_result:
        dup_data = duplication_result.to_dict() if hasattr(duplication_result, 'to_dict') else duplication_result

    # Delta
    delta_data = None
    if snapshot_delta:
        delta_data = snapshot_delta.to_dict() if hasattr(snapshot_delta, 'to_dict') else snapshot_delta

    # History trend
    trend_data = []
    for s in history_snapshots:
        if isinstance(s, dict):
            trend_data.append(s)
        elif hasattr(s, 'to_dict'):
            trend_data.append(s.to_dict())

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "project": {
            "modules": ps.modules_count,
            "files": ps.files_count,
            "classes": ps.classes_count,
            "functions": ps.functions_count,
            "loc": ps.loc_total,
            "sloc": ps.sloc_total,
            "td_hours": round(ps.technical_debt.total_hours, 1),
            "td_days": round(ps.technical_debt.total_days, 1),
        },
        "violations": violations,
        "module_table": module_table,
        "fn_hotspots": fn_hotspots,
        "cls_hotspots": cls_hotspots,
        "distributions": dist_data,
        "risk_hotspots": risk_data,
        "dsm": dsm_data,
        "duplication": dup_data,
        "delta": delta_data,
        "history": trend_data,
    }


def _render_html(data: dict) -> str:
    """Render the complete HTML dashboard."""
    data_json = json.dumps(data, ensure_ascii=False, indent=None)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Code Metrics Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
:root {{
  --bg: #0d1117; --surface: #161b22; --border: #30363d;
  --text: #c9d1d9; --text2: #8b949e; --accent: #58a6ff;
  --green: #3fb950; --yellow: #d29922; --red: #f85149; --orange: #db6d28;
  --grade-a: #3fb950; --grade-b: #56d364; --grade-c: #d29922;
  --grade-d: #db6d28; --grade-e: #f85149;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font: 14px/1.6 -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: var(--bg); color: var(--text); padding: 20px; }}
h1 {{ font-size: 24px; margin-bottom: 4px; }}
h2 {{ font-size: 18px; margin: 24px 0 12px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }}
h3 {{ font-size: 15px; margin: 16px 0 8px; color: var(--text2); }}
.subtitle {{ color: var(--text2); font-size: 13px; margin-bottom: 20px; }}
.grid {{ display: grid; gap: 16px; }}
.grid-2 {{ grid-template-columns: 1fr 1fr; }}
.grid-3 {{ grid-template-columns: 1fr 1fr 1fr; }}
.grid-4 {{ grid-template-columns: repeat(4, 1fr); }}
.card {{ background: var(--surface); border: 1px solid var(--border);
         border-radius: 8px; padding: 16px; }}
.card-header {{ font-size: 13px; color: var(--text2); text-transform: uppercase;
                letter-spacing: 0.5px; margin-bottom: 8px; }}
.stat-value {{ font-size: 28px; font-weight: 600; }}
.stat-label {{ font-size: 12px; color: var(--text2); }}
.grade {{ display: inline-flex; align-items: center; justify-content: center;
          width: 32px; height: 32px; border-radius: 6px; font-weight: 700;
          font-size: 16px; color: #fff; }}
.grade-A {{ background: var(--grade-a); }}
.grade-B {{ background: var(--grade-b); }}
.grade-C {{ background: var(--grade-c); }}
.grade-D {{ background: var(--grade-d); }}
.grade-E {{ background: var(--grade-e); }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th {{ text-align: left; padding: 8px; border-bottom: 2px solid var(--border);
     font-weight: 600; color: var(--text2); position: sticky; top: 0;
     background: var(--surface); cursor: pointer; user-select: none; }}
th:hover {{ color: var(--accent); }}
td {{ padding: 6px 8px; border-bottom: 1px solid var(--border); }}
tr:hover td {{ background: rgba(88,166,255,0.05); }}
.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
.delta-pos {{ color: var(--green); }}
.delta-neg {{ color: var(--red); }}
.delta-zero {{ color: var(--text2); }}
.tabs {{ display: flex; gap: 2px; margin-bottom: 16px; flex-wrap: wrap; }}
.tab {{ padding: 8px 16px; cursor: pointer; border-radius: 6px 6px 0 0;
        background: var(--surface); border: 1px solid var(--border);
        border-bottom: none; color: var(--text2); font-size: 13px; }}
.tab.active {{ background: var(--bg); color: var(--accent); border-color: var(--accent);
               border-bottom: 2px solid var(--bg); margin-bottom: -1px; }}
.tab-content {{ display: none; }}
.tab-content.active {{ display: block; }}
.chart-container {{ position: relative; height: 300px; }}
.dsm-table th, .dsm-table td {{ text-align: center; padding: 4px 6px; font-size: 12px; min-width: 45px; }}
.dsm-table td.diag {{ background: var(--border); }}
.dsm-table td.cycle {{ background: rgba(248,81,73,0.2); }}
.progress-bar {{ height: 8px; background: var(--border); border-radius: 4px; overflow: hidden; }}
.progress-fill {{ height: 100%; border-radius: 4px; transition: width 0.3s; }}
.search-box {{ padding: 6px 12px; background: var(--surface); border: 1px solid var(--border);
               border-radius: 6px; color: var(--text); width: 300px; margin-bottom: 12px; }}
@media (max-width: 900px) {{ .grid-2,.grid-3,.grid-4 {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>

<h1>📊 Code Metrics Dashboard</h1>
<p class="subtitle">Generated: <span id="gen-date"></span></p>

<div class="tabs" id="main-tabs">
  <div class="tab active" data-tab="overview">Overview</div>
  <div class="tab" data-tab="modules">Modules</div>
  <div class="tab" data-tab="hotspots">Hotspots</div>
  <div class="tab" data-tab="distributions">Distributions</div>
  <div class="tab" data-tab="dependencies">Dependencies</div>
  <div class="tab" data-tab="duplication">Duplication</div>
  <div class="tab" data-tab="trends">Trends & Delta</div>
</div>

<!-- OVERVIEW -->
<div class="tab-content active" id="tab-overview">
  <div class="grid grid-4" id="kpi-cards"></div>
  <h2>Module Ratings</h2>
  <div class="grid grid-3" id="rating-cards"></div>
  <h2>Violations Summary</h2>
  <div class="grid grid-2">
    <div class="card"><div class="chart-container"><canvas id="violations-chart"></canvas></div></div>
    <div class="card" id="violations-table-wrap"></div>
  </div>
</div>

<!-- MODULES -->
<div class="tab-content" id="tab-modules">
  <h2>Module Comparison</h2>
  <div class="card" style="overflow-x:auto">
    <table id="module-table"><thead></thead><tbody></tbody></table>
  </div>
  <h2>Technical Debt by Module</h2>
  <div class="card"><div class="chart-container"><canvas id="td-chart"></canvas></div></div>
  <h2>Module Radar</h2>
  <div class="grid grid-2" id="radar-container"></div>
</div>

<!-- HOTSPOTS -->
<div class="tab-content" id="tab-hotspots">
  <h2>Risk Hotspots (Churn × Complexity)</h2>
  <div class="card" style="overflow-x:auto">
    <table id="risk-table"><thead></thead><tbody></tbody></table>
  </div>
  <h2>Top Functions (CC)</h2>
  <div class="card" style="overflow-x:auto">
    <table id="fn-table"><thead></thead><tbody></tbody></table>
  </div>
  <h2>Top Classes (WMC)</h2>
  <div class="card" style="overflow-x:auto">
    <table id="cls-table"><thead></thead><tbody></tbody></table>
  </div>
</div>

<!-- DISTRIBUTIONS -->
<div class="tab-content" id="tab-distributions">
  <div class="grid grid-2" id="dist-charts"></div>
</div>

<!-- DEPENDENCIES (DSM) -->
<div class="tab-content" id="tab-dependencies">
  <h2>Design Structure Matrix (DSM)</h2>
  <div class="card" id="dsm-container" style="overflow-x:auto"></div>
</div>

<!-- DUPLICATION -->
<div class="tab-content" id="tab-duplication">
  <h2>Code Duplication</h2>
  <div class="grid grid-3" id="dup-kpi"></div>
  <h2>Duplicate Pairs (top 50)</h2>
  <div class="card" style="overflow-x:auto">
    <table id="dup-table"><thead></thead><tbody></tbody></table>
  </div>
</div>

<!-- TRENDS & DELTA -->
<div class="tab-content" id="tab-trends">
  <h2>Delta vs Previous Run</h2>
  <div class="card" id="delta-container"></div>
  <h2>Historical Trends</h2>
  <div class="grid grid-2" id="trend-charts"></div>
</div>

<script>
const D = {data_json};

// ─── Tabs ────────────────────────────────────
document.querySelectorAll('.tab').forEach(tab => {{
  tab.addEventListener('click', () => {{
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
  }});
}});

// ─── Helpers ─────────────────────────────────
const $ = id => document.getElementById(id);
const gradeClass = g => 'grade grade-' + (g || 'E');
const fmt = n => typeof n === 'number' ? n.toLocaleString() : n;

function sortTable(table, col, type) {{
  const tbody = table.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const dir = table.dataset.sortCol == col && table.dataset.sortDir == 'asc' ? 'desc' : 'asc';
  table.dataset.sortCol = col;
  table.dataset.sortDir = dir;
  rows.sort((a, b) => {{
    let va = a.cells[col].textContent.trim();
    let vb = b.cells[col].textContent.trim();
    if (type === 'num') {{ va = parseFloat(va) || 0; vb = parseFloat(vb) || 0; }}
    if (dir === 'asc') return va > vb ? 1 : va < vb ? -1 : 0;
    return va < vb ? 1 : va > vb ? -1 : 0;
  }});
  rows.forEach(r => tbody.appendChild(r));
}}

function makeTable(id, headers, rows, types) {{
  const table = $(id);
  const thead = table.querySelector('thead');
  const tbody = table.querySelector('tbody');
  thead.innerHTML = '<tr>' + headers.map((h, i) =>
    `<th onclick="sortTable(this.closest('table'),${{i}},'${{(types&&types[i])||'str'}}')">${{h}}</th>`
  ).join('') + '</tr>';
  tbody.innerHTML = rows.map(r => '<tr>' + r.map((v, i) =>
    `<td class="${{types&&types[i]==='num'?'num':''}}">${{v}}</td>`
  ).join('') + '</tr>').join('');
}}

// ─── Overview ────────────────────────────────
$('gen-date').textContent = D.generated_at;

const p = D.project;
$('kpi-cards').innerHTML = [
  ['Modules', p.modules], ['Files', fmt(p.files)],
  ['Classes', fmt(p.classes)], ['Functions', fmt(p.functions)],
  ['LOC', fmt(p.loc)], ['SLOC', fmt(p.sloc)],
  ['Tech Debt', p.td_hours + 'h'], ['TD Days', p.td_days + 'd'],
].map(([l, v]) => `<div class="card"><div class="card-header">${{l}}</div><div class="stat-value">${{v}}</div></div>`).join('');

// Rating cards
$('rating-cards').innerHTML = D.module_table.map(m => `
  <div class="card" style="display:flex;gap:12px;align-items:center">
    <div class="${{gradeClass(m.grade)}}">${{m.grade}}</div>
    <div>
      <div style="font-weight:600">${{m.name}}</div>
      <div class="stat-label">Score: ${{m.score}} · TD: ${{m.td_hours}}h · CC: ${{m.cc_avg}} · MI: ${{m.mi_avg}}</div>
    </div>
  </div>
`).join('');

// Violations chart
const vLabels = Object.keys(D.violations);
const vValues = Object.values(D.violations);
new Chart($('violations-chart'), {{
  type: 'bar',
  data: {{
    labels: vLabels,
    datasets: [{{ label: 'Count', data: vValues,
      backgroundColor: vValues.map(v => v > 10 ? '#f85149' : v > 0 ? '#d29922' : '#3fb950') }}]
  }},
  options: {{ responsive: true, maintainAspectRatio: false, indexAxis: 'y',
    plugins: {{ legend: {{ display: false }} }},
    scales: {{ x: {{ ticks: {{ color: '#8b949e' }} }}, y: {{ ticks: {{ color: '#c9d1d9', font: {{ size: 11 }} }} }} }}
  }}
}});

$('violations-table-wrap').innerHTML = '<table><thead><tr><th>Violation</th><th class="num">Count</th></tr></thead><tbody>'
  + vLabels.map((l, i) => `<tr><td>${{l}}</td><td class="num">${{vValues[i]}}</td></tr>`).join('') + '</tbody></table>';

// ─── Modules ─────────────────────────────────
makeTable('module-table',
  ['Grade', 'Module', 'Files', 'Classes', 'Functions', 'LOC', 'CC avg', 'MI avg', 'FPY', 'TD (h)', 'Score'],
  D.module_table.map(m => [
    `<span class="${{gradeClass(m.grade)}}" style="width:24px;height:24px;font-size:12px">${{m.grade}}</span>`,
    m.name, m.files, m.classes, m.functions, fmt(m.loc),
    m.cc_avg, m.mi_avg, m.fpy_avg, m.td_hours, m.score
  ]),
  ['str','str','num','num','num','num','num','num','num','num','num']
);

// TD bar chart
new Chart($('td-chart'), {{
  type: 'bar',
  data: {{
    labels: D.module_table.map(m => m.name),
    datasets: [{{ label: 'TD (hours)', data: D.module_table.map(m => m.td_hours),
      backgroundColor: D.module_table.map(m => {{
        if (m.grade === 'A') return '#3fb950';
        if (m.grade === 'B') return '#56d364';
        if (m.grade === 'C') return '#d29922';
        if (m.grade === 'D') return '#db6d28';
        return '#f85149';
      }}) }}]
  }},
  options: {{ responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{ y: {{ ticks: {{ color: '#8b949e' }} }}, x: {{ ticks: {{ color: '#c9d1d9' }} }} }}
  }}
}});

// Radar charts (top 6 modules by TD)
const radarModules = D.module_table.slice(0, 6);
$('radar-container').innerHTML = radarModules.map((m, i) => `
  <div class="card"><div class="chart-container"><canvas id="radar-${{i}}"></canvas></div></div>
`).join('');
radarModules.forEach((m, i) => {{
  const maxCC = Math.max(...D.module_table.map(x => x.cc_avg), 1);
  const maxTD = Math.max(...D.module_table.map(x => x.td_hours), 1);
  new Chart($('radar-' + i), {{
    type: 'radar',
    data: {{
      labels: ['MI', 'FPY×100', '100-CC', 'Cohesion', '100-TD%'],
      datasets: [{{
        label: m.name + ' (' + m.grade + ')',
        data: [
          m.mi_avg,
          m.fpy_avg * 100,
          Math.max(0, 100 - m.cc_avg / maxCC * 100),
          50, // placeholder
          Math.max(0, 100 - m.td_hours / maxTD * 100),
        ],
        borderColor: '#58a6ff', backgroundColor: 'rgba(88,166,255,0.15)',
      }}]
    }},
    options: {{ responsive: true, maintainAspectRatio: false,
      scales: {{ r: {{ min: 0, max: 100, ticks: {{ display: false }},
        grid: {{ color: '#30363d' }}, pointLabels: {{ color: '#8b949e' }} }} }},
      plugins: {{ legend: {{ labels: {{ color: '#c9d1d9' }} }} }}
    }}
  }});
}});

// ─── Hotspots ────────────────────────────────
if (D.risk_hotspots.length) {{
  makeTable('risk-table',
    ['#', 'File', 'Module', 'Churn', 'CC sum', 'CC max', 'TD (min)', 'MI', 'Risk'],
    D.risk_hotspots.map((r, i) => [
      i+1, r.path.split('/').slice(-3).join('/'), r.module,
      r.churn, r.cc_sum, r.cc_max, r.td_minutes.toFixed(0), r.mi_avg.toFixed(1),
      `<div class="progress-bar" style="width:100px"><div class="progress-fill" style="width:${{r.risk_score*100}}%;background:${{
        r.risk_score > 0.5 ? '#f85149' : r.risk_score > 0.2 ? '#d29922' : '#3fb950'
      }}"></div></div> ${{(r.risk_score*100).toFixed(0)}}%`,
    ]),
    ['num','str','str','num','num','num','num','num','str']
  );
}} else {{ $('risk-table').parentElement.innerHTML = '<p style="color:var(--text2)">No risk hotspots (enable --pkg-analysis with git data).</p>'; }}

makeTable('fn-table',
  ['#', 'Function', 'Class', 'Module', 'CC', 'MI', 'LOC', 'FPY', 'WMFP'],
  D.fn_hotspots.map((f, i) => [
    i+1, f.name, f.class, f.module, f.cc, f.mi, f.loc, f.fpy, f.wmfp
  ]),
  ['num','str','str','str','num','num','num','num','num']
);

makeTable('cls-table',
  ['#', 'Class', 'Module', 'WMC', 'CBO', 'RFC', 'TCC', 'NOM', 'LOC', 'FPY'],
  D.cls_hotspots.map((c, i) => [
    i+1, c.name, c.module, c.wmc, c.cbo, c.rfc, c.tcc, c.nom, c.loc, c.fpy
  ]),
  ['num','str','str','num','num','num','num','num','num','num']
);

// ─── Distributions ───────────────────────────
const distContainer = $('dist-charts');
Object.entries(D.distributions).forEach(([key, d]) => {{
  const card = document.createElement('div');
  card.className = 'card';
  card.innerHTML = `<h3>${{d.title}}</h3><div class="chart-container"><canvas id="dist-${{key}}"></canvas></div>`;
  distContainer.appendChild(card);

  new Chart(card.querySelector('canvas'), {{
    type: 'bar',
    data: {{
      labels: d.labels,
      datasets: [{{ label: 'Count', data: d.values,
        backgroundColor: '#58a6ff' }}]
    }},
    options: {{ responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }},
        tooltip: {{ callbacks: {{ label: ctx => ctx.raw.toLocaleString() + ' (' + d.pcts[ctx.dataIndex] + '%)' }} }} }},
      scales: {{ y: {{ ticks: {{ color: '#8b949e' }} }}, x: {{ ticks: {{ color: '#c9d1d9' }} }} }}
    }}
  }});
}});

// ─── DSM ─────────────────────────────────────
if (D.dsm) {{
  const m = D.dsm.modules;
  const mx = D.dsm.matrix;
  const cycleSet = new Set(D.dsm.cycles.map(c => c.from + '|' + c.to).concat(D.dsm.cycles.map(c => c.to + '|' + c.from)));
  let html = '<table class="dsm-table"><thead><tr><th></th>' + m.map(n => `<th title="${{n}}">${{n.length > 8 ? n.slice(0,7)+'…' : n}}</th>`).join('') + '</tr></thead><tbody>';
  for (let i = 0; i < m.length; i++) {{
    html += '<tr><th>' + m[i] + '</th>';
    for (let j = 0; j < m.length; j++) {{
      const cls = i === j ? 'diag' : (cycleSet.has(m[i]+'|'+m[j]) && mx[i][j] > 0 ? 'cycle' : '');
      const val = i === j ? '—' : (mx[i][j] === 0 ? '·' : mx[i][j]);
      html += `<td class="${{cls}}">${{val}}</td>`;
    }}
    html += '</tr>';
  }}
  html += '</tbody></table>';
  if (D.dsm.cycles.length) {{
    html += '<h3 style="margin-top:12px">⚠️ Cyclic Dependencies</h3><ul>';
    D.dsm.cycles.forEach(c => {{ html += `<li><strong>${{c.from}}</strong> ↔ <strong>${{c.to}}</strong></li>`; }});
    html += '</ul>';
  }} else {{
    html += '<p style="margin-top:12px;color:var(--green)">✅ No cyclic dependencies.</p>';
  }}
  $('dsm-container').innerHTML = html;
}} else {{
  $('dsm-container').innerHTML = '<p style="color:var(--text2)">DSM not available. Enable --graphs to generate.</p>';
}}

// ─── Duplication ─────────────────────────────
if (D.duplication) {{
  const dp = D.duplication;
  $('dup-kpi').innerHTML = [
    ['Total Tokens', fmt(dp.total_tokens)],
    ['Duplicated Tokens', fmt(dp.duplicated_tokens)],
    ['Duplication', dp.duplication_pct.toFixed(1) + '%'],
  ].map(([l, v]) => `<div class="card"><div class="card-header">${{l}}</div><div class="stat-value">${{v}}</div></div>`).join('');

  if (dp.duplicate_pairs && dp.duplicate_pairs.length) {{
    makeTable('dup-table',
      ['#', 'File A', 'Lines A', 'File B', 'Lines B', 'Tokens', 'Lines'],
      dp.duplicate_pairs.slice(0, 50).map((p, i) => [
        i+1,
        p.block_a.path.split('/').slice(-3).join('/'),
        p.block_a.line_start + '-' + p.block_a.line_end,
        p.block_b.path.split('/').slice(-3).join('/'),
        p.block_b.line_start + '-' + p.block_b.line_end,
        p.token_count, p.line_count,
      ]),
      ['num','str','str','str','str','num','num']
    );
  }}
}} else {{
  $('dup-kpi').innerHTML = '<div class="card"><p style="color:var(--text2)">Duplication analysis not available.</p></div>';
}}

// ─── Trends & Delta ──────────────────────────
if (D.delta) {{
  let dhtml = '<table><thead><tr><th>Metric</th><th class="num">Before</th><th class="num">After</th><th class="num">Delta</th><th class="num">%</th><th></th></tr></thead><tbody>';
  D.delta.project_delta.forEach(r => {{
    const cls = r.delta > 0.01 ? (r.indicator === '🟢' ? 'delta-pos' : 'delta-neg') : r.delta < -0.01 ? (r.indicator === '🟢' ? 'delta-pos' : 'delta-neg') : 'delta-zero';
    const sign = r.delta > 0 ? '+' : '';
    dhtml += `<tr><td>${{r.metric}}</td><td class="num">${{r.before}}</td><td class="num">${{r.after}}</td>` +
      `<td class="num ${{cls}}">${{sign}}${{r.delta.toFixed(2)}}</td><td class="num ${{cls}}">${{sign}}${{r.pct_change.toFixed(1)}}%</td><td>${{r.indicator}}</td></tr>`;
  }});
  dhtml += '</tbody></table>';
  $('delta-container').innerHTML = dhtml;
}} else {{
  $('delta-container').innerHTML = '<p style="color:var(--text2)">No previous snapshot for comparison. Run again to see deltas.</p>';
}}

// Trend charts
if (D.history.length > 1) {{
  const tc = $('trend-charts');
  const timestamps = D.history.map(h => h.timestamp ? h.timestamp.split('T')[0] : '?');

  const charts = [
    ['TD (hours)', D.history.map(h => h.td_total_hours), '#f85149'],
    ['Violations', D.history.map(h => h.violations_total), '#d29922'],
    ['LOC', D.history.map(h => h.project_loc), '#58a6ff'],
    ['Duplication %', D.history.map(h => h.duplication_pct || 0), '#db6d28'],
  ];

  charts.forEach(([label, data, color]) => {{
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `<h3>${{label}}</h3><div class="chart-container"><canvas></canvas></div>`;
    tc.appendChild(card);
    new Chart(card.querySelector('canvas'), {{
      type: 'line',
      data: {{ labels: timestamps, datasets: [{{ label, data, borderColor: color, fill: false, tension: 0.3 }}] }},
      options: {{ responsive: true, maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{ y: {{ ticks: {{ color: '#8b949e' }} }}, x: {{ ticks: {{ color: '#c9d1d9' }} }} }}
      }}
    }});
  }});
}} else {{
  $('trend-charts').innerHTML = '<div class="card"><p style="color:var(--text2)">Need 2+ snapshots for trend charts. Run the analysis multiple times.</p></div>';
}}
</script>
</body>
</html>"""
