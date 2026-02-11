"""Markdown report writer."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List

from ..models import (
    ClassMetrics,
    FileMetrics,
    FunctionMetrics,
    ModuleSummary,
    ProjectSummary,
    StatsSummary,
)


def write_module_summary_md(
    module_summary: ModuleSummary,
    function_metrics: List[FunctionMetrics],
    class_metrics: List[ClassMetrics],
    output_dir: str,
) -> str:
    """Write module summary as a Markdown report."""
    safe_name = module_summary.module.replace("/", "_").replace("\\", "_")
    path = os.path.join(output_dir, "modules", f"{safe_name}_summary.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    ms = module_summary
    lines: list = []

    lines.append(f"# Module Metrics: {ms.module}\n")
    lines.append(f"_Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n")

    # Executive summary
    lines.append("## Overview\n")
    lines.append(f"| Parameter | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| Path | `{ms.path}` |")
    lines.append(f"| Files | {ms.files_count} |")
    lines.append(f"| Classes | {ms.classes_count} |")
    lines.append(f"| Functions/methods | {ms.functions_count} |")
    lines.append(f"| LOC (total) | {ms.loc_total:,} |")
    lines.append(f"| SLOC (total) | {ms.sloc_total:,} |")
    lines.append(f"| Tech debt (hours) | {ms.technical_debt.total_hours:.1f} |")
    lines.append(f"| Tech debt (days) | {ms.technical_debt.total_days:.1f} |")
    lines.append("")

    # Metrics summary table
    lines.append("## Metrics (statistics)\n")
    lines.append("| Metric | Mean | Median | P90 | Min | Max | Std Dev |")
    lines.append("|---|---|---|---|---|---|---|")
    for name, stats in ms.metrics_summary.items():
        if isinstance(stats, StatsSummary):
            s = stats
        else:
            continue
        lines.append(
            f"| {name.upper()} | {s.mean} | {s.median} | {s.p90} "
            f"| {s.min_val} | {s.max_val} | {s.std_dev} |"
        )
    lines.append("")

    # Violations
    lines.append("## Violations\n")
    v = ms.violations
    lines.append(f"| Violation | Count | Indicator |")
    lines.append(f"|---|---|---|")
    lines.append(f"| CC > high | {v.cyclo_high} | {_indicator(v.cyclo_high, 0, 10)} |")
    lines.append(f"| CC > very high | {v.cyclo_very_high} | {_indicator(v.cyclo_very_high, 0, 5)} |")
    lines.append(f"| MI < poor | {v.mi_poor} | {_indicator(v.mi_poor, 0, 10)} |")
    lines.append(f"| MNL > critical | {v.mnl_critical} | {_indicator(v.mnl_critical, 0, 5)} |")
    lines.append(f"| God classes (WMC) | {v.god_classes} | {_indicator(v.god_classes, 0, 3)} |")
    lines.append(f"| Low cohesion (TCC) | {v.low_cohesion} | {_indicator(v.low_cohesion, 0, 10)} |")
    lines.append(f"| High coupling (CBO) | {v.high_coupling} | {_indicator(v.high_coupling, 0, 5)} |")
    lines.append(f"| Excessive params | {v.excessive_params} | {_indicator(v.excessive_params, 0, 10)} |")
    lines.append(f"| Excessive imports | {v.excessive_imports} | {_indicator(v.excessive_imports, 0, 10)} |")
    lines.append(f"| Magic numbers | {v.magic_numbers_high} | {_indicator(v.magic_numbers_high, 0, 10)} |")
    lines.append(f"| Hardcoded strings | {v.hardcoded_strings_high} | {_indicator(v.hardcoded_strings_high, 0, 10)} |")
    lines.append(f"| Dead code | {v.potential_dead_code} | {_indicator(v.potential_dead_code, 0, 5)} |")
    lines.append("")

    # Top hotspots
    lines.append("## Hotspots (Top-10 by CC)\n")
    top_cyclo = sorted(
        [f for f in function_metrics if f.module == ms.module],
        key=lambda f: f.cyclo, reverse=True,
    )[:10]

    if top_cyclo:
        lines.append("| Function | Class | CC | MI | WMFP | FPY | LOC | File |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for f in top_cyclo:
            cls = f.class_name or "\u2014"
            lines.append(
                f"| `{f.function_name}` | `{cls}` | {f.cyclo} | {f.mi:.1f} "
                f"| {f.wmfp:.1f} | {f.fpy:.2f} "
                f"| {f.loc} | `{_short_path(f.path)}:{f.line_start}` |"
            )
    lines.append("")

    # Top classes by WMC
    lines.append("## Complex Classes (Top-10 by WMC)\n")
    top_wmc = sorted(
        [c for c in class_metrics if c.module == ms.module],
        key=lambda c: c.wmc, reverse=True,
    )[:10]

    if top_wmc:
        lines.append("| Class | WMC | CBO | RFC | TCC | NOM | LOC | File |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for c in top_wmc:
            lines.append(
                f"| `{c.class_name}` | {c.wmc} | {c.cbo} | {c.rfc} "
                f"| {c.tcc:.2f} | {c.nom} | {c.loc} | `{_short_path(c.path)}:{c.line_start}` |"
            )
    lines.append("")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    return path


def write_project_summary_md(
    project_summary: ProjectSummary,
    module_summaries: List[ModuleSummary],
    output_dir: str,
) -> str:
    """Write project-level summary as Markdown."""
    path = os.path.join(output_dir, "project_summary.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    ps = project_summary
    lines: list = []

    lines.append("# Project Metrics\n")
    lines.append(f"_Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n")

    # Executive summary
    lines.append("## Overview\n")
    lines.append("| Parameter | Value |")
    lines.append("|---|---|")
    lines.append(f"| Modules | {ps.modules_count} |")
    lines.append(f"| Files | {ps.files_count:,} |")
    lines.append(f"| Classes | {ps.classes_count:,} |")
    lines.append(f"| Functions/methods | {ps.functions_count:,} |")
    lines.append(f"| LOC (total) | {ps.loc_total:,} |")
    lines.append(f"| SLOC (total) | {ps.sloc_total:,} |")
    lines.append(f"| Tech debt (hours) | {ps.technical_debt.total_hours:.1f} |")
    lines.append(f"| Tech debt (days) | {ps.technical_debt.total_days:.1f} |")
    lines.append("")

    # Metrics summary
    lines.append("## Metrics (project-wide statistics)\n")
    lines.append("| Metric | Mean | Median | P90 | Min | Max |")
    lines.append("|---|---|---|---|---|---|")
    for name, stats in ps.metrics_summary.items():
        if isinstance(stats, StatsSummary):
            s = stats
        elif isinstance(stats, dict):
            s = StatsSummary(**stats)
        else:
            continue
        lines.append(f"| {name.upper()} | {s.mean} | {s.median} | {s.p90} | {s.min_val} | {s.max_val} |")
    lines.append("")

    # Violations summary
    lines.append("## Violations (total)\n")
    v = ps.violations
    lines.append("| Violation | Count |")
    lines.append("|---|---|")
    lines.append(f"| CC > high | {v.cyclo_high} |")
    lines.append(f"| CC > very high | {v.cyclo_very_high} |")
    lines.append(f"| MI < poor | {v.mi_poor} |")
    lines.append(f"| MNL > critical | {v.mnl_critical} |")
    lines.append(f"| God classes | {v.god_classes} |")
    lines.append(f"| Low cohesion | {v.low_cohesion} |")
    lines.append(f"| High coupling | {v.high_coupling} |")
    lines.append(f"| Excessive params | {v.excessive_params} |")
    lines.append(f"| Excessive imports | {v.excessive_imports} |")
    lines.append(f"| Magic numbers | {v.magic_numbers_high} |")
    lines.append(f"| Hardcoded strings | {v.hardcoded_strings_high} |")
    lines.append(f"| Dead code | {v.potential_dead_code} |")
    lines.append("")

    # Module comparison table
    lines.append("## Module Comparison\n")
    lines.append("| Module | Files | Classes | Functions | LOC | SLOC | CC (avg) | MI (avg) | TD (hours) |")
    lines.append("|---|---|---|---|---|---|---|---|---|")

    # Sort modules by TD
    sorted_modules = sorted(module_summaries, key=lambda m: m.technical_debt.total_minutes, reverse=True)

    for ms in sorted_modules:
        cc_avg = ms.metrics_summary.get("cyclo")
        mi_avg = ms.metrics_summary.get("mi")
        cc_str = f"{cc_avg.mean:.1f}" if isinstance(cc_avg, StatsSummary) else "—"
        mi_str = f"{mi_avg.mean:.1f}" if isinstance(mi_avg, StatsSummary) else "—"
        lines.append(
            f"| `{ms.module}` | {ms.files_count} | {ms.classes_count} "
            f"| {ms.functions_count} | {ms.loc_total:,} | {ms.sloc_total:,} "
            f"| {cc_str} | {mi_str} | {ms.technical_debt.total_hours:.1f} |"
        )
    lines.append("")

    # Technical debt breakdown
    lines.append("## Technical Debt by Module\n")
    lines.append("| Module | Minutes | Hours | Days |")
    lines.append("|---|---|---|---|")
    for ms in sorted_modules:
        td = ms.technical_debt
        lines.append(f"| `{ms.module}` | {td.total_minutes:.0f} | {td.total_hours:.1f} | {td.total_days:.1f} |")
    lines.append("")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    return path


def write_hotspots_md(
    function_metrics: List[FunctionMetrics],
    class_metrics: List[ClassMetrics],
    file_metrics: List[FileMetrics],
    output_dir: str,
    top_n: int = 20,
) -> str:
    """Write hotspots report as Markdown."""
    path = os.path.join(output_dir, "hotspots.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    lines: list = []
    lines.append("# Project Hotspots\n")
    lines.append(f"_Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n")
    lines.append(f"Top-{top_n} per category.\n")

    # Top CC
    lines.append("## Highest Cyclomatic Complexity (CC)\n")
    top_cyclo = sorted(function_metrics, key=lambda f: f.cyclo, reverse=True)[:top_n]
    lines.append("| # | Function | Class | Module | CC | MI | LOC | File |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for i, f in enumerate(top_cyclo, 1):
        cls = f.class_name or "—"
        lines.append(
            f"| {i} | `{f.function_name}` | `{cls}` | `{f.module}` "
            f"| {f.cyclo} | {f.mi:.1f} | {f.loc} | `{_short_path(f.path)}:{f.line_start}` |"
        )
    lines.append("")

    # Lowest MI
    lines.append("## Lowest Maintainability Index (MI)\n")
    top_mi = sorted(function_metrics, key=lambda f: f.mi)[:top_n]
    lines.append("| # | Function | Class | Module | MI | CC | LOC | File |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for i, f in enumerate(top_mi, 1):
        cls = f.class_name or "—"
        lines.append(
            f"| {i} | `{f.function_name}` | `{cls}` | `{f.module}` "
            f"| {f.mi:.1f} | {f.cyclo} | {f.loc} | `{_short_path(f.path)}:{f.line_start}` |"
        )
    lines.append("")

    # Top WMC (god classes)
    lines.append("## God Classes (WMC)\n")
    top_wmc = sorted(class_metrics, key=lambda c: c.wmc, reverse=True)[:top_n]
    lines.append("| # | Class | Module | WMC | CBO | RFC | TCC | NOM | LOC |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for i, c in enumerate(top_wmc, 1):
        lines.append(
            f"| {i} | `{c.class_name}` | `{c.module}` | {c.wmc} | {c.cbo} "
            f"| {c.rfc} | {c.tcc:.2f} | {c.nom} | {c.loc} |"
        )
    lines.append("")

    # Highest CBO
    lines.append("## Highest Coupling (CBO)\n")
    top_cbo = sorted(class_metrics, key=lambda c: c.cbo, reverse=True)[:top_n]
    lines.append("| # | Class | Module | CBO | DIT | WMC | RFC | LOC |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for i, c in enumerate(top_cbo, 1):
        lines.append(
            f"| {i} | `{c.class_name}` | `{c.module}` | {c.cbo} | {c.dit} "
            f"| {c.wmc} | {c.rfc} | {c.loc} |"
        )
    lines.append("")

    # Top TD files
    lines.append("## Files with Highest Technical Debt\n")
    top_debt = sorted(file_metrics, key=lambda f: f.technical_debt_minutes, reverse=True)[:top_n]
    lines.append("| # | File | Module | TD (min) | CC sum | CC max | MI (avg) | LOC |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for i, f in enumerate(top_debt, 1):
        lines.append(
            f"| {i} | `{_short_path(f.path)}` | `{f.module}` "
            f"| {f.technical_debt_minutes:.0f} | {f.cyclo_sum} | {f.cyclo_max} "
            f"| {f.mi_avg:.1f} | {f.loc} |"
        )
    lines.append("")

    # Lowest TCC
    lines.append("## Lowest Cohesion (TCC)\n")
    low_tcc = sorted(
        [c for c in class_metrics if c.nom >= 2],
        key=lambda c: c.tcc,
    )[:top_n]
    lines.append("| # | Class | Module | TCC | WOC | NOM | WMC | LOC |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for i, c in enumerate(low_tcc, 1):
        lines.append(
            f"| {i} | `{c.class_name}` | `{c.module}` | {c.tcc:.3f} | {c.woc:.3f} "
            f"| {c.nom} | {c.wmc} | {c.loc} |"
        )
    lines.append("")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    return path


def write_technical_debt_md(
    module_summaries: List[ModuleSummary],
    file_metrics: List[FileMetrics],
    output_dir: str,
) -> str:
    """Write technical debt report as Markdown."""
    path = os.path.join(output_dir, "technical_debt.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    total_minutes = sum(ms.technical_debt.total_minutes for ms in module_summaries)

    lines: list = []
    lines.append("# Technical Debt Report\n")
    lines.append(f"_Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n")

    lines.append("## Total\n")
    lines.append(f"- **Total:** {total_minutes:.0f} minutes = {total_minutes/60:.1f} hours = {total_minutes/480:.1f} work days\n")

    lines.append("## By Module\n")
    lines.append("| Module | Minutes | Hours | Days | Share (%) |")
    lines.append("|---|---|---|---|---|")
    sorted_modules = sorted(module_summaries, key=lambda m: m.technical_debt.total_minutes, reverse=True)
    for ms in sorted_modules:
        td = ms.technical_debt
        pct = (td.total_minutes / total_minutes * 100) if total_minutes > 0 else 0
        lines.append(f"| `{ms.module}` | {td.total_minutes:.0f} | {td.total_hours:.1f} | {td.total_days:.1f} | {pct:.1f}% |")
    lines.append("")

    lines.append("## Top-30 Files\n")
    top_files = sorted(file_metrics, key=lambda f: f.technical_debt_minutes, reverse=True)[:30]
    lines.append("| File | Module | TD (min) | LOC | CC max |")
    lines.append("|---|---|---|---|---|")
    for f in top_files:
        lines.append(
            f"| `{_short_path(f.path)}` | `{f.module}` "
            f"| {f.technical_debt_minutes:.0f} | {f.loc} | {f.cyclo_max} |"
        )
    lines.append("")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    return path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _indicator(value: int, good_max: int, bad_min: int) -> str:
    """Return a color indicator based on value."""
    if value <= good_max:
        return "🟢"
    elif value < bad_min:
        return "🟡"
    else:
        return "🔴"


def _short_path(path: str, max_parts: int = 4) -> str:
    """Shorten a file path for display."""
    parts = path.replace("\\", "/").split("/")
    if len(parts) <= max_parts:
        return "/".join(parts)
    return ".../" + "/".join(parts[-max_parts:])


def write_graph_summary_md(
    import_graph,
    pubspec_graph,
    output_dir: str,
) -> str:
    """Write dependency graph summary as Markdown."""
    path = os.path.join(output_dir, "graph_summary.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    lines: list = []
    lines.append("# Dependency Graph\n")
    lines.append(f"_Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n")

    # Import graph summary
    if import_graph:
        lines.append("## Import Graph\n")
        lines.append(f"- Packages (nodes): {import_graph.node_count}")
        lines.append(f"- Connections (edges): {import_graph.edge_count}")
        lines.append(f"- External packages: {len(import_graph.external_packages)}")
        lines.append("")

        # Top imported packages
        in_counts: dict = {}
        for e in import_graph.edges:
            in_counts[e.to_node] = in_counts.get(e.to_node, 0) + e.weight
        top_imported = sorted(in_counts.items(), key=lambda x: -x[1])[:15]
        if top_imported:
            lines.append("### Most Imported Packages\n")
            lines.append("| Package | Import Count |")
            lines.append("|---|---|")
            for name, count in top_imported:
                lines.append(f"| `{name}` | {count} |")
            lines.append("")

        # Top importing packages
        out_counts: dict = {}
        for e in import_graph.edges:
            out_counts[e.from_node] = out_counts.get(e.from_node, 0) + e.weight
        top_importing = sorted(out_counts.items(), key=lambda x: -x[1])[:15]
        if top_importing:
            lines.append("### Most Dependent Packages\n")
            lines.append("| Package | Dependency Count |")
            lines.append("|---|---|")
            for name, count in top_importing:
                lines.append(f"| `{name}` | {count} |")
            lines.append("")

        # External packages list
        if import_graph.external_packages:
            lines.append("### External Packages\n")
            for ext in import_graph.external_packages:
                lines.append(f"- {ext}")
            lines.append("")

    # Pubspec graph summary
    if pubspec_graph:
        lines.append("## Pubspec Dependency Graph\n")
        lines.append(f"- Packages: {pubspec_graph.node_count}")
        lines.append(f"- Dependencies: {pubspec_graph.edge_count}")
        lines.append("")

        # Dependencies by type
        type_counts: dict = {}
        for e in pubspec_graph.edges:
            t = e.edge_type
            type_counts[t] = type_counts.get(t, 0) + 1
        if type_counts:
            lines.append("### By Dependency Type\n")
            lines.append("| Type | Count |")
            lines.append("|---|---|")
            for t, c in sorted(type_counts.items()):
                lines.append(f"| {t} | {c} |")
            lines.append("")

        # Top referenced packages
        ref_counts: dict = {}
        for e in pubspec_graph.edges:
            ref_counts[e.to_node] = ref_counts.get(e.to_node, 0) + 1
        top_refs = sorted(ref_counts.items(), key=lambda x: -x[1])[:20]
        if top_refs:
            lines.append("### Most Used Packages (pubspec)\n")
            lines.append("| Package | Dependents Count |")
            lines.append("|---|---|")
            for name, count in top_refs:
                lines.append(f"| `{name}` | {count} |")
            lines.append("")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    return path


def write_package_analysis_md(
    package_analyses: list,
    output_dir: str,
) -> str:
    """Write package analysis report as Markdown."""
    path = os.path.join(output_dir, "package_analysis.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    lines: list = []
    lines.append("# Package Analysis\n")
    lines.append(f"_Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n")

    for pa in package_analyses:
        lines.append(f"## {pa.module_name}\n")
        lines.append(f"Path: `{pa.module_path}`\n")

        # Cross-package imports
        if pa.cross_package_imports:
            lines.append("### Cross-Package Imports\n")
            # Group by imported package
            pkg_counts: dict = {}
            for ci in pa.cross_package_imports:
                pkg_counts[ci.imported_package] = pkg_counts.get(ci.imported_package, 0) + 1
            lines.append("| Package | Import Count |")
            lines.append("|---|---|")
            for pkg, cnt in sorted(pkg_counts.items(), key=lambda x: -x[1]):
                lines.append(f"| `{pkg}` | {cnt} |")
            lines.append("")

        # Import statistics
        if pa.import_statistics:
            lines.append("### Import Statistics\n")
            lines.append("| Package | Count |")
            lines.append("|---|---|")
            for ist in pa.import_statistics[:20]:
                lines.append(f"| `{ist.package_name}` | {ist.count} |")
            lines.append("")

        # Shotgun surgery
        if pa.shotgun_surgery_candidates:
            top_shotgun = [s for s in pa.shotgun_surgery_candidates if s.usage_count > 2][:15]
            if top_shotgun:
                lines.append("### Potential Shotgun Surgery\n")
                lines.append("Files/modules with the most imports (changes may affect many places):\n")
                lines.append("| Imported Path | Usage Count |")
                lines.append("|---|---|")
                for ss in top_shotgun:
                    lines.append(f"| `{ss.relative_path}` | {ss.usage_count} |")
                lines.append("")

        # Git hotspots
        if pa.git_hotspots:
            lines.append("### Git Hotspots (most changed files)\n")
            lines.append("| File | Commits |")
            lines.append("|---|---|")
            for gh in pa.git_hotspots:
                lines.append(f"| `{_short_path(gh.file_path)}` | {gh.commit_count} |")
            lines.append("")

        lines.append("---\n")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    return path


# ---------------------------------------------------------------------------
# Ratings
# ---------------------------------------------------------------------------

def write_ratings_md(
    module_summaries: list,
    module_ratings: dict,
    output_dir: str,
) -> str:
    """Write module quality ratings (A/B/C/D/E) as Markdown."""
    path = os.path.join(output_dir, "ratings.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    lines = [
        "# Module Quality Ratings\n",
        f"_Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n",
        "| Module | Score | Grade | LOC | Files | Avg MI | Avg CC |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    ms_map = {ms.module: ms for ms in module_summaries}

    for name, (score, grade) in sorted(module_ratings.items(), key=lambda x: -x[1][0]):
        ms = ms_map.get(name)
        loc = ms.loc_total if ms else 0
        files = ms.files_count if ms else 0
        mi_stats = ms.metrics_summary.get("mi") if ms else None
        cc_stats = ms.metrics_summary.get("cyclo") if ms else None
        avg_mi = mi_stats.mean if mi_stats else 0.0
        avg_cc = cc_stats.mean if cc_stats else 0.0
        lines.append(
            f"| `{name}` | {score:.1f} | **{grade}** | {loc:,} | {files} | {avg_mi:.1f} | {avg_cc:.1f} |"
        )

    lines.append("")
    lines.append("### Grade Scale\n")
    lines.append("| Grade | Score Range | Meaning |")
    lines.append("|---|---|---|")
    lines.append("| A | 80–100 | Excellent |")
    lines.append("| B | 60–79 | Good |")
    lines.append("| C | 40–59 | Moderate |")
    lines.append("| D | 20–39 | Poor |")
    lines.append("| E | 0–19 | Critical |")
    lines.append("")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path


# ---------------------------------------------------------------------------
# Risk Hotspots
# ---------------------------------------------------------------------------

def write_risk_hotspots_md(risk_hotspots: list, output_dir: str) -> str:
    """Write churn × complexity risk hotspots as Markdown."""
    path = os.path.join(output_dir, "risk_hotspots.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    lines = [
        "# Risk Hotspots (Churn × Complexity)\n",
        f"_Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n",
        "Files with both high change frequency and high complexity are the riskiest.\n",
        "| # | File | Churn | Complexity | Risk Score |",
        "|---:|---|---:|---:|---:|",
    ]

    for i, h in enumerate(risk_hotspots[:50], 1):
        lines.append(
            f"| {i} | `{h.path}` | {h.churn} | {h.complexity:.1f} | **{h.risk_score:.3f}** |"
        )

    lines.append("")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path


# ---------------------------------------------------------------------------
# DSM
# ---------------------------------------------------------------------------

def write_dsm_md(dsm_result, output_dir: str) -> str:
    """Write Design Structure Matrix as Markdown."""
    from ..graphs.dsm import dsm_to_markdown

    path = os.path.join(output_dir, "dsm.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    lines = [
        "# Design Structure Matrix (DSM)\n",
        f"_Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n",
        dsm_to_markdown(dsm_result),
    ]

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path


# ---------------------------------------------------------------------------
# Duplication
# ---------------------------------------------------------------------------

def write_duplication_md(duplication_result, output_dir: str) -> str:
    """Write code duplication report as Markdown."""
    path = os.path.join(output_dir, "duplication.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    dr = duplication_result
    lines = [
        "# Code Duplication Report\n",
        f"_Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n",
        "## Summary\n",
        f"- **Total tokens analysed:** {dr.total_tokens:,}",
        f"- **Duplicated tokens:** {dr.duplicated_tokens:,}",
        f"- **Duplication percentage:** {dr.duplication_pct:.1f}%",
        f"- **Duplicate pairs found:** {len(dr.duplicate_pairs)}",
        "",
    ]

    if dr.per_file:
        lines.append("## Per-File Duplication\n")
        lines.append("| File | Duplication % |")
        lines.append("|---|---:|")
        sorted_files = sorted(dr.per_file.items(), key=lambda x: -x[1])
        for fp, pct in sorted_files[:30]:
            lines.append(f"| `{fp}` | {pct:.1f}% |")
        lines.append("")

    if dr.duplicate_pairs:
        lines.append("## Top Duplicate Pairs\n")
        lines.append("| File A | Lines A | File B | Lines B | Tokens |")
        lines.append("|---|---|---|---|---:|")
        for dp in dr.duplicate_pairs[:30]:
            a = dp.block_a
            b = dp.block_b
            lines.append(
                f"| `{a.path}` | {a.line_start}-{a.line_end} "
                f"| `{b.path}` | {b.line_start}-{b.line_end} "
                f"| {dp.token_count} |"
            )
        lines.append("")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path


# ---------------------------------------------------------------------------
# Distributions
# ---------------------------------------------------------------------------

def write_distributions_md(distributions: dict, output_dir: str) -> str:
    """Write distribution histograms as Markdown."""
    from ..metrics.distributions import histogram_to_markdown

    path = os.path.join(output_dir, "distributions.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    lines = [
        "# Metric Distributions\n",
        f"_Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n",
    ]

    for name, hist in distributions.items():
        lines.append(histogram_to_markdown(hist))
        lines.append("")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path


# ---------------------------------------------------------------------------
# Delta / Trend
# ---------------------------------------------------------------------------

def write_delta_md(snapshot_delta, output_dir: str) -> str:
    """Write snapshot comparison (delta) as Markdown."""
    path = os.path.join(output_dir, "delta.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    sd = snapshot_delta
    lines = [
        "# Metrics Delta Report\n",
        f"_Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n",
        f"Comparing **{sd.baseline_ts}** → **{sd.current_ts}**\n",
    ]

    lines.append("## Project-Level Changes\n")
    lines.append("| Metric | Before | After | Delta | Δ% | |")
    lines.append("|---|---:|---:|---:|---:|---|")
    for r in sd.rows:
        lines.append(
            f"| {r.metric} | {r.before:.2f} | {r.after:.2f} | {r.delta:+.2f} | {r.pct_change:+.1f}% | {r.indicator} |"
        )
    lines.append("")

    if sd.module_deltas:
        lines.append("## Per-Module Changes\n")
        for mod_name, rows in sorted(sd.module_deltas.items()):
            lines.append(f"### {mod_name}\n")
            lines.append("| Metric | Before | After | Delta | Δ% | |")
            lines.append("|---|---:|---:|---:|---:|---|")
            for r in rows:
                lines.append(
                    f"| {r.metric} | {r.before:.2f} | {r.after:.2f} | {r.delta:+.2f} | {r.pct_change:+.1f}% | {r.indicator} |"
                )
            lines.append("")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path
