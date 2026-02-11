"""Technical Debt calculation.

Computes TD in minutes for each function, class, and file based on
configured threshold exceedances and weight factors.
"""

from __future__ import annotations

from typing import List

from ..config import Thresholds
from ..models import ClassMetrics, FileMetrics, FunctionMetrics


def compute_function_debt(
    metrics: FunctionMetrics,
    thresholds: Thresholds,
) -> float:
    """Compute technical debt in minutes for a single function."""
    td = thresholds.technical_debt
    debt = 0.0

    # Cyclomatic complexity excess
    cyclo_threshold = thresholds.cyclomatic_complexity.high
    if metrics.cyclo > cyclo_threshold:
        debt += (metrics.cyclo - cyclo_threshold) * td.cyclo_excess_per_point

    # LOC excess
    loc_threshold = thresholds.lines_of_code.function_max
    if metrics.loc > loc_threshold:
        debt += (metrics.loc - loc_threshold) * td.loc_excess_per_line

    # Nesting excess
    mnl_threshold = thresholds.max_nesting_level.warning
    if metrics.max_nesting_level > mnl_threshold:
        debt += (metrics.max_nesting_level - mnl_threshold) * td.nesting_excess_per_level

    # Parameters excess
    nop_threshold = thresholds.number_of_parameters.warning
    if metrics.number_of_parameters > nop_threshold:
        debt += (metrics.number_of_parameters - nop_threshold) * td.params_excess_per_param

    return debt


def compute_class_debt(
    metrics: ClassMetrics,
    thresholds: Thresholds,
) -> float:
    """Compute technical debt in minutes for a single class."""
    td = thresholds.technical_debt
    debt = 0.0

    # CBO excess
    cbo_threshold = thresholds.coupling_between_objects.warning
    if metrics.cbo > cbo_threshold:
        debt += (metrics.cbo - cbo_threshold) * td.cbo_excess_per_point

    # DIT excess
    dit_threshold = thresholds.depth_of_inheritance.warning
    if metrics.dit > dit_threshold:
        debt += (metrics.dit - dit_threshold) * td.dit_excess_per_level

    # Low cohesion penalty
    tcc_threshold = thresholds.tight_class_cohesion.warning
    if metrics.tcc < tcc_threshold and metrics.nom >= 2:
        debt += td.low_cohesion_penalty

    # God class penalty (WMC > critical)
    wmc_threshold = thresholds.weighted_methods_per_class.critical
    if metrics.wmc > wmc_threshold:
        debt += td.god_class_penalty

    return debt


def apply_technical_debt(
    function_metrics: List[FunctionMetrics],
    class_metrics: List[ClassMetrics],
    file_metrics: List[FileMetrics],
    thresholds: Thresholds,
) -> None:
    """Compute and apply technical debt to all metrics in-place."""
    # Function debt
    for fm in function_metrics:
        fm.technical_debt_minutes = round(compute_function_debt(fm, thresholds), 2)

    # Class debt
    for cm in class_metrics:
        cm.technical_debt_minutes = round(compute_class_debt(cm, thresholds), 2)

    # File debt = sum of function debts in that file + proportion of class debts
    file_fn_debt: dict = {}
    for fm in function_metrics:
        file_fn_debt.setdefault(fm.path, 0.0)
        file_fn_debt[fm.path] += fm.technical_debt_minutes

    file_cls_debt: dict = {}
    for cm in class_metrics:
        file_cls_debt.setdefault(cm.path, 0.0)
        file_cls_debt[cm.path] += cm.technical_debt_minutes

    for fmet in file_metrics:
        fn_debt = file_fn_debt.get(fmet.path, 0.0)
        cls_debt = file_cls_debt.get(fmet.path, 0.0)
        fmet.technical_debt_minutes = round(fn_debt + cls_debt, 2)
