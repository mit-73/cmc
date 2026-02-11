"""Distribution histograms for key metrics.

Generates bucket-based histograms for CC, MI, LOC, WMC, FPY, WMFP
with ASCII bar charts for Markdown and raw data for JSON/HTML.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..models import ClassMetrics, FileMetrics, FunctionMetrics


@dataclass
class HistogramBucket:
    """A single histogram bucket."""
    label: str          # e.g. "1-5", ">50"
    lo: float           # inclusive lower bound
    hi: float           # exclusive upper bound (inf for last bucket)
    count: int = 0
    pct: float = 0.0    # percentage of total

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "lo": self.lo,
            "hi": self.hi if not math.isinf(self.hi) else None,
            "count": self.count,
            "pct": round(self.pct, 2),
        }


@dataclass
class Histogram:
    """A complete histogram for a metric."""
    metric_name: str
    total: int
    buckets: List[HistogramBucket] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "metric_name": self.metric_name,
            "total": self.total,
            "buckets": [b.to_dict() for b in self.buckets],
        }


# ---------------------------------------------------------------------------
# Predefined bucket ranges for each metric
# ---------------------------------------------------------------------------

_CC_BUCKETS = [
    ("1", 0, 2),
    ("2-5", 2, 6),
    ("6-10", 6, 11),
    ("11-20", 11, 21),
    ("21-50", 21, 51),
    (">50", 51, float("inf")),
]

_MI_BUCKETS = [
    ("<20", 0, 20),
    ("20-40", 20, 40),
    ("40-60", 40, 60),
    ("60-80", 60, 80),
    ("80-100", 80, 101),
]

_LOC_FUNCTION_BUCKETS = [
    ("1-10", 0, 11),
    ("11-30", 11, 31),
    ("31-50", 31, 51),
    ("51-80", 51, 81),
    ("81-150", 81, 151),
    (">150", 151, float("inf")),
]

_WMC_BUCKETS = [
    ("1-5", 0, 6),
    ("6-10", 6, 11),
    ("11-20", 11, 21),
    ("21-50", 21, 51),
    (">50", 51, float("inf")),
]

_FPY_BUCKETS = [
    ("<0.2", 0, 0.2),
    ("0.2-0.4", 0.2, 0.4),
    ("0.4-0.6", 0.4, 0.6),
    ("0.6-0.8", 0.6, 0.8),
    ("0.8-1.0", 0.8, 1.01),
]

_WMFP_BUCKETS = [
    ("0-2", 0, 2),
    ("2-5", 2, 5),
    ("5-10", 5, 10),
    ("10-15", 10, 15),
    ("15-30", 15, 30),
    (">30", 30, float("inf")),
]

_TD_FILE_BUCKETS = [
    ("0", 0, 1),
    ("1-10", 1, 11),
    ("11-30", 11, 31),
    ("31-60", 31, 61),
    ("61-120", 61, 121),
    (">120", 121, float("inf")),
]


def _build_histogram(
    name: str,
    values: List[float],
    bucket_defs: List[Tuple[str, float, float]],
) -> Histogram:
    """Build a histogram from values using predefined buckets."""
    total = len(values)
    buckets: List[HistogramBucket] = []

    for label, lo, hi in bucket_defs:
        count = sum(1 for v in values if lo <= v < hi)
        pct = (count / total * 100) if total > 0 else 0.0
        buckets.append(HistogramBucket(label=label, lo=lo, hi=hi, count=count, pct=pct))

    return Histogram(metric_name=name, total=total, buckets=buckets)


def compute_distributions(
    function_metrics: List[FunctionMetrics],
    class_metrics: List[ClassMetrics],
    file_metrics: List[FileMetrics],
) -> Dict[str, Histogram]:
    """Compute distribution histograms for all key metrics.

    Returns:
        Dict of metric_name -> Histogram
    """
    distributions: Dict[str, Histogram] = {}

    if function_metrics:
        distributions["cyclomatic_complexity"] = _build_histogram(
            "Cyclomatic Complexity (CC)",
            [f.cyclo for f in function_metrics],
            _CC_BUCKETS,
        )
        distributions["maintainability_index"] = _build_histogram(
            "Maintainability Index (MI)",
            [f.mi for f in function_metrics],
            _MI_BUCKETS,
        )
        distributions["function_loc"] = _build_histogram(
            "Function LOC",
            [f.loc for f in function_metrics],
            _LOC_FUNCTION_BUCKETS,
        )
        distributions["function_fpy"] = _build_histogram(
            "Function FPY",
            [f.fpy for f in function_metrics],
            _FPY_BUCKETS,
        )
        distributions["function_wmfp"] = _build_histogram(
            "Function WMFP",
            [f.wmfp for f in function_metrics],
            _WMFP_BUCKETS,
        )

    if class_metrics:
        distributions["weighted_methods"] = _build_histogram(
            "Weighted Methods per Class (WMC)",
            [c.wmc for c in class_metrics],
            _WMC_BUCKETS,
        )

    if file_metrics:
        distributions["file_technical_debt"] = _build_histogram(
            "File Technical Debt (minutes)",
            [f.technical_debt_minutes for f in file_metrics],
            _TD_FILE_BUCKETS,
        )

    return distributions


def histogram_to_markdown(hist: Histogram, bar_width: int = 30) -> str:
    """Render a histogram as a Markdown table with ASCII bars.

    Args:
        hist: Histogram data.
        bar_width: Maximum bar width in characters.

    Returns:
        Markdown string.
    """
    lines: List[str] = []
    lines.append(f"### {hist.metric_name}\n")

    max_count = max((b.count for b in hist.buckets), default=1)
    if max_count == 0:
        max_count = 1

    lines.append(f"| Range | Count | % | Distribution |")
    lines.append("|---:|---:|---:|:---|")

    for b in hist.buckets:
        bar_len = int(b.count / max_count * bar_width)
        bar = "█" * bar_len
        lines.append(f"| {b.label} | {b.count:,} | {b.pct:.1f}% | {bar} |")

    lines.append(f"\n_Total: {hist.total:,}_\n")
    return "\n".join(lines)
