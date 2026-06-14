"""Tests for macro-scale trait registry and recursive priors."""

from __future__ import annotations

from pathlib import Path

from ri_engine import improve
from ri_engine.macro_registry import (
    MacroTraitRegistry,
    apply_macro_priors,
    classify_objective,
    record_selection,
)
from ri_engine.models import Candidate, RunConfig
from ri_engine.trait_parser import ParsedTrait


def test_classify_objective_by_keywords():
    assert classify_objective("Help customers resolve billing issues") == "customer-support"
    assert classify_objective("Review pull requests for security") == "code-review"


def test_classify_objective_uses_template_metadata():
    cls = classify_objective("Anything", {"template": "customer-support"})
    assert cls == "customer-support"


def test_registry_records_and_applies_priors(tmp_path, monkeypatch):
    reg_path = tmp_path / "macro_trait_registry.json"
    monkeypatch.setattr("ri_engine.macro_registry.DEFAULT_REGISTRY_PATH", reg_path)
    reg = MacroTraitRegistry(reg_path)

    traits = [
        ParsedTrait(
            name="constraint_first",
            instruction="Lead with measurable success criteria",
            evidence="utility=0.9",
        )
    ]
    assert reg.upsert_traits("customer-support", traits, 0.88)
    reg.save()

    config = RunConfig(
        seed_prompt="You are a helper.",
        objective="Resolve customer billing issues in one chat.",
        metadata={"template": "customer-support"},
    )
    updated, report = apply_macro_priors(config)
    assert report.source == "registry"
    assert "constraint_first" in (updated.metadata.get("macro_strategy_order") or [])
    assert "Macro lineage" in (updated.metadata.get("macro_trait_brief") or "")


def test_macro_learning_across_two_improve_runs(tmp_path, monkeypatch):
    reg_path = tmp_path / "macro_trait_registry.json"
    monkeypatch.setattr("ri_engine.macro_registry.DEFAULT_REGISTRY_PATH", reg_path)

    r1 = improve(
        seed_prompt="You are a support agent.",
        objective="Resolve billing issues in one conversation.",
        max_generations=2,
        population_size=4,
        metadata={"template": "customer-support"},
    )
    assert r1.fitness >= 0.65

    reg = MacroTraitRegistry(reg_path).load()
    assert reg.entries, "first run should record macro traits"

    r2 = improve(
        seed_prompt="You are a support agent.",
        objective="Resolve billing issues in one conversation.",
        max_generations=2,
        population_size=4,
        metadata={"template": "customer-support"},
    )
    assert r2.report.get("macro_priors") or r2.report.get("macro_learning")


def test_record_selection_respects_min_fitness(tmp_path):
    reg_path = tmp_path / "macro.json"
    reg = MacroTraitRegistry(reg_path)
    config = RunConfig(seed_prompt="x", objective="help customers")
    traits = [ParsedTrait(name="test", instruction="do thing")]
    assert not reg.upsert_traits("general", traits, 0.3)
    assert reg.upsert_traits("general", traits, 0.8)


def test_record_selection_helper(tmp_path, monkeypatch):
    reg_path = tmp_path / "macro.json"
    monkeypatch.setattr("ri_engine.macro_registry.DEFAULT_REGISTRY_PATH", reg_path)
    config = RunConfig(
        seed_prompt="seed",
        objective="Resolve billing in one chat",
        metadata={"template": "customer-support"},
    )
    lineage = "- [TRAIT:measurable_outcomes] Define quantifiable deliverables (evidence: high utility)"
    ok = record_selection(
        config,
        Candidate(id="best", content="prompt", generation=1),
        lineage,
        0.91,
    )
    assert ok
    loaded = MacroTraitRegistry(reg_path).load()
    assert "customer-support" in loaded.entries
