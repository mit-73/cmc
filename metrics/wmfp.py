"""Weighted Micro Function Points (WMFP) computation.

WMFP is a size/complexity metric that estimates the effort required
to create and maintain code by decomposing source into micro-components
and weighting them.

Formula:
    WMFP_f = W_FC * CC
           + W_OV * ln(1 + HalsteadVocab)
           + W_OC * ln(1 + HalsteadLength)
           + W_AI * ArithOps
           + W_DT * (Params + Assigns)
           + W_CS * MNL * (LOC / SLOC)
           + W_ID * InlineData
           + W_CM * CommentLines
"""

from __future__ import annotations

import math
import re

from ..config import WMFPWeights
from ..parsers.dart_parser import strip_strings_and_comments


# Arithmetic operators in Dart
_RE_ARITH_OPS = re.compile(r'(?<![/])[+\-*/%]|~/')

# Assignment operators (=, but not ==, !=, <=, >=, =>)
_RE_ASSIGNMENTS = re.compile(r'(?<![=!<>])=(?!=|>)')


def count_arithmetic_ops(body: str) -> int:
    """Count arithmetic operators in function body."""
    if not body:
        return 0
    cleaned = strip_strings_and_comments(body)
    return len(_RE_ARITH_OPS.findall(cleaned))


def count_assignments(body: str) -> int:
    """Count assignment operations in function body."""
    if not body:
        return 0
    cleaned = strip_strings_and_comments(body)
    return len(_RE_ASSIGNMENTS.findall(cleaned))


def compute_wmfp(
    cyclo: int,
    halstead_vocab: int,
    halstead_length: int,
    arith_ops: int,
    num_params: int,
    assignments: int,
    max_nesting: int,
    loc: int,
    sloc: int,
    inline_data: int = 0,
    comment_lines: int = 0,
    weights: WMFPWeights | None = None,
) -> float:
    """Compute WMFP for a single function.

    Args:
        cyclo: Cyclomatic complexity
        halstead_vocab: eta1 + eta2 (unique operators + operands)
        halstead_length: n1 + n2 (total operators + operands)
        arith_ops: Count of arithmetic operators in body
        num_params: Number of function parameters
        assignments: Count of assignment operations in body
        max_nesting: Maximum nesting level
        loc: Lines of code
        sloc: Source lines of code
        inline_data: magic_numbers + hardcoded_strings (optional, file-level)
        comment_lines: LOC - SLOC
        weights: WMFP weight configuration

    Returns:
        WMFP value (float >= 0)
    """
    if weights is None:
        weights = WMFPWeights()

    loc_sloc_ratio = loc / sloc if sloc > 0 else 1.0

    wmfp = (
        weights.flow_complexity * cyclo
        + weights.object_vocabulary * math.log(1 + halstead_vocab)
        + weights.object_conjuration * math.log(1 + halstead_length)
        + weights.arithmetic_intricacy * arith_ops
        + weights.data_transfer * (num_params + assignments)
        + weights.code_structure * max_nesting * loc_sloc_ratio
        + weights.inline_data * inline_data
        + weights.comments * comment_lines
    )

    return round(wmfp, 2)
