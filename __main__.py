"""CLI entry point for Code Metrics Collector.

Usage:
    cmc [options] [PROJECT_ROOT]
    python -m metrics [options] [PROJECT_ROOT]

Options:
    PROJECT_ROOT        Path to the project root to analyze (default: cwd)
    --config PATH       Path to metrics.yaml config file
    --module NAME       Analyze only this module
    --metrics LIST      Comma-separated metric names to compute
    --format LIST       Comma-separated output formats: json,csv,markdown
    --dcm               Force-enable DCM adapter
    --no-dcm            Force-disable DCM adapter
    --output DIR        Override output directory
    --graphs            Enable dependency graph generation (default: on)
    --no-graphs         Disable dependency graph generation
    --pkg-analysis      Enable package analysis (default: on)
    --no-pkg            Disable package analysis
    --include-dev       Include dev dependencies in pubspec graph
    --key-packages LIST Comma-separated packages for per-module graphs
    --git-since DATE    Start date for git hotspots (default: 2025-01-01)
    --verbose / -v      Verbose output (default: on)
    --quiet / -q        Suppress output
    --help / -h         Show this help
"""

from __future__ import annotations

import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="cmc",
        description="Collect metrics for a Dart monorepo",
    )
    parser.add_argument(
        "project_root",
        nargs="?",
        default=None,
        help="Path to the project root to analyze (default: current directory)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to metrics.yaml configuration file",
    )
    parser.add_argument(
        "--module",
        type=str,
        default=None,
        help="Analyze only the specified module (name or path)",
    )
    parser.add_argument(
        "--metrics",
        type=str,
        default=None,
        help="Comma-separated metric names (cyclo,cbo,wmc,...). Default: all",
    )
    parser.add_argument(
        "--format",
        type=str,
        default=None,
        help="Comma-separated output formats (json,csv,markdown)",
    )
    parser.add_argument(
        "--dcm",
        action="store_true",
        default=False,
        help="Enable DCM adapter",
    )
    parser.add_argument(
        "--no-dcm",
        action="store_true",
        default=False,
        help="Disable DCM adapter",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory for results",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=True,
        help="Verbose output (default)",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        default=False,
        help="Suppress output",
    )
    parser.add_argument(
        "--graphs",
        action="store_true",
        default=None,
        help="Enable dependency graph generation",
    )
    parser.add_argument(
        "--no-graphs",
        action="store_true",
        default=False,
        help="Disable dependency graph generation",
    )
    parser.add_argument(
        "--pkg-analysis",
        action="store_true",
        default=None,
        help="Enable package analysis",
    )
    parser.add_argument(
        "--no-pkg",
        action="store_true",
        default=False,
        help="Disable package analysis",
    )
    parser.add_argument(
        "--include-dev",
        action="store_true",
        default=False,
        help="Include dev dependencies in pubspec graph",
    )
    parser.add_argument(
        "--key-packages",
        type=str,
        default=None,
        help="Comma-separated packages for per-module graphs",
    )
    parser.add_argument(
        "--git-since",
        type=str,
        default=None,
        help="Start date for git hotspots (default: 2025-01-01)",
    )

    args = parser.parse_args()

    # Determine project root
    if args.project_root:
        repo_root = os.path.abspath(args.project_root)
    else:
        repo_root = os.getcwd()

    if not os.path.isdir(repo_root):
        print(f"Error: project root not found: {repo_root}", file=sys.stderr)
        return 1

    # Load config
    from .config import load_config
    config = load_config(config_path=args.config, repo_root=repo_root)

    # Apply CLI overrides
    if args.dcm:
        config.dcm.enabled = True
    if args.no_dcm:
        config.dcm.enabled = False
    if args.format:
        config.output.formats = [f.strip() for f in args.format.split(",")]
    if args.output:
        config.output.directory = args.output
    if args.no_graphs:
        config.graphs.enabled = False
    elif args.graphs:
        config.graphs.enabled = True
    if args.no_pkg:
        config.package_analysis.enabled = False
    elif args.pkg_analysis:
        config.package_analysis.enabled = True
    if args.include_dev:
        config.graphs.include_dev = True
    if args.key_packages:
        config.graphs.key_packages = [k.strip() for k in args.key_packages.split(",") if k.strip()]
    if args.git_since:
        config.package_analysis.git_since = args.git_since

    verbose = not args.quiet

    if verbose:
        print("=" * 60)
        print("  Code Metrics Collector v1.0")
        print("=" * 60)
        from .parsers.dart_parser import is_tree_sitter_available
        print(f"  tree-sitter: {'✓' if is_tree_sitter_available() else '✗ (using regex fallback)'}")
        dcm_status = '✗ (disabled)'
        if config.dcm.enabled:
            try:
                from .parsers.dcm_adapter import is_dcm_available
                dcm_status = '✓' if is_dcm_available(config.dcm) else '✗ (not found)'
            except ImportError:
                dcm_status = '✗ (module unavailable)'
        print(f"  DCM: {dcm_status}")
        print(f"  Formats: {', '.join(config.output.formats)}")
        print(f"  Dependency graphs: {'✓' if config.graphs.enabled else '✗'}")
        print(f"  Package analysis: {'✓' if config.package_analysis.enabled else '✗'}")
        print("=" * 60)
        print()

    # Run collection
    from .collector import collect_metrics, write_output

    metric_filter = None
    if args.metrics:
        metric_filter = [m.strip().lower() for m in args.metrics.split(",")]

    result = collect_metrics(
        config=config,
        module_filter=args.module,
        metric_filter=metric_filter,
        verbose=verbose,
    )

    # Write output
    written = write_output(result, config, verbose=verbose)

    if verbose:
        print(f"\n{'=' * 60}")
        print(f"  Done! Wrote {len(written)} files.")
        print(f"  Time: {result.duration_seconds:.1f}s")
        print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
