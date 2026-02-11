"""First-Pass Yield (FPY) computation.

FPY is a quality metric borrowed from Six Sigma that measures the
proportion of "clean" code — code that passes all quality gates
without requiring rework.

Range: 0.0 (all gates failed) to 1.0 (all gates passed).
"""

from __future__ import annotations

from typing import List

from ..config import FPYConfig
from ..models import ClassMetrics, FileMetrics, FunctionMetrics


def compute_function_fpy(
    fm: FunctionMetrics,
    config: FPYConfig,
) -> float:
    """Compute FPY for a single function (graduated).

    Checks each quality gate and returns the fraction of gates passed.
    """
    gates = config.function_gates
    checks = [
        fm.cyclo <= gates.max_cyclo,
        fm.max_nesting_level <= gates.max_nesting,
        fm.mi >= gates.min_mi,
        fm.number_of_parameters <= gates.max_params,
        fm.loc <= gates.max_loc,
    ]
    n = len(checks)
    passed = sum(1 for c in checks if c)
    return round(passed / n, 3) if n > 0 else 1.0


def compute_class_fpy(
    cm: ClassMetrics,
    config: FPYConfig,
) -> float:
    """Compute FPY for a single class (graduated).

    Checks each quality gate and returns the fraction of gates passed.
    """
    gates = config.class_gates
    checks = [
        cm.wmc <= gates.max_wmc,
        cm.cbo <= gates.max_cbo,
        cm.tcc >= gates.min_tcc or cm.nom < 2,  # TCC is meaningless for 0-1 method classes
        cm.nom <= gates.max_nom,
        cm.woc >= gates.min_woc,
    ]
    n = len(checks)
    passed = sum(1 for c in checks if c)
    return round(passed / n, 3) if n > 0 else 1.0


def compute_file_fpy(
    file_metric: FileMetrics,
    function_metrics: List[FunctionMetrics],
    class_metrics: List[ClassMetrics],
    config: FPYConfig,
) -> float:
    """Compute FPY for a file.

    Combines function, class, and file-level quality gates:
        FPY_file = alpha * FPY_functions + beta * FPY_classes + gamma * FPY_smells

    Where alpha, beta, gamma are configurable weights.
    """
    # Function FPY (average across all functions in this file)
    file_functions = [fm for fm in function_metrics if fm.path == file_metric.path]
    if file_functions:
        fn_fpy = sum(fm.fpy for fm in file_functions) / len(file_functions)
    else:
        fn_fpy = 1.0

    # Class FPY (average across all classes in this file)
    file_classes = [cm for cm in class_metrics if cm.path == file_metric.path]
    if file_classes:
        cls_fpy = sum(cm.fpy for cm in file_classes) / len(file_classes)
    else:
        cls_fpy = 1.0

    # File-level smell gates
    gates = config.file_gates
    smell_checks = [
        file_metric.noi <= gates.max_imports,
        file_metric.magic_numbers <= gates.max_magic_numbers,
        file_metric.hardcoded_strings <= gates.max_hardcoded_strings,
        file_metric.dead_code_estimate <= gates.max_dead_code,
    ]
    n_smells = len(smell_checks)
    smell_fpy = sum(1 for c in smell_checks if c) / n_smells if n_smells > 0 else 1.0

    # Weighted combination
    alpha = config.weight_functions
    beta = config.weight_classes
    gamma = config.weight_smells

    # Normalize weights in case they don't sum to 1
    total_weight = alpha + beta + gamma
    if total_weight > 0:
        alpha /= total_weight
        beta /= total_weight
        gamma /= total_weight

    # If there are no classes, redistribute their weight
    if not file_classes:
        if file_functions:
            alpha += beta
        else:
            gamma += beta
        beta = 0.0

    fpy = alpha * fn_fpy + beta * cls_fpy + gamma * smell_fpy
    return round(fpy, 3)
