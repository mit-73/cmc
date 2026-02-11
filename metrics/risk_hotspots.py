"""Churn × Complexity risk hotspot analysis.

Combines git change frequency (churn) with code complexity metrics
to identify files that are both complex and frequently changing —
the highest-risk refactoring candidates.

Risk score = normalize(churn) × normalize(complexity)
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional

from ..models import FileMetrics


@dataclass
class RiskHotspot:
    """A file with its risk score based on churn × complexity."""
    path: str
    module: str
    churn: int              # number of commits
    complexity: float       # composite complexity (CC sum + TD)
    risk_score: float       # normalized churn × normalized complexity (0-1)
    cc_max: int = 0
    cc_sum: int = 0
    td_minutes: float = 0.0
    loc: int = 0
    mi_avg: float = 0.0

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "module": self.module,
            "churn": self.churn,
            "complexity": round(self.complexity, 2),
            "risk_score": round(self.risk_score, 4),
            "cc_max": self.cc_max,
            "cc_sum": self.cc_sum,
            "td_minutes": round(self.td_minutes, 2),
            "loc": self.loc,
            "mi_avg": round(self.mi_avg, 2),
        }


def get_file_churn(
    repo_root: str,
    paths: List[str],
    since: str = "2025-01-01",
) -> Dict[str, int]:
    """Get commit counts per file using git log.

    Args:
        repo_root: Absolute path to git repository root.
        paths: List of relative file paths to check.
        since: Date string for --since.

    Returns:
        Dict of relative_path -> commit_count.
    """
    if not paths:
        return {}

    try:
        result = subprocess.run(
            [
                "git", "-C", repo_root,
                "log",
                "--format=format:",
                "--name-only",
                f"--since={since}",
                "--",
            ] + paths,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            return {}

        counts: Dict[str, int] = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            if line:
                counts[line] = counts.get(line, 0) + 1
        return counts

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return {}


def compute_risk_hotspots(
    file_metrics: List[FileMetrics],
    repo_root: str,
    since: str = "2025-01-01",
    top_n: int = 30,
) -> List[RiskHotspot]:
    """Compute risk hotspots = churn × complexity.

    Args:
        file_metrics: File-level metrics with CC, TD, etc.
        repo_root: Absolute path to git repository.
        since: Start date for git churn analysis.
        top_n: Number of top hotspots to return.

    Returns:
        List of RiskHotspot sorted by risk_score descending.
    """
    if not file_metrics:
        return []

    # Gather file paths
    all_paths = [fm.path for fm in file_metrics]

    # Get churn data
    churn_map = get_file_churn(repo_root, all_paths, since=since)

    # Build raw data: path -> (churn, complexity)
    # Complexity = CC_sum + TD_density (TD per 100 LOC)
    raw: List[dict] = []
    for fm in file_metrics:
        churn = churn_map.get(fm.path, 0)
        if churn == 0:
            continue  # skip files with no changes
        # Composite complexity: weighted CC sum + TD normalized
        complexity = fm.cyclo_sum + (fm.technical_debt_minutes / max(fm.loc, 1)) * 10
        raw.append({
            "fm": fm,
            "churn": churn,
            "complexity": complexity,
        })

    if not raw:
        return []

    # Normalize to 0-1 range
    max_churn = max(r["churn"] for r in raw)
    max_complexity = max(r["complexity"] for r in raw)

    if max_churn == 0 or max_complexity == 0:
        return []

    hotspots: List[RiskHotspot] = []
    for r in raw:
        norm_churn = r["churn"] / max_churn
        norm_complexity = r["complexity"] / max_complexity
        risk = norm_churn * norm_complexity
        fm = r["fm"]
        hotspots.append(RiskHotspot(
            path=fm.path,
            module=fm.module,
            churn=r["churn"],
            complexity=r["complexity"],
            risk_score=risk,
            cc_max=fm.cyclo_max,
            cc_sum=fm.cyclo_sum,
            td_minutes=fm.technical_debt_minutes,
            loc=fm.loc,
            mi_avg=fm.mi_avg,
        ))

    hotspots.sort(key=lambda h: h.risk_score, reverse=True)
    return hotspots[:top_n]
