"""User and project settings for ri-engine (optional features)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml

from ri_engine.paths import workspace_dir

DEFAULTS: dict[str, Any] = {
    "claude_code_handoff": False,
}

Scope = Literal["user", "project"]


def user_settings_path() -> Path:
    return Path.home() / ".config" / "ri-engine" / "settings.yaml"


def project_settings_path() -> Path:
    return workspace_dir() / ".ri-engine" / "settings.yaml"


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def load_settings() -> dict[str, Any]:
    """Merge defaults ← user config ← project config (project wins)."""
    settings = dict(DEFAULTS)
    settings.update(_read_yaml(user_settings_path()))
    settings.update(_read_yaml(project_settings_path()))
    return settings


def save_settings(settings: dict[str, Any], *, scope: Scope = "user") -> Path:
    path = project_settings_path() if scope == "project" else user_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(settings, sort_keys=False), encoding="utf-8")
    return path


def claude_code_handoff_enabled(*, override: bool | None = None) -> bool:
    if override is not None:
        return override
    return bool(load_settings().get("claude_code_handoff", False))


def set_claude_code_handoff(enabled: bool, *, scope: Scope = "user") -> Path:
    base = _read_yaml(user_settings_path() if scope == "user" else project_settings_path())
    merged = {**DEFAULTS, **base, "claude_code_handoff": enabled}
    return save_settings(merged, scope=scope)
