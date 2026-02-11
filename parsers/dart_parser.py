"""Dart source parser with a state-machine tokenizer for accurate
string / comment / interpolation handling, plus regex-based AST extraction.

Optionally uses tree-sitter when available for higher accuracy.
"""

from __future__ import annotations

import re
from enum import Enum, auto
from functools import lru_cache
from typing import List, Optional, Tuple

from ..models import ParsedClass, ParsedFile, ParsedFunction, ParsedImport

# ---------------------------------------------------------------------------
# Try to load tree-sitter
# ---------------------------------------------------------------------------
_TREE_SITTER_AVAILABLE = False
_DART_LANGUAGE = None

try:
    import tree_sitter_dart as tsdart
    from tree_sitter import Language, Parser as TSParser

    _DART_LANGUAGE = Language(tsdart.language())
    _TREE_SITTER_AVAILABLE = True
except ImportError:
    pass


# =====================================================================
# STATE-MACHINE TOKENIZER
# =====================================================================

class _TokState(Enum):
    CODE = auto()
    LINE_COMMENT = auto()
    BLOCK_COMMENT = auto()
    STRING_SQ = auto()        # single-quoted  '...'
    STRING_DQ = auto()        # double-quoted  "..."
    STRING_TSQ = auto()       # triple single  '''...'''
    STRING_TDQ = auto()       # triple double  """..."""
    RAW_SQ = auto()
    RAW_DQ = auto()
    RAW_TSQ = auto()
    RAW_TDQ = auto()


def _is_escaped(src: str, pos: int) -> bool:
    n = 0
    p = pos - 1
    while p >= 0 and src[p] == '\\':
        n += 1
        p -= 1
    return n % 2 == 1


# --------------- generic state-machine walker ---------------

def _walk_source(
    source: str,
    *,
    on_code: object = None,
    on_comment: object = None,
    on_string: object = None,
    keep_newlines_in_comments: bool = True,
) -> str:
    """Walk *source* through a state machine; for every character call the
    appropriate callback (or drop it) to build a new string.

    Each callback is ``(char, state) -> str | None``.  If *None* the char is
    kept as-is.  If a callback is not given the char is kept.
    """
    result: list[str] = []
    i = 0
    n = len(source)
    state = _TokState.CODE
    # stack of brace-depths for ${} interpolation
    interp_stack: list[int] = []
    # the string state to return to after interpolation finishes
    interp_return_state: list[_TokState] = []

    def _emit_code(ch: str):
        if on_code is not None:
            r = on_code(ch, state)
            if r is not None:
                result.append(r)
                return
        result.append(ch)

    def _emit_comment(ch: str):
        if on_comment is not None:
            r = on_comment(ch, state)
            if r is not None:
                result.append(r)
                return
        result.append(ch)

    def _emit_string(ch: str):
        if on_string is not None:
            r = on_string(ch, state)
            if r is not None:
                result.append(r)
                return
        result.append(ch)

    while i < n:
        c = source[i]

        # --- interpolation brace tracking (we are in CODE inside ${...}) ---
        if interp_stack and state == _TokState.CODE:
            if c == '{':
                interp_stack[-1] += 1
                _emit_code(c); i += 1; continue
            elif c == '}':
                interp_stack[-1] -= 1
                if interp_stack[-1] == 0:
                    interp_stack.pop()
                    state = interp_return_state.pop()
                    _emit_string(c); i += 1; continue
                _emit_code(c); i += 1; continue

        # ============ CODE ============
        if state == _TokState.CODE:
            # line comment
            if c == '/' and i + 1 < n and source[i + 1] == '/':
                state = _TokState.LINE_COMMENT; i += 2; continue
            # block comment
            if c == '/' and i + 1 < n and source[i + 1] == '*':
                state = _TokState.BLOCK_COMMENT; i += 2; continue
            # raw strings
            if c == 'r' and i + 1 < n and source[i + 1] in ('"', "'"):
                q = source[i + 1]
                if i + 3 < n and source[i+1:i+4] == q * 3:
                    state = _TokState.RAW_TSQ if q == "'" else _TokState.RAW_TDQ
                    _emit_string(source[i:i+4]); i += 4; continue
                state = _TokState.RAW_SQ if q == "'" else _TokState.RAW_DQ
                _emit_string(source[i:i+2]); i += 2; continue
            # triple-quoted strings
            if c in ('"', "'") and i + 2 < n and source[i:i+3] == c * 3:
                state = _TokState.STRING_TSQ if c == "'" else _TokState.STRING_TDQ
                _emit_string(c * 3); i += 3; continue
            # simple strings
            if c in ('"', "'"):
                state = _TokState.STRING_SQ if c == "'" else _TokState.STRING_DQ
                _emit_string(c); i += 1; continue
            _emit_code(c); i += 1; continue

        # ============ LINE COMMENT ============
        if state == _TokState.LINE_COMMENT:
            if c == '\n':
                state = _TokState.CODE
                if keep_newlines_in_comments:
                    _emit_comment('\n')
            else:
                _emit_comment(c)
            i += 1; continue

        # ============ BLOCK COMMENT ============
        if state == _TokState.BLOCK_COMMENT:
            if c == '*' and i + 1 < n and source[i + 1] == '/':
                state = _TokState.CODE; i += 2; continue
            if c == '\n' and keep_newlines_in_comments:
                _emit_comment('\n')
            else:
                _emit_comment(c)
            i += 1; continue

        # ============ RAW STRINGS (no escape, no interpolation) ============
        if state == _TokState.RAW_TSQ:
            if source[i:i+3] == "'''":
                _emit_string("'''"); state = _TokState.CODE; i += 3; continue
            _emit_string(c); i += 1; continue
        if state == _TokState.RAW_TDQ:
            if source[i:i+3] == '"""':
                _emit_string('"""'); state = _TokState.CODE; i += 3; continue
            _emit_string(c); i += 1; continue
        if state == _TokState.RAW_SQ:
            if c == "'":
                _emit_string(c); state = _TokState.CODE
            else:
                _emit_string(c)
            i += 1; continue
        if state == _TokState.RAW_DQ:
            if c == '"':
                _emit_string(c); state = _TokState.CODE
            else:
                _emit_string(c)
            i += 1; continue

        # ============ REGULAR STRINGS (escape + interpolation) ============
        # triple-quoted
        if state in (_TokState.STRING_TSQ, _TokState.STRING_TDQ):
            end_q = "'''" if state == _TokState.STRING_TSQ else '"""'
            if source[i:i+3] == end_q and not _is_escaped(source, i):
                _emit_string(end_q); state = _TokState.CODE; i += 3; continue
            if c == '$' and i + 1 < n and source[i + 1] == '{' and not _is_escaped(source, i):
                interp_stack.append(1)
                interp_return_state.append(state)
                _emit_string('${'); state = _TokState.CODE; i += 2; continue
            _emit_string(c); i += 1; continue

        # single-char quoted
        if state == _TokState.STRING_SQ:
            if c == "'" and not _is_escaped(source, i):
                _emit_string(c); state = _TokState.CODE; i += 1; continue
            if c == '$' and i + 1 < n and source[i + 1] == '{' and not _is_escaped(source, i):
                interp_stack.append(1)
                interp_return_state.append(state)
                _emit_string('${'); state = _TokState.CODE; i += 2; continue
            _emit_string(c); i += 1; continue

        if state == _TokState.STRING_DQ:
            if c == '"' and not _is_escaped(source, i):
                _emit_string(c); state = _TokState.CODE; i += 1; continue
            if c == '$' and i + 1 < n and source[i + 1] == '{' and not _is_escaped(source, i):
                interp_stack.append(1)
                interp_return_state.append(state)
                _emit_string('${'); state = _TokState.CODE; i += 2; continue
            _emit_string(c); i += 1; continue

        # fallback — should not happen
        result.append(c); i += 1

    return ''.join(result)


# --------------- public helpers built on the walker ---------------

@lru_cache(maxsize=4096)
def strip_comments(source: str) -> str:
    """Remove comments, preserving strings and newlines."""
    return _walk_source(
        source,
        on_comment=lambda ch, _st: '\n' if ch == '\n' else '',
    )


@lru_cache(maxsize=4096)
def strip_strings_and_comments(source: str) -> str:
    """Remove comments AND string contents — fast inline implementation.

    Preserves newlines so line numbers stay correct.
    Avoids the generic _walk_source callback overhead.
    """
    result: list[str] = []
    i = 0
    n = len(source)
    state = 0  # 0=CODE, 1=LINECOMMENT, 2=BLOCKCOMMENT, 3+ = string states
    # string states: 3=SQ, 4=DQ, 5=TSQ, 6=TDQ, 7=RSQ, 8=RDQ, 9=RTSQ, 10=RTDQ
    interp_stack: list[int] = []
    interp_ret: list[int] = []

    while i < n:
        c = source[i]

        # interpolation tracking
        if interp_stack and state == 0:
            if c == '{':
                interp_stack[-1] += 1; i += 1; continue
            if c == '}':
                interp_stack[-1] -= 1
                if interp_stack[-1] == 0:
                    interp_stack.pop()
                    state = interp_ret.pop()
                    i += 1; continue
                i += 1; continue

        if state == 0:  # CODE
            if c == '/' and i + 1 < n:
                c2 = source[i + 1]
                if c2 == '/':
                    state = 1; i += 2; continue
                if c2 == '*':
                    state = 2; i += 2; continue
            if c == 'r' and i + 1 < n and source[i + 1] in ("'", '"'):
                q = source[i + 1]
                if i + 3 < n and source[i + 1:i + 4] == q * 3:
                    state = 9 if q == "'" else 10; i += 4; continue
                state = 7 if q == "'" else 8; i += 2; continue
            if c in ("'", '"'):
                if i + 2 < n and source[i:i + 3] == c * 3:
                    state = 5 if c == "'" else 6; i += 3; continue
                state = 3 if c == "'" else 4; i += 1; continue
            result.append(c); i += 1; continue

        if state == 1:  # LINE COMMENT
            if c == '\n':
                state = 0; result.append('\n')
            i += 1; continue

        if state == 2:  # BLOCK COMMENT
            if c == '*' and i + 1 < n and source[i + 1] == '/':
                state = 0; i += 2; continue
            if c == '\n':
                result.append('\n')
            i += 1; continue

        # RAW strings — no escape, no interpolation
        if state == 9:  # RAW_TSQ
            if source[i:i + 3] == "'''":
                state = 0; i += 3; continue
            i += 1; continue
        if state == 10:  # RAW_TDQ
            if source[i:i + 3] == '"""':
                state = 0; i += 3; continue
            i += 1; continue
        if state == 7:  # RAW_SQ
            if c == "'":
                state = 0
            i += 1; continue
        if state == 8:  # RAW_DQ
            if c == '"':
                state = 0
            i += 1; continue

        # Regular strings: check for end-quote and interpolation
        if state == 5:  # TSQ '''
            if source[i:i + 3] == "'''" and not _is_escaped(source, i):
                state = 0; i += 3; continue
            if c == '$' and i + 1 < n and source[i + 1] == '{' and not _is_escaped(source, i):
                interp_stack.append(1); interp_ret.append(state)
                state = 0; i += 2; continue
            i += 1; continue
        if state == 6:  # TDQ """
            if source[i:i + 3] == '"""' and not _is_escaped(source, i):
                state = 0; i += 3; continue
            if c == '$' and i + 1 < n and source[i + 1] == '{' and not _is_escaped(source, i):
                interp_stack.append(1); interp_ret.append(state)
                state = 0; i += 2; continue
            i += 1; continue
        if state == 3:  # SQ '
            if c == "'" and not _is_escaped(source, i):
                state = 0; i += 1; continue
            if c == '$' and i + 1 < n and source[i + 1] == '{' and not _is_escaped(source, i):
                interp_stack.append(1); interp_ret.append(state)
                state = 0; i += 2; continue
            i += 1; continue
        if state == 4:  # DQ "
            if c == '"' and not _is_escaped(source, i):
                state = 0; i += 1; continue
            if c == '$' and i + 1 < n and source[i + 1] == '{' and not _is_escaped(source, i):
                interp_stack.append(1); interp_ret.append(state)
                state = 0; i += 2; continue
            i += 1; continue

        i += 1

    return ''.join(result)


# =====================================================================
# SLOC counting
# =====================================================================

def _count_sloc(source: str) -> int:
    cleaned = strip_strings_and_comments(source)
    return sum(1 for line in cleaned.splitlines() if line.strip())


# =====================================================================
# BRACE MATCHING
# =====================================================================

def _find_brace_block(source: str, start: int) -> Tuple[str, int]:
    """Find matching ``}`` for ``{`` at *start*.

    Returns ``(body_between_braces, position_after_close_brace)``.
    Handles strings, comments, ``${}`` interpolation correctly.
    """
    if start >= len(source) or source[start] != '{':
        return '', start

    depth = 0
    i = start
    n = len(source)
    state = _TokState.CODE
    interp_stack: list[int] = []
    interp_return: list[_TokState] = []

    while i < n:
        c = source[i]

        # interpolation tracking
        if interp_stack and state == _TokState.CODE:
            if c == '{':
                interp_stack[-1] += 1; i += 1; continue
            if c == '}':
                interp_stack[-1] -= 1
                if interp_stack[-1] == 0:
                    interp_stack.pop()
                    state = interp_return.pop()
                    i += 1; continue
                i += 1; continue

        if state == _TokState.CODE:
            if c == '/' and i + 1 < n:
                if source[i+1] == '/':
                    state = _TokState.LINE_COMMENT; i += 2; continue
                if source[i+1] == '*':
                    state = _TokState.BLOCK_COMMENT; i += 2; continue
            if c == 'r' and i + 1 < n and source[i+1] in ('"', "'"):
                q = source[i+1]
                if i + 3 < n and source[i+1:i+4] == q * 3:
                    state = _TokState.RAW_TSQ if q == "'" else _TokState.RAW_TDQ; i += 4; continue
                state = _TokState.RAW_SQ if q == "'" else _TokState.RAW_DQ; i += 2; continue
            if c in ('"', "'") and i + 2 < n and source[i:i+3] == c * 3:
                state = _TokState.STRING_TSQ if c == "'" else _TokState.STRING_TDQ; i += 3; continue
            if c in ('"', "'"):
                state = _TokState.STRING_SQ if c == "'" else _TokState.STRING_DQ; i += 1; continue
            if c == '{':
                depth += 1; i += 1; continue
            if c == '}':
                depth -= 1
                if depth == 0:
                    return source[start + 1:i], i + 1
                i += 1; continue
            i += 1; continue

        if state == _TokState.LINE_COMMENT:
            if c == '\n': state = _TokState.CODE
            i += 1; continue

        if state == _TokState.BLOCK_COMMENT:
            if c == '*' and i + 1 < n and source[i+1] == '/':
                state = _TokState.CODE; i += 2; continue
            i += 1; continue

        if state == _TokState.RAW_TSQ:
            if source[i:i+3] == "'''": state = _TokState.CODE; i += 3; continue
            i += 1; continue
        if state == _TokState.RAW_TDQ:
            if source[i:i+3] == '"""': state = _TokState.CODE; i += 3; continue
            i += 1; continue
        if state == _TokState.RAW_SQ:
            if c == "'": state = _TokState.CODE
            i += 1; continue
        if state == _TokState.RAW_DQ:
            if c == '"': state = _TokState.CODE
            i += 1; continue

        if state in (_TokState.STRING_TSQ, _TokState.STRING_TDQ):
            end_q = "'''" if state == _TokState.STRING_TSQ else '"""'
            if source[i:i+3] == end_q and not _is_escaped(source, i):
                state = _TokState.CODE; i += 3; continue
            if c == '$' and i + 1 < n and source[i+1] == '{' and not _is_escaped(source, i):
                interp_stack.append(1); interp_return.append(state)
                state = _TokState.CODE; i += 2; continue
            i += 1; continue

        if state == _TokState.STRING_SQ:
            if c == "'" and not _is_escaped(source, i):
                state = _TokState.CODE; i += 1; continue
            if c == '$' and i + 1 < n and source[i+1] == '{' and not _is_escaped(source, i):
                interp_stack.append(1); interp_return.append(state)
                state = _TokState.CODE; i += 2; continue
            i += 1; continue

        if state == _TokState.STRING_DQ:
            if c == '"' and not _is_escaped(source, i):
                state = _TokState.CODE; i += 1; continue
            if c == '$' and i + 1 < n and source[i+1] == '{' and not _is_escaped(source, i):
                interp_stack.append(1); interp_return.append(state)
                state = _TokState.CODE; i += 2; continue
            i += 1; continue

        i += 1

    return source[start + 1:], len(source)


# =====================================================================
# PUBLIC INTERFACE
# =====================================================================

def parse_file(path: str, source: Optional[str] = None) -> ParsedFile:
    if source is None:
        with open(path, 'r', encoding='utf-8') as fh:
            source = fh.read()

    loc = len(source.splitlines())
    sloc = _count_sloc(source)

    if _TREE_SITTER_AVAILABLE:
        return _parse_with_tree_sitter(path, source, loc, sloc)
    return _parse_with_regex(path, source, loc, sloc)


def is_tree_sitter_available() -> bool:
    return _TREE_SITTER_AVAILABLE


# =====================================================================
# TREE-SITTER PARSER
# =====================================================================

def _parse_with_tree_sitter(path: str, source: str, loc: int, sloc: int) -> ParsedFile:
    parser = TSParser(_DART_LANGUAGE)
    tree = parser.parse(source.encode('utf-8'))
    root = tree.root_node

    imports = _ts_extract_imports(root, source)
    classes = _ts_extract_classes(root, source)
    top_fns = _ts_extract_top_level_functions(root, source)

    return ParsedFile(path=path, source=source, classes=classes,
                      top_level_functions=top_fns, imports=imports,
                      loc=loc, sloc=sloc)


def _ts_extract_imports(root, source: str) -> List[ParsedImport]:
    out: list[ParsedImport] = []
    for node in root.children:
        if node.type == 'import_or_export':
            text = _node_text(node, source)
            uri = _extract_import_uri(text)
            if uri:
                out.append(_classify_import(uri))
    return out


def _ts_extract_classes(root, source: str) -> List[ParsedClass]:
    out: list[ParsedClass] = []
    for node in root.children:
        if node.type == 'class_definition':
            cls = _ts_parse_class(node, source)
            if cls:
                out.append(cls)
    return out


def _ts_extract_top_level_functions(root, source: str) -> List[ParsedFunction]:
    out: list[ParsedFunction] = []
    for node in root.children:
        if node.type in ('function_signature', 'function_definition',
                         'method_signature', 'getter_signature', 'setter_signature'):
            fn = _ts_parse_function(node, source, class_name=None)
            if fn:
                out.append(fn)
    return out


def _ts_parse_class(node, source: str) -> Optional[ParsedClass]:
    name = superclass = None
    interfaces: list[str] = []
    mixins: list[str] = []
    is_abstract = False
    text = _node_text(node, source)
    if text.startswith('abstract'):
        is_abstract = True

    methods: list[ParsedFunction] = []
    fields: list[str] = []
    pub_m: list[ParsedFunction] = []
    pub_f: list[str] = []

    for child in node.children:
        if child.type == 'identifier' and name is None:
            name = _node_text(child, source)
        elif child.type == 'superclass':
            for sub in child.children:
                if sub.type == 'type_identifier':
                    superclass = _node_text(sub, source); break
        elif child.type == 'interfaces':
            for sub in _walk_tree(child):
                if sub.type == 'type_identifier':
                    interfaces.append(_node_text(sub, source))
        elif child.type == 'mixins':
            for sub in _walk_tree(child):
                if sub.type == 'type_identifier':
                    mixins.append(_node_text(sub, source))
        elif child.type == 'class_body':
            methods, fields, pub_m, pub_f = _ts_parse_class_body(child, source, name or '')

    if name is None:
        return None

    return ParsedClass(
        name=name, line_start=node.start_point[0] + 1, line_end=node.end_point[0] + 1,
        full_text=text, superclass=superclass, interfaces=interfaces, mixins=mixins,
        methods=methods, fields=fields, public_methods=pub_m, public_fields=pub_f,
        is_abstract=is_abstract)


def _ts_parse_class_body(node, source: str, class_name: str):
    methods: list[ParsedFunction] = []
    fields: list[str] = []
    pub_m: list[ParsedFunction] = []
    pub_f: list[str] = []
    for child in node.children:
        if child.type in ('method_signature', 'function_definition',
                          'getter_signature', 'setter_signature', 'function_signature'):
            fn = _ts_parse_function(child, source, class_name=class_name)
            if fn:
                methods.append(fn)
                if not fn.name.startswith('_'):
                    pub_m.append(fn)
        elif child.type in ('declaration', 'initialized_variable_definition',
                            'variable_declaration', 'final_builtin'):
            _ts_extract_fields(child, source, fields, pub_f)
    return methods, fields, pub_m, pub_f


def _ts_extract_fields(node, source: str, fields: list, pub_f: list):
    for sub in _walk_tree(node):
        if sub.type == 'identifier':
            name = _node_text(sub, source)
            if name and (name[0].islower() or name.startswith('_')):
                fields.append(name)
                if not name.startswith('_'):
                    pub_f.append(name)
            break


def _ts_parse_function(node, source: str, class_name: Optional[str]) -> Optional[ParsedFunction]:
    name = None
    parameters: list[str] = []
    is_override = is_static = is_getter = is_setter = False
    text = _node_text(node, source)

    prev = node.prev_named_sibling
    while prev:
        pt = _node_text(prev, source)
        if pt.strip().startswith('@override'):
            is_override = True
        if pt.strip().startswith('@'):
            prev = prev.prev_named_sibling; continue
        break

    sig = text.split('{')[0] if '{' in text else text
    if '@override' in sig:
        is_override = True
    if 'static ' in (sig.split('(')[0] if '(' in sig else ''):
        is_static = True
    if node.type == 'getter_signature':
        is_getter = True
    elif node.type == 'setter_signature':
        is_setter = True

    for child in node.children:
        if child.type == 'identifier' and name is None:
            name = _node_text(child, source)
        elif child.type == 'formal_parameter_list':
            parameters = _ts_extract_parameters(child, source)

    if name is None:
        m = re.search(r'(\w+)\s*[(<]', text)
        if m:
            name = m.group(1)
    if name is None:
        return None

    body_text = ''
    for child in _walk_tree(node):
        if child.type in ('block', 'function_body'):
            body_text = _node_text(child, source); break
    if not body_text and '=>' in text:
        idx = text.index('=>')
        body_text = text[idx:]

    return ParsedFunction(
        name=name, class_name=class_name,
        line_start=node.start_point[0] + 1, line_end=node.end_point[0] + 1,
        body_text=body_text, full_text=text, parameters=parameters,
        is_override=is_override, is_static=is_static,
        is_getter=is_getter, is_setter=is_setter)


def _ts_extract_parameters(node, source: str) -> list:
    params: list[str] = []
    for child in _walk_tree(node):
        if child.type in ('formal_parameter', 'simple_formal_parameter',
                          'default_formal_parameter', 'field_formal_parameter',
                          'function_typed_formal_parameter'):
            params.append(_node_text(child, source))
    return params


def _walk_tree(node):
    for child in node.children:
        yield child
        yield from _walk_tree(child)


def _node_text(node, source: str) -> str:
    return source[node.start_byte:node.end_byte]


# =====================================================================
# REGEX FALLBACK PARSER  (Dart 3+)
# =====================================================================

_RE_IMPORT = re.compile(r"^\s*import\s+['\"](.+?)['\"]", re.MULTILINE)

# ---- class-like declarations ----
# Matches: [abstract|sealed|base|final|interface] [mixin] class Name<T> extends/with/implements ...
_RE_CLASS = re.compile(
    r'^(?:(?:abstract|sealed|base|final|interface)\s+)*'
    r'(?:mixin\s+)?class\s+'
    r'(\w+)(?:<[^{]*?>)?'
    r'((?:\s+(?:extends|with|implements)\s+[^{]+?)*)'
    r'\s*\{',
    re.MULTILINE,
)

# standalone mixin (not "mixin class")
_RE_MIXIN = re.compile(
    r'^(?:base\s+)?mixin\s+(?!class\b)'
    r'(\w+)(?:<[^{]*?>)?'
    r'((?:\s+(?:on|implements)\s+[^{]+?)*)'
    r'\s*\{',
    re.MULTILINE,
)

# enum with body
_RE_ENUM = re.compile(
    r'^enum\s+(\w+)(?:<[^{]*?>)?'
    r'((?:\s+(?:with|implements)\s+[^{]+?)*)'
    r'\s*\{',
    re.MULTILINE,
)

# extension
_RE_EXTENSION = re.compile(
    r'^extension\s+(\w+)(?:<[^{]*?>)?\s+on\s+([\w<>,?\s]+?)\s*\{',
    re.MULTILINE,
)

# extension type (Dart 3.3)
_RE_EXTENSION_TYPE = re.compile(
    r'^extension\s+type\s+(\w+)(?:<[^{]*?>)?\s*\([^)]*\)'
    r'((?:\s+implements\s+[^{]+?)*)'
    r'\s*\{',
    re.MULTILINE,
)

# ---- functions / methods ----
# Params are REQUIRED (not optional) to avoid false positives.
# Getters handled by _RE_GETTER; abstract methods still end with ';'.
_RE_FUNCTION = re.compile(
    r'^\s*'
    r'(?:(?:external|static|abstract)\s+)*'      # modifiers
    r'(?:[\w<>,?\[\].]+\s+)*'                     # return type words (no \s in char class!)
    r'(?:get\s+|set\s+|operator\s+\S+\s*)?'       # getter/setter/operator
    r'(\w+(?:\.\w+)?)\s*'                          # name (incl. named ctors like Foo.bar)
    r'(?:<[^>]*>)?\s*'                             # type params
    r'(\([^)]*\))'                                 # params (REQUIRED; 1 level nesting)
    r'\s*(?:async\s*\*?|sync\s*\*?)?'              # async/sync*
    r'\s*(?:\{|=>|;)',                             # body start or abstract ;
    re.MULTILINE,
)

# standalone getter (no parens): Type get name => ... or { ... }
_RE_GETTER = re.compile(
    r'^\s*(?:(?:external|static)\s+)*'
    r'(?:[\w<>,?]+\s+)?'
    r'get\s+(\w+)\s*(?:\{|=>|;)',
    re.MULTILINE,
)

# field pattern
_RE_FIELD = re.compile(
    r'^\s*(?:(?:static|late|final|const|var|covariant)\s+)*'
    r'(?:[\w<>,?\s]+?\s+)'
    r'(\w+)\s*[;=,]',
    re.MULTILINE,
)

_KEYWORDS = frozenset({
    'if', 'else', 'for', 'while', 'switch', 'catch', 'class', 'return',
    'throw', 'assert', 'import', 'export', 'extends', 'implements',
    'with', 'abstract', 'mixin', 'enum', 'typedef', 'void', 'var',
    'final', 'const', 'static', 'new', 'break', 'continue', 'do',
    'try', 'finally', 'case', 'default', 'true', 'false', 'null',
    'is', 'as', 'in', 'super', 'this', 'late', 'required', 'covariant',
    'external', 'factory', 'get', 'set', 'operator', 'part', 'of',
    'show', 'hide', 'deferred', 'library', 'sealed', 'base', 'interface',
    'when', 'async', 'await', 'yield', 'sync', 'on',
})

# ---- regex entry point ----

def _parse_with_regex(path: str, source: str, loc: int, sloc: int) -> ParsedFile:
    cleaned = strip_comments(source)

    imports = _regex_extract_imports(source)
    classes = _regex_extract_all_class_like(cleaned)
    top_fns = _regex_extract_top_level_functions(cleaned, classes)

    return ParsedFile(path=path, source=source, classes=classes,
                      top_level_functions=top_fns, imports=imports,
                      loc=loc, sloc=sloc)


def _regex_extract_imports(source: str) -> List[ParsedImport]:
    return [_classify_import(m.group(1)) for m in _RE_IMPORT.finditer(source)]


def _regex_extract_all_class_like(cleaned: str) -> List[ParsedClass]:
    classes: list[ParsedClass] = []

    # regular classes
    for m in _RE_CLASS.finditer(cleaned):
        name = m.group(1)
        clauses = m.group(2) or ''
        modifier_area = cleaned[m.start():m.start() + m.group(0).index('class')]
        is_abstract = 'abstract' in modifier_area or 'sealed' in modifier_area
        superclass, interfaces, mixins = _parse_clauses(clauses)
        cls = _build_class(cleaned, m, name, superclass, interfaces, mixins, is_abstract)
        if cls:
            classes.append(cls)

    # standalone mixins
    for m in _RE_MIXIN.finditer(cleaned):
        name = m.group(1)
        clauses = m.group(2) or ''
        _, interfaces, _ = _parse_clauses(clauses)
        on_m = re.search(r'on\s+([\w<>,\s]+?)(?:\s+implements|\s*$)', clauses)
        on_types = [t.strip() for t in on_m.group(1).split(',') if t.strip()] if on_m else []
        cls = _build_class(cleaned, m, name, None, interfaces, on_types, True)
        if cls:
            classes.append(cls)

    # enums
    for m in _RE_ENUM.finditer(cleaned):
        name = m.group(1)
        clauses = m.group(2) or ''
        _, interfaces, mixins = _parse_clauses(clauses)
        cls = _build_class(cleaned, m, name, None, interfaces, mixins, False)
        if cls:
            classes.append(cls)

    # extensions
    for m in _RE_EXTENSION.finditer(cleaned):
        name = m.group(1)
        cls = _build_class(cleaned, m, name, None, [], [], False)
        if cls:
            classes.append(cls)

    # extension types
    for m in _RE_EXTENSION_TYPE.finditer(cleaned):
        name = m.group(1)
        clauses = m.group(2) or ''
        _, interfaces, _ = _parse_clauses(clauses)
        cls = _build_class(cleaned, m, name, None, interfaces, [], False)
        if cls:
            classes.append(cls)

    return classes


def _parse_clauses(text: str):
    superclass = None
    interfaces: list[str] = []
    mixins: list[str] = []

    ext = re.search(r'extends\s+([\w<>,?\s]+?)(?=\s+(?:with|implements)|$)', text)
    if ext:
        raw = ext.group(1).strip()
        m2 = re.match(r'(\w+)', raw)
        superclass = m2.group(1) if m2 else raw.split(',')[0].strip()

    with_m = re.search(r'with\s+([\w<>,?\s]+?)(?=\s+implements|$)', text)
    if with_m:
        mixins = [t.strip() for t in with_m.group(1).split(',') if t.strip()]

    impl = re.search(r'implements\s+([\w<>,?\s]+?)$', text)
    if impl:
        interfaces = [t.strip() for t in impl.group(1).split(',') if t.strip()]

    return superclass, interfaces, mixins


def _build_class(cleaned: str, match, name: str,
                 superclass, interfaces: list, mixins: list,
                 is_abstract: bool) -> Optional[ParsedClass]:
    brace_pos = match.end() - 1
    body, end_pos = _find_brace_block(cleaned, brace_pos)

    line_start = cleaned[:match.start()].count('\n') + 1
    line_end = cleaned[:end_pos].count('\n') + 1
    full_text = cleaned[match.start():end_pos]

    methods = _regex_extract_methods(body, name, line_start)
    fields = _regex_extract_class_fields_safe(body, methods)
    pub_m = [m for m in methods if not m.name.startswith('_')]
    pub_f = [f for f in fields if not f.startswith('_')]

    return ParsedClass(
        name=name, line_start=line_start, line_end=line_end,
        full_text=full_text, superclass=superclass,
        interfaces=interfaces, mixins=mixins,
        methods=methods, fields=fields,
        public_methods=pub_m, public_fields=pub_f,
        is_abstract=is_abstract)


# ---- top-level functions ----

def _regex_extract_top_level_functions(
    cleaned: str, classes: List[ParsedClass],
) -> List[ParsedFunction]:
    class_regions = [(c.line_start, c.line_end) for c in classes]
    functions: list[ParsedFunction] = []
    seen_lines: set[int] = set()

    for match in _RE_FUNCTION.finditer(cleaned):
        name = match.group(1)
        if not name or name in _KEYWORDS:
            continue
        if '.' in name:
            continue

        line = cleaned[:match.start()].count('\n') + 1
        if any(s <= line <= e for s, e in class_regions):
            continue
        if line in seen_lines:
            continue
        seen_lines.add(line)

        fn = _build_function(cleaned, match, name, class_name=None, base_line=0)
        if fn:
            functions.append(fn)

    for match in _RE_GETTER.finditer(cleaned):
        name = match.group(1)
        if name in _KEYWORDS:
            continue
        line = cleaned[:match.start()].count('\n') + 1
        if any(s <= line <= e for s, e in class_regions):
            continue
        if line in seen_lines:
            continue
        seen_lines.add(line)

        fn = _build_getter_fn(cleaned, match, name, class_name=None, base_line=0)
        if fn:
            functions.append(fn)

    return functions


# ---- methods inside class body ----

def _regex_extract_methods(body: str, class_name: str,
                           class_start_line: int) -> List[ParsedFunction]:
    methods: list[ParsedFunction] = []
    seen_lines: set[int] = set()

    for match in _RE_FUNCTION.finditer(body):
        name = match.group(1)
        if not name or name in _KEYWORDS:
            continue
        # skip constructors (unnamed & named)
        bare = name.split('.')[0] if '.' in name else name
        if bare == class_name:
            continue

        line = body[:match.start()].count('\n') + 1
        if line in seen_lines:
            continue
        seen_lines.add(line)

        fn = _build_function(body, match, name, class_name, class_start_line - 1)
        if fn:
            methods.append(fn)

    for match in _RE_GETTER.finditer(body):
        name = match.group(1)
        if name in _KEYWORDS or name == class_name:
            continue
        line = body[:match.start()].count('\n') + 1
        if line in seen_lines:
            continue
        seen_lines.add(line)

        fn = _build_getter_fn(body, match, name, class_name, class_start_line - 1)
        if fn:
            methods.append(fn)

    return methods


# ---- build function helpers ----

def _build_function(text: str, match, name: str,
                    class_name: Optional[str], base_line: int) -> Optional[ParsedFunction]:
    params_str = match.group(2) or ''
    params = _parse_params(params_str)
    line = text[:match.start()].count('\n') + 1 + base_line

    is_override = _check_override_before(text, match.start())

    preceding = text[max(0, match.start() - 80):match.start()]
    is_static = bool(re.search(r'\bstatic\s', preceding))
    is_getter = bool(re.search(r'\bget\s+\w+\s*$', preceding + name))
    is_setter = bool(re.search(r'\bset\s+\w+\s*$', preceding + name))

    end_char = text[match.end() - 1] if match.end() > 0 else ''
    body = ''
    line_end = line

    if end_char == '{':
        body, end_idx = _find_brace_block(text, match.end() - 1)
        line_end = text[:end_idx].count('\n') + 1 + base_line
    elif end_char == '>':  # =>
        semi = text.find(';', match.end())
        if semi >= 0:
            body = '=> ' + text[match.end():semi]
            line_end = text[:semi].count('\n') + 1 + base_line
    elif end_char == ';':
        body = ''  # abstract / external

    full_text = text[match.start():match.end() + len(body)]

    return ParsedFunction(
        name=name, class_name=class_name,
        line_start=line, line_end=line_end,
        body_text=body, full_text=full_text,
        parameters=params, is_override=is_override,
        is_static=is_static, is_getter=is_getter, is_setter=is_setter)


def _build_getter_fn(text: str, match, name: str,
                     class_name: Optional[str], base_line: int) -> Optional[ParsedFunction]:
    line = text[:match.start()].count('\n') + 1 + base_line
    is_override = _check_override_before(text, match.start())

    preceding = text[max(0, match.start() - 80):match.start()]
    is_static = bool(re.search(r'\bstatic\s', preceding))

    end_char = text[match.end() - 1] if match.end() > 0 else ''
    body = ''
    line_end = line
    if end_char == '{':
        body, end_idx = _find_brace_block(text, match.end() - 1)
        line_end = text[:end_idx].count('\n') + 1 + base_line
    elif end_char == '>':
        semi = text.find(';', match.end())
        if semi >= 0:
            body = text[match.end():semi]
            line_end = text[:semi].count('\n') + 1 + base_line

    return ParsedFunction(
        name=name, class_name=class_name,
        line_start=line, line_end=line_end,
        body_text=body, full_text=text[match.start():match.end() + len(body)],
        parameters=[], is_override=is_override,
        is_static=is_static, is_getter=True)


# ---- fields (safe) ----

def _regex_extract_class_fields_safe(body: str, methods: List[ParsedFunction]) -> List[str]:
    """Extract fields from class body, excluding method bodies.

    Remove all brace-delimited blocks from the top level of the body,
    then scan what remains (class-level declarations only).
    """
    top_level = _strip_nested_blocks(body)

    fields: list[str] = []
    for match in _RE_FIELD.finditer(top_level):
        name = match.group(1)
        if name and name not in _KEYWORDS and not name[0].isupper():
            if name not in fields:
                fields.append(name)
    return fields


def _strip_nested_blocks(body: str) -> str:
    """Remove brace-delimited blocks from the top level of *body*.

    This leaves only class-level declarations (fields, signatures)
    and strips method/getter/setter bodies.
    """
    result: list[str] = []
    i = 0
    n = len(body)
    state = _TokState.CODE
    depth = 0

    while i < n:
        c = body[i]

        if state == _TokState.CODE:
            if c == '/' and i + 1 < n and body[i+1] == '/':
                # skip line comment
                j = body.find('\n', i)
                if j < 0: j = n
                result.append('\n')
                i = j + 1; continue
            if c == '/' and i + 1 < n and body[i+1] == '*':
                j = body.find('*/', i + 2)
                if j < 0: j = n - 2
                i = j + 2; continue
            if c == 'r' and i + 1 < n and body[i+1] in ('"', "'"):
                q = body[i+1]
                if i + 3 < n and body[i+1:i+4] == q * 3:
                    end_q = q * 3
                    j = body.find(end_q, i + 4)
                    if j < 0: j = n - 3
                    i = j + 3; continue
                j = body.find(q, i + 2)
                if j < 0: j = n - 1
                i = j + 1; continue
            if c in ('"', "'"):
                if i + 2 < n and body[i:i+3] == c * 3:
                    end_q = c * 3
                    j = i + 3
                    while j < n:
                        if body[j:j+3] == end_q and not _is_escaped(body, j):
                            break
                        j += 1
                    i = j + 3 if j < n else n; continue
                j = i + 1
                while j < n:
                    if body[j] == c and not _is_escaped(body, j):
                        break
                    j += 1
                i = j + 1 if j < n else n; continue
            if c == '{':
                depth += 1
                if depth == 1:
                    # This is a method/getter body — skip it
                    _, end_idx = _find_brace_block(body, i)
                    result.append(';')  # placeholder
                    i = end_idx
                    depth = 0
                    continue
            result.append(c)
            i += 1; continue

        i += 1

    return ''.join(result)


# ---- Common helpers ----

def _parse_params(params_str: str) -> list:
    inner = params_str.strip('()')
    if not inner.strip():
        return []
    params: list[str] = []
    depth = 0
    current = ''
    for c in inner:
        if c in ('(', '<', '[', '{'):
            depth += 1
        elif c in (')', '>', ']', '}'):
            depth -= 1
        elif c == ',' and depth == 0:
            p = current.strip()
            if p:
                params.append(p)
            current = ''
            continue
        current += c
    p = current.strip()
    if p:
        params.append(p)
    return params


def _check_override_before(text: str, pos: int) -> bool:
    start = max(0, pos - 300)
    chunk = text[start:pos]
    lines = chunk.rstrip().split('\n')
    for line in reversed(lines):
        stripped = line.strip()
        if stripped.startswith('@override'):
            return True
        if stripped.startswith('@'):
            continue
        if stripped.startswith('///') or stripped.startswith('//'):
            continue
        if stripped == '':
            continue
        break
    return False


def _extract_import_uri(text: str) -> Optional[str]:
    m = re.search(r"""['"](.*?)['"]""", text)
    return m.group(1) if m else None


def _classify_import(uri: str) -> ParsedImport:
    if uri.startswith('dart:'):
        return ParsedImport(uri=uri, is_dart_core=True)
    if uri.startswith('package:'):
        pkg = uri.split('/')[0].replace('package:', '')
        return ParsedImport(uri=uri, is_package=True, package_name=pkg)
    return ParsedImport(uri=uri, is_relative=True)
