"""Tests for objective clarity gate."""

import pytest

from ri_engine import assess_objective, improve, ObjectiveTooVagueError


def test_vague_goal_blocked():
    check = assess_objective("be helpful")
    assert check.blocked
    assert check.clarity_score < 45
    assert "desired outcome" in check.kickback_message.lower()
    assert check.suggested_goals


def test_measurable_goal_passes():
    check = assess_objective(
        "When this works, the AI will resolve billing issues in one conversation without escalation."
    )
    assert check.ready
    assert not check.blocked
    assert check.clarity_score >= 60


def test_template_skips_gate():
    check = assess_objective("be helpful", metadata={"template": "customer-support"})
    assert check.ready
    assert check.clarity_score == 100


def test_improve_raises_on_vague_goal():
    with pytest.raises(ObjectiveTooVagueError) as exc:
        improve("You are a helper.", "be helpful", max_generations=1, population_size=2)
    assert exc.value.assessment.blocked


def test_improve_force_goal_skips():
    result = improve(
        "You are a helper.",
        "be helpful",
        max_generations=1,
        population_size=2,
        force_goal=True,
    )
    assert result.improved_prompt
