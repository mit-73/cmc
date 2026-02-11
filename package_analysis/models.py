"""Data models for package-level analysis."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


@dataclass
class CrossPackageImport:
    """A cross-package import found in a file."""
    file_path: str
    line_number: int
    imported_package: str
    import_uri: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ImportStatistics:
    """Import statistics for a package."""
    package_name: str
    count: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ShotgunSurgeryCandidate:
    """A file/symbol that is widely imported, indicating potential shotgun surgery."""
    relative_path: str
    usage_count: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GitHotspot:
    """A file with high change frequency in git history."""
    file_path: str
    commit_count: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DirectoryInfo:
    """Directory structure information."""
    path: str
    file_count: int = 0
    total_loc: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PackageAnalysisResult:
    """Complete package analysis result."""
    module_name: str
    module_path: str
    directory_structure: List[DirectoryInfo] = field(default_factory=list)
    cross_package_imports: List[CrossPackageImport] = field(default_factory=list)
    import_statistics: List[ImportStatistics] = field(default_factory=list)
    shotgun_surgery_candidates: List[ShotgunSurgeryCandidate] = field(default_factory=list)
    git_hotspots: List[GitHotspot] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "module_name": self.module_name,
            "module_path": self.module_path,
            "directory_structure": [d.to_dict() for d in self.directory_structure],
            "cross_package_imports": [c.to_dict() for c in self.cross_package_imports],
            "import_statistics": [i.to_dict() for i in self.import_statistics],
            "shotgun_surgery_candidates": [s.to_dict() for s in self.shotgun_surgery_candidates],
            "git_hotspots": [g.to_dict() for g in self.git_hotspots],
        }
