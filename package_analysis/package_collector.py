"""Package-level analysis orchestrator.

Combines import analysis, git analysis, and directory structure analysis
into a single PackageAnalysisResult per module.
"""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Dict, List, Set

from ..config import MetricsConfig
from ..models import Module, ParsedFile
from .models import DirectoryInfo, PackageAnalysisResult
from .import_analysis import (
    get_cross_package_imports,
    get_import_statistics,
    detect_shotgun_surgery,
)
from .git_analysis import get_git_hotspots


def collect_package_analysis(
    module: Module,
    parsed_files: List[ParsedFile],
    config: MetricsConfig,
    internal_packages: Set[str],
    git_since: str = "2025-01-01",
    shotgun_top_n: int = 30,
    git_top_n: int = 15,
) -> PackageAnalysisResult:
    """Collect comprehensive package analysis for a module.

    Args:
        module: The module to analyze.
        parsed_files: Already-parsed files for this module.
        config: Configuration.
        internal_packages: Set of all internal package names.
        git_since: Start date for git history analysis.
        shotgun_top_n: Max candidates for shotgun surgery detection.
        git_top_n: Max hotspots for git analysis.

    Returns:
        PackageAnalysisResult with all package-level analysis data.
    """
    root = config.root
    abs_module_path = os.path.join(root, module.path)

    # 1. Directory structure
    dir_structure = _analyze_directory_structure(abs_module_path, parsed_files)

    # 2. Cross-package imports
    cross_imports = get_cross_package_imports(
        parsed_files, module.name, internal_packages
    )

    # 3. Import statistics
    import_stats = get_import_statistics(parsed_files)

    # 4. Shotgun surgery detection
    shotgun = detect_shotgun_surgery(parsed_files, top_n=shotgun_top_n)

    # 5. Git hotspots
    git_hotspots = get_git_hotspots(
        module_path=abs_module_path,
        repo_root=root,
        since=git_since,
        top_n=git_top_n,
    )

    return PackageAnalysisResult(
        module_name=module.name,
        module_path=module.path,
        directory_structure=dir_structure,
        cross_package_imports=cross_imports,
        import_statistics=import_stats,
        shotgun_surgery_candidates=shotgun,
        git_hotspots=git_hotspots,
    )


def _analyze_directory_structure(
    module_path: str,
    parsed_files: List[ParsedFile],
) -> List[DirectoryInfo]:
    """Analyze directory structure with file counts and LOC.

    Args:
        module_path: Absolute path to the module.
        parsed_files: Parsed files for the module.

    Returns:
        List of DirectoryInfo for each subdirectory.
    """
    lib_dir = os.path.join(module_path, "lib")
    if not os.path.isdir(lib_dir):
        return []

    # Collect directories from parsed files
    dir_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"files": 0, "loc": 0})

    for pf in parsed_files:
        # Get directory relative to module
        parts = pf.path.replace("\\", "/").split("/")
        # Find module dir index
        module_basename = os.path.basename(module_path)
        try:
            idx = parts.index("lib")
            dir_path = "/".join(parts[:idx + 1])
            # Also add subdirectory if file is deeper
            if idx + 1 < len(parts) - 1:
                for i in range(idx + 1, len(parts)):
                    sub_dir = "/".join(parts[:i])
                    dir_stats[sub_dir]["files"] += 0  # just create entry
            dir_key = "/".join(parts[:-1]) if len(parts) > 1 else pf.path
        except (ValueError, IndexError):
            dir_key = os.path.dirname(pf.path)

        dir_stats[dir_key]["files"] += 1
        dir_stats[dir_key]["loc"] += pf.loc

    results = [
        DirectoryInfo(path=path, file_count=stats["files"], total_loc=stats["loc"])
        for path, stats in sorted(dir_stats.items())
    ]
    return results
