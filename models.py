"""Data models for metrics collection."""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Optional


# ---------------------------------------------------------------------------
# Module discovery
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Module:
    """Represents a Dart package inside the monorepo."""
    name: str
    path: str  # relative to repo root
    is_flutter: bool = False


# ---------------------------------------------------------------------------
# Function-level metrics
# ---------------------------------------------------------------------------

@dataclass
class FunctionMetrics:
    path: str  # relative file path
    module: str
    class_name: Optional[str]  # None for top-level functions
    function_name: str
    line_start: int
    line_end: int
    # metrics
    cyclo: int = 0
    halstead_volume: float = 0.0
    loc: int = 0
    sloc: int = 0
    mi: float = 0.0
    max_nesting_level: int = 0
    number_of_parameters: int = 0
    wmfp: float = 0.0
    fpy: float = 1.0
    technical_debt_minutes: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Class-level metrics
# ---------------------------------------------------------------------------

@dataclass
class ClassMetrics:
    path: str
    module: str
    class_name: str
    line_start: int
    line_end: int
    # metrics
    cbo: int = 0
    dit: int = 0
    noam: int = 0
    noii: int = 0
    nom: int = 0
    noom: int = 0
    rfc: int = 0
    tcc: float = 0.0
    woc: float = 0.0
    wmc: int = 0
    loc: int = 0
    fpy: float = 1.0
    technical_debt_minutes: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# File-level metrics
# ---------------------------------------------------------------------------

@dataclass
class FileMetrics:
    path: str
    module: str
    loc: int = 0
    sloc: int = 0
    noi: int = 0
    noei: int = 0
    classes_count: int = 0
    functions_count: int = 0
    cyclo_sum: int = 0
    cyclo_avg: float = 0.0
    cyclo_max: int = 0
    halstead_volume_avg: float = 0.0
    mi_avg: float = 0.0
    mi_min: float = 100.0
    static_members: int = 0
    hardcoded_strings: int = 0
    magic_numbers: int = 0
    dead_code_estimate: int = 0
    wmfp: float = 0.0
    wmfp_density: float = 0.0
    fpy: float = 1.0
    technical_debt_minutes: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        # round floats
        for k, v in d.items():
            if isinstance(v, float):
                d[k] = round(v, 2)
        return d


# ---------------------------------------------------------------------------
# Aggregated module summary
# ---------------------------------------------------------------------------

@dataclass
class StatsSummary:
    mean: float = 0.0
    median: float = 0.0
    p90: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0
    std_dev: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: round(v, 2) for k, v in d.items()}


@dataclass
class ViolationCounts:
    cyclo_high: int = 0
    cyclo_very_high: int = 0
    mi_poor: int = 0
    mnl_critical: int = 0
    god_classes: int = 0
    low_cohesion: int = 0
    high_coupling: int = 0
    excessive_params: int = 0
    excessive_imports: int = 0
    magic_numbers_high: int = 0
    hardcoded_strings_high: int = 0
    potential_dead_code: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TechnicalDebtSummary:
    total_minutes: float = 0.0
    total_hours: float = 0.0
    total_days: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: round(v, 2) for k, v in d.items()}


@dataclass
class ModuleSummary:
    module: str
    path: str
    files_count: int = 0
    classes_count: int = 0
    functions_count: int = 0
    loc_total: int = 0
    sloc_total: int = 0
    metrics_summary: dict = field(default_factory=dict)  # metric_name -> StatsSummary
    violations: ViolationCounts = field(default_factory=ViolationCounts)
    technical_debt: TechnicalDebtSummary = field(default_factory=TechnicalDebtSummary)

    def to_dict(self) -> dict:
        d = {
            "module": self.module,
            "path": self.path,
            "files_count": self.files_count,
            "classes_count": self.classes_count,
            "functions_count": self.functions_count,
            "loc_total": self.loc_total,
            "sloc_total": self.sloc_total,
            "metrics_summary": {
                k: v.to_dict() if isinstance(v, StatsSummary) else v
                for k, v in self.metrics_summary.items()
            },
            "violations": self.violations.to_dict(),
            "technical_debt": self.technical_debt.to_dict(),
        }
        return d


@dataclass
class ProjectSummary:
    modules_count: int = 0
    files_count: int = 0
    classes_count: int = 0
    functions_count: int = 0
    loc_total: int = 0
    sloc_total: int = 0
    metrics_summary: dict = field(default_factory=dict)
    violations: ViolationCounts = field(default_factory=ViolationCounts)
    technical_debt: TechnicalDebtSummary = field(default_factory=TechnicalDebtSummary)
    modules: list = field(default_factory=list)  # list of ModuleSummary dicts

    def to_dict(self) -> dict:
        return {
            "modules_count": self.modules_count,
            "files_count": self.files_count,
            "classes_count": self.classes_count,
            "functions_count": self.functions_count,
            "loc_total": self.loc_total,
            "sloc_total": self.sloc_total,
            "metrics_summary": {
                k: v.to_dict() if isinstance(v, StatsSummary) else v
                for k, v in self.metrics_summary.items()
            },
            "violations": self.violations.to_dict(),
            "technical_debt": self.technical_debt.to_dict(),
            "modules": self.modules,
        }


# ---------------------------------------------------------------------------
# Halstead intermediate data
# ---------------------------------------------------------------------------

@dataclass
class HalsteadData:
    """Intermediate Halstead complexity data."""
    n1: int = 0  # total operators
    n2: int = 0  # total operands
    eta1: int = 0  # unique operators
    eta2: int = 0  # unique operands

    @property
    def program_length(self) -> int:
        return self.n1 + self.n2

    @property
    def vocabulary(self) -> int:
        return self.eta1 + self.eta2

    @property
    def volume(self) -> float:
        if self.vocabulary <= 0:
            return 0.0
        return self.program_length * math.log2(self.vocabulary)

    @property
    def difficulty(self) -> float:
        if self.eta2 == 0:
            return 0.0
        return (self.eta1 / 2.0) * (self.n2 / self.eta2)

    @property
    def effort(self) -> float:
        return self.difficulty * self.volume


# ---------------------------------------------------------------------------
# Parsed AST structures
# ---------------------------------------------------------------------------

@dataclass
class ParsedFunction:
    """A function/method extracted from AST."""
    name: str
    class_name: Optional[str]
    line_start: int
    line_end: int
    body_text: str  # source code of the body
    full_text: str  # full source including signature
    parameters: list = field(default_factory=list)
    is_override: bool = False
    is_static: bool = False
    is_getter: bool = False
    is_setter: bool = False


@dataclass
class ParsedClass:
    """A class extracted from AST."""
    name: str
    line_start: int
    line_end: int
    full_text: str
    superclass: Optional[str] = None
    interfaces: list = field(default_factory=list)  # implements
    mixins: list = field(default_factory=list)  # with
    methods: list = field(default_factory=list)  # list of ParsedFunction
    fields: list = field(default_factory=list)  # list of field names
    public_methods: list = field(default_factory=list)
    public_fields: list = field(default_factory=list)
    is_abstract: bool = False


@dataclass
class ParsedImport:
    """An import directive parsed from a Dart file."""
    uri: str
    is_dart_core: bool = False
    is_package: bool = False
    package_name: Optional[str] = None
    is_relative: bool = False


@dataclass
class ParsedFile:
    """Complete parsed representation of a Dart file."""
    path: str
    source: str
    classes: list = field(default_factory=list)  # list of ParsedClass
    top_level_functions: list = field(default_factory=list)  # list of ParsedFunction
    imports: list = field(default_factory=list)  # list of ParsedImport
    loc: int = 0
    sloc: int = 0
