"""Function-level metrics: CYCLO, HALVOL, LOC, MI, MNL, NOP, SLOC."""

from __future__ import annotations

import math
import re
from typing import List

from ..config import Thresholds
from ..models import FunctionMetrics, HalsteadData, ParsedFile, ParsedFunction
from ..parsers.dart_parser import strip_comments, strip_strings_and_comments
from .wmfp import compute_wmfp, count_arithmetic_ops, count_assignments


# ---------------------------------------------------------------------------
# Decision keywords / operators for cyclomatic complexity
# ---------------------------------------------------------------------------

_DECISION_KEYWORDS = re.compile(
    r"\b(?:if|for|while|do|case|catch)\b"
)

_LOGICAL_OPERATORS = re.compile(
    r"&&|\|\||\?\?"
)


# ---------------------------------------------------------------------------
# Halstead — operators sorted by length for longest-match tokenisation
# ---------------------------------------------------------------------------

_DART_MULTI_CHAR_OPS = sorted([
    ">>>=", "<<=", ">>=", "~/=",
    ">>>", "??=", "...",
    "~/", "<<", ">>", "==", "!=", ">=", "<=",
    "&&", "||", "??", "?.", "!.", "..",
    "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=",
    "=>", "is!", "as",
], key=len, reverse=True)

_DART_SINGLE_CHAR_OPS = frozenset("+-*/%=<>!&|^~?:.")

_DART_KEYWORD_OPERATORS = frozenset({
    "if", "else", "for", "while", "do", "switch", "case", "default",
    "break", "continue", "return", "throw", "try", "catch", "finally",
    "new", "const", "var", "final", "late", "required",
    "await", "async", "yield", "sync",
    "assert", "import", "export", "class", "extends", "implements",
    "with", "abstract", "mixin", "enum", "typedef",
})

# Delimiters — NOT counted as operators
_DELIMITERS = frozenset("{}()[];,@#")

_RE_IDENTIFIER = re.compile(r"[a-zA-Z_]\w*")
_RE_NUMBER = re.compile(r"\d+\.?\d*(?:[eE][+-]?\d+)?")


# ---------------------------------------------------------------------------
# Control-flow keywords for nesting
# ---------------------------------------------------------------------------

_NESTING_KEYWORDS = frozenset({
    "if", "else", "for", "while", "do", "switch",
    "try", "catch", "finally",
})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_function_metrics(
    parsed_file: ParsedFile,
    module_name: str,
    thresholds: Thresholds,
) -> List[FunctionMetrics]:
    """Compute metrics for all functions/methods in a parsed file."""
    results: List[FunctionMetrics] = []

    all_functions: List[ParsedFunction] = list(parsed_file.top_level_functions)
    for cls in parsed_file.classes:
        all_functions.extend(cls.methods)

    rel_path = parsed_file.path

    for fn in all_functions:
        cyclo = compute_cyclomatic_complexity(fn.body_text)
        halvol_data = compute_halstead(fn.full_text)
        halvol = halvol_data.volume
        loc = _count_lines(fn.full_text)
        sloc = _count_sloc(fn.full_text)
        mi = compute_maintainability_index(cyclo, halvol, loc)
        mnl = compute_max_nesting(fn.body_text)
        nop = len(fn.parameters)

        # WMFP
        arith_ops = count_arithmetic_ops(fn.body_text)
        assigns = count_assignments(fn.body_text)
        comment_lines = max(0, loc - sloc)
        wmfp = compute_wmfp(
            cyclo=cyclo,
            halstead_vocab=halvol_data.vocabulary,
            halstead_length=halvol_data.program_length,
            arith_ops=arith_ops,
            num_params=nop,
            assignments=assigns,
            max_nesting=mnl,
            loc=loc,
            sloc=sloc,
            comment_lines=comment_lines,
            weights=thresholds.wmfp_weights,
        )

        fm = FunctionMetrics(
            path=rel_path,
            module=module_name,
            class_name=fn.class_name,
            function_name=fn.name,
            line_start=fn.line_start,
            line_end=fn.line_end,
            cyclo=cyclo,
            halstead_volume=round(halvol, 2),
            loc=loc,
            sloc=sloc,
            mi=round(mi, 2),
            max_nesting_level=mnl,
            number_of_parameters=nop,
            wmfp=wmfp,
        )
        results.append(fm)

    return results


# ---------------------------------------------------------------------------
# Cyclomatic Complexity
# ---------------------------------------------------------------------------

def compute_cyclomatic_complexity(body: str) -> int:
    """Compute McCabe cyclomatic complexity of a function body.

    CC = 1 + decision keywords + logical operators + ternary '?'.
    Uses state-machine string/comment stripping for accuracy.
    """
    if not body:
        return 1

    cleaned = strip_strings_and_comments(body)

    cc = 1
    cc += len(_DECISION_KEYWORDS.findall(cleaned))
    cc += len(_LOGICAL_OPERATORS.findall(cleaned))

    # Ternary ? detection — remove ?., ?? and nullable-type ? first
    # 1) Replace ?. with XX
    tmp = re.sub(r'\?\.', 'XX', cleaned)
    # 2) Replace ?? with XX (already counted above)
    tmp = tmp.replace('??', 'XX')
    # 3) Remove nullable type annotations: SomeType? (word boundary + ?)
    #    Pattern: a type name (capitalized or not) immediately followed by ?
    #    that is then followed by whitespace, ), >, , or ;
    tmp = re.sub(r'(\w)\?(?=[\s)>,;\]\[])', r'\1X', tmp)
    # 4) Count remaining standalone ?
    ternary_count = 0
    for i, c in enumerate(tmp):
        if c == '?':
            # Must not be followed by another ? or .
            nxt = tmp[i + 1] if i + 1 < len(tmp) else ''
            if nxt not in ('.', '?', '='):
                ternary_count += 1
    cc += ternary_count

    return cc


# ---------------------------------------------------------------------------
# Halstead Volume
# ---------------------------------------------------------------------------

def compute_halstead(source: str) -> HalsteadData:
    """Compute Halstead complexity metrics.

    Uses longest-match tokenisation for multi-char operators.
    Delimiters ({, }, (, ), [, ], ;, ,) are excluded.
    """
    cleaned = strip_strings_and_comments(source)

    operators: dict[str, int] = {}
    operands: dict[str, int] = {}

    pos = 0
    n = len(cleaned)

    while pos < n:
        c = cleaned[pos]

        # Skip whitespace
        if c.isspace():
            pos += 1
            continue

        # Skip delimiters (not operators)
        if c in _DELIMITERS:
            pos += 1
            continue

        # Try identifier / keyword
        if c.isalpha() or c == '_':
            m = _RE_IDENTIFIER.match(cleaned, pos)
            if m:
                word = m.group(0)
                if word in _DART_KEYWORD_OPERATORS:
                    operators[word] = operators.get(word, 0) + 1
                elif word == 'is' or word == 'as' or word == 'in':
                    operators[word] = operators.get(word, 0) + 1
                else:
                    operands[word] = operands.get(word, 0) + 1
                pos = m.end()
                continue

        # Try number literal
        if c.isdigit():
            m = _RE_NUMBER.match(cleaned, pos)
            if m:
                operands[m.group(0)] = operands.get(m.group(0), 0) + 1
                pos = m.end()
                continue

        # Try multi-char operator (longest match)
        matched = False
        for op in _DART_MULTI_CHAR_OPS:
            if cleaned[pos:pos + len(op)] == op:
                operators[op] = operators.get(op, 0) + 1
                pos += len(op)
                matched = True
                break

        if matched:
            continue

        # Single-char operator
        if c in _DART_SINGLE_CHAR_OPS:
            operators[c] = operators.get(c, 0) + 1
            pos += 1
            continue

        # Unknown character — skip
        pos += 1

    n1 = sum(operators.values())
    n2 = sum(operands.values())
    eta1 = len(operators)
    eta2 = len(operands)

    return HalsteadData(n1=n1, n2=n2, eta1=eta1, eta2=eta2)


# ---------------------------------------------------------------------------
# Maintainability Index
# ---------------------------------------------------------------------------

def compute_maintainability_index(cyclo: int, halvol: float, loc: int) -> float:
    """MI = max(0, (171 - 5.2*ln(HV) - 0.23*CC - 16.2*ln(LOC)) / 171 * 100)"""
    if loc <= 0:
        return 100.0
    if halvol <= 0:
        halvol = 1.0

    raw = 171 - 5.2 * math.log(halvol) - 0.23 * cyclo - 16.2 * math.log(loc)
    mi = max(0.0, raw / 171.0 * 100.0)
    return min(mi, 100.0)


# ---------------------------------------------------------------------------
# Maximum Nesting Level (control-flow only)
# ---------------------------------------------------------------------------

_RE_WORD_BEFORE_BRACE = re.compile(r'(\w+)\s*$')

def compute_max_nesting(body: str) -> int:
    """Compute max nesting of control-flow structures only.

    Only counts braces following control-flow keywords (if, for, while,
    do, switch, try, catch, finally, else).  Map/Set literals, lambdas,
    and class bodies are ignored.
    """
    if not body:
        return 0

    cleaned = strip_strings_and_comments(body)

    max_depth = 0
    cf_depth = 0          # control-flow depth
    total_depth = 0       # total brace depth
    # Stack: True if this brace level is a control-flow block
    is_cf_stack: list[bool] = []

    i = 0
    n = len(cleaned)

    while i < n:
        c = cleaned[i]

        if c == '{':
            total_depth += 1
            # Check if this brace is preceded by a control-flow keyword
            preceding = cleaned[max(0, i - 60):i].rstrip()
            # Handle "else {", "else if (...) {", etc.
            word_m = _RE_WORD_BEFORE_BRACE.search(preceding)
            is_cf = False
            if word_m:
                word = word_m.group(1)
                if word in _NESTING_KEYWORDS:
                    is_cf = True
            else:
                # Check for ) { pattern (closing paren of if/for/while/catch)
                if preceding.endswith(')'):
                    is_cf = True

            is_cf_stack.append(is_cf)
            if is_cf:
                cf_depth += 1
                if cf_depth > max_depth:
                    max_depth = cf_depth

        elif c == '}':
            if is_cf_stack:
                was_cf = is_cf_stack.pop()
                if was_cf:
                    cf_depth = max(0, cf_depth - 1)
            total_depth = max(0, total_depth - 1)

        i += 1

    return max_depth


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _count_lines(text: str) -> int:
    if not text:
        return 0
    return len(text.splitlines())


def _count_sloc(text: str) -> int:
    cleaned = strip_comments(text)
    return sum(1 for line in cleaned.splitlines() if line.strip())
