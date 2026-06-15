"""Resolve paths for editable installs, PyPI wheels, and user-writable output."""

from __future__ import annotations

from pathlib import Path

_PKG = Path(__file__).resolve().parent


def package_dir() -> Path:
    return _PKG


def resource_root() -> Path:
    """Directory containing bundled ``config/`` and ``prompts/``."""
    bundled = _PKG / "bundled"
    if (bundled / "config").is_dir():
        return bundled
    repo = _PKG.parents[1]
    if (repo / "config").is_dir():
        return repo
    return bundled


def config_dir() -> Path:
    return resource_root() / "config"


def prompts_dir() -> Path:
    return resource_root() / "prompts"


def workspace_dir() -> Path:
    """User-writable project dir for ``output/``, ``runbook/``, and session files."""
    return Path.cwd()


def resolve_resource_path(relative: str | Path) -> Path:
    """Resolve bundled paths such as ``config/use_cases/foo.yaml``."""
    path = Path(relative)
    if path.is_absolute():
        return path
    return resource_root() / path
