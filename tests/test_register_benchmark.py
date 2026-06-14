"""Tests for register proof benchmark."""

from pathlib import Path

from ri_engine.register_benchmark import run_register_proof


def test_register_proof_runs_all_use_cases():
    cases_dir = Path(__file__).resolve().parents[1] / "config" / "use_cases"
    summary = run_register_proof(cases_dir)
    assert summary["use_cases_run"] == 6
    assert summary["proof_metrics"]["register_affects_outcomes"]
    assert "conclusion" in summary["proof_metrics"]
    assert summary["proof_metrics"]["avg_latinate_ratio_shift"] > 0
