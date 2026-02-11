"""Collector: orchestrates parsing, metric computation, and output generation."""

from __future__ import annotations

import os
import sys
import time
from typing import Dict, List, Optional, Set

from .config import MetricsConfig
from .discovery import discover_modules, get_internal_packages, list_dart_files
from .models import (
    ClassMetrics,
    FileMetrics,
    FunctionMetrics,
    Module,
    ModuleSummary,
    ParsedFile,
    ProjectSummary,
)
from .parsers.dart_parser import is_tree_sitter_available, parse_file

# DCM adapter is optional — import gracefully
try:
    from .parsers.dcm_adapter import is_dcm_available, merge_dcm_metrics, run_dcm_analyze
    _HAS_DCM_MODULE = True
except ImportError:
    _HAS_DCM_MODULE = False
    def is_dcm_available(cfg=None): return False
    def merge_dcm_metrics(*a, **kw): return None
    def run_dcm_analyze(*a, **kw): return None

from .metrics.function_metrics import compute_function_metrics
from .metrics.class_metrics import (
    ClassIndex,
    build_class_index,
    compute_class_metrics,
)
from .metrics.file_metrics import compute_file_metrics
from .metrics.technical_debt import apply_technical_debt
from .metrics.code_smells import compute_dead_code_for_module
from .metrics.fpy import compute_function_fpy, compute_class_fpy, compute_file_fpy
from .metrics.rating import rate_module, rate_file
from .metrics.risk_hotspots import compute_risk_hotspots
from .metrics.distributions import compute_distributions
from .metrics.duplication import detect_duplicates
from .metrics.history import (
    Snapshot, SnapshotDelta, build_snapshot, save_snapshot,
    get_latest_snapshot, load_snapshot, list_snapshots, compare_snapshots,
)
from .aggregation.module_aggregator import aggregate_module
from .aggregation.project_aggregator import aggregate_project
from .output import json_writer, csv_writer, markdown_writer, dot_writer
from .output.html_writer import write_html_dashboard
from .graphs.import_graph import build_import_graph, build_per_module_import_details
from .graphs.pubspec_graph import build_pubspec_graph
from .graphs.dsm import build_dsm, DSMResult
from .graphs.models import DependencyGraph
from .package_analysis.package_collector import collect_package_analysis
from .package_analysis.models import PackageAnalysisResult


class CollectorResult:
    """Container for all collected metrics."""

    def __init__(self):
        self.all_function_metrics: List[FunctionMetrics] = []
        self.all_class_metrics: List[ClassMetrics] = []
        self.all_file_metrics: List[FileMetrics] = []
        self.module_summaries: List[ModuleSummary] = []
        self.project_summary: Optional[ProjectSummary] = None
        self.modules_analyzed: List[str] = []
        self.duration_seconds: float = 0.0
        # New: graphs & package analysis
        self.import_graph: Optional[DependencyGraph] = None
        self.pubspec_graph: Optional[DependencyGraph] = None
        self.package_analyses: List[PackageAnalysisResult] = []
        self.modules: List[Module] = []
        self.module_parsed_files: Dict[str, List[ParsedFile]] = {}
        # New analysis results
        self.module_ratings: Dict[str, tuple] = {}   # module -> (score, grade)
        self.risk_hotspots: list = []
        self.distributions: dict = {}
        self.dsm_result: Optional[DSMResult] = None
        self.duplication_result = None
        self.snapshot: Optional[Snapshot] = None
        self.snapshot_delta: Optional[SnapshotDelta] = None
        self.history_snapshots: list = []


def collect_metrics(
    config: MetricsConfig,
    module_filter: Optional[str] = None,
    metric_filter: Optional[List[str]] = None,
    verbose: bool = True,
) -> CollectorResult:
    """Main entry point: discover modules, parse files, compute metrics, produce output."""

    start_time = time.time()
    result = CollectorResult()
    error_count = 0

    root = config.root
    parser_type = "tree-sitter" if is_tree_sitter_available() else "regex-fallback"

    if verbose:
        print(f"[metrics] Project root: {root}")
        print(f"[metrics] Parser: {parser_type}")

    # 1. Discover modules
    modules = discover_modules(config)
    if module_filter:
        modules = [m for m in modules if m.name == module_filter or m.path == module_filter]

    if not modules:
        print("[metrics] No modules found!")
        return result

    if verbose:
        print(f"[metrics] Modules found: {len(modules)}")
        for m in modules:
            print(f"  - {m.name} ({m.path})")

    internal_packages = get_internal_packages(modules)

    # 2. Phase 1: Parse all files and build cross-file class index
    if verbose:
        print("\n[metrics] Phase 1: Parsing files...")

    module_parsed_files: Dict[str, List[ParsedFile]] = {}
    class_index = ClassIndex()
    total_files = 0

    for module in modules:
        dart_files = list_dart_files(root, module.path, config)
        parsed_files: List[ParsedFile] = []

        for fpath in dart_files:
            try:
                rel_path = os.path.relpath(fpath, root)
                pf = parse_file(fpath)
                pf.path = rel_path  # Use relative path
                parsed_files.append(pf)
                class_index.add_file(pf)
            except Exception as e:
                error_count += 1
                if verbose:
                    print(f"  [!] Parse error {fpath}: {e}", file=sys.stderr)

        module_parsed_files[module.name] = parsed_files
        total_files += len(parsed_files)

        if verbose:
            print(f"  {module.name}: {len(parsed_files)} files")

    if verbose:
        print(f"  Total files: {total_files}")
        print(f"  Total classes in index: {len(class_index.classes)}")

    # 3. Phase 2: Compute metrics per module
    if verbose:
        print("\n[metrics] Phase 2: Computing metrics...")

    # Optional DCM data
    dcm_data: Dict[str, Dict] = {}
    use_dcm = _HAS_DCM_MODULE and config.dcm.enabled and is_dcm_available(config.dcm)
    if use_dcm and verbose:
        print("  DCM enabled, fetching data...")

    for module in modules:
        if verbose:
            print(f"  Processing: {module.name}...")

        parsed_files = module_parsed_files.get(module.name, [])
        if not parsed_files:
            continue

        # Optional: Get DCM data for this module
        module_dcm_data = None
        if use_dcm:
            abs_module_path = os.path.join(root, module.path)
            module_dcm_data = run_dcm_analyze(abs_module_path, config.dcm)

        module_function_metrics: List[FunctionMetrics] = []
        module_class_metrics: List[ClassMetrics] = []
        module_file_metrics: List[FileMetrics] = []

        for pf in parsed_files:
            # Function metrics
            fn_metrics = compute_function_metrics(pf, module.name, config.thresholds)

            # If DCM is available, merge its data
            if module_dcm_data and pf.path in module_dcm_data:
                dcm_records = module_dcm_data[pf.path]
                for fm in fn_metrics:
                    dcm_vals = merge_dcm_metrics(fm.function_name, fm.line_start, dcm_records)
                    if dcm_vals:
                        if "cyclo" in dcm_vals:
                            fm.cyclo = dcm_vals["cyclo"]
                        if "halvol" in dcm_vals:
                            fm.halstead_volume = dcm_vals["halvol"]
                        if "mi" in dcm_vals:
                            fm.mi = dcm_vals["mi"]
                        if "mnl" in dcm_vals:
                            fm.max_nesting_level = dcm_vals["mnl"]
                        if "nop" in dcm_vals:
                            fm.number_of_parameters = dcm_vals["nop"]
                        if "sloc" in dcm_vals:
                            fm.sloc = dcm_vals["sloc"]

            module_function_metrics.extend(fn_metrics)

            # Class metrics
            cls_metrics = compute_class_metrics(
                pf, module.name, config.thresholds, class_index, internal_packages
            )
            module_class_metrics.extend(cls_metrics)

            # File metrics
            file_met = compute_file_metrics(
                pf, module.name, fn_metrics, config.thresholds, internal_packages
            )
            module_file_metrics.append(file_met)

        # Apply technical debt
        apply_technical_debt(
            module_function_metrics,
            module_class_metrics,
            module_file_metrics,
            config.thresholds,
        )

        # Compute FPY (First-Pass Yield)
        for fm in module_function_metrics:
            fm.fpy = compute_function_fpy(fm, config.thresholds.fpy)
        for cm in module_class_metrics:
            cm.fpy = compute_class_fpy(cm, config.thresholds.fpy)
        for file_met in module_file_metrics:
            file_met.fpy = compute_file_fpy(
                file_met, module_function_metrics, module_class_metrics,
                config.thresholds.fpy,
            )
            # Also compute file-level WMFP aggregation
            file_fns = [fm for fm in module_function_metrics if fm.path == file_met.path]
            file_met.wmfp = round(sum(fm.wmfp for fm in file_fns), 2)
            file_met.wmfp_density = round(
                file_met.wmfp / file_met.sloc if file_met.sloc > 0 else 0.0, 3
            )

        # Aggregate module
        module_summary = aggregate_module(
            module.name,
            module.path,
            module_function_metrics,
            module_class_metrics,
            module_file_metrics,
            config.thresholds,
        )

        # Accumulate
        result.all_function_metrics.extend(module_function_metrics)
        result.all_class_metrics.extend(module_class_metrics)
        result.all_file_metrics.extend(module_file_metrics)
        result.module_summaries.append(module_summary)
        result.modules_analyzed.append(module.name)

        if verbose:
            td = module_summary.technical_debt
            print(
                f"    -> {module_summary.files_count} files, "
                f"{module_summary.classes_count} classes, "
                f"{module_summary.functions_count} functions, "
                f"TD: {td.total_hours:.1f}h"
            )

    # 3.5. Phase 2.5: Dead code estimate (cross-file)
    if verbose:
        print("\n[metrics] Phase 2.5: Dead code estimation...")

    for module in modules:
        parsed_files = module_parsed_files.get(module.name, [])
        if not parsed_files:
            continue
        dead_code_map = compute_dead_code_for_module(parsed_files)
        for fm in result.all_file_metrics:
            if fm.module == module.name and fm.path in dead_code_map:
                fm.dead_code_estimate = dead_code_map[fm.path][0]

    # 4. Phase 3: Project-level aggregation
    if verbose:
        print("\n[metrics] Phase 3: Project aggregation...")

    result.project_summary = aggregate_project(
        result.module_summaries,
        result.all_function_metrics,
        result.all_class_metrics,
        result.all_file_metrics,
        config.thresholds,
    )

    # 5. Phase 4: Dependency graphs
    if config.graphs.enabled:
        if verbose:
            print("\n[metrics] Phase 4: Dependency graphs...")

        # Import graph
        result.import_graph = build_import_graph(
            modules, module_parsed_files, config,
            include_tests=config.graphs.include_tests,
        )
        if verbose:
            print(f"  Import graph: {result.import_graph.node_count} nodes, "
                  f"{result.import_graph.edge_count} edges, "
                  f"{len(result.import_graph.external_packages)} external packages")

        # Pubspec graph
        result.pubspec_graph = build_pubspec_graph(
            modules, config,
            include_dev=config.graphs.include_dev,
            include_overrides=config.graphs.include_overrides,
        )
        if verbose:
            print(f"  Pubspec graph: {result.pubspec_graph.node_count} nodes, "
                  f"{result.pubspec_graph.edge_count} edges")

    # 6. Phase 5: Package analysis
    if config.package_analysis.enabled:
        if verbose:
            print("\n[metrics] Phase 5: Package analysis...")

        for module in modules:
            parsed_files = module_parsed_files.get(module.name, [])
            if not parsed_files:
                continue
            try:
                pa_result = collect_package_analysis(
                    module=module,
                    parsed_files=parsed_files,
                    config=config,
                    internal_packages=internal_packages,
                    git_since=config.package_analysis.git_since,
                    shotgun_top_n=config.package_analysis.shotgun_surgery_top_n,
                    git_top_n=config.package_analysis.git_hotspots_top_n,
                )
                result.package_analyses.append(pa_result)
                if verbose:
                    print(f"  {module.name}: "
                          f"{len(pa_result.cross_package_imports)} cross-imports, "
                          f"{len(pa_result.git_hotspots)} git hotspots")
            except Exception as e:
                error_count += 1
                if verbose:
                    print(f"  [!] Analysis error {module.name}: {e}", file=sys.stderr)

    # Store modules and parsed files for output phase
    result.modules = modules
    result.module_parsed_files = module_parsed_files

    # 7. Phase 6: Module ratings (A/B/C/D/E)
    if verbose:
        print("\n[metrics] Phase 6: Computing ratings...")

    for ms in result.module_summaries:
        score, grade = rate_module(ms)
        result.module_ratings[ms.module] = (score, grade)
        if verbose:
            print(f"  {ms.module}: {grade} ({score:.1f})")

    # 8. Phase 7: Distributions
    if verbose:
        print("\n[metrics] Phase 7: Distribution histograms...")

    result.distributions = compute_distributions(
        result.all_function_metrics,
        result.all_class_metrics,
        result.all_file_metrics,
    )
    if verbose:
        print(f"  Computed {len(result.distributions)} distributions")

    # 9. Phase 8: Risk hotspots (churn × complexity)
    if config.package_analysis.enabled:
        if verbose:
            print("\n[metrics] Phase 8: Risk hotspots (churn × complexity)...")

        result.risk_hotspots = compute_risk_hotspots(
            result.all_file_metrics,
            config.root,
            since=config.package_analysis.git_since,
            top_n=30,
        )
        if verbose:
            print(f"  Found {len(result.risk_hotspots)} risk hotspots")

    # 10. Phase 9: DSM (Design Structure Matrix)
    if result.import_graph:
        if verbose:
            print("\n[metrics] Phase 9: Design Structure Matrix...")

        result.dsm_result = build_dsm(result.import_graph)
        if verbose:
            print(f"  {len(result.dsm_result.modules)}x{len(result.dsm_result.modules)} matrix, "
                  f"{len(result.dsm_result.cycles)} cyclic pairs")

    # 11. Phase 10: Duplication detection
    if verbose:
        print("\n[metrics] Phase 10: Duplication detection...")

    all_parsed: List[ParsedFile] = []
    for pf_list in module_parsed_files.values():
        all_parsed.extend(pf_list)

    result.duplication_result = detect_duplicates(all_parsed)
    if verbose:
        dr = result.duplication_result
        print(f"  Total tokens: {dr.total_tokens:,}")
        print(f"  Duplicated: {dr.duplicated_tokens:,} ({dr.duplication_pct:.1f}%)")
        print(f"  Duplicate pairs: {len(dr.duplicate_pairs)}")

    # 12. Phase 11: History snapshot & delta
    if verbose:
        print("\n[metrics] Phase 11: History & trends...")

    abs_output_dir = config.output.directory
    if not os.path.isabs(abs_output_dir):
        abs_output_dir = os.path.join(config.root, abs_output_dir)

    # Load previous snapshot for delta
    prev_snapshot = get_latest_snapshot(abs_output_dir)

    # Build current snapshot
    dup_pct = result.duplication_result.duplication_pct if result.duplication_result else 0.0
    result.snapshot = build_snapshot(
        result.project_summary,
        result.module_summaries,
        result.module_ratings,
        duplication_pct=dup_pct,
        repo_root=config.root,
    )

    # Compare with previous
    if prev_snapshot:
        result.snapshot_delta = compare_snapshots(prev_snapshot, result.snapshot)
        if verbose:
            changed = sum(1 for r in result.snapshot_delta.rows if abs(r.delta) > 0.01)
            print(f"  Delta vs {prev_snapshot.timestamp[:10]}: {changed} metrics changed")
    else:
        if verbose:
            print("  No previous snapshot for comparison")

    # Load all history for trends
    snap_files = list_snapshots(abs_output_dir)
    for sf in snap_files[-20:]:  # last 20 snapshots max
        try:
            result.history_snapshots.append(load_snapshot(sf))
        except Exception:
            pass
    # Add current snapshot to history for display
    result.history_snapshots.append(result.snapshot)
    if verbose:
        print(f"  History snapshots: {len(result.history_snapshots)}")

    result.duration_seconds = time.time() - start_time

    if verbose:
        ps = result.project_summary
        print(f"\n[metrics] Summary:")
        print(f"  Modules: {ps.modules_count}")
        print(f"  Files: {ps.files_count}")
        print(f"  Classes: {ps.classes_count}")
        print(f"  Functions: {ps.functions_count}")
        print(f"  LOC: {ps.loc_total:,}")
        print(f"  TD: {ps.technical_debt.total_hours:.1f}h ({ps.technical_debt.total_days:.1f} days)")
        if result.duplication_result:
            print(f"  Duplication: {result.duplication_result.duplication_pct:.1f}%")
        if error_count:
            print(f"  Parse errors: {error_count}")
        print(f"  Time: {result.duration_seconds:.1f}s")

    return result


def write_output(
    result: CollectorResult,
    config: MetricsConfig,
    verbose: bool = True,
) -> List[str]:
    """Write all output files based on config."""

    output_dir = config.output.directory
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(config.root, output_dir)

    formats = config.output.formats
    parser_type = "tree-sitter" if is_tree_sitter_available() else "regex-fallback"

    written_files: List[str] = []

    if verbose:
        print(f"\n[metrics] Writing results to {output_dir}...")

    # JSON output
    if "json" in formats:
        written_files.append(
            json_writer.write_raw_file_metrics(result.all_file_metrics, output_dir)
        )
        written_files.append(
            json_writer.write_raw_function_metrics(result.all_function_metrics, output_dir)
        )
        written_files.append(
            json_writer.write_raw_class_metrics(result.all_class_metrics, output_dir)
        )

        for ms in result.module_summaries:
            written_files.append(
                json_writer.write_module_summary(ms, output_dir)
            )

        if result.project_summary:
            written_files.append(
                json_writer.write_project_summary(result.project_summary, output_dir)
            )

        written_files.append(
            json_writer.write_hotspots(
                result.all_function_metrics,
                result.all_class_metrics,
                result.all_file_metrics,
                output_dir,
            )
        )

        written_files.append(
            json_writer.write_technical_debt_report(
                result.all_function_metrics,
                result.all_class_metrics,
                result.all_file_metrics,
                result.module_summaries,
                output_dir,
            )
        )

        written_files.append(
            json_writer.write_metadata(
                output_dir,
                config.version,
                result.modules_analyzed,
                parser_type,
                result.duration_seconds,
            )
        )

    # CSV output
    if "csv" in formats:
        written_files.append(
            csv_writer.write_raw_file_metrics_csv(result.all_file_metrics, output_dir)
        )
        written_files.append(
            csv_writer.write_raw_function_metrics_csv(result.all_function_metrics, output_dir)
        )
        written_files.append(
            csv_writer.write_raw_class_metrics_csv(result.all_class_metrics, output_dir)
        )

    # Markdown output
    if "markdown" in formats:
        for ms in result.module_summaries:
            written_files.append(
                markdown_writer.write_module_summary_md(
                    ms,
                    result.all_function_metrics,
                    result.all_class_metrics,
                    output_dir,
                )
            )

        if result.project_summary:
            written_files.append(
                markdown_writer.write_project_summary_md(
                    result.project_summary,
                    result.module_summaries,
                    output_dir,
                )
            )

        written_files.append(
            markdown_writer.write_hotspots_md(
                result.all_function_metrics,
                result.all_class_metrics,
                result.all_file_metrics,
                output_dir,
            )
        )

        written_files.append(
            markdown_writer.write_technical_debt_md(
                result.module_summaries,
                result.all_file_metrics,
                output_dir,
            )
        )

    # Dependency graph output (DOT, JSON, CSV)
    if result.import_graph:
        written_files.append(
            dot_writer.write_import_graph_dot(result.import_graph, output_dir)
        )
        written_files.append(
            json_writer.write_graph_json(result.import_graph, output_dir, "import")
        )
        written_files.append(
            csv_writer.write_graph_edges_csv(result.import_graph, output_dir, "import")
        )
        # Per-module import graphs for key packages
        key_pkgs = set(config.graphs.key_packages) if config.graphs.key_packages else set()
        if key_pkgs:
            internal_names = {m.name for m in result.modules}
            for module in result.modules:
                if module.name in key_pkgs:
                    parsed_files = result.module_parsed_files.get(module.name, [])
                    details = build_per_module_import_details(
                        module.name, parsed_files, internal_names
                    )
                    if details:
                        written_files.append(
                            dot_writer.write_module_import_graph_dot(
                                module.name, details, output_dir
                            )
                        )

    if result.pubspec_graph:
        written_files.append(
            dot_writer.write_pubspec_graph_dot(result.pubspec_graph, output_dir)
        )
        written_files.append(
            json_writer.write_graph_json(result.pubspec_graph, output_dir, "pubspec")
        )
        written_files.append(
            csv_writer.write_graph_edges_csv(result.pubspec_graph, output_dir, "pubspec")
        )
        if "markdown" in formats:
            written_files.append(
                markdown_writer.write_graph_summary_md(
                    result.import_graph, result.pubspec_graph, output_dir
                )
            )

    # Package analysis output
    if result.package_analyses:
        for pa in result.package_analyses:
            written_files.append(
                json_writer.write_package_analysis_json(pa, output_dir)
            )
        if "markdown" in formats:
            written_files.append(
                markdown_writer.write_package_analysis_md(
                    result.package_analyses, output_dir
                )
            )

    # New analysis outputs: ratings, distributions, risk, DSM, duplication, history

    # Ratings JSON
    if "json" in formats and result.module_ratings:
        written_files.append(
            json_writer.write_ratings_json(result.module_ratings, output_dir)
        )

    # Distributions JSON
    if "json" in formats and result.distributions:
        written_files.append(
            json_writer.write_distributions_json(result.distributions, output_dir)
        )

    # Risk hotspots
    if result.risk_hotspots:
        if "json" in formats:
            written_files.append(
                json_writer.write_risk_hotspots_json(result.risk_hotspots, output_dir)
            )
        if "markdown" in formats:
            written_files.append(
                markdown_writer.write_risk_hotspots_md(result.risk_hotspots, output_dir)
            )

    # DSM
    if result.dsm_result:
        if "json" in formats:
            written_files.append(
                json_writer.write_dsm_json(result.dsm_result, output_dir)
            )
        if "markdown" in formats:
            written_files.append(
                markdown_writer.write_dsm_md(result.dsm_result, output_dir)
            )

    # Duplication
    if result.duplication_result:
        if "json" in formats:
            written_files.append(
                json_writer.write_duplication_json(result.duplication_result, output_dir)
            )
        if "markdown" in formats:
            written_files.append(
                markdown_writer.write_duplication_md(result.duplication_result, output_dir)
            )

    # Distributions markdown
    if "markdown" in formats and result.distributions:
        written_files.append(
            markdown_writer.write_distributions_md(result.distributions, output_dir)
        )

    # Ratings in project markdown (update module table with grades)
    if "markdown" in formats and result.module_ratings:
        written_files.append(
            markdown_writer.write_ratings_md(
                result.module_summaries, result.module_ratings, output_dir
            )
        )

    # History snapshot
    if result.snapshot:
        snap_path = save_snapshot(result.snapshot, output_dir)
        written_files.append(snap_path)

    # Delta report
    if result.snapshot_delta:
        if "json" in formats:
            written_files.append(
                json_writer.write_delta_json(result.snapshot_delta, output_dir)
            )
        if "markdown" in formats:
            written_files.append(
                markdown_writer.write_delta_md(result.snapshot_delta, output_dir)
            )

    # HTML Dashboard (always generate if data is available)
    if "html" in formats or True:  # always generate dashboard
        written_files.append(
            write_html_dashboard(
                project_summary=result.project_summary,
                module_summaries=result.module_summaries,
                function_metrics=result.all_function_metrics,
                class_metrics=result.all_class_metrics,
                file_metrics=result.all_file_metrics,
                module_ratings=result.module_ratings,
                distributions=result.distributions,
                risk_hotspots=result.risk_hotspots,
                dsm_result=result.dsm_result,
                duplication_result=result.duplication_result,
                snapshot_delta=result.snapshot_delta,
                history_snapshots=result.history_snapshots,
                output_dir=output_dir,
            )
        )

    if verbose:
        print(f"  Files written: {len(written_files)}")
        for f in written_files:
            rel = os.path.relpath(f, config.root) if os.path.isabs(f) else f
            print(f"    - {rel}")

    return written_files
