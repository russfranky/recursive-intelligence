"""Evolve operator system prompts using the engine's own VSR loop."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ri_engine.models import RunConfig
from ri_engine.system_prompt_evolver import (
    OPERATOR_PRIORITIES,
    TRAIT_COUNT,
    SystemPromptEvolver,
    _strip_generated_sections,
)

ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = ROOT / "prompts"
BACKUP_DIR = ROOT / "prompts" / ".backup"
OUTPUT_DIR = ROOT / "output" / "evolved_prompts"
CONFIG_PATH = ROOT / "config" / "improve_system_prompts.yaml"


def _load_config(cfg_path: Path) -> RunConfig:
    base = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    return RunConfig(
        seed_prompt="",
        objective=base["objective"],
        max_generations=base.get("max_generations", 8),
        population_size=base.get("population_size", 8),
        survivors_count=base.get("survivors_count", 3),
        convergence_threshold=base.get("convergence_threshold", 0.015),
        convergence_window=base.get("convergence_window", 2),
        enable_membrane_bridge=False,
        domains=base.get("domains", []),
        fitness_weights=base.get("fitness_weights", {}),
    )


def _coverage(traits: list[str]) -> float:
    return len(traits) / TRAIT_COUNT


def _composite_score(fitness: float, traits: list[str], structural: float = 0.0) -> float:
    """Blend mock fitness, trait coverage, and structural rubric."""
    if structural > 0:
        return fitness * 0.3 + _coverage(traits) * 0.2 + structural * 0.5
    return fitness * 0.7 + _coverage(traits) * 0.3


def improve_operator_prompts(config_path: Path | None = None) -> dict:
    """Single-round VSR evolution on all operator prompts."""
    return improve_until_converged(
        config_path=config_path,
        max_rounds=1,
        plateau_rounds=1,
        min_improvement=0.0,
    )


def improve_until_converged(
    config_path: Path | None = None,
    max_rounds: int = 20,
    plateau_rounds: int = 3,
    min_improvement: float = 0.005,
) -> dict:
    """
    Run evolution rounds until aggregate fitness plateaus.

    Each round: VSR evolve → greedy trait saturation → keep best version per prompt.
    Stops when no significant improvement for `plateau_rounds` consecutive rounds.
    """
    cfg_path = config_path or CONFIG_PATH
    config = _load_config(cfg_path)
    evolver = SystemPromptEvolver()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    session_log: list[dict] = []

    # Baseline snapshot
    best_state: dict[str, dict] = {}
    for path in sorted(PROMPTS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        clean = _strip_generated_sections(text)
        traits = evolver.detect_traits(text)
        fitness = evolver.score_traits(clean, traits, config)
        best_state[path.name] = {
            "content": text,
            "fitness": fitness,
            "traits": traits,
            "composite": _composite_score(fitness, traits),
        }

    baseline_composite = _aggregate_composite(best_state)
    aggregate_history: list[float] = []
    plateau_count = 0
    round_num = 0

    print(f"Baseline aggregate composite: {baseline_composite:.1%}")
    print(f"Running up to {max_rounds} rounds (stop after {plateau_rounds} plateau rounds)\n")

    while round_num < max_rounds and plateau_count < plateau_rounds:
        round_num += 1
        round_improved = False
        round_log: dict[str, dict] = {}

        for path in sorted(PROMPTS_DIR.glob("*.md")):
            name = path.name
            original = path.read_text(encoding="utf-8")
            prev = best_state[name]

            # Phase 1: VSR evolution
            evolved, vsr_fitness, history = evolver.evolve(original, config)

            # Phase 2: Greedy saturation with operator-specific priority
            priority = OPERATOR_PRIORITIES.get(name, evolver.STRATEGIES)
            saturated, sat_fitness, sat_traits = evolver.saturate_traits(
                _strip_generated_sections(original), config, priority
            )

            # Pick best candidate (never regress composite score)
            candidates = [
                ("current", original, prev["fitness"], prev["traits"]),
                ("vsr", evolved, vsr_fitness, history[-1].get("winning_traits", []) if history else []),
                ("saturated", saturated, sat_fitness, sat_traits),
            ]

            best_candidate = max(
                candidates,
                key=lambda c: _composite_score(c[2], c[3]),
            )
            source, content, fitness, traits = best_candidate
            composite = _composite_score(fitness, traits)

            if composite > prev["composite"] + min_improvement:
                round_improved = True
                if source != "current":
                    backup = BACKUP_DIR / f"{path.stem}_r{round_num}_{timestamp}.md"
                    shutil.copy2(path, backup)
                    path.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")
                best_state[name] = {
                    "content": content,
                    "fitness": fitness,
                    "traits": traits,
                    "composite": composite,
                    "source": source,
                }
                status = "IMPROVED" if source != "current" else "HELD"
            else:
                status = "HELD"

            round_log[name] = {
                "fitness": fitness,
                "composite": composite,
                "traits": traits,
                "trait_count": len(traits),
                "source": source,
                "status": status,
                "vsr_fitness": vsr_fitness,
                "sat_fitness": sat_fitness,
                "sat_traits": sat_traits,
            }
            print(
                f"  r{round_num} {name}: {composite:.1%} ({len(traits)}/{TRAIT_COUNT} traits) "
                f"[{status} via {source}]"
            )

        agg = _aggregate_composite(best_state)
        aggregate_history.append(agg)
        session_log.append({"round": round_num, "aggregate_composite": agg, "prompts": round_log})

        if round_num > 1:
            delta = agg - aggregate_history[-2]
            if delta < min_improvement and not round_improved:
                plateau_count += 1
                print(f"\n  → plateau {plateau_count}/{plateau_rounds} (Δ={delta:+.2%})\n")
            else:
                plateau_count = 0
                print(f"\n  → round {round_num} aggregate: {agg:.1%} (Δ={delta:+.2%})\n")
        else:
            print(f"\n  → round {round_num} aggregate: {agg:.1%}\n")

    # Final output
    results: dict[str, dict] = {}
    for name, state in best_state.items():
        out_path = OUTPUT_DIR / name
        out_path.write_text(state["content"], encoding="utf-8")
        results[name] = {
            "fitness": state["fitness"],
            "composite": state["composite"],
            "traits": state["traits"],
            "trait_count": len(state["traits"]),
            "trait_coverage": f"{len(state['traits'])}/{TRAIT_COUNT}",
            "status": "APPLIED",
            "source": state.get("source", "unknown"),
        }

    summary = {
        "rounds_run": round_num,
        "converged": plateau_count >= plateau_rounds,
        "final_aggregate_composite": aggregate_history[-1] if aggregate_history else 0,
        "baseline_aggregate_composite": baseline_composite,
        "aggregate_history": aggregate_history,
        "prompts": results,
        "session_log": session_log,
    }

    summary_path = OUTPUT_DIR / "evolution_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def _aggregate_composite(state: dict[str, dict]) -> float:
    if not state:
        return 0.0
    return sum(s["composite"] for s in state.values()) / len(state)


def main() -> int:
    summary = improve_until_converged()
    print("=" * 60)
    print(f"Converged: {summary['converged']} after {summary['rounds_run']} rounds")
    print(f"Baseline:  {summary['baseline_aggregate_composite']:.1%}")
    print(f"Final:     {summary['final_aggregate_composite']:.1%}")
    delta = summary["final_aggregate_composite"] - summary["baseline_aggregate_composite"]
    print(f"Total Δ:   {delta:+.2%}")
    print("=" * 60)
    for name, info in summary["prompts"].items():
        print(f"  {name}: {info['composite']:.1%}  {info['trait_coverage']} traits")
    print(f"\nSummary: {OUTPUT_DIR / 'evolution_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
