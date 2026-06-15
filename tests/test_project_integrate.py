"""Tests for plug-and-play project integration."""

from pathlib import Path

import yaml

from ri_engine.project_integrate import (
    init_project_integration,
    integration_status,
    load_manifest,
)


def test_init_scaffolds_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "CLAUDE.md").write_text("# My App\n\nAlways read runbook first.\n" * 5, encoding="utf-8")

    result = init_project_integration(name="my-app-agent", objective="When this works, tests pass.")

    assert result["status"] == "integrated"
    assert (tmp_path / "ri" / "config" / "my-app-agent.yaml").is_file()
    assert (tmp_path / "prompts" / "seed" / "my-app-agent.md").is_file()
    assert (tmp_path / "docs" / "prompt-improvement.md").is_file()
    assert (tmp_path / "runbook" / "RUNBOOK.md").is_file()
    assert (tmp_path / ".ri-engine" / "project.yaml").is_file()

    seed = (tmp_path / "prompts" / "seed" / "my-app-agent.md").read_text(encoding="utf-8")
    assert "My App" in seed
    assert "Anti-patterns" in seed

    manifest = load_manifest()
    assert manifest is not None
    assert manifest.agent_slug == "my-app-agent"


def test_init_idempotent_skips_existing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    first = init_project_integration(name="demo-agent")
    second = init_project_integration(name="demo-agent")
    assert first["created"]
    assert second["skipped"]


def test_integration_status(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    before = integration_status()
    assert before["integrated"] is False

    init_project_integration(name="status-agent")
    after = integration_status()
    assert after["integrated"] is True
    assert after["manifest"]["agent_slug"] == "status-agent"


def test_gitignore_updated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_project_integration(name="git-agent")
    gi = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert "macro_trait_registry.json" in gi


def test_manifest_roundtrip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_project_integration(name="round-agent", objective="When this works, x.")
    data = yaml.safe_load((tmp_path / ".ri-engine" / "project.yaml").read_text(encoding="utf-8"))
    assert data["objective"].startswith("When this works")
