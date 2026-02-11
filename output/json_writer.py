"""JSON output writer."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import List

from ..models import (
    ClassMetrics,
    FileMetrics,
    FunctionMetrics,
    ModuleSummary,
    ProjectSummary,
)


def write_raw_file_metrics(file_metrics: List[FileMetrics], output_dir: str) -> str:
    """Write raw file-level metrics to JSON."""
    path = os.path.join(output_dir, "raw", "file_metrics.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    data = {
        "generated_at": _now_iso(),
        "count": len(file_metrics),
        "files": [fm.to_dict() for fm in file_metrics],
    }

    _write_json(path, data)
    return path


def write_raw_function_metrics(function_metrics: List[FunctionMetrics], output_dir: str) -> str:
    """Write raw function-level metrics to JSON."""
    path = os.path.join(output_dir, "raw", "function_metrics.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    data = {
        "generated_at": _now_iso(),
        "count": len(function_metrics),
        "functions": [fm.to_dict() for fm in function_metrics],
    }

    _write_json(path, data)
    return path


def write_raw_class_metrics(class_metrics: List[ClassMetrics], output_dir: str) -> str:
    """Write raw class-level metrics to JSON."""
    path = os.path.join(output_dir, "raw", "class_metrics.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    data = {
        "generated_at": _now_iso(),
        "count": len(class_metrics),
        "classes": [cm.to_dict() for cm in class_metrics],
    }

    _write_json(path, data)
    return path


def write_module_summary(module_summary: ModuleSummary, output_dir: str) -> str:
    """Write module summary to JSON."""
    safe_name = module_summary.module.replace("/", "_").replace("\\", "_")
    path = os.path.join(output_dir, "modules", f"{safe_name}_summary.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    data = {
        "generated_at": _now_iso(),
        **module_summary.to_dict(),
    }

    _write_json(path, data)
    return path


def write_project_summary(project_summary: ProjectSummary, output_dir: str) -> str:
    """Write project summary to JSON."""
    path = os.path.join(output_dir, "project_summary.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    data = {
        "generated_at": _now_iso(),
        **project_summary.to_dict(),
    }

    _write_json(path, data)
    return path


def write_hotspots(
    function_metrics: List[FunctionMetrics],
    class_metrics: List[ClassMetrics],
    file_metrics: List[FileMetrics],
    output_dir: str,
    top_n: int = 20,
) -> str:
    """Write hotspots report to JSON."""
    path = os.path.join(output_dir, "hotspots.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Top functions by cyclomatic complexity
    top_cyclo = sorted(function_metrics, key=lambda f: f.cyclo, reverse=True)[:top_n]
    # Top functions by lowest MI
    top_mi = sorted(function_metrics, key=lambda f: f.mi)[:top_n]
    # Top classes by WMC
    top_wmc = sorted(class_metrics, key=lambda c: c.wmc, reverse=True)[:top_n]
    # Top classes by CBO
    top_cbo = sorted(class_metrics, key=lambda c: c.cbo, reverse=True)[:top_n]
    # Top files by technical debt
    top_debt = sorted(file_metrics, key=lambda f: f.technical_debt_minutes, reverse=True)[:top_n]
    # Top classes by lowest TCC
    top_low_tcc = sorted(
        [c for c in class_metrics if c.nom >= 2],
        key=lambda c: c.tcc,
    )[:top_n]

    data = {
        "generated_at": _now_iso(),
        "top_n": top_n,
        "by_cyclomatic_complexity": [f.to_dict() for f in top_cyclo],
        "by_lowest_maintainability": [f.to_dict() for f in top_mi],
        "by_weighted_methods": [c.to_dict() for c in top_wmc],
        "by_coupling": [c.to_dict() for c in top_cbo],
        "by_technical_debt": [f.to_dict() for f in top_debt],
        "by_lowest_cohesion": [c.to_dict() for c in top_low_tcc],
    }

    _write_json(path, data)
    return path


def write_technical_debt_report(
    function_metrics: List[FunctionMetrics],
    class_metrics: List[ClassMetrics],
    file_metrics: List[FileMetrics],
    module_summaries: List[ModuleSummary],
    output_dir: str,
) -> str:
    """Write detailed technical debt report to JSON."""
    path = os.path.join(output_dir, "technical_debt.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Module-level TD
    module_td = []
    for ms in module_summaries:
        module_td.append({
            "module": ms.module,
            "total_minutes": ms.technical_debt.total_minutes,
            "total_hours": ms.technical_debt.total_hours,
            "total_days": ms.technical_debt.total_days,
        })
    module_td.sort(key=lambda x: x["total_minutes"], reverse=True)

    # File-level TD (top 50)
    top_files = sorted(file_metrics, key=lambda f: f.technical_debt_minutes, reverse=True)[:50]

    # Function-level TD (top 50)
    top_functions = sorted(function_metrics, key=lambda f: f.technical_debt_minutes, reverse=True)[:50]

    # Class-level TD (top 50)
    top_classes = sorted(class_metrics, key=lambda c: c.technical_debt_minutes, reverse=True)[:50]

    total_minutes = sum(ms.technical_debt.total_minutes for ms in module_summaries)

    data = {
        "generated_at": _now_iso(),
        "total_minutes": round(total_minutes, 2),
        "total_hours": round(total_minutes / 60, 2),
        "total_days": round(total_minutes / 480, 2),
        "by_module": module_td,
        "top_files": [f.to_dict() for f in top_files],
        "top_functions": [f.to_dict() for f in top_functions],
        "top_classes": [c.to_dict() for c in top_classes],
    }

    _write_json(path, data)
    return path


def write_metadata(
    output_dir: str,
    config_version: str,
    modules_analyzed: List[str],
    parser_type: str,
    duration_seconds: float,
) -> str:
    """Write metadata about the analysis run."""
    path = os.path.join(output_dir, "metadata.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    data = {
        "generated_at": _now_iso(),
        "config_version": config_version,
        "parser": parser_type,
        "modules_analyzed": modules_analyzed,
        "duration_seconds": round(duration_seconds, 2),
    }

    _write_json(path, data)
    return path


def _write_json(path: str, data: dict):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, default=str)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_graph_json(graph, output_dir: str, graph_type: str) -> str:
    """Write a dependency graph to JSON."""
    path = os.path.join(output_dir, f"graph_{graph_type}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "generated_at": _now_iso(),
        **graph.to_dict(),
    }
    _write_json(path, data)
    return path


def write_package_analysis_json(result, output_dir: str) -> str:
    """Write package analysis result to JSON."""
    safe_name = result.module_name.replace("/", "_").replace("\\", "_")
    path = os.path.join(output_dir, "modules", f"{safe_name}_package_analysis.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "generated_at": _now_iso(),
        **result.to_dict(),
    }
    _write_json(path, data)
    return path


def write_ratings_json(module_ratings: dict, output_dir: str) -> str:
    """Write module ratings (A/B/C/D/E) to JSON."""
    path = os.path.join(output_dir, "ratings.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "generated_at": _now_iso(),
        "modules": [
            {"module": name, "score": round(score, 1), "grade": grade}
            for name, (score, grade) in sorted(module_ratings.items(), key=lambda x: -x[1][0])
        ],
    }
    _write_json(path, data)
    return path


def write_distributions_json(distributions: dict, output_dir: str) -> str:
    """Write distribution histograms to JSON."""
    path = os.path.join(output_dir, "distributions.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "generated_at": _now_iso(),
        "distributions": {
            name: hist.to_dict() for name, hist in distributions.items()
        },
    }
    _write_json(path, data)
    return path


def write_risk_hotspots_json(risk_hotspots: list, output_dir: str) -> str:
    """Write risk hotspots (churn × complexity) to JSON."""
    path = os.path.join(output_dir, "risk_hotspots.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "generated_at": _now_iso(),
        "count": len(risk_hotspots),
        "hotspots": [h.to_dict() for h in risk_hotspots],
    }
    _write_json(path, data)
    return path


def write_dsm_json(dsm_result, output_dir: str) -> str:
    """Write Design Structure Matrix to JSON."""
    path = os.path.join(output_dir, "dsm.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "generated_at": _now_iso(),
        **dsm_result.to_dict(),
    }
    _write_json(path, data)
    return path


def write_duplication_json(duplication_result, output_dir: str) -> str:
    """Write code duplication results to JSON."""
    path = os.path.join(output_dir, "duplication.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "generated_at": _now_iso(),
        **duplication_result.to_dict(),
    }
    _write_json(path, data)
    return path


def write_delta_json(snapshot_delta, output_dir: str) -> str:
    """Write snapshot delta (diff) to JSON."""
    path = os.path.join(output_dir, "delta.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "generated_at": _now_iso(),
        **snapshot_delta.to_dict(),
    }
    _write_json(path, data)
    return path
