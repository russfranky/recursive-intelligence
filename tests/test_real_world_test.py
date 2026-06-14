"""Tests for real-world test prep and session building."""

from pathlib import Path

from ri_engine.real_world_test import (
    ACTIVE_CONFIG,
    build_run_config,
    prep_real_world_test,
    write_session_from_context,
)


def test_prep_creates_session_scaffold(tmp_path, monkeypatch):
    import ri_engine.real_world_test as rw

    monkeypatch.setattr(rw, "REAL_WORLD_CONFIG_DIR", tmp_path / "config")
    monkeypatch.setattr(rw, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(rw, "ACTIVE_CONFIG", tmp_path / "config" / "active.yaml")
    monkeypatch.setattr(rw, "SESSION_TEMPLATE", tmp_path / "config" / "session.template.yaml")

    manifest = prep_real_world_test(force=True)
    assert manifest["status"] == "ready"
    assert (tmp_path / "config" / "active.yaml").exists()


def test_write_session_from_context(tmp_path, monkeypatch):
    import ri_engine.real_world_test as rw

    monkeypatch.setattr(rw, "REAL_WORLD_CONFIG_DIR", tmp_path)
    monkeypatch.setattr(rw, "ACTIVE_CONFIG", tmp_path / "active.yaml")
    path = write_session_from_context(
        name="Acme Support Test",
        seed_prompt="You are a helper.",
        objective="Resolve tickets in one turn.",
        category="Operations",
        test_id="test-001",
    )
    assert path.exists()
    cfg = build_run_config(__import__("yaml").safe_load(path.read_text()))
    assert "Resolve tickets" in cfg.objective
    assert cfg.metadata.get("use_case") == "real_world"
