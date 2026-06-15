"""Tests for prompt finalization and duplication guards."""

from pathlib import Path

from ri_engine.language_leanings import leaning_clause
from ri_engine.prompt_synthesizer import finalize_prompt


def test_finalize_simple_goal_is_compact():
    seed = "You are a helper."
    goal = "When this works, the AI will produce a structured answer"
    prompt = finalize_prompt(seed, goal, leaning="mixed")
    words = len(prompt.split())
    assert words < 120, f"expected compact prompt, got {words} words"
    assert "Failure Modes to Block" not in prompt
    assert "Self-Evaluation Rubric" not in prompt


def test_finalize_no_duplicate_linguistic_leaning():
    seed = "You are a helper."
    goal = "When this works, the AI will produce a structured answer"
    clause = leaning_clause("mixed")
    objective = f"{goal}\n\n{clause}"
    prompt = finalize_prompt(seed, objective, leaning="mixed")
    assert prompt.lower().count("mandatory linguistic leaning") == 1
    assert "## Linguistic Leaning" not in prompt


def test_claude_code_workflow_seed_not_code_review():
    seed = Path("docs/claude_code_integration.md").read_text(encoding="utf-8")
    goal = (
        "When this works, the improved prompt teaches Claude Code to run ri-engine improve on task seeds, "
        "enable handoff when needed, read runbook/RUNBOOK.md, research before editing, write a short spec, "
        "wait for proceed, then implement — with minimal ceremony and no duplicate instructions."
    )
    prompt = finalize_prompt(seed, goal, leaning="plain")
    assert "Review Protocol" not in prompt
    assert "OWASP" not in prompt
    assert "Claims | Confidence" not in prompt
    words = len(prompt.split())
    assert words < 120, f"expected compact workflow prompt, got {words} words"
