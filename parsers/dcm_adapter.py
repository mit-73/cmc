"""Optional adapter for dart_code_metrics (DCM) CLI tool.

When enabled, runs ``dcm analyze --reporter=json`` on each module and
parses the JSON output to extract accurate function-level metrics:
CYCLO, HALVOL, MI, MNL, NOP, SLOC.

These values override the built-in tree-sitter / regex calculations.
"""

from __future__ import annotations

import json
import os
import subprocess
import shutil
from typing import Dict, List, Optional

from ..config import DCMConfig


def is_dcm_available(dcm_config: DCMConfig) -> bool:
    """Check if DCM CLI is available on PATH."""
    return shutil.which(dcm_config.executable) is not None


def run_dcm_analyze(module_path: str, dcm_config: DCMConfig) -> Optional[Dict]:
    """Run DCM on a module and return parsed JSON output.

    Returns a dict mapping file_path -> list of metric records,
    or None if DCM is not available or fails.
    """
    if not is_dcm_available(dcm_config):
        return None

    lib_path = os.path.join(module_path, "lib")
    if not os.path.isdir(lib_path):
        return None

    cmd = [
        dcm_config.executable,
        "analyze",
        "--reporter=json",
        *dcm_config.extra_args,
        lib_path,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=module_path,
        )
        if result.returncode != 0 and not result.stdout.strip():
            return None
        data = json.loads(result.stdout)
        return _normalize_dcm_output(data)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return None


def _normalize_dcm_output(data) -> Dict[str, List[dict]]:
    """Normalize raw DCM JSON to a dict of file -> metric records.

    DCM output format can vary between versions. This normalizer
    handles the common structure.
    """
    result: Dict[str, List[dict]] = {}

    if isinstance(data, dict):
        # Format: {"formatVersion": ..., "records": [...]}
        records = data.get("records", data.get("files", []))
    elif isinstance(data, list):
        records = data
    else:
        return result

    for record in records:
        path = record.get("path", record.get("file", ""))
        issues = record.get("issues", record.get("metrics", []))

        file_metrics = []
        for issue in issues:
            metric = {
                "function": issue.get("function", issue.get("entity", "")),
                "line": issue.get("line", issue.get("location", {}).get("line", 0)),
            }
            # Extract metric values
            if "metrics" in issue:
                for m in issue["metrics"]:
                    key = m.get("id", m.get("metric", "")).lower()
                    value = m.get("value", 0)
                    metric[key] = value
            else:
                # Flat structure
                for key in ("cyclomatic-complexity", "halstead-volume",
                            "maintainability-index", "maximum-nesting-level",
                            "number-of-parameters", "source-lines-of-code"):
                    if key in issue:
                        metric[key.replace("-", "_")] = issue[key]

            file_metrics.append(metric)

        if path:
            result[path] = file_metrics

    return result


def merge_dcm_metrics(function_name: str, line: int,
                      dcm_records: List[dict]) -> Optional[dict]:
    """Find matching DCM record for a given function.

    Returns dict with keys: cyclo, halvol, mi, mnl, nop, sloc
    or None if no match found.
    """
    for rec in dcm_records:
        if rec.get("function") == function_name or rec.get("line") == line:
            result = {}
            # Map DCM keys to our keys
            mapping = {
                "cyclomatic_complexity": "cyclo",
                "cyclomatic-complexity": "cyclo",
                "halstead_volume": "halvol",
                "halstead-volume": "halvol",
                "maintainability_index": "mi",
                "maintainability-index": "mi",
                "maximum_nesting_level": "mnl",
                "maximum-nesting-level": "mnl",
                "number_of_parameters": "nop",
                "number-of-parameters": "nop",
                "source_lines_of_code": "sloc",
                "source-lines-of-code": "sloc",
            }
            for dcm_key, our_key in mapping.items():
                if dcm_key in rec:
                    result[our_key] = rec[dcm_key]
            if result:
                return result
    return None
