"""Rating system (A/B/C/D/E) for modules and files.

Grade is computed from a composite score based on:
- Maintainability Index (MI avg)
- Cyclomatic Complexity (CC avg)
- First-Pass Yield (FPY avg)
- Technical Debt density (TD minutes / kLOC)

Score formula (0-100):
    score = w_mi * norm_mi + w_cc * (100 - norm_cc) + w_fpy * (fpy * 100) + w_td * (100 - norm_td)

Grades:
    A  >=80   Excellent
    B  >=60   Good
    C  >=40   Acceptable
    D  >=20   Poor
    E  < 20   Critical
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..models import ClassMetrics, FileMetrics, FunctionMetrics, ModuleSummary, StatsSummary


@dataclass
class RatingConfig:
    """Weights for composite score (must sum to 1.0)."""
    weight_mi: float = 0.30
    weight_cc: float = 0.25
    weight_fpy: float = 0.25
    weight_td: float = 0.20
    # Normalization ceilings
    cc_max: float = 30.0      # CC at or above this maps to 0
    td_max: float = 100.0     # TD (min/kLOC) at or above this maps to 0


# Grade thresholds
_GRADE_THRESHOLDS = [
    (80, "A"),
    (60, "B"),
    (40, "C"),
    (20, "D"),
    (0,  "E"),
]


def score_to_grade(score: float) -> str:
    """Convert a 0-100 score to a letter grade."""
    for threshold, grade in _GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "E"


def compute_composite_score(
    mi_avg: float,
    cc_avg: float,
    fpy_avg: float,
    td_per_kloc: float,
    cfg: Optional[RatingConfig] = None,
) -> float:
    """Compute a 0-100 composite quality score.

    Args:
        mi_avg: Average Maintainability Index (0-100 scale).
        cc_avg: Average Cyclomatic Complexity.
        fpy_avg: Average First-Pass Yield (0.0-1.0).
        td_per_kloc: Technical debt minutes per 1000 lines of code.
        cfg: Rating configuration / weights.

    Returns:
        Score between 0.0 and 100.0.
    """
    if cfg is None:
        cfg = RatingConfig()

    # Normalize MI: already 0-100, clamp
    norm_mi = max(0.0, min(100.0, mi_avg))

    # Normalize CC: 1=100, cc_max=0
    norm_cc = max(0.0, min(100.0, (1.0 - cc_avg / cfg.cc_max) * 100.0))

    # Normalize FPY: 0-1 -> 0-100
    norm_fpy = max(0.0, min(100.0, fpy_avg * 100.0))

    # Normalize TD: 0=100, td_max=0
    norm_td = max(0.0, min(100.0, (1.0 - td_per_kloc / cfg.td_max) * 100.0))

    score = (
        cfg.weight_mi * norm_mi
        + cfg.weight_cc * norm_cc
        + cfg.weight_fpy * norm_fpy
        + cfg.weight_td * norm_td
    )

    return round(max(0.0, min(100.0, score)), 1)


def rate_module(
    module_summary: ModuleSummary,
    cfg: Optional[RatingConfig] = None,
) -> tuple:
    """Rate a module. Returns (score, grade).

    Args:
        module_summary: Aggregated module summary.
        cfg: Optional rating config.

    Returns:
        Tuple of (score: float, grade: str).
    """
    ms = module_summary

    # Extract averages from metrics_summary
    mi_stats = ms.metrics_summary.get("mi")
    cc_stats = ms.metrics_summary.get("cyclo")
    fpy_stats = ms.metrics_summary.get("fpy_function")

    mi_avg = mi_stats.mean if isinstance(mi_stats, StatsSummary) else 70.0
    cc_avg = cc_stats.mean if isinstance(cc_stats, StatsSummary) else 5.0
    fpy_avg = fpy_stats.mean if isinstance(fpy_stats, StatsSummary) else 0.8

    # TD per kLOC
    td_total = ms.technical_debt.total_minutes
    kloc = ms.loc_total / 1000.0 if ms.loc_total > 0 else 1.0
    td_per_kloc = td_total / kloc

    score = compute_composite_score(mi_avg, cc_avg, fpy_avg, td_per_kloc, cfg)
    return score, score_to_grade(score)


def rate_file(
    file_metric: FileMetrics,
    function_metrics: List[FunctionMetrics],
    cfg: Optional[RatingConfig] = None,
) -> tuple:
    """Rate a single file. Returns (score, grade).

    Args:
        file_metric: File-level metrics.
        function_metrics: Function metrics for this file.
        cfg: Optional rating config.

    Returns:
        Tuple of (score: float, grade: str).
    """
    # MI avg from file
    mi_avg = file_metric.mi_avg

    # CC avg
    if function_metrics:
        cc_avg = sum(f.cyclo for f in function_metrics) / len(function_metrics)
    else:
        cc_avg = file_metric.cyclo_avg

    # FPY
    fpy_avg = file_metric.fpy

    # TD density
    kloc = file_metric.loc / 1000.0 if file_metric.loc > 0 else 1.0
    td_per_kloc = file_metric.technical_debt_minutes / kloc

    score = compute_composite_score(mi_avg, cc_avg, fpy_avg, td_per_kloc, cfg)
    return score, score_to_grade(score)
