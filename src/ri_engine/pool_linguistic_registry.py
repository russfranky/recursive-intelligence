"""
Pool linguistic registry — run full-spectrum engine evaluation and persist winners.

Evaluates all SPECTRUM_LEANINGS across every category × audience cell in
linguistic_spectrum.yaml, then writes config/linguistic_registry.json for
future gate resolution.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ri_engine.engine import RecursiveIntelligenceEngine
from ri_engine.language_leanings import (
    DEFAULT_REGISTRY_PATH,
    DEFAULT_SPECTRUM_PATH,
    SPECTRUM_LEANINGS,
    LeaningScore,
    LinguisticRegistry,
    apply_linguistic_gate,
    build_registry_entry,
    leaning_clause,
    load_spectrum_entries,
    score_leaning_fit,
)
from ri_engine.llm_provider import MockLLMProvider
from ri_engine.models import RunConfig
from ri_engine.prompt_rubric import score_task_prompt
from ri_engine.prompt_synthesizer import finalize_prompt
from ri_engine.register_analysis import analyze_register

console = Console()


def _evaluate_leaning(
    seed: str,
    objective: str,
    leaning: str,
    use_case_id: str,
    *,
    engine: RecursiveIntelligenceEngine | None = None,
    use_vsr: bool = False,
    domains: list[str] | None = None,
) -> LeaningScore:
    """Score one leaning for a category cell."""
    clause = leaning_clause(leaning)
    obj = f"{objective.strip()}\n\n{clause}" if clause else objective.strip()
    membrane = MockLLMProvider()._bridge(objective)

    fitness = 0.0
    if use_vsr and engine is not None:
        config = RunConfig(
            seed_prompt=seed,
            objective=obj,
            max_generations=2,
            population_size=4,
            survivors_count=1,
            convergence_threshold=0.05,
            convergence_window=1,
            enable_membrane_bridge=False,
            domains=domains or [],
            metadata={"linguistic_leaning": leaning, "apply_linguistic_gate": False},
        )
        report = engine.run(config)
        fitness = report["best_fitness"]
        prompt = report["best_prompt"]
    else:
        prompt = finalize_prompt(seed, obj, "constraint_first", membrane, leaning=leaning)

    quality = score_task_prompt(prompt, use_case_id)
    reg = analyze_register(prompt)
    composite = score_leaning_fit(leaning, quality.total, reg)

    return LeaningScore(
        leaning=leaning,
        quality=quality.total,
        composite=composite,
        fitness=fitness,
        latinate_ratio=reg.latinate_ratio,
        readability=reg.readability_score,
        token_estimate=reg.token_estimate,
        register_label=reg.register_label,
    )


def pool_linguistic_registry(
    *,
    spectrum_path: Path | None = None,
    registry_path: Path | None = None,
    use_vsr: bool = False,
    validate_winners: bool = True,
) -> dict:
    """
    Run full-spectrum evaluation and persist categorical language leanings.

    Args:
        spectrum_path: YAML defining category × audience cells
        registry_path: Output JSON registry path
        use_vsr: Run mini VSR for every leaning (slow, thorough)
        validate_winners: Re-run mini VSR on winner to boost confidence
    """
    cells = load_spectrum_entries(spectrum_path)
    registry = LinguisticRegistry(registry_path)
    engine = RecursiveIntelligenceEngine() if (use_vsr or validate_winners) else None

    console.print(Panel(
        f"[bold]Linguistic Registry Pool[/bold]\n"
        f"Full spectrum: {', '.join(SPECTRUM_LEANINGS)}\n"
        f"Cells: {len(cells)} · Leanings per cell: {len(SPECTRUM_LEANINGS)}",
        border_style="cyan",
    ))

    pooled: list[dict] = []

    for cell in cells:
        cell_id = cell.get("id", "unknown")
        category = cell.get("category", "")
        audience = cell.get("audience", "")
        seed = cell["seed_prompt"]
        objective = cell["objective"]
        meta = cell.get("metadata", {})
        use_case_id = meta.get("use_case", cell_id.split(":")[0])
        domains = cell.get("domains", [])

        console.print(f"\n[bold cyan]▶ {cell_id}[/bold cyan] [dim]({category} / {audience})[/dim]")

        scores: list[LeaningScore] = []
        for leaning in SPECTRUM_LEANINGS:
            score = _evaluate_leaning(
                seed, objective, leaning, use_case_id,
                engine=engine, use_vsr=use_vsr, domains=domains,
            )
            scores.append(score)

        entry = build_registry_entry(cell, scores, used_vsr=use_vsr)
        registry.upsert(entry)

        # Optional validation pass on winner
        if validate_winners and engine and not use_vsr:
            winner_score = _evaluate_leaning(
                seed, objective, entry.recommended_leaning, use_case_id,
                engine=engine, use_vsr=True, domains=domains,
            )
            entry.spectrum_scores[entry.recommended_leaning]["fitness_validated"] = round(
                winner_score.fitness, 4
            )
            entry.confidence = min(0.98, entry.confidence + 0.08)
            entry.evidence_runs = 2
            registry.upsert(entry)

        ranked = sorted(scores, key=lambda s: s.composite, reverse=True)
        console.print(
            f"  Winner: [green]{entry.recommended_leaning}[/green] "
            f"(composite={ranked[0].composite:.2f}, confidence={entry.confidence:.0%})"
        )
        console.print(
            f"  [dim]Spectrum: "
            + " · ".join(f"{s.leaning}={s.composite:.2f}" for s in ranked[:4])
            + "[/dim]"
        )

        pooled.append({
            "id": entry.id,
            "category": category,
            "audience": audience,
            "recommended_leaning": entry.recommended_leaning,
            "confidence": entry.confidence,
            "alternatives": entry.alternatives,
            "rationale": entry.rationale,
        })

    registry.save()

    # Coverage report
    leaning_counts: dict[str, int] = {}
    for e in registry.entries.values():
        leaning_counts[e.recommended_leaning] = leaning_counts.get(e.recommended_leaning, 0) + 1

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "spectrum_leanings": list(SPECTRUM_LEANINGS),
        "cells_pooled": len(pooled),
        "registry_path": str(registry.path),
        "coverage": {
            "leaning_distribution": leaning_counts,
            "spectrum_complete": len(SPECTRUM_LEANINGS),
            "categories_covered": len({p["category"] for p in pooled}),
            "audiences_covered": len({p["audience"] for p in pooled}),
        },
        "entries": pooled,
    }

    report_path = registry.path.parent / "linguistic_pool_report.json"
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _print_summary(summary, registry)
    return summary


def _print_summary(summary: dict, registry: LinguisticRegistry) -> None:
    cov = summary["coverage"]
    console.print()
    console.print(Panel(
        f"[bold]Registry Pooled[/bold]\n\n"
        f"Cells: [bold]{summary['cells_pooled']}[/bold] · "
        f"Categories: [bold]{cov['categories_covered']}[/bold] · "
        f"Audiences: [bold]{cov['audiences_covered']}[/bold]\n"
        f"Spectrum leanings: {', '.join(summary['spectrum_leanings'])}\n"
        f"Distribution: {cov['leaning_distribution']}\n\n"
        f"[dim]Registry: {registry.path}[/dim]",
        title="Full-Spectrum Linguistic Coverage",
        border_style="green",
    ))

    table = Table(title="Pooled Language Leanings")
    table.add_column("Cell ID")
    table.add_column("Category")
    table.add_column("Audience")
    table.add_column("Leaning")
    table.add_column("Confidence", justify="right")

    for e in summary["entries"]:
        table.add_row(
            e["id"][:28],
            e["category"][:20],
            e["audience"],
            e["recommended_leaning"],
            f"{e['confidence']:.0%}",
        )
    console.print(table)


def main() -> int:
    pool_linguistic_registry(validate_winners=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
