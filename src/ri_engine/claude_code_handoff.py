"""Optional Claude Code terminal handoff after improve runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel

from ri_engine.runbook import approve_prompt, compile_runbook, default_runbook_dir


def handoff_after_improve(
    console: Console,
    *,
    report: dict[str, Any],
    output_path: Path | None,
    runbook_name: str = "claude-code-agent",
) -> Path | None:
    """
    When Claude Code handoff is enabled: approve prompt to runbook and print next steps.
    """
    prompt = str(report.get("best_prompt", "")).strip()
    if not prompt:
        return None

    config = report.get("config") or {}
    objective = str(config.get("objective", ""))
    fitness = float(report.get("best_fitness") or 0.0)
    meta = dict(config.get("metadata") or {})
    meta["handoff"] = "claude_code"

    entry_id = approve_prompt(
        name=runbook_name,
        objective=objective,
        prompt=prompt,
        fitness=fitness,
        metadata=meta,
        base=default_runbook_dir(),
    ).id
    runbook_path = compile_runbook()

    json_hint = str(output_path) if output_path else "output/your_improved_prompt.json"
    body = (
        "Claude Code handoff is **on**.\n\n"
        f"1. Runbook entry: `{entry_id}` → `{runbook_path}`\n"
        f"2. JSON snapshot: `{json_hint}`\n"
        "3. In Claude Code, start with:\n\n"
        "   Read `runbook/RUNBOOK.md` and follow the approved prompt for this project. "
        "Research before editing; spec before implement.\n\n"
        "Turn off globally: `ri-engine config claude-code off`\n"
        "Turn off once: `--no-claude-code`"
    )
    console.print()
    console.print(Panel(body, title="Claude Code handoff", border_style="cyan"))
    return runbook_path


def print_claude_code_handoff(console: Console, *, runbook_path: Path | None = None, output_path: Path | None = None) -> None:
    """Instructions only — runbook already saved (e.g. via --runbook)."""
    rb = runbook_path or default_runbook_dir() / "RUNBOOK.md"
    json_hint = str(output_path) if output_path else "output/your_improved_prompt.json"
    body = (
        "Claude Code handoff is **on**.\n\n"
        f"1. Runbook: `{rb}`\n"
        f"2. JSON snapshot: `{json_hint}`\n"
        "3. In Claude Code, start with:\n\n"
        "   Read `runbook/RUNBOOK.md` and follow the approved prompt for this project. "
        "Research before editing; spec before implement.\n\n"
        "Turn off: `ri-engine config claude-code off` or `--no-claude-code`"
    )
    console.print()
    console.print(Panel(body, title="Claude Code handoff", border_style="cyan"))
