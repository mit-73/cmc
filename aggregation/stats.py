"""Statistical utilities for aggregation."""

from __future__ import annotations

import math
from typing import List

from ..models import StatsSummary


def compute_stats(values: List[float]) -> StatsSummary:
    """Compute statistical summary for a list of values."""
    if not values:
        return StatsSummary()

    sorted_vals = sorted(values)
    n = len(sorted_vals)

    mean = sum(sorted_vals) / n
    median = _percentile(sorted_vals, 50)
    p90 = _percentile(sorted_vals, 90)
    min_val = sorted_vals[0]
    max_val = sorted_vals[-1]

    # Standard deviation
    if n > 1:
        variance = sum((x - mean) ** 2 for x in sorted_vals) / (n - 1)
        std_dev = math.sqrt(variance)
    else:
        std_dev = 0.0

    return StatsSummary(
        mean=round(mean, 2),
        median=round(median, 2),
        p90=round(p90, 2),
        min_val=round(min_val, 2),
        max_val=round(max_val, 2),
        std_dev=round(std_dev, 2),
    )


def _percentile(sorted_values: List[float], pct: float) -> float:
    """Compute the given percentile from sorted values."""
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    idx = (pct / 100.0) * (n - 1)
    lower = int(math.floor(idx))
    upper = int(math.ceil(idx))
    if lower == upper:
        return sorted_values[lower]
    frac = idx - lower
    return sorted_values[lower] * (1 - frac) + sorted_values[upper] * frac
