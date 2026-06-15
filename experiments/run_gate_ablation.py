#!/usr/bin/env python3
"""
Linguistic gate ablation — local, no API key.

Compares gate modes on fixture seed/goal pairs under mock provider scoring.
Does not prove downstream LLM task performance.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from ri_engine import improve  # noqa: E402

CASES_PATH = Path(__file__).with_name("gate_ablation_cases.yaml")
OUTPUT_PATH = Path(__file__).with_name("gate_ablation_results.json")


def load_config() -> tuple[list[dict], list[str]]:
    data = yaml.safe_load(CASES_PATH.read_text(encoding="utf-8"))
    return data["cases"], data["conditions"]


def run_ablation(*, max_generations: int = 2, population_size: int = 4) -> list[dict]:
    cases, conditions = load_config()
    results: list[dict] = []

    for case in cases:
        for condition in conditions:
            result = improve(
                seed_prompt=case["seed"],
                objective=case["goal"],
                provider="mock",
                max_generations=max_generations,
                population_size=population_size,
                linguistic_gate=condition,
                skip_clarity_check=True,
                return_diagnostics=True,
            )
            diag = result.diagnostics or {}
            chosen = diag.get("chosen_scores") or {}
            results.append(
                {
                    "case_id": case["id"],
                    "expected_leaning": case["expected_leaning"],
                    "condition": condition,
                    "resolved_leaning": diag.get("resolved_leaning"),
                    "leaning_confidence": diag.get("leaning_confidence"),
                    "objective_signal": diag.get("objective_signal"),
                    "registry_signal": diag.get("registry_signal"),
                    "fitness": result.fitness,
                    "rubric_score": chosen.get("rubric_score"),
                    "objective_alignment": chosen.get("objective_alignment"),
                    "register_fit": chosen.get("register_fit"),
                    "instruction_economy": chosen.get("instruction_economy"),
                    "chosen_source": diag.get("chosen_source"),
                    "score_gain_vs_baseline": diag.get("score_gain_vs_baseline"),
                    "length_ratio_vs_baseline": diag.get("length_ratio_vs_baseline"),
                    "prompt_length": int(chosen.get("word_count") or 0),
                    "prompt": result.improved_prompt,
                }
            )
    return results


def print_summary(results: list[dict]) -> None:
    by_condition: dict[str, list[dict]] = {}
    for row in results:
        by_condition.setdefault(row["condition"], []).append(row)

    print("\nAverage composite score by condition:")
    for condition, rows in sorted(by_condition.items()):
        scores = [r["rubric_score"] for r in rows if r.get("rubric_score") is not None]
        if scores:
            print(f"  {condition:16} {statistics.mean(scores):.4f}")

    print("\nExpected-leaning win check (by composite rubric score):")
    case_ids = sorted({r["case_id"] for r in results})
    for case_id in case_ids:
        rows = [r for r in results if r["case_id"] == case_id]
        scored = [r for r in rows if r.get("rubric_score") is not None]
        if not scored:
            continue
        winner = max(scored, key=lambda r: r["rubric_score"])
        expected = next(r["expected_leaning"] for r in rows)
        print(
            f"  {case_id}: expected={expected}, "
            f"winner={winner['condition']} (score={winner['rubric_score']})"
        )


def main() -> int:
    results = run_ablation()
    OUTPUT_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote {len(results)} rows to {OUTPUT_PATH}")
    print_summary(results)
    print(
        "\nNote: mock mode scores structural prompt quality locally; "
        "it does not prove downstream LLM task performance."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
