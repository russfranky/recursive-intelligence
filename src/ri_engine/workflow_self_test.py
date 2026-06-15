"""Middle-loop task battery for Claude Code + ri-engine workflow self-tests."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from ri_engine.paths import workspace_dir


@dataclass
class TaskResult:
    id: str
    description: str
    passed: bool
    detail: str


def resolve_seed_from_session(data: dict[str, Any]) -> str:
    """Load seed from seed_file when present, else use inline seed_prompt."""
    seed = str(data.get("seed_prompt", "")).strip()
    seed_file = data.get("seed_file")
    if not seed_file:
        return seed
    path = Path(seed_file)
    if not path.is_absolute():
        path = workspace_dir() / path
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    if seed:
        return seed
    raise FileNotFoundError(f"seed_file not found: {path}")


def load_task_battery(path: Path | str | None = None) -> dict[str, Any]:
    if path is None:
        path = workspace_dir() / "config" / "workflow_self_test_tasks.yaml"
    battery_path = Path(path)
    if not battery_path.is_absolute():
        battery_path = workspace_dir() / battery_path
    if not battery_path.is_file():
        raise FileNotFoundError(f"Task battery not found: {battery_path}")
    data = yaml.safe_load(battery_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "tasks" not in data:
        raise ValueError(f"Invalid task battery: {battery_path}")
    data["_path"] = str(battery_path)
    return data


def _check_task(task: dict[str, Any], prompt: str) -> TaskResult:
    task_id = str(task.get("id", "unknown"))
    description = str(task.get("description", ""))
    task_type = task.get("type", "")
    text = prompt
    ignore_case = bool(task.get("ignore_case", True))
    haystack = text.lower() if ignore_case else text

    def contains(pattern: str) -> bool:
        needle = pattern.lower() if ignore_case else pattern
        return needle in haystack

    passed = False
    detail = ""

    if task_type == "must_not_contain":
        patterns = [str(p) for p in task.get("patterns", [])]
        hits = [p for p in patterns if contains(p)]
        passed = not hits
        detail = "ok" if passed else f"found: {', '.join(hits)}"

    elif task_type == "must_contain_any":
        patterns = [str(p) for p in task.get("patterns", [])]
        hits = [p for p in patterns if contains(p)]
        passed = bool(hits)
        detail = f"matched: {', '.join(hits)}" if passed else f"need one of: {', '.join(patterns)}"

    elif task_type == "must_contain_all":
        patterns = [str(p) for p in task.get("patterns", [])]
        missing = [p for p in patterns if not contains(p)]
        passed = not missing
        detail = "ok" if passed else f"missing: {', '.join(missing)}"

    elif task_type == "max_words":
        limit = int(task.get("max", 150))
        count = len(prompt.split())
        passed = count <= limit
        detail = f"{count} words (max {limit})"

    elif task_type == "max_occurrences":
        pattern = str(task.get("pattern", ""))
        limit = int(task.get("max", 1))
        flags = re.I if ignore_case else 0
        count = len(re.findall(re.escape(pattern), text, flags=flags))
        passed = count <= limit
        detail = f"{count} occurrence(s) (max {limit})"

    else:
        detail = f"unknown task type: {task_type}"
        passed = False

    return TaskResult(id=task_id, description=description, passed=passed, detail=detail)


def score_task_battery(prompt: str, battery: dict[str, Any] | None = None, *, path: Path | str | None = None) -> dict[str, Any]:
    """Score a prompt against the workflow task battery."""
    data = battery if battery is not None else load_task_battery(path)
    tasks = data.get("tasks") or []
    results = [_check_task(task, prompt) for task in tasks]
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    pass_rate = (passed / total) if total else 0.0
    threshold = float(data.get("pass_threshold", 0.85))
    return {
        "battery_id": data.get("battery_id", ""),
        "description": data.get("description", ""),
        "pass_threshold": threshold,
        "passed": passed,
        "total": total,
        "pass_rate": pass_rate,
        "battery_passed": pass_rate >= threshold,
        "tasks": [asdict(r) for r in results],
        "battery_path": data.get("_path", str(path or "")),
    }


def compare_battery_scores(seed_prompt: str, evolved_prompt: str, *, path: Path | str | None = None) -> dict[str, Any]:
    """Score seed vs evolved and report delta."""
    seed_score = score_task_battery(seed_prompt, path=path)
    evolved_score = score_task_battery(evolved_prompt, path=path)
    return {
        "seed": seed_score,
        "evolved": evolved_score,
        "delta_pass_rate": evolved_score["pass_rate"] - seed_score["pass_rate"],
        "improved": evolved_score["pass_rate"] >= seed_score["pass_rate"],
    }


def default_workflow_config_path() -> Path:
    return workspace_dir() / "config" / "workflow_self_test.yaml"


def run_workflow_self_test(
    *,
    config_path: Path | str | None = None,
    provider: str | None = None,
    expert: bool = False,
    quiet: bool = False,
) -> dict[str, Any]:
    """Prep + run workflow session + task battery (middle loop)."""
    from ri_engine.real_world_test import prep_real_world_test, run_real_world_test

    prep_real_world_test(force=False)
    cfg = config_path or default_workflow_config_path()
    summary = run_real_world_test(Path(cfg), provider=provider, expert=expert, quiet=quiet)
    summary["workflow"] = "claude_code_self_test"
    return summary
