"""
Client view — plain-language presentation layer for commercial users.

Translates engine internals into outcomes anyone can understand.
Technical details remain available via expert mode (--expert).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console

from ri_engine.paths import config_dir

TEMPLATES_DIR = config_dir() / "templates"

# Friendly labels (what users see)
PHASE_FRIENDLY = {
    "membrane": "Finding fresh ideas",
    "variation": "Trying new versions",
    "selection": "Picking the best",
    "retention": "Keeping what works",
    "converge": "Wrapping up",
    "init": "Getting started",
    "done": "Complete",
}

LEANING_FRIENDLY = {
    "plain": "Clear, everyday language",
    "latinate": "Formal, professional tone",
    "mixed": "Plain instructions + expert terms where needed",
    "neutral": "No style preference — clarity first",
    "technical": "Specialist vocabulary",
    "conversational": "Friendly, natural tone",
}

STATUS_FRIENDLY = {
    "converged": "Finished — quality plateau reached",
    "completed": "Finished — all improvement rounds done",
    "running": "Improving your prompt…",
}


def list_templates() -> list[dict[str, str]]:
    """Return plug-and-play templates for mainstream users."""
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


# Maps business category to gate audience (internal — not shown to users)
_GATE_AUDIENCE: dict[str, str] = {
    "Software Engineering": "developer",
    "Agentic Development": "developer",
    "Operations": "end_user",
    "Research & Intelligence": "researcher",
    "Revenue": "prospect",
    "Security": "operator",
}


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
    """Convert technical engine report into a mainstream-friendly summary."""
    meta = report.get("meta", {})
    gate = report.get("linguistic_gate", {})
    config = report.get("config", {})

    fitness = report.get("best_fitness")
    quality_pct = f"{fitness:.0%}" if fitness is not None else "—"
    rounds = meta.get("generations_run", 0)
    converged = meta.get("converged", False)

    leaning = gate.get("leaning", "plain")
    style = LEANING_FRIENDLY.get(leaning, leaning)
    style_note = ""
    if gate:
        conf = gate.get("confidence", 0)
        style_note = f"{style} ({conf:.0%} match for your task type)"

    status = STATUS_FRIENDLY["converged" if converged else "completed"]

    summary: dict[str, Any] = {
        "headline": _headline(fitness, converged, rounds),
        "status": status,
        "quality_score": quality_pct,
        "improvement_rounds": rounds,
        "writing_style": style_note or style,
        "your_improved_prompt": clean_prompt_for_client(report.get("best_prompt", "")),
        "ready_to_use": True,
        "what_we_did": [
            "Matched the best writing style for your task type",
            "Added clear steps, output format, and quality checks",
            "Removed vague wording that causes AI mistakes",
            f"Ran {rounds} round{'s' if rounds != 1 else ''} of automatic improvement",
        ],
        "next_step": "Copy 'your_improved_prompt' into your AI assistant as the system prompt.",
    }

    if gate.get("rationale"):
        summary["style_reason"] = _plain_rationale(gate["rationale"])

    objective = config.get("objective", "")
    if objective:
        summary["your_goal"] = objective.split("\n")[0][:120]

    return summary


def _headline(fitness: float | None, converged: bool, rounds: int) -> str:
    if fitness is None:
        return "Prompt improvement complete"
    if fitness >= 0.85:
        return "Your prompt is production-ready"
    if fitness >= 0.65:
        return "Your prompt is much stronger now"
    if converged:
        return f"Improvement finished after {rounds} rounds"
    return "Prompt improved — review and run again if needed"


def _plain_rationale(technical: str) -> str:
    """Strip jargon from gate rationale."""
    replacements = [
        ("composite", "overall score"),
        ("lat_ratio", "formality level"),
        ("latinate", "formal wording"),
        ("read=", "readability "),
        ("quality=", "quality "),
        ("wins", "works best"),
        ("runner-up", "second choice"),
    ]
    text = technical
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def print_client_result(console: Console, report: dict, *, output_path: Path | None = None) -> dict:
    """Print and optionally save a mainstream-friendly result summary."""
    summary = build_client_summary(report)

    from ri_engine.terminal_ui import print_result

    print_result(console, summary)

    if output_path:
        payload = {
            "client_summary": summary,
            "technical_report": report if False else None,  # omit by default in client file
        }
        # Client file: summary only + prompt
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
    """Remove internal directives; use mainstream section labels."""
    lines = []
    for line in prompt.splitlines():
        if "MANDATORY LINGUISTIC LEANING" in line or "MANDATORY REGISTER" in line:
            continue
        line = line.replace("## Linguistic Leaning", "## Tone & Style")
        lines.append(line)
    return "\n".join(lines).strip()


def expert_mode_enabled(args: Any) -> bool:
    return getattr(args, "expert", False)
