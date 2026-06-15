"""Tests for use case benchmark and prompt rubric."""

from pathlib import Path

from ri_engine.benchmark import run_benchmark
from ri_engine.prompt_rubric import compare_prompts, score_task_prompt

WEAK = "You are a code reviewer. Review the pull request and give feedback."
STRONG = """# Code Review Agent

## Process
1. Step 1: Read diff
2. Step 2: Score severity (P0-P3)

## Failure Modes
Never optimize for engagement. Avoid style nitpicks.

## Self-Evaluation
Before submitting, score yourself 0.0-1.0 on completeness. Revise once if < 0.7.

## Output Format
Return ONLY markdown with severity ratings.

Success criteria: actionable feedback developer can implement."""


def test_weak_prompt_scores_low():
    q = score_task_prompt(WEAK)
    assert q.total < 0.5
    assert q.grade.startswith("D") or q.grade.startswith("F")


def test_strong_prompt_scores_high():
    q = score_task_prompt(STRONG)
    assert q.total > 0.6
    assert len(q.features_present) > len(score_task_prompt(WEAK).features_present)


def test_compare_shows_improvement():
    cmp = compare_prompts(WEAK, STRONG)
    assert cmp["after_score"] > cmp["before_score"]
    assert cmp["delta"] > 0
    assert len(cmp["features_gained"]) > 0


def test_benchmark_runs_all_use_cases():
    cases_dir = Path(__file__).resolve().parents[1] / "config" / "use_cases"
    summary = run_benchmark(cases_dir)
    assert summary["use_cases_run"] == 6
    assert summary["proof_metrics"]["all_improved"]
    assert summary["proof_metrics"]["avg_quality_after"] > summary["proof_metrics"]["avg_quality_before"]
