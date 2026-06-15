"""Tests for user settings and Claude Code handoff toggle."""

from ri_engine.user_settings import (
    claude_code_handoff_enabled,
    load_settings,
    project_settings_path,
    set_claude_code_handoff,
)


def test_claude_code_handoff_default_off():
    assert claude_code_handoff_enabled() is False


def test_set_claude_code_handoff_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = set_claude_code_handoff(True, scope="project")
    assert path == project_settings_path()
    assert claude_code_handoff_enabled() is True
    settings = load_settings()
    assert settings["claude_code_handoff"] is True

    set_claude_code_handoff(False, scope="project")
    assert claude_code_handoff_enabled() is False


def test_claude_code_override():
    assert claude_code_handoff_enabled(override=True) is True
    assert claude_code_handoff_enabled(override=False) is False
