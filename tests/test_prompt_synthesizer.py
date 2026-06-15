"""Tests for prompt finalization and duplication guards."""

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
