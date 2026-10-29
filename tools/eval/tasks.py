#!/usr/bin/env python3
"""30-task census over the frozen task list (D2 of XJ-20261030-001).

Read-only: loads ``tools/eval/tasks/T*.json`` through ``schema.load_task_dir``
and reports the census that prereg v1.3 (C6) froze for round four -- exactly
30 tasks, 10 per layer (fact / code / process). The count is asserted, not
narrated: a list that drifts from the frozen 30 fails loudly (nonzero exit via
``run.py --tasks``) instead of silently shrinking the paired design, which is
how round 3 ended up below the prereg floor (20 < 30 after C4 excluded the
code layer).

This module deliberately adds no validation of its own: schema drift findings
come from schema.load_task_dir verbatim; the only new check is the C6 total.
"""
from __future__ import annotations

from typing import Any, Dict, List

from schema import LAYER_COUNTS, TOTAL_TASKS, load_task_dir


def census(task_dir: Any) -> Dict[str, Any]:
    """Load the task list and count it. Returns a plain dict so a report can
    print it and a test can assert on it:

    ``{"task_dir", "total", "layers": {layer: count}, "tasks": [{id, layer,
    title}], "errors": [...]}`` -- errors are schema.load_task_dir findings
    verbatim (schema drift is reported, never raised over)."""
    tasks, errors = load_task_dir(task_dir)
    layers: Dict[str, int] = {layer: 0 for layer in LAYER_COUNTS}
    for task in tasks:
        layers[task.layer] = layers.get(task.layer, 0) + 1
    return {
        "task_dir": str(task_dir),
        "total": len(tasks),
        "layers": layers,
        "tasks": [
            {"id": task.id, "layer": task.layer, "title": task.title}
            for task in sorted(tasks, key=lambda item: item.id)
        ],
        "errors": list(errors),
    }


def census_errors(result: Dict[str, Any]) -> List[str]:
    """The C6 assertion on top of any schema findings: the parsed total must
    equal the frozen 30. Layer drift needs no new check here -- frozen
    LAYER_COUNTS are already enforced per-layer by schema.load_task_dir."""
    errors = list(result["errors"])
    total = result["total"]
    if total != TOTAL_TASKS:
        errors.append(
            f"census: {total} tasks parsed, C6 frozen design requires exactly "
            f"{TOTAL_TASKS}")
    return errors


def format_census(result: Dict[str, Any]) -> List[str]:
    """Human-readable lines: the per-task inventory first (same shape the
    --tasks listing always had), then the census block."""
    lines = [
        f"{item['id']} [{item['layer']}] {item['title']}"
        for item in result["tasks"]
    ]
    lines.append("")
    lines.append(f"tasks total: {result['total']} (frozen C6 census: {TOTAL_TASKS})")
    for layer in LAYER_COUNTS:
        lines.append(f"layer {layer}: {result['layers'].get(layer, 0)}"
                     f"/{LAYER_COUNTS[layer]}")
    return lines
