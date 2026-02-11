"""CSV output writer."""

from __future__ import annotations

import csv
import os
from typing import List

from ..models import ClassMetrics, FileMetrics, FunctionMetrics


_FILE_HEADERS = [
    "path", "module", "loc", "sloc", "noi", "noei",
    "classes_count", "functions_count",
    "cyclo_sum", "cyclo_avg", "cyclo_max",
    "halstead_volume_avg", "mi_avg", "mi_min",
    "static_members", "hardcoded_strings", "magic_numbers",
    "dead_code_estimate",
    "wmfp", "wmfp_density", "fpy",
    "technical_debt_minutes",
]

_FUNCTION_HEADERS = [
    "path", "module", "class_name", "function_name",
    "line_start", "line_end",
    "cyclo", "halstead_volume", "loc", "sloc",
    "mi", "max_nesting_level", "number_of_parameters",
    "wmfp", "fpy",
    "technical_debt_minutes",
]

_CLASS_HEADERS = [
    "path", "module", "class_name",
    "line_start", "line_end",
    "cbo", "dit", "noam", "noii", "nom", "noom",
    "rfc", "tcc", "woc", "wmc", "loc",
    "fpy",
    "technical_debt_minutes",
]


def write_raw_file_metrics_csv(file_metrics: List[FileMetrics], output_dir: str) -> str:
    """Write raw file-level metrics to CSV."""
    path = os.path.join(output_dir, "raw", "file_metrics.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_FILE_HEADERS)
        writer.writeheader()
        for fm in file_metrics:
            writer.writerow({k: fm.to_dict().get(k, "") for k in _FILE_HEADERS})

    return path


def write_raw_function_metrics_csv(function_metrics: List[FunctionMetrics], output_dir: str) -> str:
    """Write raw function-level metrics to CSV."""
    path = os.path.join(output_dir, "raw", "function_metrics.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_FUNCTION_HEADERS)
        writer.writeheader()
        for fm in function_metrics:
            d = fm.to_dict()
            writer.writerow({k: d.get(k, "") for k in _FUNCTION_HEADERS})

    return path


def write_raw_class_metrics_csv(class_metrics: List[ClassMetrics], output_dir: str) -> str:
    """Write raw class-level metrics to CSV."""
    path = os.path.join(output_dir, "raw", "class_metrics.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CLASS_HEADERS)
        writer.writeheader()
        for cm in class_metrics:
            d = cm.to_dict()
            writer.writerow({k: d.get(k, "") for k in _CLASS_HEADERS})

    return path


def write_graph_edges_csv(graph, output_dir: str, graph_type: str) -> str:
    """Write graph edges to CSV."""
    path = os.path.join(output_dir, f"edges_{graph_type}.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if graph_type == "pubspec":
            writer.writerow(["from", "to", "weight", "edge_type", "source", "version_constraint"])
            for e in graph.edges:
                writer.writerow([
                    e.from_node, e.to_node, e.weight, e.edge_type,
                    e.metadata.get("source", ""),
                    e.metadata.get("version_constraint", ""),
                ])
        else:
            writer.writerow(["from", "to", "weight", "edge_type"])
            for e in graph.edges:
                writer.writerow([e.from_node, e.to_node, e.weight, e.edge_type])

    return path
