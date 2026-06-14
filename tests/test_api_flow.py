"""API contract tests — external-consumer flow and structure."""

import json

import pytest

from ri_engine import ImproveResult, improve, improve_template, list_templates


def test_public_exports():
    assert callable(improve)
    assert callable(improve_template)
    assert callable(list_templates)


def test_list_templates_structure():
    templates = list_templates()
    assert len(templates) >= 6
    sample = templates[0]
    assert {"id", "name", "description"}.issubset(sample.keys())


def test_improve_minimal_contract():
    result = improve(
        seed_prompt="You are a helper. Answer questions.",
        objective="Help customers resolve billing issues in one conversation.",
        max_generations=2,
        population_size=4,
    )
    assert isinstance(result, ImproveResult)
    assert len(result.improved_prompt) > 100
    assert 0.0 <= result.fitness <= 1.0
    assert result.generations >= 1
    assert isinstance(result.converged, bool)
    assert result.engine_prompt
    assert "best_prompt" in result.report


def test_improve_template_contract():
    result = improve_template("code-review", max_generations=2, population_size=4)
    assert "review" in result.improved_prompt.lower() or "Review" in result.improved_prompt
    assert result.to_dict()["improved_prompt"] == result.improved_prompt


def test_to_dict_is_json_serializable():
    result = improve(
        seed_prompt="You are a sales assistant.",
        objective="When this works, the AI will draft a 120-word outreach email with one clear CTA.",
        max_generations=1,
        population_size=2,
    )
    payload = result.to_dict()
    encoded = json.dumps(payload)
    decoded = json.loads(encoded)
    assert decoded["improved_prompt"] == result.improved_prompt
    assert "fitness_trajectory" in decoded


def test_validation_rejects_empty_seed():
    with pytest.raises(ValueError, match="seed_prompt"):
        improve(seed_prompt="  ", objective="Do something useful.")


def test_validation_rejects_empty_objective():
    with pytest.raises(ValueError, match="objective"):
        improve(seed_prompt="You are a helper.", objective="")


def test_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unknown provider"):
        improve(
            seed_prompt="test",
            objective="When this works, the AI will return a one-line test response.",
            provider="not-a-provider",
            max_generations=1,
            population_size=2,
        )


def test_unknown_template_raises():
    with pytest.raises(FileNotFoundError, match="Template not found"):
        improve_template("nonexistent-template-xyz")


def test_improved_vs_engine_prompt_documented():
    """Both outputs exist: finalized (deploy) and raw VSR winner (inspect)."""
    result = improve(
        seed_prompt="You are a security analyst.",
        objective="Triage alerts with severity and MITRE mapping.",
        max_generations=2,
        population_size=4,
    )
    assert result.improved_prompt
    assert result.engine_prompt
    # Both are structured task prompts from the same synthesis family
    assert len(result.improved_prompt) > 50
    assert len(result.engine_prompt) > 50
