"""Configuration loading and validation for metrics collection."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

import yaml


# ---------------------------------------------------------------------------
# Threshold config dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CycloThresholds:
    low: int = 5
    moderate: int = 10
    high: int = 20
    very_high: int = 50


@dataclass
class HalsteadVolumeThresholds:
    low: float = 100
    moderate: float = 500
    high: float = 1000
    very_high: float = 2000


@dataclass
class LOCThresholds:
    function_max: int = 80
    file_max: int = 500
    class_max: int = 300


@dataclass
class MIThresholds:
    good: float = 60
    moderate: float = 40
    poor: float = 20


@dataclass
class MNLThresholds:
    warning: int = 4
    critical: int = 6


@dataclass
class NOPThresholds:
    warning: int = 4
    critical: int = 7


@dataclass
class SLOCThresholds:
    function_warning: int = 50
    file_warning: int = 400


@dataclass
class CBOThresholds:
    warning: int = 10
    critical: int = 20


@dataclass
class DITThresholds:
    warning: int = 4
    critical: int = 6


@dataclass
class NOMThresholds:
    warning: int = 15
    critical: int = 30


@dataclass
class RFCThresholds:
    warning: int = 50
    critical: int = 100


@dataclass
class TCCThresholds:
    warning: float = 0.33
    good: float = 0.66


@dataclass
class WOCThresholds:
    warning: float = 0.33


@dataclass
class WMCThresholds:
    warning: int = 20
    critical: int = 50


@dataclass
class NOIThresholds:
    warning: int = 15
    critical: int = 30


@dataclass
class NOEIThresholds:
    warning: int = 10
    critical: int = 20


@dataclass
class TechnicalDebtWeights:
    cyclo_excess_per_point: float = 10
    loc_excess_per_line: float = 2
    nesting_excess_per_level: float = 15
    params_excess_per_param: float = 5
    cbo_excess_per_point: float = 20
    dit_excess_per_level: float = 30
    low_cohesion_penalty: float = 60
    god_class_penalty: float = 120


@dataclass
class CodeSmellsThresholds:
    magic_numbers_warning: int = 5
    hardcoded_strings_warning: int = 10
    static_members_warning: int = 10
    dead_code_warning: int = 5


@dataclass
class WMFPWeights:
    """Weights for Weighted Micro Function Points computation."""
    flow_complexity: float = 0.30
    object_vocabulary: float = 0.20
    object_conjuration: float = 0.10
    arithmetic_intricacy: float = 0.05
    data_transfer: float = 0.10
    code_structure: float = 0.15
    inline_data: float = 0.05
    comments: float = 0.05


@dataclass
class WMFPThresholds:
    warning: float = 15.0
    critical: float = 30.0
    density_warning: float = 0.5
    density_critical: float = 1.0


@dataclass
class FPYFunctionGates:
    """Quality gates for function-level FPY."""
    max_cyclo: int = 10
    max_nesting: int = 4
    min_mi: float = 50.0
    max_params: int = 4
    max_loc: int = 50


@dataclass
class FPYClassGates:
    """Quality gates for class-level FPY."""
    max_wmc: int = 20
    max_cbo: int = 8
    min_tcc: float = 0.33
    max_nom: int = 20
    min_woc: float = 0.33


@dataclass
class FPYFileGates:
    """Quality gates for file-level FPY."""
    max_imports: int = 15
    max_magic_numbers: int = 3
    max_hardcoded_strings: int = 5
    max_dead_code: int = 0


@dataclass
class FPYConfig:
    """FPY (First-Pass Yield) configuration."""
    function_gates: FPYFunctionGates = field(default_factory=FPYFunctionGates)
    class_gates: FPYClassGates = field(default_factory=FPYClassGates)
    file_gates: FPYFileGates = field(default_factory=FPYFileGates)
    # Weights for file-level FPY aggregation
    weight_functions: float = 0.5
    weight_classes: float = 0.3
    weight_smells: float = 0.2


@dataclass
class Thresholds:
    cyclomatic_complexity: CycloThresholds = field(default_factory=CycloThresholds)
    halstead_volume: HalsteadVolumeThresholds = field(default_factory=HalsteadVolumeThresholds)
    lines_of_code: LOCThresholds = field(default_factory=LOCThresholds)
    maintainability_index: MIThresholds = field(default_factory=MIThresholds)
    max_nesting_level: MNLThresholds = field(default_factory=MNLThresholds)
    number_of_parameters: NOPThresholds = field(default_factory=NOPThresholds)
    source_lines_of_code: SLOCThresholds = field(default_factory=SLOCThresholds)
    coupling_between_objects: CBOThresholds = field(default_factory=CBOThresholds)
    depth_of_inheritance: DITThresholds = field(default_factory=DITThresholds)
    number_of_methods: NOMThresholds = field(default_factory=NOMThresholds)
    response_for_class: RFCThresholds = field(default_factory=RFCThresholds)
    tight_class_cohesion: TCCThresholds = field(default_factory=TCCThresholds)
    weight_of_class: WOCThresholds = field(default_factory=WOCThresholds)
    weighted_methods_per_class: WMCThresholds = field(default_factory=WMCThresholds)
    number_of_imports: NOIThresholds = field(default_factory=NOIThresholds)
    number_of_external_imports: NOEIThresholds = field(default_factory=NOEIThresholds)
    technical_debt: TechnicalDebtWeights = field(default_factory=TechnicalDebtWeights)
    code_smells: CodeSmellsThresholds = field(default_factory=CodeSmellsThresholds)
    wmfp_weights: WMFPWeights = field(default_factory=WMFPWeights)
    wmfp: WMFPThresholds = field(default_factory=WMFPThresholds)
    fpy: FPYConfig = field(default_factory=FPYConfig)


# ---------------------------------------------------------------------------
# Discovery config
# ---------------------------------------------------------------------------

@dataclass
class DiscoveryConfig:
    strategy: str = "workspace"  # workspace | auto | manual
    modules: list = field(default_factory=list)
    exclude_patterns: list = field(default_factory=lambda: [
        "**/.dart_tool/**",
        "**/build/**",
    ])
    exclude_files: list = field(default_factory=lambda: [
        "**/*.g.dart",
        "**/*.freezed.dart",
        "**/*.mocks.dart",
        "**/generated_plugin_registrant.dart",
    ])
    include_tests: bool = False


# ---------------------------------------------------------------------------
# DCM adapter config
# ---------------------------------------------------------------------------

@dataclass
class DCMConfig:
    enabled: bool = False
    executable: str = "dcm"
    extra_args: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Output config
# ---------------------------------------------------------------------------

@dataclass
class OutputConfig:
    directory: str = "analysis/metrics_output"
    formats: list = field(default_factory=lambda: ["json", "csv", "markdown"])


# ---------------------------------------------------------------------------
# Graph config
# ---------------------------------------------------------------------------

@dataclass
class GraphConfig:
    enabled: bool = True
    include_dev: bool = False
    include_overrides: bool = False
    include_tests: bool = False
    key_packages: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Package analysis config
# ---------------------------------------------------------------------------

@dataclass
class PackageAnalysisConfig:
    enabled: bool = True
    git_since: str = "2025-01-01"
    git_hotspots_top_n: int = 15
    shotgun_surgery_top_n: int = 30


# ---------------------------------------------------------------------------
# Top-level Config
# ---------------------------------------------------------------------------

@dataclass
class MetricsConfig:
    version: str = "1.0"
    root: str = "."
    discovery: DiscoveryConfig = field(default_factory=DiscoveryConfig)
    dcm: DCMConfig = field(default_factory=DCMConfig)
    thresholds: Thresholds = field(default_factory=Thresholds)
    output: OutputConfig = field(default_factory=OutputConfig)
    graphs: GraphConfig = field(default_factory=GraphConfig)
    package_analysis: PackageAnalysisConfig = field(default_factory=PackageAnalysisConfig)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def _apply_dict(obj, data: dict):
    """Apply dictionary values to a dataclass instance, recursively."""
    if not isinstance(data, dict):
        return
    for key, value in data.items():
        if hasattr(obj, key):
            current = getattr(obj, key)
            if hasattr(current, '__dataclass_fields__') and isinstance(value, dict):
                _apply_dict(current, value)
            else:
                setattr(obj, key, value)


def load_config(config_path: Optional[str] = None, repo_root: Optional[str] = None) -> MetricsConfig:
    """Load metrics configuration from YAML file.

    Search order when *config_path* is None:
      1. ``metrics.yaml`` in *repo_root*
      2. ``analysis/metrics.yaml`` in *repo_root*

    *repo_root* defaults to cwd.
    """
    if repo_root is None:
        repo_root = os.getcwd()

    config = MetricsConfig()

    if config_path is None:
        # Try root-level first, then analysis/ subdirectory
        candidates = [
            os.path.join(repo_root, "metrics.yaml"),
            os.path.join(repo_root, "analysis", "metrics.yaml"),
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                config_path = candidate
                break

    if config_path and os.path.isfile(config_path):
        with open(config_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        # Apply top-level scalars
        if "version" in data:
            config.version = str(data["version"])
        if "root" in data:
            config.root = data["root"]
        if "discovery" in data:
            _apply_dict(config.discovery, data["discovery"])
        if "dcm" in data:
            _apply_dict(config.dcm, data["dcm"])
        if "thresholds" in data:
            _apply_dict(config.thresholds, data["thresholds"])
        if "output" in data:
            _apply_dict(config.output, data["output"])
        if "graphs" in data:
            _apply_dict(config.graphs, data["graphs"])
        if "package_analysis" in data:
            _apply_dict(config.package_analysis, data["package_analysis"])

    # Resolve root to absolute
    if not os.path.isabs(config.root):
        if config_path:
            config_dir = os.path.dirname(os.path.abspath(config_path))
            config.root = os.path.normpath(os.path.join(config_dir, config.root))
        else:
            config.root = os.path.abspath(os.path.join(repo_root, config.root))

    return config
