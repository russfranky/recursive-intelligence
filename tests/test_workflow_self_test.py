"""Tests for workflow self-test task battery."""

from pathlib import Path

import yaml

from ri_engine.prompt_synthesizer import finalize_prompt
from ri_engine.workflow_self_test import (
    compare_battery_scores,
    load_task_battery,
    resolve_seed_from_session,
    score_task_battery,
)


def test_resolve_seed_from_file():
    data = {"seed_file": "docs/claude_code_integration.md", "seed_prompt": "fallback"}
    seed = resolve_seed_from_session(data)
    assert "Claude Code integration" in seed
    assert seed != "fallback"


def test_workflow_battery_passes_compact_prompt():
    seed = Path("docs/claude_code_integration.md").read_text(encoding="utf-8")
    goal = (
        "When this works, the improved prompt teaches Claude Code to run ri-engine improve on task seeds, "
        "enable handoff when needed, read runbook/RUNBOOK.md, research before editing, write a short spec, "
        "wait for proceed, then implement — with minimal ceremony and no duplicate instructions."
    )
    prompt = finalize_prompt(seed, goal, leaning="plain")
    report = score_task_battery(prompt)
    assert report["pass_rate"] >= report["pass_threshold"], report["tasks"]


def test_workflow_battery_fails_code_review_bleed():
    bad = (
        "# Agent\n\n## Review Protocol\nOWASP\n"
        "When this works, research, spec, implement via runbook handoff."
    )
    report = score_task_battery(bad)
    failed = [t for t in report["tasks"] if t["id"] == "no_code_review_bleed"]
    assert failed and not failed[0]["passed"]


def test_compare_battery_improves_over_raw_doc():
    seed = Path("docs/claude_code_integration.md").read_text(encoding="utf-8")
    goal = (
        "When this works, Claude Code reads runbook/RUNBOOK.md, researches before editing, "
        "writes a short spec, waits for proceed, then implements."
    )
    evolved = finalize_prompt(seed, goal, leaning="plain")
    report = compare_battery_scores(seed, evolved)
    assert report["evolved"]["pass_rate"] >= report["seed"]["pass_rate"]


def test_load_task_battery():
    battery = load_task_battery()
    assert battery["battery_id"] == "claude_code_workflow_v1"
    assert len(battery["tasks"]) >= 6


def test_workflow_config_exists():
    cfg = Path("config/workflow_self_test.yaml")
    assert cfg.is_file()
    data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    assert data["metadata"]["use_case"] == "workflow_self_test"
    assert data["metadata"]["task_battery"]
