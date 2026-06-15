"""Tests for package path resolution."""

from pathlib import Path

from ri_engine import paths


def test_config_dir_has_templates():
    templates = paths.config_dir() / "templates"
    assert templates.is_dir()
    assert len(list(templates.glob("*.yaml"))) >= 6


def test_prompts_dir_has_operator_prompts():
    prompts = paths.prompts_dir()
    assert prompts.is_dir()
    assert len(list(prompts.glob("*.md"))) >= 5


def test_bundled_data_available_for_wheel_layout():
    bundled = paths.package_dir() / "bundled" / "config"
    assert bundled.is_dir() or (paths.config_dir() / "templates").is_dir()
