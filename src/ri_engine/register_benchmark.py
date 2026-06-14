"""
Register proof benchmark — A/B test plain Anglo-Saxon vs Latinate register.

Runs the same use cases through the VSR engine with identical seeds but
opposing register objectives, then compares quality, readability, and fitness.
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
from ri_engine.register_analysis import analyze_register, composite_task_score

ROOT = Path(__file__).resolve().parents[2]
USE_CASES_DIR = ROOT / "config" / "use_cases"
OUTPUT_DIR = ROOT / "output" / "benchmark"

PLAIN_CLAUSE = (
    "MANDATORY REGISTER: Use plain Anglo-Saxon English throughout. "
    "Short direct words. Avoid Latinate filler (facilitate, utilize, comprehensive methodology)."
)
LATINATE_CLAUSE = (
    "MANDATORY REGISTER: Use formal Latinate register throughout. "
    "Prefer Latinate vocabulary (facilitate, implement, evaluate, assess, verify, protocol, remediation)."
)

console = Console()


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
        metadata=data.get("metadata", {}),
    )
    return data, config


def _run_arm(
    engine: RecursiveIntelligenceEngine,
    base_config: RunConfig,
    register: str,
    use_case_id: str,
) -> dict:
    clause = PLAIN_CLAUSE if register == "plain" else LATINATE_CLAUSE
    config = RunConfig(
        seed_prompt=base_config.seed_prompt,
        objective=f"{base_config.objective.strip()}\n\n{clause}",
        max_generations=base_config.max_generations,
        population_size=base_config.population_size,
        survivors_count=base_config.survivors_count,
        convergence_threshold=base_config.convergence_threshold,
        convergence_window=base_config.convergence_window,
        variation_temperature=base_config.variation_temperature,
        enable_membrane_bridge=base_config.enable_membrane_bridge,
        domains=base_config.domains,
        fitness_weights=base_config.fitness_weights,
        metadata={
            **base_config.metadata,
            "apply_linguistic_gate": False,
            "linguistic_leaning": register,
        },
    )

    seed = config.seed_prompt
    seed_quality = score_task_prompt(seed, use_case_id)
    report = engine.run(config)

    membrane_insight = ""
    if config.enable_membrane_bridge:
        from ri_engine.llm_provider import MockLLMProvider

        membrane_insight = MockLLMProvider()._bridge(config.objective)

    evolved = finalize_prompt(seed, config.objective, "constraint_first", membrane_insight, register=register)
    evolved_quality = score_task_prompt(evolved, use_case_id)
    comparison = compare_prompts(seed, evolved, use_case_id)
    register_metrics = analyze_register(evolved)
    composite = composite_task_score(evolved_quality.total, register_metrics, target=register)

    return {
        "register": register,
        "generations": report["meta"]["generations_run"],
        "converged": report["meta"]["converged"],
        "engine_fitness": report["best_fitness"],
        "quality_before": seed_quality.total,
        "quality_after": evolved_quality.total,
        "quality_delta": comparison["delta"],
        "quality_delta_pct": comparison["delta_pct"],
        "grade_before": seed_quality.grade,
        "grade_after": evolved_quality.grade,
        "features_before": seed_quality.features_present,
        "features_after": evolved_quality.features_present,
        "features_gained": comparison["features_gained"],
        "words_after": evolved_quality.word_count,
        "latinate_ratio": register_metrics.latinate_ratio,
        "readability_score": register_metrics.readability_score,
        "token_estimate": register_metrics.token_estimate,
        "register_label": register_metrics.register_label,
        "latinate_words_found": register_metrics.latinate_words_found[:12],
        "plain_words_found": register_metrics.plain_words_found[:12],
        "composite_score": composite,
        "evolved_prompt": evolved,
        "fitness_trajectory": report["fitness_trajectory"],
    }


def run_register_proof(use_cases_dir: Path | None = None) -> dict:
    """Run plain vs latinate A/B benchmark across all use cases."""
    cases_dir = use_cases_dir or USE_CASES_DIR
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    engine = RecursiveIntelligenceEngine()
    comparisons: list[dict] = []

    console.print(Panel(
        "[bold]Register Proof Benchmark[/bold]\n"
        "Same seeds · same VSR engine · opposing register objectives\n"
        "Plain Anglo-Saxon vs formal Latinate",
        border_style="magenta",
    ))

    for path in sorted(cases_dir.glob("*.yaml")):
        meta, config = _load_use_case(path)
        name = meta.get("name", path.stem)
        use_case_id = meta.get("metadata", {}).get("use_case", path.stem)

        console.print(f"\n[bold magenta]▶ {name}[/bold magenta]")

        plain = _run_arm(engine, config, "plain", use_case_id)
        latinate = _run_arm(engine, config, "latinate", use_case_id)

        quality_winner = "plain" if plain["quality_after"] >= latinate["quality_after"] else "latinate"
        composite_winner = "plain" if plain["composite_score"] >= latinate["composite_score"] else "latinate"
        fitness_winner = "plain" if plain["engine_fitness"] >= latinate["engine_fitness"] else "latinate"

        artifact_dir = OUTPUT_DIR / "register_proof" / use_case_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "plain_evolved.md").write_text(plain["evolved_prompt"], encoding="utf-8")
        (artifact_dir / "latinate_evolved.md").write_text(latinate["evolved_prompt"], encoding="utf-8")

        entry = {
            "name": name,
            "use_case_id": use_case_id,
            "category": meta.get("category", ""),
            "plain": {k: v for k, v in plain.items() if k != "evolved_prompt"},
            "latinate": {k: v for k, v in latinate.items() if k != "evolved_prompt"},
            "comparison": {
                "quality_delta_plain_vs_latinate": plain["quality_after"] - latinate["quality_after"],
                "quality_winner": quality_winner,
                "composite_winner": composite_winner,
                "fitness_winner": fitness_winner,
                "latinate_ratio_shift": latinate["latinate_ratio"] - plain["latinate_ratio"],
                "readability_delta": plain["readability_score"] - latinate["readability_score"],
                "token_delta": latinate["token_estimate"] - plain["token_estimate"],
            },
            "artifact_dir": str(artifact_dir),
        }
        comparisons.append(entry)

        q_style = "green" if quality_winner == "plain" else "yellow"
        console.print(
            f"  Plain:    quality={plain['quality_after']:.0%}  "
            f"lat_ratio={plain['latinate_ratio']:.2f}  "
            f"read={plain['readability_score']:.2f}  "
            f"fitness={plain['engine_fitness']:.3f}"
        )
        console.print(
            f"  Latinate: quality={latinate['quality_after']:.0%}  "
            f"lat_ratio={latinate['latinate_ratio']:.2f}  "
            f"read={latinate['readability_score']:.2f}  "
            f"fitness={latinate['engine_fitness']:.3f}"
        )
        console.print(
            f"  Winner: quality=[{q_style}]{quality_winner}[/{q_style}]  "
            f"composite={composite_winner}  "
            f"latinate_ratio_shift=+{entry['comparison']['latinate_ratio_shift']:.2f}"
        )

    plain_quality_wins = sum(1 for c in comparisons if c["comparison"]["quality_winner"] == "plain")
    plain_composite_wins = sum(1 for c in comparisons if c["comparison"]["composite_winner"] == "plain")
    avg_plain_quality = sum(c["plain"]["quality_after"] for c in comparisons) / len(comparisons)
    avg_latinate_quality = sum(c["latinate"]["quality_after"] for c in comparisons) / len(comparisons)
    avg_lat_shift = sum(c["comparison"]["latinate_ratio_shift"] for c in comparisons) / len(comparisons)
    avg_read_delta = sum(c["comparison"]["readability_delta"] for c in comparisons) / len(comparisons)
    avg_token_delta = sum(c["comparison"]["token_delta"] for c in comparisons) / len(comparisons)

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "experiment": "plain_vs_latinate_register_ab",
        "use_cases_run": len(comparisons),
        "proof_metrics": {
            "plain_quality_wins": plain_quality_wins,
            "latinate_quality_wins": len(comparisons) - plain_quality_wins,
            "plain_composite_wins": plain_composite_wins,
            "latinate_composite_wins": len(comparisons) - plain_composite_wins,
            "avg_plain_quality": avg_plain_quality,
            "avg_latinate_quality": avg_latinate_quality,
            "avg_quality_advantage_plain": avg_plain_quality - avg_latinate_quality,
            "avg_latinate_ratio_shift": avg_lat_shift,
            "avg_readability_advantage_plain": avg_read_delta,
            "avg_token_overhead_latinate": avg_token_delta,
            "register_affects_outcomes": avg_lat_shift > 0.05,
            "plain_wins_on_quality": plain_quality_wins > len(comparisons) / 2,
            "conclusion": _build_conclusion(
                plain_quality_wins,
                len(comparisons),
                avg_plain_quality - avg_latinate_quality,
                avg_lat_shift,
                avg_read_delta,
            ),
        },
        "use_cases": comparisons,
    }

    summary_path = OUTPUT_DIR / "register_proof_results.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _print_summary(summary)
    return summary


def _build_conclusion(
    plain_wins: int,
    total: int,
    quality_gap: float,
    lat_shift: float,
    read_delta: float,
) -> str:
    parts = []
    if lat_shift > 0.05:
        parts.append(
            f"Register choice measurably shifts evolution (+{lat_shift:.0%} avg latinate ratio under Latinate objective)."
        )
    if plain_wins > total / 2:
        parts.append(
            f"Plain Anglo-Saxon wins on task quality in {plain_wins}/{total} use cases "
            f"(avg +{quality_gap:.0%} quality advantage)."
        )
    if read_delta > 0.02:
        parts.append(f"Plain register improves readability by {read_delta:.0%} on average.")
    if not parts:
        return "Register had minimal measurable effect on engine outcomes in this run."
    parts.append(
        "For agent system prompts and fine-tuning objectives, plain language optimizes utility; "
        "Latinate register is useful only when formal domain tone is explicitly required."
    )
    return " ".join(parts)


def _print_summary(summary: dict) -> None:
    m = summary["proof_metrics"]
    console.print()
    console.print(Panel(
        f"[bold]Register Proof Results[/bold]\n\n"
        f"Quality wins:  plain [green]{m['plain_quality_wins']}[/green] · "
        f"latinate [yellow]{m['latinate_quality_wins']}[/yellow]\n"
        f"Avg quality:   plain [green]{m['avg_plain_quality']:.0%}[/green] vs "
        f"latinate [yellow]{m['avg_latinate_quality']:.0%}[/yellow]  "
        f"([green]+{m['avg_quality_advantage_plain']:.0%}[/green] plain)\n"
        f"Latinate shift: [bold]+{m['avg_latinate_ratio_shift']:.0%}[/bold] under Latinate objective\n"
        f"Readability:   plain +{m['avg_readability_advantage_plain']:.0%} vs latinate\n"
        f"Token overhead: latinate +{m['avg_token_overhead_latinate']:.0f} tokens avg\n\n"
        f"[italic]{m['conclusion']}[/italic]",
        title="Proof: Register Affects Engine Outcomes",
        border_style="green",
    ))

    table = Table(title="Plain vs Latinate by Use Case")
    table.add_column("Use Case")
    table.add_column("Plain Q", justify="right")
    table.add_column("Lat Q", justify="right")
    table.add_column("Winner")
    table.add_column("Lat Ratio Δ", justify="right")
    table.add_column("Read Δ", justify="right")

    for c in summary["use_cases"]:
        cmp = c["comparison"]
        winner_style = "green" if cmp["quality_winner"] == "plain" else "yellow"
        table.add_row(
            c["name"][:24],
            f"{c['plain']['quality_after']:.0%}",
            f"{c['latinate']['quality_after']:.0%}",
            f"[{winner_style}]{cmp['quality_winner']}[/{winner_style}]",
            f"+{cmp['latinate_ratio_shift']:.2f}",
            f"+{cmp['readability_delta']:.2f}",
        )
    console.print(table)
    console.print(f"\n[dim]Full report: {OUTPUT_DIR / 'register_proof_results.json'}[/dim]")


def main() -> int:
    run_register_proof()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
