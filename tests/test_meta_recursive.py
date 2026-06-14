"""Tests for meta-recursive self-improvement round."""

from pathlib import Path

from ri_engine.meta_recursive import (
    META_PROMPTS_DIR,
    generate_all_metaprompts,
    synthesize_metaprompt,
)
from ri_engine.improve_prompts import PROMPTS_DIR


def test_synthesize_metaprompt_contains_diagnosis():
    content = (PROMPTS_DIR / "variation.md").read_text(encoding="utf-8")
    meta = (PROMPTS_DIR / "meta_improvement.md").read_text(encoding="utf-8")
    mp = synthesize_metaprompt("variation.md", content, meta)
    assert "META-RECURSIVE IMPROVEMENT" in mp
    assert "Structural score" in mp
    assert "Recursive mandates" in mp
    assert "variation.md" in mp


def test_generate_all_metaprompts(tmp_path, monkeypatch):
    import ri_engine.meta_recursive as mr

    monkeypatch.setattr(mr, "META_PROMPTS_DIR", tmp_path / "metaprompts")
    monkeypatch.setattr(mr, "META_OUTPUT", tmp_path)
    mps = generate_all_metaprompts()
    assert len(mps) >= 5
    assert (tmp_path / "metaprompts" / "manifest.json").exists()
    for name in ("variation.md", "selection.md", "meta_improvement.md"):
        assert name in mps
