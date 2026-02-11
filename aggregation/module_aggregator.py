"""Module-level aggregation of metrics."""

from __future__ import annotations

from typing import List

from ..config import Thresholds
from ..models import (
    ClassMetrics,
    FileMetrics,
    FunctionMetrics,
    ModuleSummary,
    TechnicalDebtSummary,
    ViolationCounts,
)
from .stats import compute_stats


def aggregate_module(
    module_name: str,
    module_path: str,
    function_metrics: List[FunctionMetrics],
    class_metrics: List[ClassMetrics],
    file_metrics: List[FileMetrics],
    thresholds: Thresholds,
) -> ModuleSummary:
    """Aggregate all metrics for a single module into a summary."""

    summary = ModuleSummary(
        module=module_name,
        path=module_path,
        files_count=len(file_metrics),
        classes_count=len(class_metrics),
        functions_count=len(function_metrics),
        loc_total=sum(fm.loc for fm in file_metrics),
        sloc_total=sum(fm.sloc for fm in file_metrics),
    )

    # Metric summaries
    if function_metrics:
        summary.metrics_summary["cyclo"] = compute_stats(
            [fm.cyclo for fm in function_metrics]
        )
        summary.metrics_summary["halvol"] = compute_stats(
            [fm.halstead_volume for fm in function_metrics]
        )
        summary.metrics_summary["mi"] = compute_stats(
            [fm.mi for fm in function_metrics]
        )
        summary.metrics_summary["mnl"] = compute_stats(
            [fm.max_nesting_level for fm in function_metrics]
        )
        summary.metrics_summary["nop"] = compute_stats(
            [fm.number_of_parameters for fm in function_metrics]
        )
        summary.metrics_summary["loc_function"] = compute_stats(
            [fm.loc for fm in function_metrics]
        )
        summary.metrics_summary["sloc_function"] = compute_stats(
            [fm.sloc for fm in function_metrics]
        )
        summary.metrics_summary["wmfp"] = compute_stats(
            [fm.wmfp for fm in function_metrics]
        )
        summary.metrics_summary["fpy_function"] = compute_stats(
            [fm.fpy for fm in function_metrics]
        )

    if class_metrics:
        summary.metrics_summary["cbo"] = compute_stats(
            [cm.cbo for cm in class_metrics]
        )
        summary.metrics_summary["dit"] = compute_stats(
            [cm.dit for cm in class_metrics]
        )
        summary.metrics_summary["noam"] = compute_stats(
            [cm.noam for cm in class_metrics]
        )
        summary.metrics_summary["noii"] = compute_stats(
            [cm.noii for cm in class_metrics]
        )
        summary.metrics_summary["nom"] = compute_stats(
            [cm.nom for cm in class_metrics]
        )
        summary.metrics_summary["noom"] = compute_stats(
            [cm.noom for cm in class_metrics]
        )
        summary.metrics_summary["rfc"] = compute_stats(
            [cm.rfc for cm in class_metrics]
        )
        summary.metrics_summary["tcc"] = compute_stats(
            [cm.tcc for cm in class_metrics]
        )
        summary.metrics_summary["woc"] = compute_stats(
            [cm.woc for cm in class_metrics]
        )
        summary.metrics_summary["wmc"] = compute_stats(
            [cm.wmc for cm in class_metrics]
        )
        summary.metrics_summary["fpy_class"] = compute_stats(
            [cm.fpy for cm in class_metrics]
        )

    if file_metrics:
        summary.metrics_summary["noi"] = compute_stats(
            [fm.noi for fm in file_metrics]
        )
        summary.metrics_summary["noei"] = compute_stats(
            [fm.noei for fm in file_metrics]
        )
        summary.metrics_summary["wmfp_file"] = compute_stats(
            [fm.wmfp for fm in file_metrics]
        )
        summary.metrics_summary["wmfp_density"] = compute_stats(
            [fm.wmfp_density for fm in file_metrics]
        )
        summary.metrics_summary["fpy_file"] = compute_stats(
            [fm.fpy for fm in file_metrics]
        )

    # Violations
    v = ViolationCounts()
    for fm in function_metrics:
        if fm.cyclo > thresholds.cyclomatic_complexity.very_high:
            v.cyclo_very_high += 1
        elif fm.cyclo > thresholds.cyclomatic_complexity.high:
            v.cyclo_high += 1

        if fm.mi < thresholds.maintainability_index.poor:
            v.mi_poor += 1

        if fm.max_nesting_level > thresholds.max_nesting_level.critical:
            v.mnl_critical += 1

        if fm.number_of_parameters > thresholds.number_of_parameters.critical:
            v.excessive_params += 1

    for cm in class_metrics:
        if cm.wmc > thresholds.weighted_methods_per_class.critical:
            v.god_classes += 1
        if cm.tcc < thresholds.tight_class_cohesion.warning and cm.nom >= 2:
            v.low_cohesion += 1
        if cm.cbo > thresholds.coupling_between_objects.critical:
            v.high_coupling += 1

    for fm in file_metrics:
        if fm.noi > thresholds.number_of_imports.critical:
            v.excessive_imports += 1
        if fm.magic_numbers > thresholds.code_smells.magic_numbers_warning:
            v.magic_numbers_high += 1
        if fm.hardcoded_strings > thresholds.code_smells.hardcoded_strings_warning:
            v.hardcoded_strings_high += 1
        if fm.dead_code_estimate > thresholds.code_smells.dead_code_warning:
            v.potential_dead_code += 1

    summary.violations = v

    # Technical debt
    total_fn_debt = sum(fm.technical_debt_minutes for fm in function_metrics)
    total_cls_debt = sum(cm.technical_debt_minutes for cm in class_metrics)
    total_minutes = total_fn_debt + total_cls_debt
    summary.technical_debt = TechnicalDebtSummary(
        total_minutes=round(total_minutes, 2),
        total_hours=round(total_minutes / 60, 2),
        total_days=round(total_minutes / 480, 2),  # 8h = 1 working day
    )

    return summary
