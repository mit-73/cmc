"""Pubspec-level dependency graph builder.

Reads pubspec.yaml files to build a dependency graph at the package declaration
level.
"""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

from ..config import MetricsConfig
from ..discovery import discover_modules
from ..models import Module
from .models import DependencyGraph, GraphEdge, GraphNode


def build_pubspec_graph(
    modules: List[Module],
    config: MetricsConfig,
    include_dev: bool = False,
    include_overrides: bool = False,
) -> DependencyGraph:
    """Build a dependency graph from pubspec.yaml declarations.

    Args:
        modules: Discovered modules.
        config: Configuration.
        include_dev: Include dev_dependencies.
        include_overrides: Include dependency_overrides.

    Returns:
        DependencyGraph with pubspec-level dependency edges.
    """
    root = config.root
    internal_names: Set[str] = {m.name for m in modules}
    external_packages: Set[str] = set()

    # Read all pubspecs
    pkg_data: Dict[str, Dict[str, Any]] = {}
    pkg_versions: Dict[str, Optional[str]] = {}
    pkg_publish: Dict[str, Optional[str]] = {}

    for m in modules:
        pubspec_path = os.path.join(root, m.path, "pubspec.yaml")
        if not os.path.isfile(pubspec_path):
            continue
        try:
            with open(pubspec_path, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
        except Exception:
            continue
        pkg_data[m.name] = data
        pkg_versions[m.name] = data.get("version")
        pkg_publish[m.name] = data.get("publish_to")

    # Build edges
    edges_list: List[GraphEdge] = []
    edge_counts: Dict[Tuple[str, str], int] = defaultdict(int)

    for pkg_name, data in pkg_data.items():
        sections = [("dependencies", "dependency")]
        if include_dev:
            sections.append(("dev_dependencies", "dev_dependency"))
        if include_overrides:
            sections.append(("dependency_overrides", "override"))

        for section_key, edge_type in sections:
            deps = data.get(section_key) or {}
            if not isinstance(deps, dict):
                continue
            for dep_name, dep_val in deps.items():
                source, version_constraint = _detect_dep_source(dep_val)
                # Resolve target name (for path deps, it might differ)
                target_name = dep_name

                # Check if path dependency points to internal package
                if source == "path" and isinstance(dep_val, dict):
                    path_val = dep_val.get("path", "")
                    resolved = _resolve_path_dep(root, pkg_name, data, path_val, modules)
                    if resolved:
                        target_name = resolved

                is_internal = target_name in internal_names

                if not is_internal:
                    external_packages.add(target_name)

                metadata = {
                    "source": source,
                    "dep_name": dep_name,
                    "section": section_key,
                }
                if version_constraint:
                    metadata["version_constraint"] = version_constraint
                if source == "path" and isinstance(dep_val, dict):
                    metadata["path"] = dep_val.get("path")

                edges_list.append(GraphEdge(
                    from_node=pkg_name,
                    to_node=target_name,
                    weight=1,
                    edge_type=edge_type,
                    metadata=metadata,
                ))

    # Build nodes
    nodes = []
    for m in modules:
        metadata = {}
        if pkg_versions.get(m.name):
            metadata["version"] = pkg_versions[m.name]
        if pkg_publish.get(m.name):
            metadata["publish_to"] = pkg_publish[m.name]
        nodes.append(GraphNode(
            id=m.name,
            name=m.name,
            path=m.path,
            version=pkg_versions.get(m.name),
            metadata=metadata,
        ))

    return DependencyGraph(
        nodes=nodes,
        edges=edges_list,
        external_packages=sorted(external_packages),
        graph_type="pubspec",
    )


def _detect_dep_source(dep_val: Any) -> Tuple[str, Optional[str]]:
    """Detect dependency source type and version constraint."""
    if dep_val is None:
        return "unknown", None
    if isinstance(dep_val, str):
        return "hosted", dep_val
    if isinstance(dep_val, dict):
        if "path" in dep_val:
            return "path", dep_val.get("version")
        if "git" in dep_val:
            git = dep_val["git"]
            if isinstance(git, str):
                return "git", git
            if isinstance(git, dict):
                return "git", git.get("ref")
        if "hosted" in dep_val:
            return "hosted", dep_val.get("version")
        if "sdk" in dep_val:
            return "sdk", dep_val.get("version")
        return "unknown", None
    return "unknown", None


def _resolve_path_dep(
    root: str,
    from_pkg: str,
    from_data: Dict,
    path_val: str,
    modules: List[Module],
) -> Optional[str]:
    """Resolve a path dependency to a module name."""
    if not path_val:
        return None

    # Try to find the matching module by path
    module_map = {m.path: m.name for m in modules}

    # Resolve relative to the package dir
    for m in modules:
        if from_pkg == m.name:
            abs_from = os.path.join(root, m.path)
            abs_target = os.path.normpath(os.path.join(abs_from, path_val))
            rel_target = os.path.relpath(abs_target, root)
            # Normalize path separators
            rel_target = rel_target.replace(os.sep, "/")
            if rel_target in module_map:
                return module_map[rel_target]
            # Try reading pubspec of target
            target_pubspec = os.path.join(abs_target, "pubspec.yaml")
            if os.path.isfile(target_pubspec):
                try:
                    with open(target_pubspec, "r", encoding="utf-8") as fh:
                        target_data = yaml.safe_load(fh) or {}
                    return target_data.get("name")
                except Exception:
                    pass
            break
    return None
