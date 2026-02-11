"""Class-level metrics: CBO, DIT, NOAM, NOII, NOM, NOOM, RFC, TCC, WOC, WMC."""

from __future__ import annotations

import re
from itertools import combinations
from typing import Dict, List, Optional, Set

from ..config import Thresholds
from ..models import ClassMetrics, ParsedClass, ParsedFile, ParsedFunction
from ..parsers.dart_parser import strip_strings_and_comments
from .function_metrics import compute_cyclomatic_complexity


# ---------------------------------------------------------------------------
# Types to ignore for CBO
# ---------------------------------------------------------------------------

_PRIMITIVE_TYPES: frozenset[str] = frozenset({
    # Dart core
    "int", "double", "num", "String", "bool", "void", "dynamic", "Never",
    "Object", "Null", "Type", "Symbol", "Enum", "Record", "Function",
    # Common containers
    "List", "Map", "Set", "Iterable", "Iterator",
    "Future", "Stream", "FutureOr",
    # Core value types
    "Duration", "DateTime", "RegExp", "Uri", "BigInt", "Pattern", "Match",
    "Comparable", "Error", "Exception", "StackTrace",
    # Flutter commonly used
    "Key", "Widget", "BuildContext", "State",
    "Color", "Size", "Offset", "Rect", "EdgeInsets",
})

# Single-letter generic type parameters — always exclude from CBO
_RE_SINGLE_LETTER_GENERIC = re.compile(r'^[A-Z]$')

# ALL_CAPS identifiers are typically constants/enum values, not types
_RE_ALL_CAPS = re.compile(r'^[A-Z][A-Z0-9_]+$')

_RE_TYPE_REFERENCE = re.compile(r"\b([A-Z][a-zA-Z0-9_]*)\b")
_RE_INVOCATION = re.compile(r"\b(\w+)\s*\(")


# ---------------------------------------------------------------------------
# Known DIT depths for common Flutter/Dart framework classes
# ---------------------------------------------------------------------------

_KNOWN_DIT: dict[str, int] = {
    # Object is the root (DIT=0)
    "Object": 0,
    # Dart core
    "Error": 1, "StateError": 2, "ArgumentError": 2, "RangeError": 3,
    "TypeError": 2, "UnsupportedError": 2, "UnimplementedError": 2,
    "FormatException": 1, "IOException": 1,
    # Flutter widgets (Widget -> DiagnosticableTree -> Diagnosticable -> Object)
    "Diagnosticable": 1, "DiagnosticableTree": 2, "Widget": 3,
    "StatelessWidget": 4, "StatefulWidget": 4,
    "InheritedWidget": 4, "InheritedModel": 5, "InheritedNotifier": 5,
    "RenderObjectWidget": 4, "LeafRenderObjectWidget": 5,
    "SingleChildRenderObjectWidget": 5, "MultiChildRenderObjectWidget": 5,
    "ProxyWidget": 4,
    # State
    "State": 1,
    # ChangeNotifier
    "ChangeNotifier": 1, "ValueNotifier": 2,
    # RenderObject chain
    "AbstractNode": 1, "RenderObject": 2, "RenderBox": 3,
    "RenderSliver": 3, "RenderProxyBox": 4,
    # Materials
    "MaterialApp": 4, "Scaffold": 4, "AppBar": 4,
    "Container": 4, "Padding": 4, "Center": 4, "Align": 4,
    "SizedBox": 4, "Row": 4, "Column": 4, "Stack": 4, "Flex": 4,
    "ListView": 4, "GridView": 4, "CustomScrollView": 4,
    # Cupertino
    "CupertinoApp": 4, "CupertinoPageScaffold": 4,
    # Animations
    "Animation": 1, "AnimationController": 2,
    "Tween": 1, "ColorTween": 2,
}


# ---------------------------------------------------------------------------
# Cross-file class index
# ---------------------------------------------------------------------------

class ClassIndex:
    """Index of all classes across files for cross-file analysis."""

    def __init__(self):
        self.classes: Dict[str, ParsedClass] = {}
        self.class_files: Dict[str, str] = {}
        self.inheritance: Dict[str, Optional[str]] = {}

    def add_file(self, parsed_file: ParsedFile):
        for cls in parsed_file.classes:
            self.classes[cls.name] = cls
            self.class_files[cls.name] = parsed_file.path
            self.inheritance[cls.name] = cls.superclass

    def get_superclass(self, class_name: str) -> Optional[ParsedClass]:
        super_name = self.inheritance.get(class_name)
        return self.classes.get(super_name) if super_name else None

    def get_dit(self, class_name: str) -> int:
        """Compute Depth of Inheritance Tree.

        Walks the inheritance chain within the codebase. For external
        classes, uses ``_KNOWN_DIT`` lookup when available; otherwise
        assumes depth = 1 for the external parent.
        """
        depth = 0
        current = class_name
        visited: set[str] = set()
        while current in self.inheritance:
            if current in visited:
                break
            visited.add(current)
            parent = self.inheritance[current]
            if parent is None:
                break
            if parent not in self.inheritance:
                # External class — try known DIT table
                if parent in _KNOWN_DIT:
                    depth += _KNOWN_DIT[parent] + 1
                else:
                    depth += 1  # at least 1 for the external parent
                break
            depth += 1
            current = parent
        return depth

    def get_superclass_methods(self, class_name: str) -> set[str]:
        methods: set[str] = set()
        current = class_name
        visited: set[str] = set()
        while current in self.inheritance:
            if current in visited:
                break
            visited.add(current)
            parent_name = self.inheritance[current]
            if parent_name and parent_name in self.classes:
                parent_cls = self.classes[parent_name]
                methods.update(m.name for m in parent_cls.methods)
                current = parent_name
            else:
                break
        return methods


def build_class_index(parsed_files: List[ParsedFile]) -> ClassIndex:
    index = ClassIndex()
    for pf in parsed_files:
        index.add_file(pf)
    return index


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_class_metrics(
    parsed_file: ParsedFile,
    module_name: str,
    thresholds: Thresholds,
    class_index: ClassIndex,
    internal_packages: Set[str],
) -> List[ClassMetrics]:
    results: List[ClassMetrics] = []

    for cls in parsed_file.classes:
        nom = len(cls.methods)
        superclass_methods = class_index.get_superclass_methods(cls.name)
        noam = sum(1 for m in cls.methods if m.name not in superclass_methods)
        noom = sum(1 for m in cls.methods if m.is_override)
        noii = len(cls.interfaces)
        dit = class_index.get_dit(cls.name)
        wmc = sum(compute_cyclomatic_complexity(m.body_text) for m in cls.methods)
        cbo = _compute_cbo(cls)
        rfc = _compute_rfc(cls)
        tcc = _compute_tcc(cls)
        woc = _compute_woc(cls)
        loc = cls.line_end - cls.line_start + 1

        results.append(ClassMetrics(
            path=parsed_file.path,
            module=module_name,
            class_name=cls.name,
            line_start=cls.line_start,
            line_end=cls.line_end,
            cbo=cbo,
            dit=dit,
            noam=noam,
            noii=noii,
            nom=nom,
            noom=noom,
            rfc=rfc,
            tcc=round(tcc, 3),
            woc=round(woc, 3),
            wmc=wmc,
            loc=loc,
        ))

    return results


# ---------------------------------------------------------------------------
# CBO — Coupling Between Object Classes
# ---------------------------------------------------------------------------

def _compute_cbo(cls: ParsedClass) -> int:
    """Count unique external types referenced by the class.

    Improvements over naive approach:
    - Strips strings and comments before scanning (no false positives from URLs etc.)
    - Filters single-letter generics (T, K, V, E, R, S)
    - Filters ALLCAPS identifiers (likely enum constants, not types)
    - Expanded primitive/built-in type exclusion list
    """
    # Strip strings AND comments to avoid catching types from string content
    cleaned = strip_strings_and_comments(cls.full_text)

    referenced_types: set[str] = set()
    for match in _RE_TYPE_REFERENCE.finditer(cleaned):
        type_name = match.group(1)
        if type_name == cls.name:
            continue
        if type_name in _PRIMITIVE_TYPES:
            continue
        if _RE_SINGLE_LETTER_GENERIC.match(type_name):
            continue
        if _RE_ALL_CAPS.match(type_name):
            continue
        referenced_types.add(type_name)

    return len(referenced_types)


# ---------------------------------------------------------------------------
# RFC — Response for a Class
# ---------------------------------------------------------------------------

_RFC_SKIP_CALLS = frozenset({
    "if", "for", "while", "switch", "catch", "return",
    "throw", "assert", "print", "super", "this",
    "true", "false", "null",
})

def _compute_rfc(cls: ParsedClass) -> int:
    own_methods = {m.name for m in cls.methods}
    external_calls: set[str] = set()

    for method in cls.methods:
        body = strip_strings_and_comments(method.body_text)
        for match in _RE_INVOCATION.finditer(body):
            call_name = match.group(1)
            if call_name in _RFC_SKIP_CALLS:
                continue
            if call_name not in own_methods:
                external_calls.add(call_name)

    return len(own_methods) + len(external_calls)


# ---------------------------------------------------------------------------
# TCC — Tight Class Cohesion
# ---------------------------------------------------------------------------

def _compute_tcc(cls: ParsedClass) -> float:
    """TCC = connected pairs / total pairs.

    Includes regular methods, getters and setters in the analysis
    (getters/setters access fields and contribute to cohesion).
    Only excludes static methods and constructors.
    """
    if len(cls.methods) < 2:
        return 1.0

    # Determine all instance fields
    class_fields = set(cls.fields) if cls.fields else set()

    # Augment from this.x and _x patterns if parser missed some
    if not class_fields:
        for m in cls.methods:
            if m.body_text:
                for match in re.finditer(r"\bthis\.(\w+)", m.body_text):
                    class_fields.add(match.group(1))
                for match in re.finditer(r"\b(_[a-z]\w*)\b", m.body_text):
                    name = match.group(1)
                    # Exclude private method calls: _method(
                    if not re.search(r'\b' + re.escape(name) + r'\s*\(', m.body_text):
                        class_fields.add(name)

    if not class_fields:
        return 0.0

    # Instance methods (non-static) — include getters and setters
    instance_methods = [
        m for m in cls.methods
        if not m.is_static
    ]

    if len(instance_methods) < 2:
        return 1.0

    # For each method, find which fields it accesses
    method_fields: list[set[str]] = []
    for method in instance_methods:
        body = method.body_text or ''
        used: set[str] = set()
        for f in class_fields:
            if re.search(r'\b' + re.escape(f) + r'\b', body):
                used.add(f)
        # Getters/setters implicitly access their backing field
        if method.is_getter or method.is_setter:
            backing = '_' + method.name
            if backing in class_fields:
                used.add(backing)
            if method.name in class_fields:
                used.add(method.name)
        method_fields.append(used)

    total_pairs = 0
    connected_pairs = 0
    for i, j in combinations(range(len(method_fields)), 2):
        total_pairs += 1
        if method_fields[i] & method_fields[j]:
            connected_pairs += 1

    return connected_pairs / total_pairs if total_pairs > 0 else 0.0


# ---------------------------------------------------------------------------
# WOC — Weight of a Class
# ---------------------------------------------------------------------------

def _compute_woc(cls: ParsedClass) -> float:
    """WOC = public functional methods / all public members."""
    public_functional = sum(
        1 for m in cls.methods
        if not m.name.startswith('_') and not m.is_getter and not m.is_setter
    )
    public_fields_count = len(cls.public_fields) if cls.public_fields else 0
    public_accessors = sum(
        1 for m in cls.methods
        if not m.name.startswith('_') and (m.is_getter or m.is_setter)
    )

    total_public = public_functional + public_fields_count + public_accessors
    if total_public == 0:
        return 0.0

    return public_functional / total_public
