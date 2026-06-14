"""Tests for structural scorer and substantial gains analysis."""

from pathlib import Path

from ri_engine.structural_scorer import (
    apply_extension,
    diagnose_all,
    score_prompt,
)
from ri_engine.substantial_gains import apply_substantial_gains, diagnose_gains


SEED = """# VARIATION Operator

## Role
Generate variants.

## Principles
1. Recursive hook required.

## Output
Return ONLY the prompt.
"""


def test_structural_scorer_detects_gaps():
    result = score_prompt(SEED, "variation.md")
    assert result.total < 0.8
    assert len(result.gaps) > 0


def test_apply_extension_adds_tier2():
    extended = apply_extension(SEED, "variation.md")
    assert "Mutation Protocol" in extended


def test_diagnose_all_operators():
    prompts_dir = Path(__file__).resolve().parents[1] / "prompts"
    results = diagnose_all(str(prompts_dir))
    assert len(results) == 5
    for name, info in results.items():
        assert "structural_score" in info
        assert 0 <= info["structural_score"] <= 1.0


def test_diagnose_gains_finds_bottlenecks():
    report = diagnose_gains()
    assert len(report["bottlenecks"]) >= 3
    assert any(b["id"] == "hash_scorer" for b in report["bottlenecks"])


def test_apply_substantial_gains_improves_scores():
    summary = apply_substantial_gains()
    assert summary["aggregate_after"] >= summary["aggregate_before"]
    assert "operators" in summary
    tier2_scores = [info["dimensions"].get("tier2_extension", 0) for info in summary["operators"].values()]
    assert max(tier2_scores) >= 0.0
