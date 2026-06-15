"""
Client view — CLI presentation for improve() results.

Keeps engine output intact (including linguistic gate clauses). Expert mode
exposes the full VSR report via --expert.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console

from ri_engine.paths import config_dir

TEMPLATES_DIR = config_dir() / "templates"

STATUS_LABELS = {
    "converged": "VSR converged — fitness plateau",
    "completed": "VSR completed — all generations run",
    "running": "Running VSR…",
}

# Maps business category to gate audience (linguistic registry lookup key)
_GATE_AUDIENCE: dict[str, str] = {
    "Software Engineering": "developer",
    "Agentic Development": "developer",
    "Operations": "end_user",
    "Research & Intelligence": "researcher",
    "Revenue": "prospect",
    "Security": "operator",
}


def list_templates() -> list[dict[str, str]]:
    """Return benchmark/fixture templates (optional — not required for improve)."""
    templates: list[dict[str, str]] = []
    if not TEMPLATES_DIR.exists():
        return templates
    for path in sorted(TEMPLATES_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        templates.append({
            "id": path.stem,
            "name": data.get("display_name", path.stem.replace("-", " ").title()),
            "description": data.get("description", ""),
            "audience": data.get("audience", ""),
            "path": str(path),
        })
    return templates


def load_template(template_id: str) -> dict[str, Any]:
    """Load a named template by id (filename without .yaml)."""
    path = TEMPLATES_DIR / f"{template_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {template_id}. Run: ri-engine templates")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if ref := data.get("extends"):
        base_path = config_dir() / ref
        base = yaml.safe_load(base_path.read_text(encoding="utf-8"))
        merged_meta = {**base.get("metadata", {}), **data.get("metadata", {})}
        data = {**base, **{k: v for k, v in data.items() if k not in ("extends", "metadata")}}
        data["metadata"] = merged_meta
    return data


def template_to_metadata(data: dict[str, Any]) -> dict[str, Any]:
    category = data.get("category", "")
    return {
        **data.get("metadata", {}),
        "category": category,
        "audience": _GATE_AUDIENCE.get(category, "operator"),
        "apply_linguistic_gate": True,
    }


def print_welcome(console: Console) -> None:
    from ri_engine.terminal_ui import print_welcome as _tw

    _tw(console)


def print_templates(console: Console) -> None:
    from ri_engine.terminal_ui import print_templates as _tt

    _tt(console)


def build_client_summary(report: dict) -> dict[str, Any]:
    """Summarize a VSR run for CLI output."""
    meta = report.get("meta", {})
    gate = report.get("linguistic_gate", {})
    config = report.get("config", {})

    fitness = report.get("best_fitness")
    fitness_pct = f"{fitness:.0%}" if fitness is not None else "—"
    rounds = meta.get("generations_run", 0)
    converged = meta.get("converged", False)

    leaning = gate.get("leaning", "plain")
    style_note = leaning
    if gate:
        conf = gate.get("confidence", 0)
        style_note = f"{leaning} ({conf:.0%} from linguistic gate)"

    status = STATUS_LABELS["converged" if converged else "completed"]

    summary: dict[str, Any] = {
        "headline": _headline(fitness, converged, rounds),
        "status": status,
        "quality_score": fitness_pct,
        "improvement_rounds": rounds,
        "writing_style": style_note,
        "your_improved_prompt": clean_prompt_for_client(report.get("best_prompt", "")),
        "ready_to_use": True,
        "what_we_did": [
            "Resolved linguistic leaning (plain / latinate / mixed / …) from your goal",
            "Ran Variation → Selection → Retention cycles",
            "Applied Occam's razor tie-break where enabled",
            f"Completed {rounds} improvement round{'s' if rounds != 1 else ''}",
        ],
        "next_step": "Copy 'your_improved_prompt' into your system prompt.",
    }

    if gate.get("rationale"):
        summary["style_reason"] = gate["rationale"]

    objective = config.get("objective", "")
    if objective:
        summary["your_goal"] = objective.split("\n")[0][:120]

    return summary


def _headline(fitness: float | None, converged: bool, rounds: int) -> str:
    if fitness is None:
        return "VSR run complete"
    if fitness >= 0.85:
        return f"VSR complete — fitness {fitness:.0%}"
    if fitness >= 0.65:
        return f"VSR complete — fitness {fitness:.0%} (room to iterate)"
    if converged:
        return f"VSR converged after {rounds} rounds"
    return "VSR finished — review output and re-run if needed"


def print_client_result(console: Console, report: dict, *, output_path: Path | None = None) -> dict:
    """Print and optionally save improve() summary."""
    summary = build_client_summary(report)

    from ri_engine.terminal_ui import print_result

    print_result(console, summary)

    if output_path:
        client_payload = {
            "headline": summary["headline"],
            "quality_score": summary["quality_score"],
            "status": summary["status"],
            "writing_style": summary["writing_style"],
            "improvement_rounds": summary["improvement_rounds"],
            "what_we_did": summary["what_we_did"],
            "your_improved_prompt": summary["your_improved_prompt"],
            "next_step": summary["next_step"],
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(client_payload, indent=2), encoding="utf-8")
        console.print(f"\n[green]Saved:[/green] {output_path}")

    return summary


def print_demo_summary(console: Console, summary: dict) -> None:
    from ri_engine.terminal_ui import print_demo_result

    print_demo_result(console, summary)


def clean_prompt_for_client(prompt: str) -> str:
    """Return the improved prompt unchanged — linguistic gate output stays intact."""
    return prompt.strip()


def expert_mode_enabled(args: Any) -> bool:
    return getattr(args, "expert", False)
