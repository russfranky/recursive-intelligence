"""Tests for linguistic leanings registry and gate."""

from pathlib import Path

import yaml

from ri_engine.language_leanings import (
    SPECTRUM_LEANINGS,
    LinguisticRegistry,
    apply_linguistic_gate,
    detect_linguistic_leaning,
    load_spectrum_entries,
    resolve_linguistic_direction,
)
from ri_engine.models import RunConfig


def test_spectrum_has_full_coverage():
    assert len(SPECTRUM_LEANINGS) == 6
    assert "plain" in SPECTRUM_LEANINGS
    assert "latinate" in SPECTRUM_LEANINGS
    assert "conversational" in SPECTRUM_LEANINGS


def test_detect_linguistic_leaning_from_objective():
    assert detect_linguistic_leaning("Use formal Latinate register throughout") == "latinate"
    assert detect_linguistic_leaning("Use plain Anglo-Saxon English") == "plain"
    assert detect_linguistic_leaning("Use casual, user-friendly language") == "conversational"


def test_resolve_uses_registry_when_present(tmp_path: Path):
    registry_path = tmp_path / "registry.json"
    from ri_engine.language_leanings import LanguageLeaningEntry

    reg = LinguisticRegistry(registry_path)
    reg.upsert(
        LanguageLeaningEntry(
            id="security:operator",
            category="Security",
            audience="operator",
            task_type="agent_prompt",
            recommended_leaning="plain",
            confidence=0.91,
            spectrum_scores={"plain": {"composite": 0.95}},
            rationale="test entry",
        )
    )
    reg.save()

    config = RunConfig(
        seed_prompt="You are a security analyst.",
        objective="Handle incidents.",
        metadata={"category": "Security", "audience": "operator"},
    )
    gate = resolve_linguistic_direction(config, reg)
    assert gate.leaning == "plain"
    assert gate.source == "registry"
    assert gate.confidence == 0.91


def test_apply_linguistic_gate_injects_clause():
    config = RunConfig(
        seed_prompt="Help the user.",
        objective="Resolve support tickets quickly.",
        metadata={"category": "Operations", "audience": "end_user", "apply_linguistic_gate": True},
    )
    updated, gate = apply_linguistic_gate(config)
    assert gate.leaning in SPECTRUM_LEANINGS
    assert "MANDATORY LINGUISTIC LEANING" in updated.objective
    assert updated.metadata["linguistic_leaning"] == gate.leaning


def test_spectrum_yaml_loads_all_cells():
    entries = load_spectrum_entries()
    assert len(entries) >= 9
    categories = {e["category"] for e in entries}
    assert "Legal & Compliance" in categories
    assert "Clinical & Medical" in categories
