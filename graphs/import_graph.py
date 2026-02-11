"""Import-level dependency graph builder.

Scans Dart import statements across all modules to build an inter-package
dependency graph. Reuses ParsedFile.imports from the existing parser.
"""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Dict, List, Optional, Set

from ..config import MetricsConfig
from ..discovery import discover_modules, list_dart_files
from ..models import Module, ParsedFile, ParsedImport
from .models import DependencyGraph, GraphEdge, GraphNode


def build_import_graph(
    modules: List[Module],
    module_parsed_files: Dict[str, List[ParsedFile]],
    config: MetricsConfig,
    include_tests: bool = False,
) -> DependencyGraph:
    """Build an import-level dependency graph between packages.

    Uses already-parsed files from the collector to extract import information.

    Args:
        modules: List of discovered modules.
        module_parsed_files: Map of module_name -> list of ParsedFile.
        config: Configuration.
        include_tests: Whether to include test imports.

    Returns:
        DependencyGraph with inter-package import edges.
    """
    internal_names: Set[str] = {m.name for m in modules}
    external_packages: Set[str] = set()
    edge_counts: Dict[tuple, int] = defaultdict(int)

    # Map module name by path prefix for fallback resolution
    path_to_module: Dict[str, str] = {}
    for m in modules:
        path_to_module[m.path] = m.name

    for module in modules:
        parsed_files = module_parsed_files.get(module.name, [])
        for pf in parsed_files:
            for imp in pf.imports:
                if imp.is_dart_core:
                    continue

                if imp.is_package and imp.package_name:
                    to_name = imp.package_name
                    if to_name == module.name:
                        continue  # self-import
                    if to_name in internal_names:
                        edge_counts[(module.name, to_name)] += 1
                    else:
                        external_packages.add(to_name)
                # Relative imports stay within the same package, skip

    # Build graph
    node_names: Set[str] = set()
    for (a, b) in edge_counts:
        node_names.add(a)
        node_names.add(b)

    # Ensure all modules are nodes even without edges
    for m in modules:
        node_names.add(m.name)

    module_map = {m.name: m for m in modules}
    nodes = []
    for name in sorted(node_names):
        m = module_map.get(name)
        nodes.append(GraphNode(
            id=name,
            name=name,
            path=m.path if m else None,
        ))

    edges = []
    for (a, b), weight in sorted(edge_counts.items()):
        edges.append(GraphEdge(
            from_node=a,
            to_node=b,
            weight=weight,
            edge_type="import",
        ))

    return DependencyGraph(
        nodes=nodes,
        edges=edges,
        external_packages=sorted(external_packages),
        graph_type="import",
    )


def build_per_module_import_details(
    module_name: str,
    parsed_files: List[ParsedFile],
    internal_names: Set[str],
) -> Dict[str, Dict[str, int]]:
    """Build per-file import details for a specific module.

    Returns dict: from_relative_path -> {to_package: count}
    """
    result: Dict[str, Dict[str, int]] = {}
    for pf in parsed_files:
        imports_by_pkg: Dict[str, int] = defaultdict(int)
        for imp in pf.imports:
            if imp.is_dart_core:
                continue
            if imp.is_package and imp.package_name:
                if imp.package_name != module_name:
                    imports_by_pkg[imp.package_name] += 1
        if imports_by_pkg:
            result[pf.path] = dict(imports_by_pkg)
    return result
