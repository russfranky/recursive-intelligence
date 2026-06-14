#!/usr/bin/env python3
"""Example: run the recursive intelligence engine on the Uzwyshyn-inspired config."""

from pathlib import Path

from ri_engine import RecursiveIntelligenceEngine


def main() -> None:
    config_path = Path(__file__).resolve().parents[1] / "config" / "example.yaml"
    config = RecursiveIntelligenceEngine.load_config(config_path)

    engine = RecursiveIntelligenceEngine()
    report = engine.run(config)

    print(f"\n{'='*60}")
    print(f"Generations: {report['meta']['generations_run']}")
    print(f"Converged:   {report['meta']['converged']}")
    print(f"Best fitness: {report['best_fitness']:.4f}")
    print(f"{'='*60}\n")
    print("BEST PROMPT:\n")
    print(report["best_prompt"])
    print(f"\n{'='*60}")
    print("Fitness trajectory:")
    for entry in report["fitness_trajectory"]:
        bar = "█" * int(entry["fitness"] * 30)
        print(f"  Gen {entry['generation']:2d}: {entry['fitness']:.4f} {bar}")


if __name__ == "__main__":
    main()
