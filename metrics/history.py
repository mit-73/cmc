"""History / trend tracking for metrics snapshots.

Saves a compact JSON snapshot after each run and provides
comparison (delta) between any two snapshots.
"""

from __future__ import annotations

import glob
import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..models import ModuleSummary, ProjectSummary, StatsSummary


# ---------------------------------------------------------------------------
# Snapshot model
# ---------------------------------------------------------------------------

@dataclass
class ModuleSnapshot:
    """Compact per-module data in a snapshot."""
    name: str
    files: int = 0
    classes: int = 0
    functions: int = 0
    loc: int = 0
    sloc: int = 0
    td_minutes: float = 0.0
    cc_avg: float = 0.0
    mi_avg: float = 0.0
    fpy_avg: float = 0.0
    violations_total: int = 0
    grade: str = "—"
    score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "files": self.files,
            "classes": self.classes,
            "functions": self.functions,
            "loc": self.loc,
            "sloc": self.sloc,
            "td_minutes": round(self.td_minutes, 2),
            "cc_avg": round(self.cc_avg, 2),
            "mi_avg": round(self.mi_avg, 2),
            "fpy_avg": round(self.fpy_avg, 2),
            "violations_total": self.violations_total,
            "grade": self.grade,
            "score": round(self.score, 1),
        }


@dataclass
class Snapshot:
    """A complete metrics snapshot for trend tracking."""
    timestamp: str = ""
    git_commit: str = ""
    git_branch: str = ""
    project_loc: int = 0
    project_sloc: int = 0
    project_files: int = 0
    project_classes: int = 0
    project_functions: int = 0
    td_total_minutes: float = 0.0
    td_total_hours: float = 0.0
    violations_total: int = 0
    duplication_pct: float = 0.0
    modules: List[ModuleSnapshot] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "git_commit": self.git_commit,
            "git_branch": self.git_branch,
            "project_loc": self.project_loc,
            "project_sloc": self.project_sloc,
            "project_files": self.project_files,
            "project_classes": self.project_classes,
            "project_functions": self.project_functions,
            "td_total_minutes": round(self.td_total_minutes, 2),
            "td_total_hours": round(self.td_total_hours, 2),
            "violations_total": self.violations_total,
            "duplication_pct": round(self.duplication_pct, 2),
            "modules": [m.to_dict() for m in self.modules],
        }


# ---------------------------------------------------------------------------
# Delta model
# ---------------------------------------------------------------------------

@dataclass
class DeltaRow:
    """Delta for a single metric."""
    metric: str
    before: float
    after: float
    delta: float
    pct_change: float
    indicator: str  # 🟢 improved, 🔴 worsened, ⚪ unchanged

    def to_dict(self) -> dict:
        return {
            "metric": self.metric,
            "before": round(self.before, 2),
            "after": round(self.after, 2),
            "delta": round(self.delta, 2),
            "pct_change": round(self.pct_change, 2),
            "indicator": self.indicator,
        }


@dataclass
class SnapshotDelta:
    """Comparison between two snapshots."""
    baseline_ts: str
    current_ts: str
    rows: List[DeltaRow] = field(default_factory=list)
    module_deltas: Dict[str, List[DeltaRow]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "baseline": self.baseline_ts,
            "current": self.current_ts,
            "project_delta": [r.to_dict() for r in self.rows],
            "module_deltas": {
                k: [r.to_dict() for r in v]
                for k, v in self.module_deltas.items()
            },
        }


# ---------------------------------------------------------------------------
# Build snapshot
# ---------------------------------------------------------------------------

def build_snapshot(
    project_summary: ProjectSummary,
    module_summaries: List[ModuleSummary],
    module_ratings: Dict[str, Tuple[float, str]],
    duplication_pct: float = 0.0,
    repo_root: str = ".",
) -> Snapshot:
    """Build a snapshot from current analysis results.

    Args:
        project_summary: Project-level summary.
        module_summaries: Per-module summaries.
        module_ratings: Dict of module_name -> (score, grade).
        duplication_pct: Overall duplication percentage.
        repo_root: Git repository root for commit/branch info.

    Returns:
        Snapshot object.
    """
    snap = Snapshot(
        timestamp=datetime.now(timezone.utc).isoformat(),
        git_commit=_git_rev(repo_root),
        git_branch=_git_branch(repo_root),
        project_loc=project_summary.loc_total,
        project_sloc=project_summary.sloc_total,
        project_files=project_summary.files_count,
        project_classes=project_summary.classes_count,
        project_functions=project_summary.functions_count,
        td_total_minutes=project_summary.technical_debt.total_minutes,
        td_total_hours=project_summary.technical_debt.total_hours,
        duplication_pct=duplication_pct,
    )

    # Count total violations
    v = project_summary.violations
    snap.violations_total = (
        v.cyclo_high + v.cyclo_very_high + v.mi_poor + v.mnl_critical
        + v.god_classes + v.low_cohesion + v.high_coupling
        + v.excessive_params + v.excessive_imports
        + v.magic_numbers_high + v.hardcoded_strings_high + v.potential_dead_code
    )

    for ms in module_summaries:
        score, grade = module_ratings.get(ms.module, (0.0, "—"))
        cc_stats = ms.metrics_summary.get("cyclo")
        mi_stats = ms.metrics_summary.get("mi")
        fpy_stats = ms.metrics_summary.get("fpy_function")

        v_ms = ms.violations
        v_total = (
            v_ms.cyclo_high + v_ms.cyclo_very_high + v_ms.mi_poor + v_ms.mnl_critical
            + v_ms.god_classes + v_ms.low_cohesion + v_ms.high_coupling
            + v_ms.excessive_params + v_ms.excessive_imports
            + v_ms.magic_numbers_high + v_ms.hardcoded_strings_high + v_ms.potential_dead_code
        )

        snap.modules.append(ModuleSnapshot(
            name=ms.module,
            files=ms.files_count,
            classes=ms.classes_count,
            functions=ms.functions_count,
            loc=ms.loc_total,
            sloc=ms.sloc_total,
            td_minutes=ms.technical_debt.total_minutes,
            cc_avg=cc_stats.mean if isinstance(cc_stats, StatsSummary) else 0.0,
            mi_avg=mi_stats.mean if isinstance(mi_stats, StatsSummary) else 0.0,
            fpy_avg=fpy_stats.mean if isinstance(fpy_stats, StatsSummary) else 0.0,
            violations_total=v_total,
            grade=grade,
            score=score,
        ))

    return snap


# ---------------------------------------------------------------------------
# Save / load snapshots
# ---------------------------------------------------------------------------

def save_snapshot(snapshot: Snapshot, snapshot_dir: str) -> str:
    """Save compact snapshot inside the given snapshot directory.

    Args:
        snapshot: The snapshot to save.
        snapshot_dir: The concrete snapshot directory
                      (e.g. ``<output>/history/20260216_133352/``).

    Returns the path to the saved file.
    """
    os.makedirs(snapshot_dir, exist_ok=True)
    path = os.path.join(snapshot_dir, "snapshot.json")

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(snapshot.to_dict(), fh, indent=2, ensure_ascii=False)

    return path


def load_snapshot(path: str) -> Snapshot:
    """Load a snapshot from JSON file."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    snap = Snapshot(
        timestamp=data.get("timestamp", ""),
        git_commit=data.get("git_commit", ""),
        git_branch=data.get("git_branch", ""),
        project_loc=data.get("project_loc", 0),
        project_sloc=data.get("project_sloc", 0),
        project_files=data.get("project_files", 0),
        project_classes=data.get("project_classes", 0),
        project_functions=data.get("project_functions", 0),
        td_total_minutes=data.get("td_total_minutes", 0),
        td_total_hours=data.get("td_total_hours", 0),
        violations_total=data.get("violations_total", 0),
        duplication_pct=data.get("duplication_pct", 0),
    )

    for m in data.get("modules", []):
        snap.modules.append(ModuleSnapshot(
            name=m.get("name", ""),
            files=m.get("files", 0),
            classes=m.get("classes", 0),
            functions=m.get("functions", 0),
            loc=m.get("loc", 0),
            sloc=m.get("sloc", 0),
            td_minutes=m.get("td_minutes", 0),
            cc_avg=m.get("cc_avg", 0),
            mi_avg=m.get("mi_avg", 0),
            fpy_avg=m.get("fpy_avg", 0),
            violations_total=m.get("violations_total", 0),
            grade=m.get("grade", "—"),
            score=m.get("score", 0),
        ))

    return snap


def list_snapshots(output_dir: str) -> List[str]:
    """List all snapshot directories inside ``history/``.

    Returns directory paths sorted chronologically (by directory name).
    Each directory must contain ``metadata.json``.
    """
    history_dir = os.path.join(output_dir, "history")
    if not os.path.isdir(history_dir):
        return []
    dirs = sorted(
        os.path.join(history_dir, d)
        for d in os.listdir(history_dir)
        if os.path.isdir(os.path.join(history_dir, d))
        and os.path.isfile(os.path.join(history_dir, d, "metadata.json"))
    )
    return dirs


def list_snapshot_ids(output_dir: str) -> List[str]:
    """Return sorted list of snapshot directory names (e.g. '20260216_133352').

    A directory is considered a valid snapshot when it contains at least
    ``metadata.json`` (always written by the collector).
    """
    history_dir = os.path.join(output_dir, "history")
    if not os.path.isdir(history_dir):
        return []
    ids = sorted(
        d for d in os.listdir(history_dir)
        if os.path.isdir(os.path.join(history_dir, d))
        and os.path.isfile(os.path.join(history_dir, d, "metadata.json"))
    )
    return ids


def get_latest_snapshot(output_dir: str) -> Optional[Snapshot]:
    """Load the most recent snapshot (if any).

    Reconstructs the Snapshot from actual data files in the latest
    snapshot directory (metadata.json, project_summary.json,
    technical_debt.json, duplication.json, ratings.json).
    """
    dirs = list_snapshots(output_dir)
    if not dirs:
        return None
    snap_dir = dirs[-1]

    # Try legacy snapshot.json first (backward compat)
    legacy_path = os.path.join(snap_dir, "snapshot.json")
    if os.path.isfile(legacy_path):
        return load_snapshot(legacy_path)

    # Reconstruct from actual data files
    return _reconstruct_snapshot(snap_dir)


def _load_json(path: str) -> Optional[dict]:
    """Load JSON file, return None on error."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def _reconstruct_snapshot(snap_dir: str) -> Optional[Snapshot]:
    """Reconstruct a Snapshot from individual data files in snap_dir."""
    meta = _load_json(os.path.join(snap_dir, "metadata.json"))
    if not meta:
        return None

    ps = _load_json(os.path.join(snap_dir, "project_summary.json")) or {}
    td = _load_json(os.path.join(snap_dir, "technical_debt.json")) or {}
    dup = _load_json(os.path.join(snap_dir, "duplication.json")) or {}
    rat = _load_json(os.path.join(snap_dir, "ratings.json")) or {}

    snap = Snapshot(
        timestamp=meta.get("timestamp", ""),
        git_commit=meta.get("git_commit", ""),
        git_branch=meta.get("git_branch", ""),
        project_loc=ps.get("loc_total", 0),
        project_sloc=ps.get("sloc_total", 0),
        project_files=ps.get("files_count", 0),
        project_classes=ps.get("classes_count", 0),
        project_functions=ps.get("functions_count", 0),
        td_total_minutes=td.get("total_minutes", 0),
        td_total_hours=td.get("total_hours", 0),
        violations_total=rat.get("violations_total", 0),
        duplication_pct=dup.get("duplication_pct", 0),
    )

    # Reconstruct module snapshots from ratings + module summaries
    modules_dir = os.path.join(snap_dir, "modules")
    rat_modules = {m["module"]: m for m in rat.get("modules", [])}
    td_by_module = {m["module"]: m for m in td.get("by_module", [])}

    if os.path.isdir(modules_dir):
        for fname in sorted(os.listdir(modules_dir)):
            if not fname.endswith("_summary.json"):
                continue
            mod_name = fname[:-len("_summary.json")]
            ms = _load_json(os.path.join(modules_dir, fname))
            if not ms:
                continue

            ri = rat_modules.get(mod_name, {})
            ti = td_by_module.get(mod_name, {})
            ms_summ = ms.get("metrics_summary", {})
            cc = ms_summ.get("cyclo", {})
            mi = ms_summ.get("mi", {})
            fpy = ms_summ.get("fpy_function", {})

            snap.modules.append(ModuleSnapshot(
                name=mod_name,
                files=ms.get("files_count", 0),
                classes=ms.get("classes_count", 0),
                functions=ms.get("functions_count", 0),
                loc=ms.get("loc_total", 0),
                sloc=ms.get("sloc_total", 0),
                td_minutes=ti.get("total_hours", 0) * 60 if ti else 0,
                cc_avg=cc.get("mean", 0) if isinstance(cc, dict) else 0,
                mi_avg=mi.get("mean", 0) if isinstance(mi, dict) else 0,
                fpy_avg=fpy.get("mean", 0) if isinstance(fpy, dict) else 0,
                violations_total=ri.get("violations_total", 0),
                grade=ri.get("grade", "—"),
                score=ri.get("score", 0),
            ))

    return snap


# ---------------------------------------------------------------------------
# Comparison / delta
# ---------------------------------------------------------------------------

def compare_snapshots(baseline: Snapshot, current: Snapshot) -> SnapshotDelta:
    """Compare two snapshots and produce a delta report.

    Args:
        baseline: Previous snapshot.
        current: Current snapshot.

    Returns:
        SnapshotDelta with project-level and module-level deltas.
    """
    delta = SnapshotDelta(
        baseline_ts=baseline.timestamp,
        current_ts=current.timestamp,
    )

    # Project-level deltas
    # For metrics where lower is better: TD, violations, duplication
    # For metrics where higher is better: (none at project level directly)
    _project_metrics = [
        ("LOC", baseline.project_loc, current.project_loc, "neutral"),
        ("SLOC", baseline.project_sloc, current.project_sloc, "neutral"),
        ("Files", baseline.project_files, current.project_files, "neutral"),
        ("Classes", baseline.project_classes, current.project_classes, "neutral"),
        ("Functions", baseline.project_functions, current.project_functions, "neutral"),
        ("TD (hours)", baseline.td_total_hours, current.td_total_hours, "lower"),
        ("Violations", baseline.violations_total, current.violations_total, "lower"),
        ("Duplication %", baseline.duplication_pct, current.duplication_pct, "lower"),
    ]

    for name, before, after, direction in _project_metrics:
        delta.rows.append(_make_delta_row(name, before, after, direction))

    # Module-level deltas
    baseline_modules = {m.name: m for m in baseline.modules}
    for cm in current.modules:
        bm = baseline_modules.get(cm.name)
        if bm is None:
            continue
        module_rows = [
            ("LOC", bm.loc, cm.loc, "neutral"),
            ("TD (min)", bm.td_minutes, cm.td_minutes, "lower"),
            ("CC avg", bm.cc_avg, cm.cc_avg, "lower"),
            ("MI avg", bm.mi_avg, cm.mi_avg, "higher"),
            ("FPY avg", bm.fpy_avg, cm.fpy_avg, "higher"),
            ("Violations", bm.violations_total, cm.violations_total, "lower"),
            ("Score", bm.score, cm.score, "higher"),
        ]
        delta.module_deltas[cm.name] = [
            _make_delta_row(n, b, a, d) for n, b, a, d in module_rows
        ]

    return delta


def _make_delta_row(
    metric: str,
    before: float,
    after: float,
    direction: str,
) -> DeltaRow:
    """Create a DeltaRow with indicator.

    Args:
        direction: "higher" = higher is better, "lower" = lower is better,
                   "neutral" = no judgment.
    """
    d = after - before
    pct = (d / before * 100) if before != 0 else 0.0

    if abs(d) < 0.01:
        indicator = "⚪"
    elif direction == "higher":
        indicator = "🟢" if d > 0 else "🔴"
    elif direction == "lower":
        indicator = "🟢" if d < 0 else "🔴"
    else:
        indicator = "⚪"

    return DeltaRow(
        metric=metric,
        before=before,
        after=after,
        delta=d,
        pct_change=pct,
        indicator=indicator,
    )


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def _git_rev(repo_root: str) -> str:
    """Get current git commit short hash."""
    try:
        r = subprocess.run(
            ["git", "-C", repo_root, "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def _git_branch(repo_root: str) -> str:
    """Get current git branch name."""
    try:
        r = subprocess.run(
            ["git", "-C", repo_root, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""
