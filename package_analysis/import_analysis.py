"""Import analysis for packages.

Detects cross-package imports, import statistics per package,
and shotgun surgery candidates (widely imported internal files).
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List, Set

from ..models import ParsedFile, ParsedImport
from .models import CrossPackageImport, ImportStatistics, ShotgunSurgeryCandidate


def get_cross_package_imports(
    parsed_files: List[ParsedFile],
    module_name: str,
    internal_packages: Set[str],
) -> List[CrossPackageImport]:
    """Find all imports that reference other internal packages.

    Args:
        parsed_files: Parsed files for the module.
        module_name: Name of the current module.
        internal_packages: Set of all internal package names.

    Returns:
        List of cross-package imports found.
    """
    results: List[CrossPackageImport] = []

    for pf in parsed_files:
        # We need line numbers — scan source directly
        for line_num, line in enumerate(pf.source.splitlines(), 1):
            stripped = line.strip()
            if not stripped.startswith(('import ', 'export ')):
                continue
            # Extract URI
            m = re.search(r"['\"]([^'\"]+)['\"]", stripped)
            if not m:
                continue
            uri = m.group(1)
            if not uri.startswith('package:'):
                continue
            # Extract package name
            pkg = uri[len('package:'):].split('/')[0]
            if pkg == module_name:
                continue  # self-import
            if pkg in internal_packages:
                results.append(CrossPackageImport(
                    file_path=pf.path,
                    line_number=line_num,
                    imported_package=pkg,
                    import_uri=uri,
                ))

    return results


def get_import_statistics(
    parsed_files: List[ParsedFile],
) -> List[ImportStatistics]:
    """Count imports grouped by target package name.

    Args:
        parsed_files: Parsed files for the module.

    Returns:
        Sorted list of ImportStatistics (descending by count).
    """
    counts: Dict[str, int] = defaultdict(int)

    for pf in parsed_files:
        for imp in pf.imports:
            if imp.is_dart_core:
                continue
            if imp.is_package and imp.package_name:
                counts[imp.package_name] += 1
            elif imp.is_relative:
                counts["(relative)"] += 1

    results = [
        ImportStatistics(package_name=pkg, count=cnt)
        for pkg, cnt in counts.items()
    ]
    results.sort(key=lambda x: x.count, reverse=True)
    return results


def detect_shotgun_surgery(
    parsed_files: List[ParsedFile],
    top_n: int = 30,
) -> List[ShotgunSurgeryCandidate]:
    """Find internal files that are most widely imported (potential shotgun surgery).

    Shotgun surgery is indicated when a single file is imported by many others,
    meaning changes to it propagate widely.

    Args:
        parsed_files: Parsed files for the module.
        top_n: Maximum number of candidates to return.

    Returns:
        List of ShotgunSurgeryCandidate sorted by usage_count descending.
    """
    import_counts: Dict[str, int] = defaultdict(int)

    for pf in parsed_files:
        for imp in pf.imports:
            if imp.is_relative:
                import_counts[imp.uri] += 1
            elif imp.is_package and imp.package_name:
                # Track the full import path (package:foo/bar.dart)
                import_counts[imp.uri] += 1

    results = [
        ShotgunSurgeryCandidate(relative_path=path, usage_count=count)
        for path, count in import_counts.items()
    ]
    results.sort(key=lambda x: x.usage_count, reverse=True)
    return results[:top_n]
