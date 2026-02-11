"""Design Structure Matrix (DSM) for module dependencies.

Produces an NxN matrix (module × module) where cell[i][j] = number
of imports from module i to module j. Reveals cyclic dependencies
at a glance: if both cell[i][j] and cell[j][i] are non-zero, there
is a cycle between modules i and j.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from ..graphs.models import DependencyGraph


@dataclass
class DSMResult:
    """Design Structure Matrix result."""
    modules: List[str]                    # ordered module names
    matrix: List[List[int]]              # matrix[from_idx][to_idx] = import count
    cycles: List[Tuple[str, str]]        # detected cyclic pairs
    total_imports: int = 0

    def to_dict(self) -> dict:
        return {
            "modules": self.modules,
            "matrix": self.matrix,
            "cycles": [{"from": a, "to": b} for a, b in self.cycles],
            "total_imports": self.total_imports,
        }


def build_dsm(import_graph: DependencyGraph) -> DSMResult:
    """Build a Design Structure Matrix from an import graph.

    Args:
        import_graph: The import-level dependency graph.

    Returns:
        DSMResult with the matrix, module names, and detected cycles.
    """
    # Collect internal module names (those that appear as from_node in edges)
    internal_modules: Set[str] = set()
    for node in import_graph.nodes:
        if not node.is_external:
            internal_modules.add(node.name)

    # Sort alphabetically for consistent ordering
    modules = sorted(internal_modules)
    idx_map = {name: i for i, name in enumerate(modules)}
    n = len(modules)

    # Initialize NxN matrix
    matrix = [[0] * n for _ in range(n)]

    total_imports = 0
    for edge in import_graph.edges:
        if edge.from_node in idx_map and edge.to_node in idx_map:
            fi = idx_map[edge.from_node]
            ti = idx_map[edge.to_node]
            matrix[fi][ti] = edge.weight
            total_imports += edge.weight

    # Detect cyclic pairs
    cycles: List[Tuple[str, str]] = []
    for i in range(n):
        for j in range(i + 1, n):
            if matrix[i][j] > 0 and matrix[j][i] > 0:
                cycles.append((modules[i], modules[j]))

    return DSMResult(
        modules=modules,
        matrix=matrix,
        cycles=cycles,
        total_imports=total_imports,
    )


def dsm_to_markdown(dsm: DSMResult) -> str:
    """Render DSM as a Markdown table.

    Args:
        dsm: DSM result.

    Returns:
        Markdown string with the matrix table and cycle warnings.
    """
    lines: List[str] = []
    modules = dsm.modules
    n = len(modules)

    if n == 0:
        return "_No modules to display._\n"

    # Abbreviate module names for header
    short_names = [_abbreviate(m) for m in modules]

    # Header
    header = "| From \\ To | " + " | ".join(f"**{s}**" for s in short_names) + " |"
    sep = "|---|" + "|".join(["---:"] * n) + "|"
    lines.append(header)
    lines.append(sep)

    # Rows
    for i in range(n):
        row_vals = []
        for j in range(n):
            v = dsm.matrix[i][j]
            if i == j:
                row_vals.append("—")
            elif v == 0:
                row_vals.append("·")
            else:
                row_vals.append(str(v))
        lines.append(f"| **{short_names[i]}** | " + " | ".join(row_vals) + " |")

    lines.append("")

    # Legend
    lines.append(f"_Total inter-module imports: {dsm.total_imports}_\n")

    # Full name mapping
    lines.append("<details><summary>Module abbreviations</summary>\n")
    for short, full in zip(short_names, modules):
        lines.append(f"- **{short}** = `{full}`")
    lines.append("\n</details>\n")

    # Cycles
    if dsm.cycles:
        lines.append(f"### ⚠️ Cyclic Dependencies ({len(dsm.cycles)})\n")
        for a, b in dsm.cycles:
            i, j = modules.index(a), modules.index(b)
            lines.append(f"- **{a}** ↔ **{b}** ({dsm.matrix[i][j]} → / {dsm.matrix[j][i]} ←)")
        lines.append("")
    else:
        lines.append("✅ No cyclic dependencies detected.\n")

    return "\n".join(lines)


def _abbreviate(name: str, max_len: int = 8) -> str:
    """Abbreviate a module name for table headers."""
    if len(name) <= max_len:
        return name
    # Try to use significant parts: split on _ and take initials
    parts = name.replace("-", "_").split("_")
    if len(parts) >= 2:
        abbr = "_".join(p[:3] for p in parts[:3])
        if len(abbr) <= max_len:
            return abbr
    return name[:max_len]
