"""Tests for trait export bundles."""

import json
from pathlib import Path

from ri_engine.macro_registry import FORBIDDEN_EXPORT_FIELDS, export_trait_bundle
from ri_engine.trait_parser import ParsedTrait


def test_export_trait_bundle_schema(tmp_path, monkeypatch):
    monkeypatch.setattr("ri_engine.macro_registry.DEFAULT_EXPORT_DIR", tmp_path / "traits")
    monkeypatch.setattr("ri_engine.macro_registry.DEFAULT_REGISTRY_PATH", tmp_path / "registry.json")

    path = export_trait_bundle(
        objective_class="customer-support",
        fitness=0.88,
        traits=[
            ParsedTrait(
                name="constraint_first",
                instruction="Lead with measurable success criteria",
                evidence="utility=0.9",
            )
        ],
        cycles=2,
        plateaued=True,
        fitness_delta=0.07,
    )
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["objective_class"] == "customer-support"
    assert len(data["traits"]) == 1
    assert set(data["forbidden_omitted"]) == set(FORBIDDEN_EXPORT_FIELDS)
    blob = json.dumps({k: v for k, v in data.items() if k != "forbidden_omitted"})
    for forbidden in ("seed_prompt", "improved_prompt"):
        assert forbidden not in blob
