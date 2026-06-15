"""Tests for linguistic registry pooling."""

from pathlib import Path

from ri_engine.language_leanings import LinguisticRegistry, load_spectrum_entries
from ri_engine.pool_linguistic_registry import pool_linguistic_registry


def test_pool_linguistic_registry_full_spectrum(tmp_path: Path):
    # Use subset for speed: copy first 2 spectrum entries to temp yaml
    from ri_engine.paths import config_dir

    spectrum_src = config_dir() / "linguistic_spectrum.yaml"
    import yaml

    data = yaml.safe_load(spectrum_src.read_text())
    data["entries"] = data["entries"][:2]
    spectrum_path = tmp_path / "spectrum.yaml"
    spectrum_path.write_text(yaml.dump(data), encoding="utf-8")

    registry_path = tmp_path / "linguistic_registry.json"
    summary = pool_linguistic_registry(
        spectrum_path=spectrum_path,
        registry_path=registry_path,
        validate_winners=False,
    )

    assert summary["cells_pooled"] == 2
    assert summary["coverage"]["spectrum_complete"] == 6
    assert registry_path.exists()

    reg = LinguisticRegistry(registry_path).load()
    assert len(reg.entries) == 2
    for entry in reg.entries.values():
        assert entry.recommended_leaning in summary["spectrum_leanings"]
        assert len(entry.spectrum_scores) == 6
