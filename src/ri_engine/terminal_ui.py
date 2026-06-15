"""
Terminal presentation — Grok-inspired dark TUI character for ri-engine.

Minimal header, live stream, witty status lines, footer hint bar.
"""

from __future__ import annotations

import random
from typing import Iterable

from rich.box import MINIMAL, ROUNDED
from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from ri_engine import __version__

# Dark, minimal palette — white on black with cool accent (Grok-adjacent)
RI_THEME = Theme(
    {
        "brand": "bold white",
        "brand.dim": "dim white",
        "accent": "bold cyan",
        "accent.dim": "cyan",
        "success": "bold green",
        "warn": "yellow",
        "error": "bold red",
        "muted": "dim white",
        "highlight": "reverse bold white",
        "prompt": "white",
        "quip": "italic dim cyan",
    }
)

BRAND = "ri-engine"
TAGLINE = "variation → selection → retention"

PHASE_QUIPS: dict[str, list[str]] = {
    "init": [
        "booting the selection environment. no prompts were harmed. yet.",
        "warming up. darwin coded this part himself. allegedly.",
    ],
    "membrane": [
        "cross-pollinating ideas from unrelated domains. chaotic good.",
        "stealing structural tricks from adjacent fields. tastefully.",
    ],
    "variation": [
        "spawning variants. survival of the clearest.",
        "trying new versions. most will not make it. natural selection.",
    ],
    "selection": [
        "judging candidates. harsh rubric, fair outcomes.",
        "scoring fitness. engagement-bait does not survive here.",
    ],
    "retention": [
        "keeping winners. the rest become cautionary tales.",
        "distilling what worked into the next generation.",
    ],
    "converge": [
        "plateau detected. your prompt has opinions now.",
        "convergence. diminishing returns accepted gracefully.",
    ],
    "done": [
        "done. seed in, fitness-scored prompt out.",
        "finished. mock rubric scored — verify on your real task.",
    ],
}

WELCOME_HINTS = [
    "integrate init",
    "integrate improve",
    "improve --seed prompt.txt --goal \"When this works, the AI will …\"",
    "demo",
    "templates",
]

IMPROVE_HINTS = [
    "until-plateau --runbook",
    "real-world workflow",
    "config claude-code on",
    "Ctrl+C: stop",
    "--quiet: no animation",
    "--until-plateau: cycle until stable",
    "--runbook: save to local runbook",
]


def make_console(*, stderr: bool = False) -> Console:
    """Themed console for all interactive ri-engine output."""
    return Console(theme=RI_THEME, stderr=stderr, highlight=False)


def phase_quip(phase: str, *, seed: int = 0) -> str:
    """Deterministic-ish witty line for a VSR phase."""
    options = PHASE_QUIPS.get(phase, PHASE_QUIPS["init"])
    if not options:
        return ""
    rng = random.Random(seed + hash(phase) % 9973)
    return rng.choice(options)


def hint_bar(hints: Iterable[str], *, prefix: str = "") -> Text:
    """Grok-style footer: Enter:run │ Tab:next │ …"""
    parts = list(hints)
    if prefix:
        parts.insert(0, prefix)
    line = Text()
    for i, hint in enumerate(parts):
        if i:
            line.append(" │ ", style="muted")
        if ":" in hint:
            key, _, val = hint.partition(":")
            line.append(key, style="accent")
            line.append(":", style="muted")
            line.append(val, style="prompt")
        else:
            line.append(hint, style="prompt")
    return line


def print_brand_bar(console: Console, *, subtitle: str = TAGLINE, right: str = "") -> None:
    """Top bar: brand + version."""
    left = Text.assemble((BRAND, "brand"), ("  ", ""), (subtitle, "brand.dim"))
    header = Table.grid(expand=True)
    header.add_column(justify="left")
    header.add_column(justify="right")
    header.add_row(left, Text(right or f"v{__version__}", style="muted"))
    console.print(Panel(header, box=MINIMAL, border_style="white", padding=(0, 1)))


def print_welcome(console: Console | None = None) -> None:
    con = console or make_console()
    print_brand_bar(con)
    con.print()
    con.print(Text("seed + goal in. VSR-scored prompt out.", style="quip"))
    con.print()
    rows = Table(show_header=False, box=None, padding=(0, 2), expand=True)
    rows.add_column(style="accent", width=14)
    rows.add_column(style="prompt")
    rows.add_row("templates", "see ready-made starting points")
    rows.add_row("improve", "run recursive improvement on your prompt")
    rows.add_row("demo", "proof: 6 scenarios, F → A")
    con.print(rows)
    con.print()
    con.print(Rule(style="dim white"))
    con.print(hint_bar(WELCOME_HINTS))
    con.print()


def print_run_intro(
    console: Console,
    *,
    template: str = "",
    rounds: int = 5,
    mode: str = "improve",
) -> None:
    """Brief intro before improve/demo runs."""
    subtitle = "demo proof" if mode == "demo" else "improving…"
    print_brand_bar(console, subtitle=subtitle, right=f"{rounds} rounds max")
    if template:
        console.print(Text(f"template: {template}", style="accent.dim"))
    console.print(Text(phase_quip("init", seed=rounds), style="quip"))
    console.print()


def print_templates(console: Console) -> None:
    from ri_engine.client_view import list_templates

    print_brand_bar(console, subtitle="templates")
    console.print()
    table = Table(show_header=True, header_style="accent", box=MINIMAL, expand=True)
    table.add_column("name", style="prompt")
    table.add_column("best for", style="muted")
    table.add_column("command", style="accent.dim")
    for t in list_templates():
        desc = t["description"]
        if len(desc) > 52:
            desc = desc[:49] + "…"
        table.add_row(t["name"], desc, f"improve -t {t['id']}")
    console.print(table)
    console.print()
    console.print(hint_bar(["improve -t code-review", "demo"]))


def print_result(console: Console, summary: dict) -> None:
    """Grok-style result: headline + prompt block + hints."""
    console.print()
    print_brand_bar(
        console,
        subtitle=summary.get("headline", "complete"),
        right=str(summary.get("fitness_score", summary.get("quality_score", ""))),
    )
    console.print()
    meta = Table(show_header=False, box=None, padding=(0, 2))
    meta.add_column(style="muted")
    meta.add_column(style="prompt")
    meta.add_row("status", summary.get("status", ""))
    meta.add_row("fitness", summary.get("fitness_score", summary.get("quality_score", "")))
    meta.add_row("style", summary.get("writing_style", ""))
    meta.add_row("rounds", str(summary.get("improvement_rounds", "")))
    if note := summary.get("scope_note"):
        meta.add_row("scope", note)
    console.print(meta)
    console.print()
    console.print(Text("what changed", style="accent"))
    for item in summary.get("what_we_did", []):
        console.print(Text.assemble(("  · ", "muted"), (item, "prompt")))
    console.print()
    console.print(Panel(
        summary.get("your_improved_prompt", ""),
        title="[accent]your improved prompt[/] — copy this",
        border_style="white",
        box=ROUNDED,
        padding=(1, 2),
    ))
    if note := summary.get("curation_note"):
        console.print(Text(note, style="warn"))
        console.print()
    console.print(Text(summary.get("next_step", ""), style="quip"))
    console.print()
    console.print(hint_bar(["improve again", "demo", "templates"]))


def print_demo_result(console: Console, summary: dict) -> None:
    metrics = summary.get("proof_metrics", {})
    print_brand_bar(
        console,
        subtitle="demo proof",
        right=f"{summary.get('use_cases_run', 0)} scenarios",
    )
    console.print()
    console.print(Text.assemble(
        ("avg quality  ", "muted"),
        (f"{metrics.get('avg_quality_before', 0):.0%}", "error"),
        (" → ", "muted"),
        (f"{metrics.get('avg_quality_after', 0):.0%}", "success"),
        (f"  (+{metrics.get('avg_improvement_pct', 0):.0f}%)", "accent"),
    ))
    console.print(Text("every scenario improved. no hand-waving.", style="quip"))
    console.print()
    table = Table(show_header=True, header_style="accent", box=MINIMAL)
    table.add_column("use case")
    table.add_column("before", justify="right")
    table.add_column("after", justify="right")
    table.add_column("gain", justify="right", style="success")
    for r in summary.get("use_cases", []):
        table.add_row(
            r.get("name", "")[:30],
            f"{r.get('quality_before', 0):.0%}",
            f"{r.get('quality_after', 0):.0%}",
            f"+{r.get('quality_delta_pct', 0):.0f}%",
        )
    console.print(table)
    console.print()
    console.print(hint_bar(["improve -t customer-support", "templates"]))


def print_plateau_cycle(
    console: Console,
    *,
    cycle: int,
    max_cycles: int,
    fitness: float,
    previous_fitness: float | None = None,
) -> None:
    """Status line between outer plateau cycles."""
    delta = ""
    if previous_fitness is not None:
        change = fitness - previous_fitness
        sign = "+" if change >= 0 else ""
        delta = f"  ({sign}{change:.1%} vs last cycle)"
    console.print(
        Text.assemble(
            (f"cycle {cycle}/{max_cycles}", "accent"),
            ("  ·  fitness ", "muted"),
            (f"{fitness:.1%}", "success"),
            (delta, "muted"),
        )
    )
    console.print(Text(phase_quip("converge", seed=cycle), style="quip"))


def print_plateau_complete(
    console: Console,
    *,
    cycles_run: int,
    plateau_reason: str,
    fitness: float,
    runbook_path: str = "",
) -> None:
    """Summary after multi-cycle plateau run."""
    reason = {
        "fitness_plateau": "fitness plateau — gains tapered off",
        "unchanged_prompt": "prompt stable — no further edits",
        "max_cycles": "max cycles reached",
    }.get(plateau_reason, plateau_reason)
    console.print()
    console.print(
        Text.assemble(
            ("plateau reached", "accent"),
            ("  ·  ", "muted"),
            (f"{cycles_run} cycle{'s' if cycles_run != 1 else ''}", "prompt"),
            ("  ·  ", "muted"),
            (reason, "muted"),
        )
    )
    console.print(Text.assemble(("final fitness ", "muted"), (f"{fitness:.1%}", "success")))
    if runbook_path:
        console.print(Text.assemble(("runbook ", "muted"), (runbook_path, "accent")))
        console.print(Text("next AI session: point it at runbook/RUNBOOK.md", style="quip"))
    console.print()
