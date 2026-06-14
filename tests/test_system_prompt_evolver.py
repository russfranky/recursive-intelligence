"""Tests for system prompt self-improvement."""

from pathlib import Path

from ri_engine.models import RunConfig
from ri_engine.system_prompt_evolver import SystemPromptEvolver, apply_transform, compose_from_traits


SEED = """# TEST Operator

You are a test operator.

## Role

Do test things.

## Output

Return test output only.
"""


def test_apply_transform_adds_section():
    result = apply_transform(SEED, __import__("ri_engine.system_prompt_evolver", fromlist=["TRANSFORMS"]).TRANSFORMS[0])
    assert "Output Contract" in result
    assert "Do test things" in result


def test_compose_accumulates_traits():
    composed = compose_from_traits(SEED, ["constraint_first", "recursive_self_eval"])
    assert "Output Contract" in composed
    assert "Self-Evaluation Rubric" in composed


def test_evolver_improves_fitness():
    evolver = SystemPromptEvolver()
    config = RunConfig(
        seed_prompt=SEED,
        objective="Improve operator reliability and output contracts.",
        max_generations=4,
        survivors_count=2,
    )
    evolved, fitness, history = evolver.evolve(SEED, config)
    assert fitness > 0
    assert len(evolved) > len(SEED)
    assert len(history) >= 1


def test_operator_prompts_exist_and_have_evolved_sections():
    prompts_dir = Path(__file__).resolve().parents[1] / "prompts"
    variation = (prompts_dir / "variation.md").read_text(encoding="utf-8")
    selection = (prompts_dir / "selection.md").read_text(encoding="utf-8")
    assert "Success Metrics" in variation or "Output Contract" in variation
    assert "Self-Evaluation Rubric" in selection or "Pre-execution Check" in selection
