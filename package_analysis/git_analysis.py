"""Git history analysis for packages.

Detects files with the most git changes (hotspots by change frequency).
"""

from __future__ import annotations

import os
import subprocess
from typing import List, Optional

from .models import GitHotspot


def get_git_hotspots(
    module_path: str,
    repo_root: str,
    since: str = "2025-01-01",
    top_n: int = 15,
    file_pattern: str = "*.dart",
) -> List[GitHotspot]:
    """Find files with the most git commits since a given date.

    Args:
        module_path: Absolute path to the module directory.
        repo_root: Root of the git repository.
        since: Date string for --since flag (e.g. "2025-01-01").
        top_n: Maximum number of hotspots to return.
        file_pattern: File pattern to filter (default: *.dart).

    Returns:
        List of GitHotspot sorted by commit_count descending.
    """
    lib_dir = os.path.join(module_path, "lib")
    if not os.path.isdir(lib_dir):
        return []

    try:
        # Get list of changed files using git log
        result = subprocess.run(
            [
                "git", "-C", repo_root,
                "log",
                "--format=format:",
                "--name-only",
                f"--since={since}",
                "--",
                os.path.relpath(lib_dir, repo_root),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return []

        # Count occurrences of each file
        file_counts: dict = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            if not line.endswith('.dart'):
                continue
            file_counts[line] = file_counts.get(line, 0) + 1

        # Sort and limit
        hotspots = [
            GitHotspot(file_path=path, commit_count=count)
            for path, count in file_counts.items()
        ]
        hotspots.sort(key=lambda h: h.commit_count, reverse=True)
        return hotspots[:top_n]

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []


def get_git_file_age(
    file_path: str,
    repo_root: str,
) -> Optional[str]:
    """Get the date of the first commit for a file.

    Returns ISO date string or None.
    """
    try:
        result = subprocess.run(
            [
                "git", "-C", repo_root,
                "log", "--format=%aI", "--diff-filter=A",
                "--follow", "--", file_path,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().splitlines()
            return lines[-1].strip()  # oldest commit date
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None
