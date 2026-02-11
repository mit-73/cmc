"""File-level metrics: NOI, NOEI, and per-file aggregation."""

from __future__ import annotations

from typing import List, Set

from ..config import Thresholds
from ..models import FileMetrics, FunctionMetrics, ParsedFile
from .code_smells import compute_code_smells


def compute_file_metrics(
    parsed_file: ParsedFile,
    module_name: str,
    function_metrics: List[FunctionMetrics],
    thresholds: Thresholds,
    internal_packages: Set[str],
) -> FileMetrics:
    """Compute file-level metrics including import analysis, aggregation, and code smells."""

    # NOI - Number of Imports
    noi = len(parsed_file.imports)

    # NOEI - Number of External Imports
    noei = sum(
        1 for imp in parsed_file.imports
        if imp.is_package and imp.package_name not in internal_packages
    )

    # Code smells
    smells = compute_code_smells(parsed_file)

    # Count classes and functions
    classes_count = len(parsed_file.classes)
    functions_count = len(function_metrics)

    # Aggregate function metrics
    cyclo_sum = sum(fm.cyclo for fm in function_metrics)
    cyclo_avg = cyclo_sum / functions_count if functions_count > 0 else 0.0
    cyclo_max = max((fm.cyclo for fm in function_metrics), default=0)

    halvol_values = [fm.halstead_volume for fm in function_metrics]
    halvol_avg = sum(halvol_values) / len(halvol_values) if halvol_values else 0.0

    mi_values = [fm.mi for fm in function_metrics]
    mi_avg = sum(mi_values) / len(mi_values) if mi_values else 100.0
    mi_min = min(mi_values) if mi_values else 100.0

    return FileMetrics(
        path=parsed_file.path,
        module=module_name,
        loc=parsed_file.loc,
        sloc=parsed_file.sloc,
        noi=noi,
        noei=noei,
        classes_count=classes_count,
        functions_count=functions_count,
        cyclo_sum=cyclo_sum,
        cyclo_avg=round(cyclo_avg, 2),
        cyclo_max=cyclo_max,
        halstead_volume_avg=round(halvol_avg, 2),
        mi_avg=round(mi_avg, 2),
        mi_min=round(mi_min, 2),
        static_members=smells["static_members"],
        hardcoded_strings=smells["hardcoded_strings"],
        magic_numbers=smells["magic_numbers"],
    )
