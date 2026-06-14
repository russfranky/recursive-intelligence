"""Tests for Occam's razor simplicity pressure."""

from ri_engine.models import Candidate, RunConfig
from ri_engine.occams_razor import (
    adjust_fitness,
    apply_occam_to_candidates,
    composite_simplicity,
    occams_enabled,
    rank_with_occam_tiebreak,
    simplicity_score,
)


def test_simplicity_prefers_moderate_length():
    short = simplicity_score(" ".join(["word"] * 50))
    optimal = simplicity_score(" ".join(["word"] * 300))
    bloated = simplicity_score(" ".join(["word"] * 2000))
    assert optimal > short
    assert optimal > bloated


def test_composite_simplicity_penalizes_many_sections():
    body = " ".join(["word"] * 40)
    few = composite_simplicity(f"## A\n{body}\n## B\n{body}")
    many = composite_simplicity("\n".join(f"## Section {i}\n{body}" for i in range(15)))
    assert few > many


def test_adjust_fitness_blends_simplicity():
    lean = adjust_fitness(0.9, " ".join(["word"] * 200))
    fat = adjust_fitness(0.9, " ".join(["word"] * 2500))
    assert lean > fat


def test_rank_tiebreak_prefers_shorter_at_equal_fitness():
    long_c = Candidate(id="a", content=" ".join(["word"] * 500), generation=1, fitness=0.85)
    short_c = Candidate(id="b", content=" ".join(["word"] * 100), generation=1, fitness=0.85)
    ranked = rank_with_occam_tiebreak([long_c, short_c])
    assert ranked[0].id == "b"


def test_apply_occam_adds_simplicity_score():
    c = Candidate(id="x", content="hello world", generation=1, fitness=0.8, scores={})
    apply_occam_to_candidates([c])
    assert "simplicity" in c.scores
    assert c.fitness is not None


def test_occams_enabled_default_true():
    assert occams_enabled(RunConfig(seed_prompt="a", objective="b"))


def test_occams_can_disable_via_metadata():
    cfg = RunConfig(
        seed_prompt="a",
        objective="b",
        metadata={"enable_occams_razor": False},
    )
    assert not occams_enabled(cfg)
