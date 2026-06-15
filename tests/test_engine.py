"""Tests for the Recursive Intelligence Engine."""

from ri_engine import RecursiveIntelligenceEngine
from ri_engine.models import Candidate, RunConfig


def test_single_generation():
    engine = RecursiveIntelligenceEngine()
    config = RunConfig(
        seed_prompt="Analyze the given topic thoroughly.",
        objective="Improve clarity and add measurable outcomes.",
        population_size=4,
        survivors_count=2,
    )
    result = engine.run_single_generation(config, generation=1)
    assert len(result.candidates) == 4
    assert len(result.survivors) == 2
    assert result.best.fitness is not None
    assert result.best.fitness >= result.survivors[-1].fitness  # type: ignore[operator]


def test_full_run_converges_or_completes():
    engine = RecursiveIntelligenceEngine()
    config = RunConfig(
        seed_prompt="Write a product description.",
        objective="Maximize clarity and conversion-oriented structure.",
        max_generations=3,
        population_size=4,
        survivors_count=2,
        enable_membrane_bridge=True,
        domains=["marketing", "cognitive psychology"],
    )
    report = engine.run(config)
    assert report["meta"]["generations_run"] >= 1
    assert report["best_prompt"]
    assert report["best_fitness"] is not None
    assert len(report["fitness_trajectory"]) == report["meta"]["generations_run"]


def test_selection_scoring():
    from ri_engine.selection import SelectionEnvironment
    from ri_engine.llm_provider import MockLLMProvider

    env = SelectionEnvironment(MockLLMProvider())
    config = RunConfig(
        seed_prompt="test",
        objective="test objective",
    )
    candidates = [
        Candidate(id="a", content="Short prompt.", generation=1),
        Candidate(id="b", content="A much longer and more detailed prompt with constraints.", generation=1),
    ]
    ranked = env.evaluate(config, candidates)
    assert all(c.fitness is not None for c in ranked)
    assert ranked[0].fitness >= ranked[1].fitness  # type: ignore[operator]


def test_retention_convergence():
    from ri_engine.retention import RetentionEngine
    from ri_engine.llm_provider import MockLLMProvider

    ret = RetentionEngine(MockLLMProvider())
    assert not ret.check_convergence([0.5, 0.6, 0.65], threshold=0.02, window=2)
    assert ret.check_convergence([0.80, 0.81, 0.805, 0.802], threshold=0.02, window=3)


def test_load_config():
    from pathlib import Path

    config_path = Path(__file__).resolve().parents[1] / "config" / "example.yaml"
    config = RecursiveIntelligenceEngine.load_config(config_path)
    assert "research agent" in config.seed_prompt.lower() or "research" in config.seed_prompt.lower()
    assert config.enable_membrane_bridge is True
    assert len(config.domains) >= 3
