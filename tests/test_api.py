"""Tests for the public improve() API."""

from ri_engine import improve


def test_improve_returns_result():
    result = improve(
        seed_prompt="You are a helper. Answer questions.",
        objective="Help customers resolve billing issues in one conversation.",
        max_generations=2,
        population_size=4,
    )
    assert result.improved_prompt
    assert len(result.improved_prompt) > 50
    assert result.generations >= 1
    assert 0.0 <= result.fitness <= 1.0
