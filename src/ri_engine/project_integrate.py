"""Plug-and-play project integration — drop ri-engine into any active repo."""

from __future__ import annotations

import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from ri_engine.paths import config_dir, workspace_dir

MANIFEST_PATH = Path(".ri-engine/project.yaml")
DEFAULT_CONFIG_DIR = "ri/config"
DEFAULT_SEED_DIR = "prompts/seed"
SCAFFOLD_DIR = config_dir() / "integration" / "scaffold"

DEFAULT_OBJECTIVE = (
    "When this works, agents read runbook/RUNBOOK.md, research before editing, "
    "write a short spec, wait for proceed, then implement — with falsifiable success criteria."
)

GITIGNORE_LINES = (
    "# ri-engine local artifacts",
    "config/macro_trait_registry.json",
    "output/real_world/",
)

SEED_CANDIDATES = (
    "CLAUDE.md",
    "AGENTS.md",
    ".cursorrules",
    "docs/AGENTS.md",
)


@dataclass
class IntegrationManifest:
    version: int = 1
    project_name: str = ""
    agent_name: str = ""
    agent_slug: str = ""
    config_path: str = ""
    seed_path: str = ""
    docs_path: str = "docs/prompt-improvement.md"
    runbook_dir: str = "runbook"
    integrated_at: str = ""
    objective: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IntegrationManifest:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def manifest_path() -> Path:
    return workspace_dir() / MANIFEST_PATH


def load_manifest() -> IntegrationManifest | None:
    path = manifest_path()
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None
    return IntegrationManifest.from_dict(data)


def save_manifest(manifest: IntegrationManifest) -> Path:
    path = manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(manifest.to_dict(), sort_keys=False), encoding="utf-8")
    return path


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "project-agent"


def _title(text: str) -> str:
    return text.replace("-", " ").replace("_", " ").title()


def detect_project_name() -> str:
    root = workspace_dir()
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        for line in pyproject.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("name"):
                m = re.search(r'name\s*=\s*["\']([^"\']+)', line)
                if m:
                    return m.group(1).strip()
    package = root / "package.json"
    if package.is_file():
        try:
            import json

            data = json.loads(package.read_text(encoding="utf-8"))
            if name := data.get("name"):
                return str(name).lstrip("@").split("/")[-1]
        except (json.JSONDecodeError, OSError):
            pass
    return root.name


def _read_template(name: str) -> str:
    path = SCAFFOLD_DIR / name
    if not path.is_file():
        repo_path = workspace_dir() / "config" / "integration" / "scaffold" / name
        if repo_path.is_file():
            path = repo_path
        else:
            raise FileNotFoundError(f"Integration scaffold missing: {name}")
    return path.read_text(encoding="utf-8")


def _render(template: str, mapping: dict[str, str]) -> str:
    out = template
    for key, value in mapping.items():
        out = out.replace(f"{{{{{key}}}}}", value)
    return out


def _find_existing_seed_content() -> str | None:
    root = workspace_dir()
    for name in SEED_CANDIDATES:
        path = root / name
        if path.is_file() and path.stat().st_size > 50:
            return path.read_text(encoding="utf-8").strip()
    return None


def _ensure_gitignore_lines() -> bool:
    path = workspace_dir() / ".gitignore"
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    to_add = [ln for ln in GITIGNORE_LINES if ln not in existing]
    if not to_add:
        return False
    block = "\n".join(to_add) + "\n"
    if path.is_file():
        path.write_text(existing.rstrip() + "\n\n" + block, encoding="utf-8")
    else:
        path.write_text(block, encoding="utf-8")
    return True


def init_project_integration(
    *,
    name: str = "",
    objective: str = "",
    config_dir_name: str = DEFAULT_CONFIG_DIR,
    from_claude: bool = True,
    claude_code_handoff: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """
    Scaffold ri-engine into the current repo (plug-and-play).
    Idempotent: skips existing files unless force=True.
    """
    root = workspace_dir()
    project_name = detect_project_name()
    agent_slug = _slug(name or f"{project_name}-agent")
    agent_title = _title(agent_slug)
    obj = (objective or DEFAULT_OBJECTIVE).strip()

    cfg_dir = root / config_dir_name
    seed_dir = root / DEFAULT_SEED_DIR
    cfg_dir.mkdir(parents=True, exist_ok=True)
    seed_dir.mkdir(parents=True, exist_ok=True)
    (root / "runbook").mkdir(parents=True, exist_ok=True)
    (root / "runbook" / "prompts").mkdir(parents=True, exist_ok=True)
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "output").mkdir(parents=True, exist_ok=True)

    config_path = cfg_dir / f"{agent_slug}.yaml"
    seed_path = seed_dir / f"{agent_slug}.md"
    docs_path = root / "docs" / "prompt-improvement.md"

    mapping = {
        "PROJECT_NAME": project_name,
        "AGENT_NAME": agent_slug,
        "AGENT_SLUG": agent_slug,
        "AGENT_TITLE": agent_title,
        "OBJECTIVE": obj,
        "SEED_PATH": str(seed_path.relative_to(root)),
        "CONFIG_PATH": str(config_path.relative_to(root)),
    }

    created: list[str] = []
    skipped: list[str] = []

    def _write(path: Path, content: str) -> None:
        if path.exists() and not force:
            skipped.append(str(path.relative_to(root)))
            return
        path.write_text(content, encoding="utf-8")
        created.append(str(path.relative_to(root)))

    if from_claude and (existing := _find_existing_seed_content()):
        seed_body = (
            f"# {agent_title}\n\n"
            f"> Merged from existing project instructions. Original canon preserved below.\n\n"
            f"{existing}\n\n"
            f"---\n\n"
            f"{_render(_read_template('seed.md.template'), mapping)}"
        )
    else:
        seed_body = _render(_read_template("seed.md.template"), mapping)
    _write(seed_path, seed_body)

    _write(config_path, _render(_read_template("config.yaml.template"), mapping))
    _write(docs_path, _render(_read_template("prompt-improvement.md.template"), mapping))

    gitkeep = root / "runbook" / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()
        created.append(str(gitkeep.relative_to(root)))

    from ri_engine.runbook import compile_runbook

    compile_runbook(root / "runbook")

    manifest = IntegrationManifest(
        project_name=project_name,
        agent_name=agent_title,
        agent_slug=agent_slug,
        config_path=str(config_path.relative_to(root)),
        seed_path=str(seed_path.relative_to(root)),
        docs_path=str(docs_path.relative_to(root)),
        runbook_dir="runbook",
        integrated_at=datetime.now(timezone.utc).isoformat(),
        objective=obj,
    )
    save_manifest(manifest)

    if claude_code_handoff:
        from ri_engine.user_settings import set_claude_code_handoff

        set_claude_code_handoff(True, scope="project")
        created.append(".ri-engine/settings.yaml")

    gitignore_updated = _ensure_gitignore_lines()

    return {
        "status": "integrated",
        "project_name": project_name,
        "agent_slug": agent_slug,
        "manifest": str(MANIFEST_PATH),
        "config_path": str(config_path.relative_to(root)),
        "seed_path": str(seed_path.relative_to(root)),
        "runbook": "runbook/RUNBOOK.md",
        "created": created,
        "skipped": skipped,
        "gitignore_updated": gitignore_updated,
        "next_commands": [
            "ri-engine integrate improve",
            "ri-engine integrate status",
            f"Edit {seed_path.relative_to(root)} — add canon + anti-patterns",
        ],
    }


def integration_status() -> dict[str, Any]:
    manifest = load_manifest()
    root = workspace_dir()
    if not manifest:
        return {
            "integrated": False,
            "message": "Not integrated. Run: ri-engine integrate init",
        }
    paths = {
        "manifest": manifest_path().is_file(),
        "config": (root / manifest.config_path).is_file(),
        "seed": (root / manifest.seed_path).is_file(),
        "runbook": (root / manifest.runbook_dir / "RUNBOOK.md").is_file(),
        "docs": (root / manifest.docs_path).is_file(),
    }
    return {
        "integrated": all(paths.values()),
        "manifest": manifest.to_dict(),
        "paths_ok": paths,
        "improve_command": "ri-engine integrate improve",
    }


def _safe_unlink(path: Path) -> bool:
    if path.is_file():
        path.unlink()
        return True
    return False


def _remove_runbook_entries_for_agent(agent_slug: str, runbook_base: Path) -> list[str]:
    """Remove runbook index entries and prompt files matching the integrated agent."""
    from ri_engine.runbook import compile_runbook, load_index, save_index

    if not runbook_base.is_dir():
        return []
    slug = _slug(agent_slug)
    removed: list[str] = []
    kept: list[dict[str, Any]] = []
    for entry in load_index(runbook_base):
        entry_slug = _slug(str(entry.get("name", "")))
        entry_id = str(entry.get("id", ""))
        if entry_slug == slug or entry_id.startswith(f"{slug}-"):
            pf = entry.get("prompt_file")
            if pf:
                prompt_path = runbook_base / pf
                if _safe_unlink(prompt_path):
                    removed.append(str(prompt_path))
            removed.append(f"runbook entry:{entry.get('id', '')}")
        else:
            kept.append(entry)
    if len(kept) != len(load_index(runbook_base)):
        save_index(kept, runbook_base)
        compile_runbook(runbook_base)
    return removed


def reset_project_integration(
    *,
    yes: bool = False,
    keep_runbook: bool = False,
    keep_settings: bool = False,
    reinit: bool = False,
    name: str = "",
) -> dict[str, Any]:
    """
    Remove integration scaffold files and manifest so you can start fresh.
    Dry-run by default — pass yes=True to execute.
    """
    root = workspace_dir()
    manifest = load_manifest()
    agent_slug = _slug(name or (manifest.agent_slug if manifest else "") or f"{detect_project_name()}-agent")

    targets: list[Path] = []
    if manifest:
        for rel in (manifest.config_path, manifest.seed_path, manifest.docs_path):
            if rel:
                targets.append(root / rel)
        targets.append(manifest_path())
        if not keep_settings:
            targets.append(root / ".ri-engine" / "settings.yaml")
        targets.append(root / "output" / f"{manifest.agent_slug}-improved.json")
        runbook_base = root / manifest.runbook_dir
        runbook_agent = manifest.agent_slug
    else:
        targets.extend([
            root / DEFAULT_CONFIG_DIR / f"{agent_slug}.yaml",
            root / DEFAULT_SEED_DIR / f"{agent_slug}.md",
            root / "docs" / "prompt-improvement.md",
            manifest_path(),
        ])
        if not keep_settings:
            targets.append(root / ".ri-engine" / "settings.yaml")
        targets.append(root / "output" / f"{agent_slug}-improved.json")
        runbook_base = root / "runbook"
        runbook_agent = agent_slug

    # De-dupe while preserving order
    seen: set[str] = set()
    unique_targets: list[Path] = []
    for p in targets:
        key = str(p)
        if key not in seen:
            seen.add(key)
            unique_targets.append(p)

    would_remove = [str(p.relative_to(root)) for p in unique_targets if p.is_file()]

    runbook_removals: list[str] = []
    if not keep_runbook:
        from ri_engine.runbook import load_index

        slug = _slug(runbook_agent)
        if runbook_base.is_dir():
            for entry in load_index(runbook_base):
                entry_slug = _slug(str(entry.get("name", "")))
                entry_id = str(entry.get("id", ""))
                if entry_slug == slug or entry_id.startswith(f"{slug}-"):
                    runbook_removals.append(f"runbook entry:{entry.get('id', '')}")

    if not yes:
        return {
            "status": "dry_run",
            "agent_slug": agent_slug,
            "would_remove": would_remove,
            "would_clean_runbook": runbook_removals,
            "message": "Re-run with: ri-engine integrate reset --yes",
            "next_commands": ["ri-engine integrate reset --yes", "ri-engine integrate init"],
        }

    removed: list[str] = []
    for path in unique_targets:
        if _safe_unlink(path):
            removed.append(str(path.relative_to(root)))

    if not keep_runbook and runbook_removals:
        removed.extend(_remove_runbook_entries_for_agent(runbook_agent, runbook_base))

    # Remove empty .ri-engine dir if only had manifest/settings
    ri_dir = root / ".ri-engine"
    if ri_dir.is_dir() and not any(ri_dir.iterdir()):
        ri_dir.rmdir()
        removed.append(".ri-engine/ (empty)")

    result: dict[str, Any] = {
        "status": "reset",
        "agent_slug": agent_slug,
        "removed": removed,
        "kept_runbook": keep_runbook,
        "kept_settings": keep_settings,
        "next_commands": ["ri-engine integrate init"],
    }

    if reinit:
        result["reinit"] = init_project_integration(name=agent_slug, from_claude=True, force=True)

    return result


def run_integrated_improve(
    *,
    provider: str | None = None,
    until_plateau: bool = True,
    runbook: bool = True,
    claude_code: bool | None = None,
    quiet: bool = False,
    expert: bool = False,
) -> dict[str, Any]:
    """Run improve using the integration manifest (recursive loop entry point)."""
    manifest = load_manifest()
    if not manifest:
        raise FileNotFoundError(
            "Project not integrated. Run: ri-engine integrate init"
        )
    config_path = workspace_dir() / manifest.config_path
    if not config_path.is_file():
        raise FileNotFoundError(f"Config missing: {config_path}. Re-run: ri-engine integrate init")

    import argparse

    from ri_engine.cli import _run_improve

    argv = ["improve", "--config", str(config_path)]
    if until_plateau:
        argv.append("--until-plateau")
    if runbook:
        argv.extend(["--runbook", "--runbook-name", manifest.agent_slug])
    if provider:
        argv.extend(["--provider", provider])
    if claude_code is True:
        argv.append("--claude-code")
    elif claude_code is False:
        argv.append("--no-claude-code")
    if quiet:
        argv.append("--quiet")
    if expert:
        argv.append("--expert")

    parser = __import__("ri_engine.cli", fromlist=["_build_parser"])._build_parser()
    args = parser.parse_args(argv)
    exit_code = _run_improve(args)
    return {
        "exit_code": exit_code,
        "config_path": str(config_path),
        "agent_slug": manifest.agent_slug,
        "runbook": f"{manifest.runbook_dir}/RUNBOOK.md",
        "curation_hint": (
            "Merge VSR output with canon/anti-patterns in seed before agents run. "
            f"See {manifest.docs_path}"
        ),
    }
