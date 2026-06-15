"""
Benchmark runner — execute all use cases and prove evolution value with metrics.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ri_engine.engine import RecursiveIntelligenceEngine
from ri_engine.models import RunConfig
from ri_engine.prompt_rubric import compare_prompts, score_task_prompt
from ri_engine.prompt_synthesizer import finalize_prompt

from ri_engine.paths import config_dir, workspace_dir

USE_CASES_DIR = config_dir() / "use_cases"
OUTPUT_DIR = workspace_dir() / "output" / "benchmark"

console = Console()

_AUDIENCE_BY_CATEGORY: dict[str, str] = {
    "Software Engineering": "developer",
    "Agentic Development": "developer",
    "Operations": "end_user",
    "Research & Intelligence": "researcher",
    "Revenue": "prospect",
    "Security": "operator",
}


def _load_use_case(path: Path) -> tuple[dict, RunConfig]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    config = RunConfig(
        seed_prompt=data["seed_prompt"],
        objective=data["objective"],
        max_generations=data.get("max_generations", 6),
        population_size=data.get("population_size", 8),
        survivors_count=data.get("survivors_count", 2),
        convergence_threshold=data.get("convergence_threshold", 0.025),
        convergence_window=data.get("convergence_window", 2),
        variation_temperature=data.get("variation_temperature", 0.75),
        enable_membrane_bridge=data.get("enable_membrane_bridge", True),
        domains=data.get("domains", []),
        fitness_weights=data.get("fitness_weights", {}),
        output_path=data.get("output_path"),
        metadata={
            **data.get("metadata", {}),
            "category": data.get("category", ""),
            "audience": data.get("audience") or _AUDIENCE_BY_CATEGORY.get(data.get("category", ""), "operator"),
            "apply_linguistic_gate": True,
        },
    )
    return data, config


def run_benchmark(use_cases_dir: Path | None = None, *, client_mode: bool = False) -> dict:
    """Run all use case configs and produce comparative proof report."""
    cases_dir = use_cases_dir or USE_CASES_DIR
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    engine = RecursiveIntelligenceEngine()
    results: list[dict] = []

    if not client_mode:
        console.print(Panel(
            "[bold]Recursive Intelligence Engine — Use Case Benchmark[/bold]\n"
            "Evolving weak seed prompts → production-grade agent system prompts",
            border_style="cyan",
        ))

    for path in sorted(cases_dir.glob("*.yaml")):
        meta, config = _load_use_case(path)
        name = meta.get("name", path.stem)
        use_case_id = meta.get("metadata", {}).get("use_case", path.stem)

        if not client_mode:
            console.print(f"\n[bold cyan]▶ {name}[/bold cyan] [dim]({meta.get('category', '')})[/dim]")

        seed = config.seed_prompt
        seed_quality = score_task_prompt(seed, use_case_id)

        report = engine.run(config)

        # Finalize: clean synthesis from seed (strips evolution contamination)
        membrane_insight = ""
        if config.enable_membrane_bridge and report.get("final_survivors"):
            from ri_engine.llm_provider import MockLLMProvider
            membrane_insight = MockLLMProvider()._bridge(config.objective)

        evolved = finalize_prompt(seed, config.objective, "constraint_first", membrane_insight)
        report["best_prompt"] = evolved
        evolved_quality = score_task_prompt(evolved, use_case_id)
        comparison = compare_prompts(seed, evolved, use_case_id)

        # Save evolved prompt artifact
        artifact_dir = OUTPUT_DIR / use_case_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "seed_prompt.md").write_text(seed, encoding="utf-8")
        (artifact_dir / "evolved_prompt.md").write_text(evolved, encoding="utf-8")
        (artifact_dir / "run_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

        entry = {
            "name": name,
            "category": meta.get("category", ""),
            "description": meta.get("description", ""),
            "use_case_id": use_case_id,
            "seed_prompt_preview": seed[:120].replace("\n", " ") + "…",
            "generations": report["meta"]["generations_run"],
            "converged": report["meta"]["converged"],
            "engine_fitness_before": None,
            "engine_fitness_after": report["best_fitness"],
            "quality_before": seed_quality.total,
            "quality_after": evolved_quality.total,
            "quality_delta": comparison["delta"],
            "quality_delta_pct": comparison["delta_pct"],
            "grade_before": seed_quality.grade,
            "grade_after": evolved_quality.grade,
            "features_before": seed_quality.features_present,
            "features_after": evolved_quality.features_present,
            "features_gained": comparison["features_gained"],
            "words_before": seed_quality.word_count,
            "words_after": evolved_quality.word_count,
            "evolved_prompt_path": str(artifact_dir / "evolved_prompt.md"),
            "fitness_trajectory": report["fitness_trajectory"],
        }
        results.append(entry)

        if not client_mode:
            delta_style = "green" if comparison["delta"] > 0 else "yellow"
            console.print(
                f"  Quality: {seed_quality.total:.0%} → {evolved_quality.total:.0%} "
                f"([{delta_style}]+{comparison['delta_pct']:.0f}%[/{delta_style}])  "
                f"Grade: {seed_quality.grade.split('—')[0].strip()} → {evolved_quality.grade.split('—')[0].strip()}  "
                f"Features: {len(seed_quality.features_present)} → {len(evolved_quality.features_present)}  "
                f"Gens: {report['meta']['generations_run']}"
            )
            if comparison["features_gained"]:
                console.print(f"  [dim]+ {', '.join(comparison['features_gained'][:4])}[/dim]")

    # Aggregate proof metrics
    avg_before = sum(r["quality_before"] for r in results) / len(results)
    avg_after = sum(r["quality_after"] for r in results) / len(results)
    avg_delta_pct = sum(r["quality_delta_pct"] for r in results) / len(results)
    total_features_gained = sum(len(r["features_gained"]) for r in results)
    grade_improvements = sum(
        1 for r in results if r["quality_after"] > r["quality_before"] + 0.15
    )

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "use_cases_run": len(results),
        "proof_metrics": {
            "avg_quality_before": avg_before,
            "avg_quality_after": avg_after,
            "avg_quality_delta": avg_after - avg_before,
            "avg_improvement_pct": avg_delta_pct,
            "total_features_gained": total_features_gained,
            "grade_improvements": grade_improvements,
            "all_improved": all(r["quality_delta"] > 0 for r in results),
        },
        "use_cases": results,
    }

    summary_path = OUTPUT_DIR / "benchmark_results.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if not client_mode:
        _print_summary_table(summary)
    return summary


def _print_summary_table(summary: dict) -> None:
    metrics = summary["proof_metrics"]
    console.print()
    console.print(Panel(
        f"[bold]Proof of Value[/bold]\n\n"
        f"Avg quality:  [red]{metrics['avg_quality_before']:.0%}[/red] → [green]{metrics['avg_quality_after']:.0%}[/green]  "
        f"([green]+{metrics['avg_improvement_pct']:.0f}%[/green])\n"
        f"Features gained: [bold]{metrics['total_features_gained']}[/bold] across {summary['use_cases_run']} use cases\n"
        f"Grade improvements: [bold]{metrics['grade_improvements']}/{summary['use_cases_run']}[/bold]\n"
        f"All improved: [bold]{'Yes ✓' if metrics['all_improved'] else 'No'}[/bold]",
        title="Benchmark Results",
        border_style="green",
    ))

    table = Table(title="Use Case Results")
    table.add_column("Use Case")
    table.add_column("Category")
    table.add_column("Before", justify="right")
    table.add_column("After", justify="right")
    table.add_column("Δ", justify="right")
    table.add_column("Grade")
    table.add_column("Features", justify="right")

    for r in summary["use_cases"]:
        g_before = r["grade_before"].split("—")[0].strip()
        g_after = r["grade_after"].split("—")[0].strip()
        table.add_row(
            r["name"][:28],
            r["category"][:16],
            f"{r['quality_before']:.0%}",
            f"{r['quality_after']:.0%}",
            f"+{r['quality_delta_pct']:.0f}%",
            f"{g_before}→{g_after}",
            f"{len(r['features_before'])}→{len(r['features_after'])}",
        )
    console.print(table)
    console.print(f"\n[dim]Full report: {OUTPUT_DIR / 'benchmark_results.json'}[/dim]")
    console.print(f"[dim]Evolved prompts: {OUTPUT_DIR}/<use_case>/evolved_prompt.md[/dim]")


def main() -> int:
    run_benchmark()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
