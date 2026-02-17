// ══════════════════════════════════════════
// Metrics Reference – definitions, formulas, ranges
// ══════════════════════════════════════════

var METRICS_REFERENCE = [
  // ── Function-Level Metrics ──
  {
    category: 'Function-Level Metrics',
    metrics: [
      {
        name: 'Cyclomatic Complexity',
        abbr: 'CC',
        desc: 'Measures the number of linearly independent paths through a function\'s source code. Each decision point (if, else, for, while, case, catch, &&, ||, ?:) adds one to the complexity count.',
        formula: 'CC = E − N + 2P\nwhere E = edges, N = nodes, P = connected components in the control flow graph.\nSimplified: CC = 1 + (number of decision points)',
        range: '1–5: Low risk | 6–10: Moderate | 11–20: High | 21+: Very high risk'
      },
      {
        name: 'Maintainability Index',
        abbr: 'MI',
        desc: 'A composite metric that combines Halstead Volume, Cyclomatic Complexity, and Lines of Code into a single score indicating how maintainable the code is. Higher values mean more maintainable code.',
        formula: 'MI = max(0, (171 − 5.2 × ln(HV) − 0.23 × CC − 16.2 × ln(LOC)) × 100 / 171)\nwhere HV = Halstead Volume, CC = Cyclomatic Complexity, LOC = Lines of Code',
        range: '80–100: Good | 40–80: Moderate | 20–40: Poor | 0–20: Unmaintainable'
      },
      {
        name: 'Halstead Volume',
        abbr: 'H.Vol',
        desc: 'Measures the size of a function\'s implementation based on the number of operators and operands. It represents the information content of the program.',
        formula: 'V = N × log₂(η)\nwhere N = N1 + N2 (total occurrences),\n      η = η1 + η2 (distinct operators + distinct operands),\n      N1 = total operators, N2 = total operands,\n      η1 = distinct operators, η2 = distinct operands',
        range: 'Lower is simpler. Typical values: 20–1000 for functions, >8000 indicates high complexity.'
      },
      {
        name: 'Max Nesting Level',
        abbr: 'MNL',
        desc: 'The maximum depth of nested control structures (if, for, while, try, etc.) within a function. Deep nesting makes code harder to read and maintain.',
        formula: 'Max depth of nested { } blocks within control flow statements.',
        range: '0–2: Good | 3: Acceptable | 4: Warning | 5+: Critical — consider refactoring'
      },
      {
        name: 'Number of Parameters',
        abbr: 'NOP / Params',
        desc: 'The number of parameters a function accepts. Functions with many parameters are harder to understand, test, and call correctly.',
        formula: 'Count of declared parameters in the function signature.',
        range: '0–3: Good | 4–5: Acceptable | 6+: Excessive — consider using parameter objects'
      },
      {
        name: 'Lines of Code (Function)',
        abbr: 'LOC / SLOC',
        desc: 'LOC counts all lines in the function body (including blanks and comments). SLOC (Source Lines of Code) counts only lines with actual code statements.',
        formula: 'LOC = total lines from function start to end\nSLOC = LOC − blank lines − comment-only lines',
        range: 'LOC ≤30: Good | 31–60: Moderate | 61–100: Long | >100: Too long'
      },
      {
        name: 'Weighted Methods per Function Points',
        abbr: 'WMFP',
        desc: 'A composite quality indicator that weights cyclomatic complexity, Halstead volume, and lines of code to produce a normalized difficulty measure per function.',
        formula: 'WMFP = w₁ × CC_norm + w₂ × HV_norm + w₃ × LOC_norm\nwhere CC_norm, HV_norm, LOC_norm are normalized to [0,1] and w₁, w₂, w₃ are configurable weights.',
        range: 'Lower is better. Values > 0.7 indicate functions that need refactoring.'
      },
      {
        name: 'First-Pass Yield (Function)',
        abbr: 'FPY',
        desc: 'Estimates the probability that a function will pass code review or testing without defects on first attempt. Based on complexity and size metrics.',
        formula: 'FPY = ∏(1 − p_defect_i)\nwhere p_defect_i is the defect probability contribution from each quality factor (CC, MI, nesting, etc.).',
        range: '0.9–1.0: Excellent | 0.7–0.9: Good | 0.5–0.7: Fair | <0.5: Poor'
      },
      {
        name: 'Technical Debt (Function)',
        abbr: 'TD (min)',
        desc: 'Estimated time in minutes needed to fix quality issues in the function. Calculated from violations of thresholds for CC, MI, nesting, LOC, and other metrics.',
        formula: 'TD = Σ (remediation_time_i × severity_weight_i)\nfor each violated threshold in the function.',
        range: 'Lower is better. Values vary by project; compare within your codebase.'
      },
    ]
  },
  // ── Class-Level Metrics (OOP) ──
  {
    category: 'Class-Level Metrics (OOP)',
    metrics: [
      {
        name: 'Weighted Methods per Class',
        abbr: 'WMC',
        desc: 'Sum of cyclomatic complexities of all methods in a class. Indicates the overall complexity of a class — higher WMC means the class is more complex and harder to maintain.',
        formula: 'WMC = Σ CC(mᵢ)\nwhere CC(mᵢ) is the cyclomatic complexity of method i.',
        range: '1–10: Good | 11–20: Moderate | 21–50: High | >50: God class candidate'
      },
      {
        name: 'Coupling Between Objects',
        abbr: 'CBO',
        desc: 'Number of other classes that a class is coupled to (uses or is used by). High coupling makes classes harder to test, reuse, and modify independently.',
        formula: 'CBO = |{c ∈ Classes : c ≠ this ∧ (this uses c ∨ c uses this)}|',
        range: '0–5: Low coupling | 6–10: Moderate | 11–20: High | >20: Excessive coupling'
      },
      {
        name: 'Response for Class',
        abbr: 'RFC',
        desc: 'Number of methods that can potentially be executed in response to a message received by a class. Includes methods of the class itself plus methods called by those methods.',
        formula: 'RFC = |RS|\nwhere RS = {M} ∪ {all methods called by methods in M},\n      M = set of methods in the class.',
        range: 'Lower is better. High RFC increases testing effort and defect probability.'
      },
      {
        name: 'Number of Methods',
        abbr: 'NOM',
        desc: 'Total count of methods defined in a class, including constructors, getters, setters, and regular methods.',
        formula: 'NOM = count of method declarations in the class.',
        range: 'Varies by convention. Very high NOM may indicate a class doing too much.'
      },
      {
        name: 'Tight Class Cohesion',
        abbr: 'TCC',
        desc: 'Ratio of directly connected method pairs to total possible method pairs. Methods are connected if they access at least one common instance variable. Higher TCC means better cohesion.',
        formula: 'TCC = NDC / NP\nwhere NDC = number of directly connected method pairs,\n      NP = N × (N − 1) / 2 (total possible pairs),\n      N = number of visible methods.',
        range: '0.5–1.0: Good cohesion | 0.33–0.5: Moderate | <0.33: Low — consider splitting the class'
      },
      {
        name: 'Depth of Inheritance Tree',
        abbr: 'DIT',
        desc: 'Number of ancestor classes from the root of the inheritance hierarchy. Deeper trees mean more inherited behavior to understand.',
        formula: 'DIT = length of the longest path from the class to the root of its inheritance tree.',
        range: '0–2: Good | 3–4: Moderate | 5+: Deep hierarchy — favor composition over inheritance'
      },
      {
        name: 'Weight of Class',
        abbr: 'WOC',
        desc: 'Ratio of "functional" public methods (non-accessor, non-constructor) to total public members. Low WOC indicates a data-only class (potential data class smell).',
        formula: 'WOC = functional_public_methods / total_public_members\nwhere functional methods exclude getters, setters, and constructors.',
        range: '0.5–1.0: Good (behavior-rich) | <0.33: Likely a data class'
      },
      {
        name: 'Number of Accessors',
        abbr: 'NOAM',
        desc: 'Count of getter and setter methods in a class. High NOAM relative to total methods may indicate a data class or anemic domain model.',
        formula: 'NOAM = count of getter + setter methods.',
        range: 'Context-dependent. Compare with NOM and WOC.'
      },
      {
        name: 'Number of Inherited Interfaces',
        abbr: 'NOII',
        desc: 'Count of interfaces (abstract classes, mixins, protocols) implemented by the class.',
        formula: 'NOII = count of implemented interfaces / mixins.',
        range: 'Context-dependent.'
      },
      {
        name: 'Number of Overridden Methods',
        abbr: 'NOOM',
        desc: 'Count of methods in the class that override a method from a parent class. High NOOM may indicate subclass is redefining too much inherited behavior.',
        formula: 'NOOM = count of @override methods.',
        range: 'Context-dependent. Compare with NOM.'
      },
      {
        name: 'First-Pass Yield (Class)',
        abbr: 'FPY (Class)',
        desc: 'Aggregated FPY at the class level — probability the class passes review/testing without defects. Combines FPY of all methods in the class.',
        formula: 'FPY_class = ∏ FPY(mᵢ) for each method mᵢ in the class,\nor a weighted average depending on configuration.',
        range: 'Same scale as function FPY: closer to 1.0 is better.'
      },
    ]
  },
  // ── File-Level Metrics ──
  {
    category: 'File-Level Metrics',
    metrics: [
      {
        name: 'Technical Debt (File)',
        abbr: 'TD (min)',
        desc: 'Sum of technical debt from all functions and classes in the file. Represents total estimated remediation time.',
        formula: 'TD_file = Σ TD(fᵢ) + Σ TD(cⱼ)\nwhere fᵢ = functions in file, cⱼ = classes in file.',
        range: 'Lower is better.'
      },
      {
        name: 'TD per LOC',
        abbr: 'TD/LOC',
        desc: 'Technical debt density — minutes of debt per line of code. Normalizes debt relative to file size.',
        formula: 'TD/LOC = TD_minutes / LOC',
        range: 'Lower is better. High values indicate concentrated quality issues.'
      },
      {
        name: 'Cyclomatic Complexity Sum',
        abbr: 'CC Σ',
        desc: 'Sum of cyclomatic complexity of all functions in the file. Indicates overall file complexity.',
        formula: 'CC_sum = Σ CC(fᵢ) for all functions fᵢ in the file.',
        range: 'Context-dependent. Compare across files in the same project.'
      },
      {
        name: 'MI Average',
        abbr: 'MI Avg',
        desc: 'Average maintainability index across all functions in the file.',
        formula: 'MI_avg = (Σ MI(fᵢ)) / N, where N = number of functions.',
        range: 'Same scale as function MI: 80+ is good.'
      },
      {
        name: 'WMFP (File)',
        abbr: 'WMFP (File)',
        desc: 'Aggregated WMFP score for the file, summarizing weighted quality of all functions.',
        formula: 'WMFP_file = Σ WMFP(fᵢ) or average, depending on configuration.',
        range: 'Lower is better.'
      },
      {
        name: 'WMFP Density',
        abbr: 'WMFP Density',
        desc: 'WMFP normalized by file size, indicating quality density per line of code.',
        formula: 'WMFP_density = WMFP_file / LOC',
        range: 'Lower is better.'
      },
      {
        name: 'FPY (File)',
        abbr: 'FPY (File)',
        desc: 'Aggregated first-pass yield at the file level.',
        formula: 'FPY_file = ∏ FPY(fᵢ) or weighted combination.',
        range: 'Closer to 1.0 is better.'
      },
    ]
  },
  // ── Module / Package Metrics ──
  {
    category: 'Module / Package Metrics',
    metrics: [
      {
        name: 'Number of Imports',
        abbr: 'NOI',
        desc: 'Total import statements in the module, counting all dependencies.',
        formula: 'NOI = count of import/include statements.',
        range: 'Context-dependent. Very high values may indicate a module doing too much.'
      },
      {
        name: 'Number of External Imports',
        abbr: 'NOEI',
        desc: 'Import statements referencing packages/libraries outside the project. High external dependency count increases risk.',
        formula: 'NOEI = count of imports from external (third-party) packages.',
        range: 'Context-dependent.'
      },
      {
        name: 'Cross-Package Imports',
        abbr: 'XPI',
        desc: 'Imports from other internal packages/modules. These create coupling between modules and should be minimized.',
        formula: 'XPI = count of import statements referencing other internal modules.',
        range: 'Lower is better — reduces inter-module coupling.'
      },
    ]
  },
  // ── Dependency & Structure Metrics ──
  {
    category: 'Dependency & Structure Metrics',
    metrics: [
      {
        name: 'Dependency Structure Matrix',
        abbr: 'DSM',
        desc: 'A square matrix where cell (i,j) shows the number of imports from module i to module j. Used to visualize and analyze inter-module dependencies.',
        formula: 'DSM[i][j] = count of import statements in module i referencing module j.',
        range: 'Matrix visualization. Look for clusters, cycles, and asymmetries.'
      },
      {
        name: 'Dependency Cycles',
        abbr: 'Cycles',
        desc: 'Circular dependencies between modules (A→B→C→A). Cycles make the codebase harder to understand, test, and deploy independently.',
        formula: 'Detected via graph analysis: any strongly connected component with >1 node in the module dependency graph.',
        range: '0 cycles is ideal. Every cycle should be resolved.'
      },
      {
        name: 'Risk Hotspots',
        abbr: 'Risk',
        desc: 'Files ranked by the combination of code churn (git change frequency) and complexity. High-churn, high-complexity files are the most risky.',
        formula: 'Risk Score = normalize(churn) × normalize(complexity)\nwhere complexity = CC_max × td_minutes / LOC.',
        range: 'Higher risk scores need more attention. Top items are prime refactoring targets.'
      },
      {
        name: 'Shotgun Surgery Candidates',
        abbr: 'SSC',
        desc: 'Files that are used by many other files. Changes to these files may require modifications across many dependents — the "shotgun surgery" code smell.',
        formula: 'Usage count = number of other files importing/referencing this file.',
        range: 'High usage count = higher impact of changes. Consider interface stabilization.'
      },
      {
        name: 'Git Hotspots',
        abbr: 'Git HS',
        desc: 'Files with the highest number of git commits. Frequently changed files may indicate unstable design or areas of active development.',
        formula: 'Commit count = number of git commits affecting this file.',
        range: 'Context-dependent. Combine with complexity metrics for actionable insights.'
      },
    ]
  },
  // ── Duplication Metrics ──
  {
    category: 'Duplication Metrics',
    metrics: [
      {
        name: 'Duplication Percentage',
        abbr: 'Dup %',
        desc: 'Percentage of total tokens in the codebase that appear in duplicate code blocks. Measures overall code redundancy.',
        formula: 'Dup% = (duplicated_tokens / total_tokens) × 100',
        range: '0–3%: Good | 3–5%: Acceptable | 5–10%: High | >10%: Critical'
      },
      {
        name: 'Duplicate Pairs',
        abbr: 'Pairs',
        desc: 'Number of detected code block pairs that are syntactically identical or near-identical.',
        formula: 'Count of (block_a, block_b) pairs where token sequences match above the configured threshold.',
        range: '0 is ideal. Each pair is a refactoring opportunity.'
      },
      {
        name: 'Files with Duplicates',
        abbr: 'Files w/ Dups',
        desc: 'Number of unique files that contain at least one duplicated code block.',
        formula: 'Count of distinct files appearing in any duplicate pair.',
        range: 'Lower is better.'
      },
    ]
  },
  // ── Aggregate / Rating Metrics ──
  {
    category: 'Aggregate / Rating Metrics',
    metrics: [
      {
        name: 'Module Score',
        abbr: 'Score',
        desc: 'A composite quality score (0–100) for each module, combining weighted metrics: complexity, maintainability, coupling, cohesion, duplication, and technical debt.',
        formula: 'Score = 100 − Σ (penalty_i × weight_i)\nwhere penalties are applied for exceeding metric thresholds.',
        range: '80–100: A grade | 60–80: B | 40–60: C | 20–40: D | 0–20: F'
      },
      {
        name: 'Module Grade',
        abbr: 'Grade (A–F)',
        desc: 'Letter grade derived from the module score, providing a quick quality assessment.',
        formula: 'A: score ≥ 80 | B: 60–79 | C: 40–59 | D: 20–39 | F: < 20',
        range: 'A is best, F is worst.'
      },
      {
        name: 'Technical Debt (Total)',
        abbr: 'TD (hours/days)',
        desc: 'Estimated total remediation time for all quality issues across the project or module.',
        formula: 'TD_total = Σ TD(all functions) + Σ TD(all classes)\nConverted: hours = minutes / 60, days = hours / 8.',
        range: 'Context-dependent. Track the trend over time — should decrease.'
      },
      {
        name: 'TD per KLOC',
        abbr: 'TD/KLOC',
        desc: 'Technical debt per thousand lines of code. Normalizes debt relative to codebase size for cross-project comparison.',
        formula: 'TD/KLOC = (TD_minutes / LOC) × 1000',
        range: 'Lower is better. Use for comparing modules of different sizes.'
      },
    ]
  },
  // ── Violation Types ──
  {
    category: 'Violation Types',
    metrics: [
      {
        name: 'High Complexity',
        abbr: 'cyclo_high',
        desc: 'Functions with cyclomatic complexity above the warning threshold (default: 10).',
        formula: 'Triggered when CC > threshold_warning.',
        range: 'Each violation adds remediation time to technical debt.'
      },
      {
        name: 'Very High Complexity',
        abbr: 'cyclo_very_high',
        desc: 'Functions with cyclomatic complexity above the critical threshold (default: 20).',
        formula: 'Triggered when CC > threshold_critical.',
        range: 'Critical — these functions should be refactored immediately.'
      },
      {
        name: 'Poor Maintainability',
        abbr: 'mi_poor',
        desc: 'Functions with Maintainability Index below the threshold (default: 20).',
        formula: 'Triggered when MI < threshold.',
        range: 'These functions are very hard to maintain.'
      },
      {
        name: 'Critical Nesting',
        abbr: 'mnl_critical',
        desc: 'Functions with max nesting level at or above the threshold (default: 5).',
        formula: 'Triggered when max_nesting_level ≥ threshold.',
        range: 'Deep nesting severely impacts readability.'
      },
      {
        name: 'God Classes',
        abbr: 'god_classes',
        desc: 'Classes with WMC above the threshold (default: 47). These classes do too much and should be split.',
        formula: 'Triggered when WMC > threshold.',
        range: 'God classes are a major design smell.'
      },
      {
        name: 'Low Cohesion',
        abbr: 'low_cohesion',
        desc: 'Classes with TCC below the threshold (default: 0.33). Methods don\'t share instance variables — the class may have multiple responsibilities.',
        formula: 'Triggered when TCC < threshold.',
        range: 'Consider splitting into more focused classes.'
      },
      {
        name: 'High Coupling',
        abbr: 'high_coupling',
        desc: 'Classes with CBO above the threshold (default: 14). Too many dependencies make the class fragile.',
        formula: 'Triggered when CBO > threshold.',
        range: 'Reduce dependencies by applying SOLID principles.'
      },
      {
        name: 'Excessive Parameters',
        abbr: 'excessive_params',
        desc: 'Functions with more parameters than the threshold (default: 5).',
        formula: 'Triggered when parameter_count > threshold.',
        range: 'Use parameter objects or builder pattern.'
      },
      {
        name: 'Excessive Imports',
        abbr: 'excessive_imports',
        desc: 'Files with more import statements than the threshold.',
        formula: 'Triggered when import_count > threshold.',
        range: 'May indicate a file with too many responsibilities.'
      },
      {
        name: 'Magic Numbers',
        abbr: 'magic_numbers_high',
        desc: 'Files containing numeric literals that should be named constants.',
        formula: 'Count of numeric literals (excluding 0, 1, -1) not assigned to named constants.',
        range: 'Extract to named constants for clarity.'
      },
      {
        name: 'Hardcoded Strings',
        abbr: 'hardcoded_strings_high',
        desc: 'Files containing string literals that should be externalized (e.g., for localization).',
        formula: 'Count of string literals not in designated constant files.',
        range: 'Externalize for localization and maintainability.'
      },
      {
        name: 'Potential Dead Code',
        abbr: 'potential_dead_code',
        desc: 'Functions or classes that appear to be unused — no references found in the codebase.',
        formula: 'Detected when no call sites or references are found for a function/class.',
        range: 'Verify and remove to reduce maintenance burden.'
      },
    ]
  },
];

// ── Modal toggle ──

function toggleMetricsRef() {
  var overlay = document.getElementById('metricsRefOverlay');
  var isVisible = overlay.classList.contains('visible');
  if (!isVisible) {
    // Build content on first open
    if (!overlay.dataset.built) {
      document.getElementById('metricsRefBody').innerHTML = buildMetricsRefHTML();
      overlay.dataset.built = '1';
    }
    overlay.classList.add('visible');
    document.body.style.overflow = 'hidden';
    var searchInput = document.getElementById('metricsRefSearch');
    searchInput.value = '';
    filterMetricsRef('');
    setTimeout(function () { searchInput.focus(); }, 100);
  } else {
    overlay.classList.remove('visible');
    document.body.style.overflow = '';
  }
}

function closeMetricsRef(e) {
  if (e.target === e.currentTarget) toggleMetricsRef();
}

function buildMetricsRefHTML() {
  var html = '';
  METRICS_REFERENCE.forEach(function (cat, ci) {
    html += '<h3 class="metric-cat-header" data-cat="' + ci + '">' + cat.category + '</h3>';
    cat.metrics.forEach(function (m) {
      html += '<div class="metric-item" data-cat="' + ci + '" data-name="' + m.name.toLowerCase() + '" data-abbr="' + m.abbr.toLowerCase() + '" data-name-orig="' + m.name + '" data-abbr-orig="' + m.abbr + '">';
      html += '<div class="metric-name">' + m.name + '<span class="metric-abbr">' + m.abbr + '</span></div>';
      html += '<div class="metric-desc">' + m.desc + '</div>';
      if (m.formula) html += '<div class="metric-formula">' + m.formula + '</div>';
      if (m.range) html += '<div class="metric-range">📏 ' + m.range + '</div>';
      html += '</div>';
    });
  });
  return html;
}

function filterMetricsRef(query) {
  var q = query.toLowerCase().trim();
  var body = document.getElementById('metricsRefBody');
  var items = body.querySelectorAll('.metric-item');
  var headers = body.querySelectorAll('.metric-cat-header');
  var visibleCats = {};

  items.forEach(function (el) {
    var nameOrig = el.dataset.nameOrig;
    var abbrOrig = el.dataset.abbrOrig;
    var nameEl = el.querySelector('.metric-name');
    
    if (!q) {
      el.classList.remove('hidden');
      // Restore original without highlights
      nameEl.innerHTML = nameOrig + '<span class="metric-abbr">' + abbrOrig + '</span>';
      visibleCats[el.dataset.cat] = true;
      return;
    }
    var name = el.dataset.name;
    var abbr = el.dataset.abbr;
    var match = name.indexOf(q) >= 0 || abbr.indexOf(q) >= 0;
    el.classList.toggle('hidden', !match);
    if (match) {
      visibleCats[el.dataset.cat] = true;
      // Highlight matches using original values
      nameEl.innerHTML = highlightText(nameOrig, q) +
        '<span class="metric-abbr">' + highlightText(abbrOrig, q) + '</span>';
    }
  });

  headers.forEach(function (h) {
    h.classList.toggle('hidden', !visibleCats[h.dataset.cat] && q !== '');
  });
}

function highlightText(text, query) {
  if (!query) return text;
  var lower = text.toLowerCase();
  var idx = lower.indexOf(query);
  if (idx < 0) return text;
  return text.substring(0, idx) +
    '<span class="highlight">' + text.substring(idx, idx + query.length) + '</span>' +
    highlightText(text.substring(idx + query.length), query);
}
