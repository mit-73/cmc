"""Monorepo module discovery."""

from __future__ import annotations

import fnmatch
import os
from typing import List

import yaml

from .config import MetricsConfig
from .models import Module


def discover_modules(config: MetricsConfig) -> List[Module]:
    """Discover all Dart modules in the monorepo based on strategy."""
    strategy = config.discovery.strategy
    if strategy == "workspace":
        return _discover_workspace(config)
    elif strategy == "manual":
        return _discover_manual(config)
    else:
        return _discover_auto(config)


def _discover_workspace(config: MetricsConfig) -> List[Module]:
    """Read workspace field from root pubspec.yaml."""
    root = config.root
    pubspec_path = os.path.join(root, "pubspec.yaml")
    if not os.path.isfile(pubspec_path):
        print(f"[discovery] root pubspec.yaml not found at {pubspec_path}, falling back to auto")
        return _discover_auto(config)

    with open(pubspec_path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    workspace_paths = data.get("workspace", [])
    if not workspace_paths:
        print("[discovery] workspace field is empty, falling back to auto")
        return _discover_auto(config)

    modules: List[Module] = []
    for rel_path in workspace_paths:
        if _is_excluded_path(rel_path, config.discovery.exclude_patterns):
            continue
        module = _load_module(root, rel_path)
        if module is not None:
            modules.append(module)

    return modules


def _discover_manual(config: MetricsConfig) -> List[Module]:
    """Use explicit module list from configuration."""
    modules: List[Module] = []
    for rel_path in config.discovery.modules:
        module = _load_module(config.root, rel_path)
        if module is not None:
            modules.append(module)
    return modules


def _discover_auto(config: MetricsConfig) -> List[Module]:
    """Recursively find all pubspec.yaml files."""
    root = config.root
    modules: List[Module] = []

    for dirpath, dirs, files in os.walk(root):
        # Prune hidden/build directories
        dirs[:] = [
            d for d in dirs
            if not d.startswith(".")
            and d not in (".dart_tool", "build", ".pub", "node_modules")
        ]

        if "pubspec.yaml" not in files:
            continue

        rel = os.path.relpath(dirpath, root)
        if rel == ".":
            continue  # skip root workspace pubspec

        if _is_excluded_path(rel, config.discovery.exclude_patterns):
            continue

        module = _load_module(root, rel)
        if module is not None:
            modules.append(module)

    return modules


def _load_module(root: str, rel_path: str) -> Module | None:
    """Load a single module from its pubspec.yaml."""
    abs_path = os.path.join(root, rel_path)
    pubspec_path = os.path.join(abs_path, "pubspec.yaml")

    if not os.path.isfile(pubspec_path):
        return None

    try:
        with open(pubspec_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception:
        return None

    name = data.get("name")
    if not name:
        return None

    # Check if it's a Flutter package
    deps = data.get("dependencies", {}) or {}
    is_flutter = "flutter" in deps

    return Module(name=name, path=rel_path, is_flutter=is_flutter)


def _is_excluded_path(rel_path: str, patterns: list) -> bool:
    """Check if a relative path matches any exclude pattern."""
    normalized = rel_path.replace(os.sep, "/")
    for pattern in patterns:
        if fnmatch.fnmatch(normalized, pattern):
            return True
        # Also check individual path components
        parts = normalized.split("/")
        for part in parts:
            if fnmatch.fnmatch(part, pattern):
                return True
    return False


def list_dart_files(root: str, module_path: str, config: MetricsConfig) -> List[str]:
    """List all Dart source files in a module, applying filters.

    Returns absolute paths.
    """
    abs_module = os.path.join(root, module_path) if not os.path.isabs(module_path) else module_path
    lib_dir = os.path.join(abs_module, "lib")
    test_dir = os.path.join(abs_module, "test")

    dirs_to_scan = [lib_dir]
    if config.discovery.include_tests and os.path.isdir(test_dir):
        dirs_to_scan.append(test_dir)

    files: List[str] = []
    for scan_dir in dirs_to_scan:
        if not os.path.isdir(scan_dir):
            continue
        for dirpath, dirs, filenames in os.walk(scan_dir):
            # Prune build dirs
            dirs[:] = [d for d in dirs if d not in (".dart_tool", "build", ".pub")]

            for f in filenames:
                if not f.endswith(".dart"):
                    continue
                full_path = os.path.join(dirpath, f)
                rel_to_root = os.path.relpath(full_path, root)
                if _is_file_excluded(rel_to_root, config.discovery.exclude_files):
                    continue
                files.append(full_path)

    return sorted(files)


def _is_file_excluded(rel_path: str, patterns: list) -> bool:
    """Check if a file matches any exclusion pattern."""
    normalized = rel_path.replace(os.sep, "/")
    for pattern in patterns:
        if fnmatch.fnmatch(normalized, pattern):
            return True
        # Also match just the filename
        if fnmatch.fnmatch(os.path.basename(normalized), pattern.lstrip("*/")):
            return True
    return False


def get_internal_packages(modules: List[Module]) -> set:
    """Return the set of package names that are internal to the monorepo."""
    return {m.name for m in modules}
