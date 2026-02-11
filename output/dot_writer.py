"""DOT graph output writer.

Generates Graphviz DOT format files for import and pubspec dependency graphs.
"""

from __future__ import annotations

import os
from typing import Optional

from ..graphs.models import DependencyGraph


def write_import_graph_dot(
    graph: DependencyGraph,
    output_dir: str,
) -> str:
    """Write import dependency graph as DOT file."""
    path = os.path.join(output_dir, "graph_import.dot")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write("digraph import_graph {\n")
        f.write("  rankdir=LR;\n")
        f.write("  node [shape=box, style=filled, fillcolor=lightyellow];\n")
        f.write("  edge [color=gray40];\n")
        f.write("\n")

        # Internal nodes
        for node in graph.nodes:
            label = node.name
            f.write(f'  "{node.id}" [label="{label}"];\n')

        # External nodes (grey)
        for ext in graph.external_packages:
            f.write(
                f'  "ext:{ext}" [label="{ext}", '
                f'style=filled, fillcolor=lightgray, shape=ellipse];\n'
            )
        f.write("\n")

        # Edges
        for edge in graph.edges:
            label = str(edge.weight) if edge.weight > 1 else ""
            style = ""
            if label:
                style = f' [label="{label}"]'
            f.write(f'  "{edge.from_node}" -> "{edge.to_node}"{style};\n')

        f.write("}\n")

    return path


def write_pubspec_graph_dot(
    graph: DependencyGraph,
    output_dir: str,
    local_only: bool = True,
) -> str:
    """Write pubspec dependency graph as DOT file.

    Args:
        graph: Pubspec dependency graph.
        output_dir: Output directory.
        local_only: If True, show only edges between internal packages.
    """
    path = os.path.join(output_dir, "graph_pubspec.dot")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    internal_ids = {n.id for n in graph.nodes}

    with open(path, "w", encoding="utf-8") as f:
        f.write("digraph pubspec_graph {\n")
        f.write("  rankdir=LR;\n")
        f.write("  node [shape=box];\n")
        f.write("\n")

        # Internal nodes
        for node in graph.nodes:
            label = node.name
            attrs = []
            if node.version:
                attrs.append(f"v{node.version}")
            if node.metadata.get("publish_to") in ("none", "none://"):
                attrs.append("private")
            attr_str = f"\\n{', '.join(attrs)}" if attrs else ""
            f.write(f'  "{node.id}" [label="{label}{attr_str}"];\n')

        if not local_only:
            # External nodes
            for ext in graph.external_packages:
                f.write(
                    f'  "ext:{ext}" [label="{ext}", '
                    f'style=filled, fillcolor=lightgray];\n'
                )
        f.write("\n")

        # Edges
        for edge in graph.edges:
            to_id = edge.to_node
            if local_only and to_id not in internal_ids:
                continue

            label_parts = []
            source = edge.metadata.get("source", "")
            version = edge.metadata.get("version_constraint", "")
            if source:
                label_parts.append(source)
            if version:
                label_parts.append(str(version))

            style_parts = []
            if edge.edge_type == "dev_dependency":
                style_parts.append("style=dashed")
                label_parts.append("dev")
            if edge.edge_type == "override":
                style_parts.append("style=bold")
                label_parts.append("override")

            label = "\\n".join(label_parts) if label_parts else ""
            attrs = []
            if label:
                attrs.append(f'label="{label}"')
            attrs.extend(style_parts)
            attr_str = f' [{", ".join(attrs)}]' if attrs else ""

            f.write(f'  "{edge.from_node}" -> "{to_id}"{attr_str};\n')

        f.write("}\n")

    return path


def write_module_import_graph_dot(
    module_name: str,
    import_details: dict,
    output_dir: str,
) -> str:
    """Write per-module import detail graph as DOT.

    Args:
        module_name: Name of the module.
        import_details: Dict from_file -> {to_package: count}.
        output_dir: Output directory.
    """
    safe = module_name.replace("/", "_").replace("\\", "_")
    path = os.path.join(output_dir, "modules", f"{safe}_import_graph.dot")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Collect unique nodes
    file_nodes = set()
    pkg_nodes = set()
    for from_file, targets in import_details.items():
        file_nodes.add(from_file)
        for pkg in targets:
            pkg_nodes.add(pkg)

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"digraph {safe}_imports {{\n")
        f.write("  rankdir=LR;\n")
        f.write("  node [shape=box, fontsize=9];\n")
        f.write("\n")

        # File nodes
        for fn in sorted(file_nodes):
            short = _short_path(fn)
            f.write(f'  "{fn}" [label="{short}", shape=note];\n')

        # Package nodes
        for pkg in sorted(pkg_nodes):
            f.write(f'  "{pkg}" [label="{pkg}", shape=box3d, '
                    f'style=filled, fillcolor=lightyellow];\n')
        f.write("\n")

        # Edges
        for from_file, targets in import_details.items():
            for pkg, count in targets.items():
                label = str(count) if count > 1 else ""
                style = f' [label="{label}"]' if label else ""
                f.write(f'  "{from_file}" -> "{pkg}"{style};\n')

        f.write("}\n")

    return path


def _short_path(path: str, max_parts: int = 3) -> str:
    """Shorten a file path for DOT labels."""
    parts = path.replace("\\", "/").split("/")
    if len(parts) <= max_parts:
        return "/".join(parts)
    return ".../" + "/".join(parts[-max_parts:])
