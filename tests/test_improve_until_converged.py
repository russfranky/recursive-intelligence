"""Tests for iterative prompt improvement until convergence."""

from ri_engine.improve_prompts import _composite_score, improve_until_converged
from ri_engine.system_prompt_evolver import SystemPromptEvolver, TRAIT_COUNT


def test_composite_score_weights_coverage():
    assert _composite_score(0.9, ["a", "b"]) > _composite_score(0.9, [])
    assert _composite_score(0.5, ["a"] * TRAIT_COUNT) > _composite_score(0.5, [])


def test_saturate_accumulates_traits():
    from ri_engine.models import RunConfig

    evolver = SystemPromptEvolver()
    seed = "# TEST\n\n## Role\nDo things.\n\n## Output\nDone."
    config = RunConfig(seed_prompt=seed, objective="Improve reliability.", convergence_threshold=0.02)
    _, fitness, traits = evolver.saturate_traits(seed, config)
    assert fitness > 0
    assert len(traits) >= 1


def test_improve_until_converged_runs_and_converges():
    summary = improve_until_converged(max_rounds=10, plateau_rounds=2, min_improvement=0.001)
    assert summary["rounds_run"] >= 1
    assert "final_aggregate_composite" in summary
    assert len(summary["prompts"]) == 5
    for info in summary["prompts"].values():
        assert info["trait_count"] >= 1
