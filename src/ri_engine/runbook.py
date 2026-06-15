"""
Local runbook — compiled approved prompts for the next AI session to read.

Default location: ``runbook/RUNBOOK.md`` at the project root (next to output/).
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ri_engine.paths import workspace_dir

def default_runbook_dir() -> Path:
    """Project-local runbook directory (``runbook/`` in the current working directory)."""
    return workspace_dir() / "runbook"


@dataclass
class RunbookEntry:
    """One approved prompt in the runbook."""

    id: str
    name: str
    objective: str
    prompt: str
    fitness: float
    approved_at: str
    cycles: int = 1
    plateaued: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "prompt"


def runbook_dir(path: Path | str | None = None) -> Path:
    d = Path(path) if path else default_runbook_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "prompts").mkdir(parents=True, exist_ok=True)
    return d


def _index_path(base: Path) -> Path:
    return base / "index.json"


def load_index(base: Path | str | None = None) -> list[dict[str, Any]]:
    path = _index_path(runbook_dir(base))
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_index(entries: list[dict[str, Any]], base: Path | str | None = None) -> None:
    path = _index_path(runbook_dir(base))
    path.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def list_entries(base: Path | str | None = None) -> list[RunbookEntry]:
    fields = RunbookEntry.__dataclass_fields__
    return [
        RunbookEntry(**{k: v for k, v in e.items() if k in fields})
        for e in load_index(base)
    ]


def approve_prompt(
    *,
    name: str,
    objective: str,
    prompt: str,
    fitness: float,
    cycles: int = 1,
    plateaued: bool = True,
    metadata: dict[str, Any] | None = None,
    base: Path | str | None = None,
) -> RunbookEntry:
    """Add an approved prompt to the runbook and recompile RUNBOOK.md."""
    base_path = runbook_dir(base)
    slug = _slug(name)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    entry_id = f"{slug}-{ts}"

    entry = RunbookEntry(
        id=entry_id,
        name=name,
        objective=objective.strip(),
        prompt=prompt.strip(),
        fitness=fitness,
        approved_at=datetime.now(timezone.utc).isoformat(),
        cycles=cycles,
        plateaued=plateaued,
        metadata=metadata or {},
    )

    prompt_file = base_path / "prompts" / f"{entry_id}.md"
    prompt_file.write_text(
        f"# {entry.name}\n\n"
        f"**Objective:** {entry.objective}\n\n"
        f"**Fitness:** {entry.fitness:.1%} · **Cycles:** {entry.cycles} · "
        f"**Plateaued:** {entry.plateaued}\n\n"
        f"---\n\n{entry.prompt}\n",
        encoding="utf-8",
    )

    entries = load_index(base_path)
    entries.append({**entry.to_dict(), "prompt_file": str(prompt_file.relative_to(base_path))})
    save_index(entries, base_path)
    compile_runbook(base_path)
    _record_runbook_traits(objective, prompt, fitness, metadata or {})
    return entry


def _record_runbook_traits(
    objective: str,
    prompt: str,
    fitness: float,
    metadata: dict[str, Any],
) -> None:
    """Internal: approved runbook prompts feed macro trait pool."""
    from ri_engine.macro_registry import record_selection
    from ri_engine.models import Candidate, RunConfig
    from ri_engine.trait_parser import ParsedTrait

    cfg = RunConfig(seed_prompt=prompt[:500], objective=objective, metadata=metadata)
    traits = [
        ParsedTrait(
            name="runbook_approved",
            instruction="Approved production prompt after plateau",
            evidence=f"fitness={fitness:.0%}",
        )
    ]
    if metadata.get("plateau_reason"):
        traits.append(
            ParsedTrait(
                name="constraint_first",
                instruction="Plateau-stable prompt ready for deployment",
                evidence=str(metadata["plateau_reason"]),
            )
        )
    record_selection(
        cfg,
        Candidate(id="runbook", content=prompt[:200], generation=0),
        "\n".join(f"- [TRAIT:{t.name}] {t.instruction} (evidence: {t.evidence})" for t in traits),
        fitness,
    )


def compile_runbook(base: Path | str | None = None) -> Path:
    """Build RUNBOOK.md — single file for the next AI to read."""
    base_path = runbook_dir(base)
    entries = load_index(base_path)
    lines = [
        "# Prompt Runbook",
        "",
        "> Approved production prompts compiled by **ri-engine**.",
        "> Point your next AI session at this file before executing tasks.",
        "",
        "```",
        "Read runbook/RUNBOOK.md — use matching system prompts for each task type.",
        "```",
        "",
        f"*Last compiled: {datetime.now(timezone.utc).isoformat()} · {len(entries)} entries*",
        "",
    ]

    if not entries:
        lines.extend([
            "",
            "_No approved prompts yet. Run:_",
            "",
            "```bash",
            "ri-engine improve --template customer-support --until-plateau --runbook",
            "```",
            "",
        ])
    else:
        for e in entries:
            name = e.get("name", e.get("id", "prompt"))
            lines.extend([
                "---",
                "",
                f"## {name}",
                "",
                f"- **ID:** `{e.get('id', '')}`",
                f"- **Approved:** {e.get('approved_at', '')}",
                f"- **Objective:** {e.get('objective', '').split(chr(10))[0]}",
                f"- **Fitness:** {e.get('fitness', 0):.1%}",
                f"- **Improvement cycles:** {e.get('cycles', 1)}",
                f"- **Plateau reached:** {e.get('plateaued', True)}",
                "",
                "### System prompt",
                "",
                "```markdown",
                e.get("prompt", "").strip(),
                "```",
                "",
            ])

    out = base_path / "RUNBOOK.md"
    out.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return out


def get_entry(name_or_id: str, base: Path | str | None = None) -> RunbookEntry | None:
    for e in list_entries(base):
        if e.id == name_or_id or e.name == name_or_id or _slug(e.name) == _slug(name_or_id):
            return e
    return None
