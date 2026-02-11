"""Code smells detection: magic numbers, hardcoded strings, static members, dead code."""

from __future__ import annotations

import re
from typing import Dict, List, Set, Tuple

from ..models import ParsedFile

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_RE_STATIC = re.compile(r'\bstatic\b')

# Number literals (excluding 0, 1, -1 and common constants)
_RE_NUMBER = re.compile(r'(?<![\w.])(-?\d+\.?\d*(?:[eE][+-]?\d+)?)(?![\w.])')

# String literals (single and double quoted, non-triple)
_RE_STRING_SQ = re.compile(r"'(?:\\.|[^'\\])*'")
_RE_STRING_DQ = re.compile(r'"(?:\\.|[^"\\])*"')
_RE_TRIPLE_SQ = re.compile(r"'''.*?'''", re.DOTALL)
_RE_TRIPLE_DQ = re.compile(r'""".*?"""', re.DOTALL)

# Line/block comments
_RE_LINE_COMMENT = re.compile(r'//.*')
_RE_BLOCK_COMMENT = re.compile(r'/\*.*?\*/', re.DOTALL)

# Private symbols (_name)
_RE_PRIVATE_DEF = re.compile(r'\b(_[A-Za-z][A-Za-z0-9_]*)\b')

# Trivial numbers that are NOT magic
_TRIVIAL_NUMBERS = frozenset({0, 0.0, 1, 1.0, -1, -1.0, 2, 2.0})


def _strip_comments(source: str) -> str:
    """Remove comments from source code."""
    s = _RE_BLOCK_COMMENT.sub('', source)
    s = _RE_LINE_COMMENT.sub('', s)
    return s


def _strip_comments_and_strings(source: str) -> str:
    """Remove comments and string literals from source."""
    s = _strip_comments(source)
    # Triple-quoted first (greedy match)
    s = _RE_TRIPLE_SQ.sub('""', s)
    s = _RE_TRIPLE_DQ.sub('""', s)
    s = _RE_STRING_SQ.sub('""', s)
    s = _RE_STRING_DQ.sub('""', s)
    return s


# ---------------------------------------------------------------------------
# Individual smell detectors
# ---------------------------------------------------------------------------

def count_static_members(source: str) -> int:
    """Count static members in the source code."""
    cleaned = _strip_comments_and_strings(source)
    return len(_RE_STATIC.findall(cleaned))


def count_string_literals(source: str) -> int:
    """Count non-trivial string literals (excluding empty strings).

    Counts strings that are not empty or single-character.
    Looks at code WITH comments stripped but WITH strings present.
    """
    s = _strip_comments(source)
    count = 0
    # Triple-quoted strings
    for m in _RE_TRIPLE_SQ.finditer(s):
        content = m.group()[3:-3]
        if content.strip():
            count += 1
    for m in _RE_TRIPLE_DQ.finditer(s):
        content = m.group()[3:-3]
        if content.strip():
            count += 1
    # Remove triple strings before counting singles
    s = _RE_TRIPLE_SQ.sub('', s)
    s = _RE_TRIPLE_DQ.sub('', s)
    # Single/double quoted
    for m in _RE_STRING_SQ.finditer(s):
        content = m.group()[1:-1]
        if len(content) > 1:  # skip empty and single-char
            count += 1
    for m in _RE_STRING_DQ.finditer(s):
        content = m.group()[1:-1]
        if len(content) > 1:
            count += 1
    return count


def count_magic_numbers(source: str) -> int:
    """Count magic number occurrences (non-trivial numeric literals).

    Excludes 0, 1, -1, 2 and numbers inside annotations, const declarations.
    """
    cleaned = _strip_comments_and_strings(source)
    count = 0
    for m in _RE_NUMBER.finditer(cleaned):
        try:
            val = float(m.group())
        except ValueError:
            continue
        if val in _TRIVIAL_NUMBERS:
            continue
        # Check if it's in a const/enum context — simple heuristic
        start = max(0, m.start() - 80)
        prefix = cleaned[start:m.start()]
        # Skip if preceded by const, @, =const, enum value
        if 'const ' in prefix.split('\n')[-1]:
            continue
        count += 1
    return count


def find_private_symbols(source: str) -> Set[str]:
    """Find all private symbol definitions in source code."""
    cleaned = _strip_comments_and_strings(source)
    return set(_RE_PRIVATE_DEF.findall(cleaned))


def estimate_dead_code(
    file_path: str,
    file_private_symbols: Set[str],
    all_sources: Dict[str, str],
) -> Tuple[int, List[str]]:
    """Estimate dead code by finding private symbols used only in their defining file.

    Returns (count, list_of_potentially_dead_symbols).
    """
    dead_symbols: List[str] = []
    for symbol in file_private_symbols:
        usage_count = 0
        for path, source in all_sources.items():
            if symbol in source:
                usage_count += 1
                if usage_count > 1:
                    break
        if usage_count <= 1:
            dead_symbols.append(symbol)
    return len(dead_symbols), dead_symbols


# ---------------------------------------------------------------------------
# Unified computation
# ---------------------------------------------------------------------------

def compute_code_smells(parsed_file: ParsedFile) -> Dict[str, int]:
    """Compute all code smell metrics for a parsed file.

    Returns dict with keys:
        static_members, hardcoded_strings, magic_numbers
    """
    source = parsed_file.source
    return {
        "static_members": count_static_members(source),
        "hardcoded_strings": count_string_literals(source),
        "magic_numbers": count_magic_numbers(source),
    }


def compute_dead_code_for_module(
    parsed_files: List[ParsedFile],
) -> Dict[str, Tuple[int, List[str]]]:
    """Compute dead code estimates across all files in a module.

    Returns dict: file_path -> (dead_count, dead_symbol_list)
    """
    # Build source map
    all_sources: Dict[str, str] = {pf.path: pf.source for pf in parsed_files}

    # Find private symbols per file
    file_privates: Dict[str, Set[str]] = {}
    for pf in parsed_files:
        file_privates[pf.path] = find_private_symbols(pf.source)

    # Estimate dead code per file
    results: Dict[str, Tuple[int, List[str]]] = {}
    for pf in parsed_files:
        count, symbols = estimate_dead_code(
            pf.path, file_privates[pf.path], all_sources
        )
        results[pf.path] = (count, symbols)

    return results
