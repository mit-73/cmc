"""Code duplication detection using token-based rolling hash.

Tokenizes Dart source code, then uses a rolling hash (Rabin-Karp style)
to find duplicated blocks of tokens across files. Reports duplicate
pairs with their locations and token counts.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from ..models import ParsedFile


# Minimum number of tokens for a block to be considered a duplicate
MIN_TOKENS = 50
# Minimum number of lines for a block to be considered a duplicate
MIN_LINES = 6


@dataclass
class DuplicateBlock:
    """A single occurrence of a duplicated code block."""
    path: str
    line_start: int
    line_end: int
    token_count: int

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "token_count": self.token_count,
        }


@dataclass
class DuplicatePair:
    """A pair of duplicate blocks."""
    block_a: DuplicateBlock
    block_b: DuplicateBlock
    token_count: int
    line_count: int

    def to_dict(self) -> dict:
        return {
            "block_a": self.block_a.to_dict(),
            "block_b": self.block_b.to_dict(),
            "token_count": self.token_count,
            "line_count": self.line_count,
        }


@dataclass
class DuplicationResult:
    """Complete duplication analysis result."""
    total_files: int = 0
    total_tokens: int = 0
    duplicated_tokens: int = 0
    duplication_pct: float = 0.0
    duplicate_pairs: List[DuplicatePair] = field(default_factory=list)
    per_file: Dict[str, float] = field(default_factory=dict)  # path -> dup %

    def to_dict(self) -> dict:
        return {
            "total_files": self.total_files,
            "total_tokens": self.total_tokens,
            "duplicated_tokens": self.duplicated_tokens,
            "duplication_pct": round(self.duplication_pct, 2),
            "duplicate_pairs_count": len(self.duplicate_pairs),
            "duplicate_pairs": [p.to_dict() for p in self.duplicate_pairs[:100]],
            "files_with_duplicates": len(self.per_file),
        }


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

# Simple Dart tokenizer — splits on whitespace, punctuation, operators
_TOKEN_RE = re.compile(
    r"""
    (?:'[^']*')                    |  # single-quoted strings
    (?:"[^"]*")                    |  # double-quoted strings
    (?:///.*$)                     |  # doc comments
    (?://.*$)                      |  # line comments
    (?:/\*[\s\S]*?\*/)             |  # block comments
    (?:\d+\.?\d*(?:e[+-]?\d+)?)   |  # numbers
    (?:[a-zA-Z_$]\w*)              |  # identifiers
    (?:[+\-*/~%^&|<>=!?.]+)       |  # operators
    (?:[{}()\[\];,:@#])               # punctuation
    """,
    re.VERBOSE | re.MULTILINE,
)


@dataclass
class _Token:
    """A simple token with its line number."""
    value: str
    line: int


def _tokenize(source: str) -> List[_Token]:
    """Tokenize Dart source code.

    Strips comments and string literals (normalizes them to placeholders)
    to detect structural duplication regardless of naming.
    """
    tokens: List[_Token] = []
    for match in _TOKEN_RE.finditer(source):
        text = match.group(0)
        # Compute line number
        line = source[:match.start()].count("\n") + 1

        # Normalize: skip comments
        if text.startswith("//") or text.startswith("/*"):
            continue
        # Normalize strings to placeholder
        if (text.startswith("'") and text.endswith("'")) or \
           (text.startswith('"') and text.endswith('"')):
            tokens.append(_Token("$STR", line))
            continue
        # Normalize numbers to placeholder
        if text[0].isdigit():
            tokens.append(_Token("$NUM", line))
            continue
        # Normalize identifiers to placeholder (keep keywords)
        if text[0].isalpha() or text[0] == '_':
            if text in _DART_KEYWORDS:
                tokens.append(_Token(text, line))
            else:
                tokens.append(_Token("$ID", line))
            continue
        tokens.append(_Token(text, line))

    return tokens


_DART_KEYWORDS = frozenset({
    "abstract", "as", "assert", "async", "await", "break", "case", "catch",
    "class", "const", "continue", "covariant", "default", "deferred", "do",
    "dynamic", "else", "enum", "export", "extends", "extension", "external",
    "factory", "false", "final", "finally", "for", "Function", "get", "hide",
    "if", "implements", "import", "in", "interface", "is", "late", "library",
    "mixin", "new", "null", "on", "operator", "part", "required", "rethrow",
    "return", "sealed", "set", "show", "static", "super", "switch", "sync",
    "this", "throw", "true", "try", "typedef", "var", "void", "while",
    "with", "yield",
    # Types
    "int", "double", "String", "bool", "List", "Map", "Set", "Future",
    "Stream", "Iterable", "Object", "dynamic", "Never", "void",
})


# ---------------------------------------------------------------------------
# Duplication detection via rolling hash
# ---------------------------------------------------------------------------

def _token_hash(tokens: List[str], start: int, length: int) -> str:
    """Compute a hash for a token subsequence."""
    seq = " ".join(tokens[start:start + length])
    return hashlib.md5(seq.encode(), usedforsecurity=False).hexdigest()


def detect_duplicates(
    parsed_files: List[ParsedFile],
    min_tokens: int = MIN_TOKENS,
    min_lines: int = MIN_LINES,
) -> DuplicationResult:
    """Detect code duplicates across files using token-based comparison.

    Args:
        parsed_files: List of parsed Dart files.
        min_tokens: Minimum tokens for a duplicate block.
        min_lines: Minimum lines for a duplicate block.

    Returns:
        DuplicationResult with pairs and statistics.
    """
    result = DuplicationResult(total_files=len(parsed_files))

    # Tokenize all files
    file_tokens: List[Tuple[str, List[_Token]]] = []
    for pf in parsed_files:
        tokens = _tokenize(pf.source)
        if tokens:
            file_tokens.append((pf.path, tokens))
            result.total_tokens += len(tokens)

    if not file_tokens:
        return result

    # Build hash index: hash -> [(file_path, token_start_idx, line_start, line_end)]
    hash_index: Dict[str, List[Tuple[str, int, int, int]]] = defaultdict(list)

    for path, tokens in file_tokens:
        token_values = [t.value for t in tokens]
        n = len(token_values)
        if n < min_tokens:
            continue

        # Slide window of min_tokens size
        for i in range(n - min_tokens + 1):
            h = _token_hash(token_values, i, min_tokens)
            line_start = tokens[i].line
            line_end = tokens[min(i + min_tokens - 1, n - 1)].line
            # Only add if the block spans enough lines
            if line_end - line_start + 1 >= min_lines:
                hash_index[h].append((path, i, line_start, line_end))

    # Find duplicate pairs
    seen_pairs: Set[Tuple[str, int, str, int]] = set()
    duplicated_file_tokens: Dict[str, Set[int]] = defaultdict(set)

    for h, occurrences in hash_index.items():
        if len(occurrences) < 2:
            continue

        # Group by file to avoid self-overlapping matches as much as possible
        for i in range(len(occurrences)):
            for j in range(i + 1, len(occurrences)):
                path_a, idx_a, line_a_start, line_a_end = occurrences[i]
                path_b, idx_b, line_b_start, line_b_end = occurrences[j]

                # Skip if same file and overlapping
                if path_a == path_b and abs(idx_a - idx_b) < min_tokens:
                    continue

                # Deduplicate
                pair_key = (path_a, idx_a, path_b, idx_b)
                reverse_key = (path_b, idx_b, path_a, idx_a)
                if pair_key in seen_pairs or reverse_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                line_count = max(
                    line_a_end - line_a_start + 1,
                    line_b_end - line_b_start + 1,
                )

                result.duplicate_pairs.append(DuplicatePair(
                    block_a=DuplicateBlock(
                        path=path_a,
                        line_start=line_a_start,
                        line_end=line_a_end,
                        token_count=min_tokens,
                    ),
                    block_b=DuplicateBlock(
                        path=path_b,
                        line_start=line_b_start,
                        line_end=line_b_end,
                        token_count=min_tokens,
                    ),
                    token_count=min_tokens,
                    line_count=line_count,
                ))

                # Track duplicated tokens per file
                for k in range(min_tokens):
                    duplicated_file_tokens[path_a].add(idx_a + k)
                    duplicated_file_tokens[path_b].add(idx_b + k)

                # Limit pairs to prevent memory explosion
                if len(result.duplicate_pairs) >= 500:
                    break
            if len(result.duplicate_pairs) >= 500:
                break
        if len(result.duplicate_pairs) >= 500:
            break

    # Sort pairs by token count (desc) then by path
    result.duplicate_pairs.sort(
        key=lambda p: (-p.token_count, p.block_a.path, p.block_a.line_start)
    )

    # Compute per-file duplication percentage
    file_token_counts = {path: len(tokens) for path, tokens in file_tokens}
    for path, dup_indices in duplicated_file_tokens.items():
        total = file_token_counts.get(path, 1)
        result.per_file[path] = round(len(dup_indices) / total * 100, 2)

    # Overall duplication
    total_dup = sum(len(indices) for indices in duplicated_file_tokens.values())
    result.duplicated_tokens = total_dup
    if result.total_tokens > 0:
        result.duplication_pct = total_dup / result.total_tokens * 100

    return result
