"""
Meta-recursive round — metaprompt the system's own improvements, then evolve again.

1. Synthesize metaprompts from meta_improvement + structural diagnosis per operator
2. Round A: evolve each operator prompt against its metaprompt objective
3. Round B: standard VSR convergence pass on the metaprompt-evolved prompts
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ri_engine.improve_prompts import (
    BACKUP_DIR,
    CONFIG_PATH,
    OUTPUT_DIR,
    PROMPTS_DIR,
    _aggregate_composite,
    _composite_score,
    _load_config,
)
from ri_engine.models import RunConfig
from ri_engine.structural_scorer import apply_extension, score_prompt
from ri_engine.system_prompt_evolver import (
    OPERATOR_PRIORITIES,
    SystemPromptEvolver,
    _strip_generated_sections,
)

META_PROMPTS_DIR = OUTPUT_DIR / "meta_recursive" / "metaprompts"
META_OUTPUT = OUTPUT_DIR / "meta_recursive"

console = Console()

# Recursive improvement focus per operator (self-referential mandates)
OPERATOR_META_FOCUS: dict[str, str] = {
    "variation.md": (
        "Every variant must embed a scorable recursive hook so Selection can evaluate "
        "Output(N) as Input(N+1). Mutations must be structural, not synonym swaps."
    ),
    "selection.md": (
        "Fitness scoring must resist proxy optimization (engagement, length, speed). "
        "Output must be mechanically parseable for Retention lineage extraction."
    ),
    "retention.md": (
        "Lineage memory must encode heritable traits as bullet schema, not verbatim copies. "
        "Downstream Variation must breed from extracted traits without contamination."
    ),
    "membrane_bridge.md": (
        "Cross-domain correlations must be non-obvious deep structure, not surface analogy. "
        "Each correlation must specify a concrete mutation pressure for Variation."
    ),
    "meta_improvement.md": (
        "Diagnose which selection-environment ceiling is binding and prescribe the highest-leverage "
        "plateau breaker. Output must be YAML-actionable for the next meta-generation."
    ),
}

RECURSIVE_MANDATES = [
    "Output(N) → Input(N+1): every operator output must be scorable by the next iteration",
    "Block proxy optimization: utility and task fitness over engagement, length, or verbosity",
    "Commercial legibility: support plug-and-play delivery without exposing VSR jargon to end users",
    "Machine-actionable contracts: strict output formats parseable without human interpretation",
    "Recursive self-eval: score clarity, utility, coherence before finalizing; revise if any < 0.7",
]


def synthesize_metaprompt(
    operator_name: str,
    operator_content: str,
    meta_template: str,
    generation: int = 1,
) -> str:
    """Generate a meta-improvement objective for one operator prompt."""
    rubric = score_prompt(operator_content, operator_name)
    evolver = SystemPromptEvolver()
    traits = evolver.detect_traits(operator_content)
    focus = OPERATOR_META_FOCUS.get(operator_name, "Maximize recursive self-improvement hooks.")

    gap_block = "\n".join(f"  - {g}" for g in rubric.gaps[:6]) or "  - (none — maintain and compress)"
    rec_block = "\n".join(f"  - {r}" for r in rubric.recommendations[:4]) or "  - (none)"
    mandate_block = "\n".join(f"  {i + 1}. {m}" for i, m in enumerate(RECURSIVE_MANDATES))

    return f"""META-RECURSIVE IMPROVEMENT — Generation {generation}
Target operator: {operator_name}

## Diagnosis (structural rubric)
- Structural score: {rubric.total:.1%}
- Trait coverage: {len(traits)}/8 ({', '.join(traits[:4])}{'…' if len(traits) > 4 else ''})
- Operator focus: {focus}

## Gaps to close
{gap_block}

## Recommendations
{rec_block}

## Recursive mandates (all operators)
{mandate_block}

## Evolution objective
Evolve this operator system prompt to close all gaps above while preserving concision,
executable LLM-first-read clarity, and strict output format contracts.

The improved prompt must:
- Maximize agent reliability within the VSR pipeline
- Include explicit failure-mode guards and measurable success metrics
- Remain coherent with sibling operators (Membrane → Variation → Selection → Retention → Meta)
- Support commercial plug-and-play use: value exposed, internals hidden from end users

Do not add bloat. Prefer 4–5 highest-signal trait sections over exhaustive duplication.
Apply tier-2 operator-specific extensions where missing.

Reference meta-operator principles:
{meta_template[:400]}…
"""


def generate_all_metaprompts(generation: int = 1) -> dict[str, str]:
    """Synthesize metaprompts for every operator prompt."""
    meta_template = (PROMPTS_DIR / "meta_improvement.md").read_text(encoding="utf-8")
    META_PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

    metaprompts: dict[str, str] = {}
    for path in sorted(PROMPTS_DIR.glob("*.md")):
        if path.name == "meta_improvement.md":
            continue  # meta improves others; skip self-target for round A
        content = path.read_text(encoding="utf-8")
        mp = synthesize_metaprompt(path.name, content, meta_template, generation=generation)
        metaprompts[path.name] = mp
        out = META_PROMPTS_DIR / f"{path.stem}_metaprompt.md"
        out.write_text(mp, encoding="utf-8")

    # Meta-improvement metaprompt (self-referential)
    meta_content = (PROMPTS_DIR / "meta_improvement.md").read_text(encoding="utf-8")
    meta_mp = synthesize_metaprompt(
        "meta_improvement.md",
        meta_content,
        meta_template,
        generation=generation,
    )
    meta_mp += "\n## Self-referential mandate\nImprove this meta-operator's ability to diagnose "
    meta_mp += "plateaus and prescribe plateau breakers for the entire engine.\n"
    metaprompts["meta_improvement.md"] = meta_mp
    (META_PROMPTS_DIR / "meta_improvement_metaprompt.md").write_text(meta_mp, encoding="utf-8")

    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "generation": generation,
        "operators": list(metaprompts.keys()),
        "paths": {k: str(META_PROMPTS_DIR / f"{Path(k).stem}_metaprompt.md") for k in metaprompts},
    }
    (META_PROMPTS_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return metaprompts


def evolve_with_metaprompt(
    operator_path: Path,
    metaprompt: str,
    base_config: RunConfig,
    evolver: SystemPromptEvolver,
) -> dict:
    """Evolve one operator using its metaprompt as the selection objective."""
    original = operator_path.read_text(encoding="utf-8")
    config = RunConfig(
        seed_prompt=original[:200],
        objective=metaprompt,
        max_generations=base_config.max_generations,
        population_size=base_config.population_size,
        survivors_count=base_config.survivors_count,
        convergence_threshold=base_config.convergence_threshold,
        convergence_window=base_config.convergence_window,
        enable_membrane_bridge=False,
        domains=base_config.domains,
        fitness_weights=base_config.fitness_weights,
    )

    clean = _strip_generated_sections(original)
    prev_traits = evolver.detect_traits(original)
    prev_structural = score_prompt(original, operator_path.name).total
    prev_composite = _composite_score(
        evolver.score_traits(clean, prev_traits, config),
        prev_traits,
        prev_structural,
    )

    # VSR + greedy saturation under metaprompt objective
    evolved, vsr_fitness, _ = evolver.evolve(original, config)
    priority = OPERATOR_PRIORITIES.get(operator_path.name, evolver.STRATEGIES)
    saturated, sat_fitness, sat_traits = evolver.saturate_traits(
        _strip_generated_sections(original), config, priority
    )

    # Apply tier-2 extension if missing
    ext_applied = apply_extension(saturated, operator_path.name)
    ext_traits = evolver.detect_traits(ext_applied)
    ext_structural = score_prompt(ext_applied, operator_path.name).total
    ext_fitness = evolver.score_traits(_strip_generated_sections(ext_applied), ext_traits, config)
    ext_composite = _composite_score(ext_fitness, ext_traits, ext_structural)

    candidates = [
        ("current", original, prev_composite, prev_traits),
        ("vsr", evolved, _composite_score(vsr_fitness, evolver.detect_traits(evolved), score_prompt(evolved, operator_path.name).total), evolver.detect_traits(evolved)),
        ("saturated", saturated, _composite_score(sat_fitness, sat_traits, score_prompt(saturated, operator_path.name).total), sat_traits),
        ("tier2", ext_applied, ext_composite, ext_traits),
    ]
    source, content, composite, traits = max(candidates, key=lambda c: c[2])

    improved = composite > prev_composite + 0.002
    if improved and source != "current":
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        shutil.copy2(operator_path, BACKUP_DIR / f"{operator_path.stem}_meta_{ts}.md")
        operator_path.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")

    return {
        "operator": operator_path.name,
        "source": source,
        "composite_before": prev_composite,
        "composite_after": composite,
        "delta": composite - prev_composite,
        "structural_after": score_prompt(content, operator_path.name).total,
        "traits": traits,
        "trait_count": len(traits),
        "improved": improved,
        "metaprompt_chars": len(metaprompt),
    }


def run_metaprompt_round(metaprompts: dict[str, str], base_config: RunConfig) -> list[dict]:
    """Round A: evolve operators against their metaprompt objectives."""
    evolver = SystemPromptEvolver()
    results: list[dict] = []

    console.print(Panel(
        "[bold]Round A — Metaprompt-Guided Evolution[/bold]\n"
        f"Evolving {len(metaprompts)} operators against synthesized meta-objectives",
        border_style="magenta",
    ))

    for name, mp in metaprompts.items():
        path = PROMPTS_DIR / name
        if not path.exists():
            continue
        entry = evolve_with_metaprompt(path, mp, base_config, evolver)
        results.append(entry)
        style = "green" if entry["improved"] else "dim"
        console.print(
            f"  [{style}]{name}[/{style}]: {entry['composite_before']:.1%} → "
            f"{entry['composite_after']:.1%} ({entry['delta']:+.1%}) via {entry['source']}"
        )
    return results


def run_follow_up_round(max_rounds: int = 3) -> dict:
    """Round B: standard improve_until_converged on metaprompt-evolved prompts."""
    from ri_engine.improve_prompts import improve_until_converged

    console.print(Panel(
        f"[bold]Round B — Convergence Pass[/bold]\n"
        f"Running up to {max_rounds} standard VSR rounds on metaprompt-evolved operators",
        border_style="cyan",
    ))
    return improve_until_converged(max_rounds=max_rounds, plateau_rounds=2, min_improvement=0.003)


def _current_aggregate_composite() -> float:
    """Snapshot current operator composite scores."""
    from ri_engine.improve_prompts import _composite_score
    from ri_engine.system_prompt_evolver import SystemPromptEvolver, _strip_generated_sections

    config = _load_config(CONFIG_PATH)
    evolver = SystemPromptEvolver()
    scores: list[float] = []
    for path in sorted(PROMPTS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        traits = evolver.detect_traits(text)
        clean = _strip_generated_sections(text)
        fitness = evolver.score_traits(clean, traits, config)
        structural = score_prompt(text, path.name).total
        scores.append(_composite_score(fitness, traits, structural))
    return sum(scores) / max(len(scores), 1)


def run_meta_recursive(
    *,
    follow_up_rounds: int = 3,
    skip_follow_up: bool = False,
    quiet: bool = False,
    generation: int = 1,
) -> dict:
    """
    Full meta-recursive pipeline:
    1. Metaprompt all operators
    2. Round A: evolve against metaprompts
    3. Round B: convergence pass on results
    """
    META_OUTPUT.mkdir(parents=True, exist_ok=True)
    base_config = _load_config(CONFIG_PATH)

    if not quiet:
        console.print(Panel(
            "[bold]Meta-Recursive Self-Improvement[/bold]\n"
            "Metaprompt → evolve → evolve again",
            border_style="green",
        ))

    # Step 1: Metaprompt
    if not quiet:
        console.print("\n[bold]Step 1:[/bold] Synthesizing metaprompts from structural diagnosis…")
    metaprompts = generate_all_metaprompts(generation=generation)
    if not quiet:
        console.print(f"  Generated {len(metaprompts)} metaprompts → {META_PROMPTS_DIR}")

    # Step 2: Round A
    if not quiet:
        console.print("\n[bold]Step 2:[/bold] Round A — evolve operators against metaprompts…")
    round_a = run_metaprompt_round(metaprompts, base_config) if not quiet else _run_metaprompt_round_quiet(metaprompts, base_config)
    agg_a_before = sum(r["composite_before"] for r in round_a) / max(len(round_a), 1)
    agg_a_after = sum(r["composite_after"] for r in round_a) / max(len(round_a), 1)

    # Step 3: Round B
    round_b: dict = {}
    if not skip_follow_up:
        if not quiet:
            console.print("\n[bold]Step 3:[/bold] Round B — convergence pass on evolved prompts…")
        round_b = _run_follow_up_quiet(follow_up_rounds) if quiet else run_follow_up_round(max_rounds=follow_up_rounds)

    # Final diagnosis
    final_diagnosis = {}
    for path in sorted(PROMPTS_DIR.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        rubric = score_prompt(content, path.name)
        final_diagnosis[path.name] = {
            "structural_score": rubric.total,
            "gaps_remaining": len(rubric.gaps),
        }

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metaprompts_dir": str(META_PROMPTS_DIR),
        "round_a": {
            "operators": round_a,
            "aggregate_before": agg_a_before,
            "aggregate_after": agg_a_after,
            "aggregate_delta": agg_a_after - agg_a_before,
            "improved_count": sum(1 for r in round_a if r["improved"]),
        },
        "round_b": round_b if round_b else {"skipped": True},
        "final_diagnosis": final_diagnosis,
    }

    report_path = META_OUTPUT / "meta_recursive_report.json"
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if not quiet:
        _print_summary(summary)
    return summary


def _run_metaprompt_round_quiet(metaprompts: dict[str, str], base_config: RunConfig) -> list[dict]:
    evolver = SystemPromptEvolver()
    results: list[dict] = []
    for name, mp in metaprompts.items():
        path = PROMPTS_DIR / name
        if path.exists():
            results.append(evolve_with_metaprompt(path, mp, base_config, evolver))
    return results


def _run_follow_up_quiet(max_rounds: int) -> dict:
    import io
    import contextlib

    from ri_engine.improve_prompts import improve_until_converged

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return improve_until_converged(max_rounds=max_rounds, plateau_rounds=2, min_improvement=0.003)


def run_meta_recursive_loops(
    *,
    max_loops: int = 15,
    stop_delta: float = 0.002,
    plateau_loops: int = 2,
    follow_up_rounds: int = 3,
    auto_break_plateau: bool = True,
    max_plateau_breaks: int = 3,
) -> dict:
    """
    Run meta-recursive cycles until composite score plateaus.

    Stops when aggregate composite improves less than stop_delta for
    `plateau_loops` consecutive meta-loops.
    """
    campaign_start = _current_aggregate_composite()
    history: list[dict] = []
    plateau_count = 0
    loop_num = 0
    plateau_breaks = 0
    breakthroughs: list[dict] = []

    console.print(Panel(
        f"[bold]Meta-Recursive Loop Campaign[/bold]\n"
        f"Starting composite: [cyan]{campaign_start:.1%}[/cyan]\n"
        f"Max loops: {max_loops} · Stop when Δ < {stop_delta:.1%} for {plateau_loops} loops",
        border_style="green",
    ))

    while loop_num < max_loops and plateau_count < plateau_loops:
        loop_num += 1
        before = _current_aggregate_composite()
        console.print(f"\n[bold cyan]━━ Loop {loop_num} ━━[/bold cyan] composite={before:.1%}")

        summary = run_meta_recursive(
            follow_up_rounds=follow_up_rounds,
            quiet=True,
            generation=loop_num,
        )
        after = _current_aggregate_composite()
        delta = after - before

        rb = summary.get("round_b", {})
        ra = summary.get("round_a", {})
        entry = {
            "loop": loop_num,
            "composite_before": before,
            "composite_after": after,
            "delta": delta,
            "round_a_delta": ra.get("aggregate_delta", 0),
            "round_b_final": rb.get("final_aggregate_composite"),
            "round_b_converged": rb.get("converged"),
            "operators_improved": ra.get("improved_count", 0),
            "structural_avg": sum(
                v["structural_score"] for v in summary.get("final_diagnosis", {}).values()
            ) / max(len(summary.get("final_diagnosis", {})), 1),
        }
        history.append(entry)

        style = "green" if delta > stop_delta else "yellow"
        console.print(
            f"  Loop {loop_num}: {before:.1%} → {after:.1%} "
            f"([{style}]{delta:+.2%}[/{style}]) · "
            f"Round A {ra.get('aggregate_delta', 0):+.1%} · "
            f"{ra.get('improved_count', 0)}/5 improved"
        )

        if delta < stop_delta:
            plateau_count += 1
            console.print(f"  [dim]Plateau signal {plateau_count}/{plateau_loops}[/dim]")
            if (
                auto_break_plateau
                and plateau_count >= plateau_loops
                and plateau_breaks < max_plateau_breaks
            ):
                plateau_breaks += 1
                console.print(
                    f"\n[bold yellow]⚡ Plateau break #{plateau_breaks} — running substantial-gains…[/bold yellow]"
                )
                from ri_engine.substantial_gains import apply_substantial_gains

                before_sg = _current_aggregate_composite()
                sg_report = apply_substantial_gains()
                after_sg = _current_aggregate_composite()
                sg_delta = after_sg - before_sg
                breakthroughs.append({
                    "break": plateau_breaks,
                    "after_loop": loop_num,
                    "composite_before": before_sg,
                    "composite_after": after_sg,
                    "delta": sg_delta,
                    "structural_gain": sg_report.get("aggregate_delta", 0),
                })
                console.print(
                    f"  Substantial gains: {before_sg:.1%} → {after_sg:.1%} ({sg_delta:+.2%})"
                )
                plateau_count = 0
                continue
        else:
            plateau_count = 0

    campaign_end = _current_aggregate_composite()
    campaign = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "loops_run": loop_num,
        "stopped_reason": "plateau" if plateau_count >= plateau_loops else "max_loops",
        "campaign_start_composite": campaign_start,
        "campaign_end_composite": campaign_end,
        "campaign_total_delta": campaign_end - campaign_start,
        "plateau_breaks_run": plateau_breaks,
        "breakthroughs": breakthroughs,
        "history": history,
    }

    campaign_path = META_OUTPUT / "loop_campaign.json"
    campaign_path.write_text(json.dumps(campaign, indent=2), encoding="utf-8")
    _print_campaign(campaign)
    return campaign


def _print_campaign(campaign: dict) -> None:
    console.print()
    console.print(Panel(
        f"[bold]Loop Campaign Complete[/bold]\n\n"
        f"Loops run: [bold]{campaign['loops_run']}[/bold] ({campaign['stopped_reason']})\n"
        f"Start: {campaign['campaign_start_composite']:.1%} → "
        f"End: [green]{campaign['campaign_end_composite']:.1%}[/green] "
        f"([green]{campaign['campaign_total_delta']:+.2%}[/green] total)",
        title="Campaign Results",
        border_style="green",
    ))

    table = Table(title="Loop History")
    table.add_column("Loop", justify="right")
    table.add_column("Before", justify="right")
    table.add_column("After", justify="right")
    table.add_column("Δ", justify="right")
    table.add_column("Round A Δ", justify="right")
    table.add_column("Improved", justify="right")

    for h in campaign["history"]:
        d_style = "green" if h["delta"] > 0 else "dim"
        table.add_row(
            str(h["loop"]),
            f"{h['composite_before']:.1%}",
            f"{h['composite_after']:.1%}",
            f"[{d_style}]{h['delta']:+.2%}[/{d_style}]",
            f"{h['round_a_delta']:+.1%}",
            str(h["operators_improved"]),
        )
    console.print(table)
    console.print(f"\n[dim]Campaign report: {META_OUTPUT / 'loop_campaign.json'}[/dim]")


def _print_summary(summary: dict) -> None:
    ra = summary["round_a"]
    console.print()
    console.print(Panel(
        f"[bold]Meta-Recursive Complete[/bold]\n\n"
        f"Round A: {ra['aggregate_before']:.1%} → {ra['aggregate_after']:.1%} "
        f"([green]{ra['aggregate_delta']:+.1%}[/green])\n"
        f"Operators improved: {ra['improved_count']}/{len(ra['operators'])}\n"
        f"Metaprompts: {summary['metaprompts_dir']}",
        title="Results",
        border_style="green",
    ))

    if summary.get("round_b") and not summary["round_b"].get("skipped"):
        rb = summary["round_b"]
        console.print(
            f"Round B: {rb.get('baseline_aggregate_composite', 0):.1%} → "
            f"{rb.get('final_aggregate_composite', 0):.1%} "
            f"({rb.get('rounds_run', 0)} rounds, converged={rb.get('converged')})"
        )

    table = Table(title="Final Structural Scores")
    table.add_column("Operator")
    table.add_column("Structural", justify="right")
    table.add_column("Gaps Left", justify="right")
    for name, info in summary["final_diagnosis"].items():
        table.add_row(name, f"{info['structural_score']:.0%}", str(info["gaps_remaining"]))
    console.print(table)
    console.print(f"\n[dim]Report: {META_OUTPUT / 'meta_recursive_report.json'}[/dim]")


def main() -> int:
    import sys

    if "--loops" in sys.argv:
        max_loops = 15
        for i, arg in enumerate(sys.argv):
            if arg == "--loops" and i + 1 < len(sys.argv):
                max_loops = int(sys.argv[i + 1])
        run_meta_recursive_loops(max_loops=max_loops)
    else:
        run_meta_recursive()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
