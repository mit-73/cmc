# Code Metrics Collector

A tool for collecting code quality metrics.

### Supported languages

- **Dart** (full support, monorepo-aware)

## Installation

```bash
# Clone the repository
git clone git@github.com:mit-73/cmc.git
cd cmc

# Create venv and install
python3 -m venv .venv
source .venv/bin/activate
pip install .

# (Optional) Install with tree-sitter for more precise AST parsing
pip install '.[tree-sitter]'
```

After installation, the `cmc` command is available globally within the virtualenv.
You can also run it as `python -m cmc`.

## Nix

The project includes a Nix flake for reproducible builds and easy usage without
manual dependency management. Two package variants are available:

| Package | Description |
|---|---|
| `minimal` | Base build with regex parser only (no extra dependencies) |
| `dart` | Full build with `tree-sitter` and `tree-sitter-dart` for precise AST parsing |

### Run without installing

Use `nix run` to execute `cmc` directly from the flake without installing
anything permanently:

```bash
# Run the full (tree-sitter) variant on a project
nix run github:mit-73/cmc#dart -- /path/to/your/dart-project

# Run the minimal variant
nix run github:mit-73/cmc#minimal -- /path/to/your/dart-project

# Pass any CLI flags as usual
nix run github:mit-73/cmc#dart -- /path/to/project --graphs --pkg-analysis
nix run github:mit-73/cmc#dart -- --format json --module core
nix run github:mit-73/cmc#dart -- --dcm --graphs --key-packages core,sdk
```

If you have the repository cloned locally:

```bash
cd cmc
nix run .#dart -- /path/to/your/dart-project
nix run .#minimal -- /path/to/your/dart-project
```

### Build

Build the package without installing it:

```bash
nix build github:mit-73/cmc#dart
./result/bin/cmc /path/to/your/dart-project

# Or from a local checkout
nix build .#dart
./result/bin/cmc --help
```

### Development shell

Enter a development shell with all dependencies available:

```bash
nix develop

# Or from a remote flake
nix develop github:mit-73/cmc
```

### Use as a flake input

Add `cmc` as an input in another flake:

```nix
{
  inputs = {
    cmc.url = "github:mit-73/cmc";
  };

  outputs = { cmc, ... }: {
    # Use cmc.packages.${system}.dart or cmc.packages.${system}.minimal
  };
}
```

## Supported Metrics

### Function-level
| Metric | Abbreviation | Description |
|---|---|---|
| Cyclomatic Complexity | CYCLO | Cyclomatic complexity (number of execution paths) |
| Halstead Volume | HALVOL | Halstead volume (complexity based on operators/operands) |
| Lines of Code | LOC | Total number of lines |
| Maintainability Index | MI | Maintainability index (0–100, higher is better) |
| Maximum Nesting Level | MNL | Maximum nesting depth |
| Number of Parameters | NOP | Number of function parameters |
| Source Lines of Code | SLOC | Lines of code excluding comments and blank lines |
| Weighted Micro Function Points | WMFP | Size/complexity score based on 8 weighted components |
| First-Pass Yield | FPY | Quality gate pass rate (0–1, higher is better) |

### Class-level
| Metric | Abbreviation | Description |
|---|---|---|
| Coupling Between Objects | CBO | Coupling with other classes |
| Depth of Inheritance Tree | DIT | Depth of the inheritance tree |
| Number of Added Methods | NOAM | Methods added in the class (not from superclass) |
| Number of Implemented Interfaces | NOII | Number of implemented interfaces |
| Number of Methods | NOM | Total number of methods |
| Number of Overridden Methods | NOOM | Number of overridden methods |
| Response for a Class | RFC | NOM + unique external calls |
| Tight Class Cohesion | TCC | Class cohesion (0–1, higher is better) |
| Weight of a Class | WOC | Proportion of functional public methods |
| Weighted Methods per Class | WMC | Sum of CC across all methods |
| First-Pass Yield | FPY | Quality gate pass rate (0–1, higher is better) |

### File-level
| Metric | Abbreviation | Description |
|---|---|---|
| Number of External Imports | NOEI | External package imports |
| Number of Imports | NOI | Total number of imports |
| Static Members | — | Count of static fields and methods |
| Hardcoded Strings | — | Count of hardcoded string literals |
| Magic Numbers | — | Count of unexplained numeric literals |
| Dead Code Estimate | — | Estimated dead code via cross-file private symbol analysis |
| Weighted Micro Function Points | WMFP | Sum of function WMFPs in the file |
| WMFP Density | — | WMFP / SLOC — normalized complexity density |
| First-Pass Yield | FPY | Weighted combination of function, class, and smell gate pass rates |

### Composite
| Metric | Description |
|---|---|
| Technical Debt | Technical debt in minutes based on threshold violations |
| Weighted Micro Function Points (WMFP) | Weighted linear combination of 8 components: flow complexity (CC), object vocabulary (Halstead), object conjuration, arithmetic intricacy, data transfer (params), code structure (nesting, LOC), inline data, comments |
| First-Pass Yield (FPY) | Fraction of quality gates passed — computed at function, class, and file level |

## Code Smells

The tool detects the following code smells at the file level:

| Smell | Description |
|---|---|
| **Static Members** | Counts static fields and methods — excessive statics may indicate procedural style |
| **Hardcoded Strings** | Detects hardcoded string literals that should be constants or l10n keys |
| **Magic Numbers** | Finds unexplained numeric literals (excluding 0, 1, 2, common values) |
| **Dead Code Estimate** | Cross-file analysis of private symbols (`_`-prefixed) that are never imported elsewhere |

These metrics appear in `file_metrics.json` / `file_metrics.csv` and generate violations
(`magic_numbers_high`, `hardcoded_strings_high`, `potential_dead_code`) when thresholds are exceeded.

## Quick Start

```bash
# Clone the repository
git clone git@github.com:mit-73/cmc.git
cd cmc

# Create venv and install
python3 -m venv .venv
source .venv/bin/activate
pip install .

# (Optional) Install with tree-sitter for more precise parsing
pip install '.[tree-sitter]'

# Run on a project (from any directory)
cmc /path/to/your/dart-project

# Or specify the project root as the current directory
cd /path/to/your/dart-project
cmc

# Single module only
cmc --module core

# JSON output only
cmc --format json

# With DCM (if installed)
cmc --dcm

# With dependency graphs
cmc --graphs

# With package analysis
cmc --pkg-analysis

# Full run: metrics + graphs + package analysis
cmc --graphs --pkg-analysis

# Custom key packages for per-module import graphs
cmc --graphs --key-packages core,sdk

# Include dev dependencies in pubspec graph
cmc --graphs --include-dev

# Custom git hotspot start date
cmc --pkg-analysis --git-since 2024-06-01

# Disable graphs explicitly
cmc --no-graphs --no-pkg

# Alternative: run as a Python module
python -m cmc /path/to/your/dart-project

# View interactive dashboard after running metrics
cmc view /path/to/your/metrics/output
```

## Viewing Dashboard

After running metrics collection, you can view an interactive HTML dashboard:

```bash
# Start local HTTP server for the dashboard
cmc view /path/to/your/metrics/output

# Or from the metrics output directory
cd /path/to/your/metrics/output
cmc view

# Custom port (default: 4000)
cmc view --port 8080
```

The dashboard will be available at `http://localhost:4000/index.html` (or your custom port).
The dashboard is served from the `cmc/server/` directory with metrics data loaded from the metrics output directory.

No installation required — just run `cmc view` and open the URL in any browser.

## CLI Flags

| Flag | Default | Description |
|---|---|---|
| `PROJECT_ROOT` | cwd | Positional: path to the project root to analyze |
| `--config PATH` | *(auto)* | Path to `metrics.yaml` (searches `./metrics.yaml` then `./analysis/metrics.yaml`) |
| `--module NAME` | *(all)* | Analyze only the specified module |
| `--metrics LIST` | *(all)* | Comma-separated metric names to compute (e.g., `cyclo,cbo,wmc`) |
| `--format FORMAT` | *(all)* | Output format: `json`, `csv`, `markdown` |
| `--output DIR` | *(config)* | Override output directory for results |
| `--dcm` / `--no-dcm` | off | Enable/disable DCM adapter for more accurate function-level metrics |
| `--graphs` / `--no-graphs` | off | Enable/disable dependency graph generation |
| `--pkg-analysis` / `--no-pkg` | off | Enable/disable package analysis |
| `--include-dev` | off | Include dev dependencies in pubspec graph |
| `--key-packages LIST` | *(config)* | Comma-separated list of packages for per-module import graphs |
| `--git-since DATE` | `2025-01-01` | Start date for git hotspot analysis |
| `--verbose` / `-v` | on | Verbose output (default) |
| `--quiet` / `-q` | off | Suppress output |

## Configuration

Configuration is loaded from a YAML file. The tool searches in this order:
1. Path passed via `--config`
2. `metrics.yaml` in the project root
3. `analysis/metrics.yaml` in the project root

Supported sections (show details in [metrics.yaml](metrics.yaml)):

- **discovery** — module discovery strategy (`workspace`, `auto`, `manual`)
- **exclude_patterns** — glob patterns for excluding directories
- **exclude_files** — glob patterns for excluding files (`*.g.dart`, `*.freezed.dart`)
- **thresholds** — threshold values for each metric
- **technical_debt** — weight coefficients for technical debt calculation
- **code_smells** — thresholds for code smell violations
- **wmfp** — WMFP component weights and thresholds
- **fpy** — First-Pass Yield quality gate thresholds and aggregation weights
- **dcm** — optional DCM integration
- **graphs** — dependency graph generation settings
- **package_analysis** — package analysis settings
- **rating** — module quality rating weights and normalization ceilings
- **duplication** — code duplication detection parameters
- **history** — snapshot-based trend tracking settings
- **output** — output directory and formats


## Module Quality Rating (A/B/C/D/E)

Every module receives a composite quality score (0–100) and a letter grade.
The score is computed from four normalized components:

| Component | Weight | Scale |
|---|---|---|
| Maintainability Index (MI) | 30% | 0–100 (direct) |
| Cyclomatic Complexity (CC) | 25% | inverted: lower CC → higher score |
| First-Pass Yield (FPY) | 25% | 0–1 scaled to 0–100 |
| Technical Debt density | 20% | inverted: lower TD/kLOC → higher score |

| Grade | Score | Meaning |
|---|---|---|
| **A** | 80–100 | Excellent |
| **B** | 60–79 | Good |
| **C** | 40–59 | Moderate |
| **D** | 20–39 | Poor |
| **E** | 0–19 | Critical |

Output: `ratings.json`, `ratings.md`

## Risk Hotspots (Churn × Complexity)

Combines git change frequency (number of commits) with file-level complexity
(CC sum + technical debt) to identify the riskiest files in the codebase.
Both churn and complexity are normalized to 0–1 and multiplied to produce a
risk score. Requires `--pkg-analysis` to enable git data.

Output: `risk_hotspots.json`, `risk_hotspots.md`

## Design Structure Matrix (DSM)

Generates an N×N module dependency matrix from the import graph. Each cell
`[i][j]` shows how many imports module `i` has from module `j`. Bidirectional
non-zero cells indicate cyclic dependencies. Requires `--graphs`.

Output: `dsm.json`, `dsm.md`

## Distribution Histograms

Bucket-based histograms for 7 key metrics:

| Metric | Buckets |
|---|---|
| Cyclomatic Complexity | 1–5, 6–10, 11–20, 21–50, 51+ |
| Maintainability Index | 0–20, 21–40, 41–60, 61–80, 81–100 |
| Function LOC | 1–10, 11–25, 26–50, 51–100, 101+ |
| WMC | 1–10, 11–20, 21–50, 51–100, 101+ |
| FPY (function) | 0–0.2, 0.2–0.4, 0.4–0.6, 0.6–0.8, 0.8–1.0 |
| WMFP | 0–5, 5–15, 15–30, 30–60, 60+ |
| File Tech Debt (min) | 0, 1–30, 31–120, 121–480, 481+ |

Output: `distributions.json`, `distributions.md`

## Code Duplication Detection

Token-based copy-paste detection using MD5 rolling hash (Rabin-Karp style).
Dart source is tokenized with normalization: string literals → `$STR`,
numeric literals → `$NUM`, non-keyword identifiers → `$ID`, Dart keywords
preserved. Finds duplicate blocks across all files.

Output: `duplication.json`, `duplication.md`

## History & Trend Tracking

Each run saves a snapshot (`history/snapshot_YYYYMMDD_HHMMSS.json`) containing
project-level and per-module metrics, ratings, and duplication percentage.
On subsequent runs the tool:

1. Loads the latest previous snapshot
2. Computes a delta with directional indicators (🟢 improved / 🔴 worsened / ⚪ unchanged)
3. Loads up to 20 historical snapshots for trend charts

Output: `history/snapshot_*.json`, `delta.json`, `delta.md`

## HTML Dashboard

An interactive HTML dashboard served via local HTTP server.
Run `cmc view` to start the server and view metrics in your browser.

The dashboard contains 7 tabs:

| Tab | Contents |
|---|---|
| **Overview** | KPI cards, module rating cards, violations bar chart |
| **Modules** | Sortable comparison table, tech debt bars, radar charts |
| **Hotspots** | Risk hotspots (churn × complexity), top functions/classes |
| **Distributions** | Interactive bar charts for all 7 metric histograms |
| **Dependencies** | DSM matrix with cycle highlighting |
| **Duplication** | Duplication KPIs and top duplicate pairs table |
| **Trends & Delta** | Delta table vs previous run, historical line charts |

The dashboard uses Chart.js for interactive visualizations and loads metrics data
from JSON files in the output directory.

## Dependency Graphs

When enabled (`--graphs`), the tool generates dependency graphs at two levels:

### Import-level Graph
- Parses Dart `import` statements across all source files
- Resolves `package:` imports to their target modules
- Outputs: `graph_import.dot`, `graph_import.json`, `edges_import.csv`

### Pubspec-level Graph
- Parses `pubspec.yaml` files to extract declared dependencies
- Optionally includes `dev_dependencies` (`--include-dev`)
- Outputs: `graph_pubspec.dot`, `graph_pubspec.json`, `edges_pubspec.csv`

### Per-module Import Graphs
- For each package listed in `key_packages`, generates a focused import graph
- Shows how that package is imported by other modules

### Graph Summary
- `graph_summary.md` — a Markdown report with node/edge counts, most connected modules, and fan-in/fan-out statistics

DOT files can be visualized with [Graphviz](https://graphviz.org/) or online at [edotor.net](https://edotor.net/).

## Package Analysis

When enabled (`--pkg-analysis`), the tool performs cross-package structural analysis:

| Analysis | Description |
|---|---|
| **Cross-package imports** | Detects imports between packages that are not declared as dependencies |
| **Import statistics** | Per-package import counts and breakdown (internal vs external) |
| **Shotgun surgery detection** | Files that are imported by many other packages (high fan-in) |
| **Git hotspots** | Most frequently changed files in the repository (since `--git-since`) |
| **Directory structure** | Analysis of directory depth and organization per module |

### Output
- `{module}_package_analysis.json` — per-module analysis results
- `package_analysis.md` — consolidated Markdown report

## Output Files

```
analysis/metrics/
├── raw/                                # Raw metrics
│   ├── file_metrics.json/.csv          # includes static_members, hardcoded_strings,
│   │                                   #   magic_numbers, dead_code_estimate
│   ├── function_metrics.json/.csv
│   └── class_metrics.json/.csv
├── modules/                            # Per-module reports
│   ├── {module}_summary.json
│   ├── {module}_summary.md
│   └── {module}_package_analysis.json  # if --pkg-analysis
├── history/                            # Snapshots for trend tracking
│   └── snapshot_YYYYMMDD_HHMMSS.json
├── graph_import.dot/.json              # import-level dependency graph
├── graph_pubspec.dot/.json             # pubspec-level dependency graph
├── edges_import.csv                    # import graph edges
├── edges_pubspec.csv                   # pubspec graph edges
├── graph_summary.md                    # graph statistics report
├── package_analysis.md                 # package analysis report
├── project_summary.json/.md            # Overall project summary
├── hotspots.json/.md                   # Hotspots (Top-20)
├── technical_debt.json/.md             # Technical debt report
├── ratings.json/.md                    # Module quality ratings (A/B/C/D/E)
├── distributions.json/.md              # Metric distribution histograms
├── risk_hotspots.json/.md              # Churn × Complexity risk hotspots
├── dsm.json/.md                        # Design Structure Matrix
├── duplication.json/.md                # Code duplication report
├── delta.json/.md                      # Diff vs previous snapshot
├── index.json                          # Dashboard data index
└── metadata.json                       # Run metadata
```

View the dashboard by running `cmc view` — it serves the interactive HTML interface
from `cmc/server/` and loads metrics data from the output directory.

## Violations

The following violations are tracked and contribute to technical debt:

| Violation | Trigger |
|---|---|
| `cyclo_high` | Cyclomatic complexity exceeds `high` threshold |
| `loc_high` | Function/file/class exceeds LOC limits |
| `nesting_high` | Nesting level exceeds `warning` threshold |
| `params_high` | Parameter count exceeds `warning` threshold |
| `cbo_high` | Coupling between objects exceeds `warning` threshold |
| `dit_high` | Inheritance depth exceeds `warning` threshold |
| `low_cohesion` | TCC below `warning` threshold |
| `god_class` | WMC exceeds `critical` threshold |
| `magic_numbers_high` | Magic number count exceeds `magic_numbers_warning` |
| `hardcoded_strings_high` | Hardcoded string count exceeds `hardcoded_strings_warning` |
| `potential_dead_code` | Dead code estimate exceeds `dead_code_warning` |

## Parser

Two parsers are supported:
1. **tree-sitter** (precise AST) — requires the `tree-sitter-dart` package
2. **regex fallback** — works without additional dependencies

When tree-sitter is available, it is used automatically.

## DCM (Optional)

If [DCM](https://dcm.dev/) is installed, it can be enabled in the configuration.
DCM provides more accurate values for function-level metrics
(CYCLO, HALVOL, MI, MNL, NOP, SLOC).

```bash
dart pub global activate dcm
cmc --dcm
```

## Architecture

```
cmc/
├── __main__.py                  # CLI entry point
├── config.py                    # Configuration loading
├── discovery.py                 # Module discovery
├── collector.py                 # Orchestrator
├── models.py                    # Data models
├── parsers/
│   ├── dart_parser.py           # tree-sitter + regex fallback
│   └── dcm_adapter.py           # DCM CLI adapter
├── metrics/
│   ├── function_metrics.py      # CYCLO, HALVOL, LOC, MI, MNL, NOP, SLOC, WMFP
│   ├── class_metrics.py         # CBO, DIT, NOAM, NOII, NOM, NOOM, RFC, TCC, WOC, WMC
│   ├── file_metrics.py          # NOI, NOEI
│   ├── code_smells.py           # Static members, hardcoded strings, magic numbers, dead code
│   ├── technical_debt.py        # Technical Debt
│   ├── wmfp.py                  # Weighted Micro Function Points (WMFP)
│   ├── fpy.py                   # First-Pass Yield (FPY)
│   ├── rating.py                # Module quality rating (A/B/C/D/E)
│   ├── risk_hotspots.py         # Churn × Complexity risk analysis
│   ├── distributions.py         # Metric distribution histograms
│   ├── duplication.py           # Token-based code duplication detection
│   └── history.py               # Snapshot-based trend tracking & delta
├── graphs/
│   ├── models.py                # Graph data models (nodes, edges)
│   ├── import_graph.py          # Import-level graph builder
│   ├── pubspec_graph.py         # Pubspec-level graph builder
│   └── dsm.py                   # Design Structure Matrix
├── package_analysis/
│   ├── models.py                # Analysis data models
│   ├── import_analysis.py       # Cross-package import detection, shotgun surgery
│   ├── git_analysis.py          # Git hotspot analysis
│   └── package_collector.py     # Package-level data collector
├── aggregation/
│   ├── stats.py                 # Statistics (mean, median, p90, std_dev)
│   ├── module_aggregator.py     # Per-module aggregation
│   └── project_aggregator.py    # Project-wide aggregation
├── output/
│   ├── json_writer.py           # JSON output
│   ├── csv_writer.py            # CSV output
│   ├── markdown_writer.py       # Markdown reports
│   └── dot_writer.py            # Graphviz DOT output
└── server/                      # Dashboard web server
    ├── index.html               # Dashboard HTML
    ├── styles.css               # Dashboard styles
    └── js/                      # Dashboard JavaScript modules
```
