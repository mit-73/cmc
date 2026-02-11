"""Project-level aggregation across all modules."""

from __future__ import annotations

from typing import List

from ..config import Thresholds
from ..models import (
    ClassMetrics,
    FileMetrics,
    FunctionMetrics,
    ModuleSummary,
    ProjectSummary,
    TechnicalDebtSummary,
    ViolationCounts,
)
from .module_aggregator import aggregate_module
from .stats import compute_stats


def aggregate_project(
    module_summaries: List[ModuleSummary],
    all_function_metrics: List[FunctionMetrics],
    all_class_metrics: List[ClassMetrics],
    all_file_metrics: List[FileMetrics],
    thresholds: Thresholds,
) -> ProjectSummary:
    """Aggregate all module summaries into a project-level summary."""
    summary = ProjectSummary(
        modules_count=len(module_summaries),
        files_count=sum(ms.files_count for ms in module_summaries),
        classes_count=sum(ms.classes_count for ms in module_summaries),
        functions_count=sum(ms.functions_count for ms in module_summaries),
        loc_total=sum(ms.loc_total for ms in module_summaries),
        sloc_total=sum(ms.sloc_total for ms in module_summaries),
    )

    # Aggregate metrics across all functions/classes
    if all_function_metrics:
        summary.metrics_summary["cyclo"] = compute_stats(
            [fm.cyclo for fm in all_function_metrics]
        )
        summary.metrics_summary["halvol"] = compute_stats(
            [fm.halstead_volume for fm in all_function_metrics]
        )
        summary.metrics_summary["mi"] = compute_stats(
            [fm.mi for fm in all_function_metrics]
        )
        summary.metrics_summary["mnl"] = compute_stats(
            [fm.max_nesting_level for fm in all_function_metrics]
        )
        summary.metrics_summary["nop"] = compute_stats(
            [fm.number_of_parameters for fm in all_function_metrics]
        )

    if all_class_metrics:
        summary.metrics_summary["cbo"] = compute_stats(
            [cm.cbo for cm in all_class_metrics]
        )
        summary.metrics_summary["dit"] = compute_stats(
            [cm.dit for cm in all_class_metrics]
        )
        summary.metrics_summary["nom"] = compute_stats(
            [cm.nom for cm in all_class_metrics]
        )
        summary.metrics_summary["rfc"] = compute_stats(
            [cm.rfc for cm in all_class_metrics]
        )
        summary.metrics_summary["tcc"] = compute_stats(
            [cm.tcc for cm in all_class_metrics]
        )
        summary.metrics_summary["wmc"] = compute_stats(
            [cm.wmc for cm in all_class_metrics]
        )
        summary.metrics_summary["woc"] = compute_stats(
            [cm.woc for cm in all_class_metrics]
        )

    if all_file_metrics:
        summary.metrics_summary["noi"] = compute_stats(
            [fm.noi for fm in all_file_metrics]
        )
        summary.metrics_summary["noei"] = compute_stats(
            [fm.noei for fm in all_file_metrics]
        )

    # Aggregate violations
    v = ViolationCounts()
    for ms in module_summaries:
        v.cyclo_high += ms.violations.cyclo_high
        v.cyclo_very_high += ms.violations.cyclo_very_high
        v.mi_poor += ms.violations.mi_poor
        v.mnl_critical += ms.violations.mnl_critical
        v.god_classes += ms.violations.god_classes
        v.low_cohesion += ms.violations.low_cohesion
        v.high_coupling += ms.violations.high_coupling
        v.excessive_params += ms.violations.excessive_params
        v.excessive_imports += ms.violations.excessive_imports
    summary.violations = v

    # Aggregate technical debt
    total_minutes = sum(ms.technical_debt.total_minutes for ms in module_summaries)
    summary.technical_debt = TechnicalDebtSummary(
        total_minutes=round(total_minutes, 2),
        total_hours=round(total_minutes / 60, 2),
        total_days=round(total_minutes / 480, 2),
    )

    # Add module summaries as dicts
    summary.modules = [ms.to_dict() for ms in module_summaries]

    return summary
