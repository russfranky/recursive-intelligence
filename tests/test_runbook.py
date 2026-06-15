"""Tests for local runbook storage and compilation."""

from __future__ import annotations

from pathlib import Path

from ri_engine.runbook import (
    approve_prompt,
    compile_runbook,
    default_runbook_dir,
    list_entries,
)


def test_approve_and_list_entries(tmp_path):
    rb = tmp_path / "runbook"
    entry = approve_prompt(
        name="customer-support",
        prompt="You are a support agent. Be kind.",
        objective="Handle tickets well",
        fitness=0.82,
        base=rb,
        metadata={"notes": "Approved after plateau"},
    )
    assert (rb / "prompts" / f"{entry.id}.md").exists()
    entries = list_entries(rb)
    assert len(entries) == 1
    assert entries[0].name == "customer-support"
    assert entries[0].fitness == 0.82


def test_compile_runbook_for_next_ai(tmp_path):
    rb = tmp_path / "runbook"
    approve_prompt(
        name="research",
        prompt="You research topics thoroughly.",
        objective="Deep research",
        fitness=0.9,
        base=rb,
    )
    compiled = compile_runbook(rb)
    assert compiled.exists()
    text = compiled.read_text(encoding="utf-8")
    assert "RUNBOOK" in text
    assert "research" in text
    assert "You research topics thoroughly." in text
    assert "next ai" in text.lower()


def test_default_runbook_dir_is_under_project():
    d = default_runbook_dir()
    assert d.name == "runbook"
