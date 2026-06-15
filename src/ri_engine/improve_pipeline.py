"""Improve pipeline — gate metadata, baseline vs VSR selection, diagnostics."""

from __future__ import annotations

from typing import Any

from ri_engine.prompt_rubric import composite_prompt_score
from ri_engine.prompt_synthesizer import finalize_prompt

VSR_MIN_GAIN = 0.03
VSR_MAX_LENGTH_GROWTH = 0.35


def build_improve_metadata(
    *,
    metadata: dict[str, Any] | None = None,
    linguistic_gate: str = "auto",
    leaning: str | None = None,
    enable_macro_learning: bool = False,
) -> dict[str, Any]:
    """Merge user metadata with gate/macro defaults from the research-backed API."""
    meta = dict(metadata or {})
    meta.setdefault("linguistic_gate_mode", linguistic_gate)
    meta.setdefault("apply_linguistic_gate", linguistic_gate != "off")
    meta.setdefault("enable_macro_learning", enable_macro_learning)
    if leaning:
        meta["linguistic_leaning"] = leaning
    return meta


def pick_improved_prompt(
    *,
    seed: str,
    objective: str,
    report: dict[str, Any],
    leaning: str,
    membrane: str = "",
) -> tuple[str, dict[str, Any]]:
    """
    Compare one-shot finalize vs VSR winner; return the better prompt + diagnostics.

    VSR must beat baseline by ``VSR_MIN_GAIN`` without excessive length growth.
    """
    baseline = finalize_prompt(seed, objective, "constraint_first", membrane, leaning=leaning)
    vsr_raw = str(report.get("best_prompt", "")).strip()
    candidates: list[tuple[str, str]] = [("one_shot_finalize", baseline)]
    if vsr_raw and vsr_raw != baseline.strip():
        candidates.append(("vsr_winner", vsr_raw))

    scored = [
        (name, text, composite_prompt_score(text, objective, leaning=leaning))
        for name, text in candidates
    ]
    baseline_row = next(row for row in scored if row[0] == "one_shot_finalize")
    best = max(scored, key=lambda row: row[2]["total"])

    chosen_name, chosen_text, chosen_scores = best
    b_scores = baseline_row[2]
    length_ratio = chosen_scores["word_count"] / max(b_scores["word_count"], 1.0)
    gain = chosen_scores["total"] - b_scores["total"]

    if chosen_name != "one_shot_finalize":
        if gain < VSR_MIN_GAIN or (
            length_ratio > 1.0 + VSR_MAX_LENGTH_GROWTH
            and chosen_scores["objective_alignment"] <= b_scores["objective_alignment"] + 0.02
        ):
            chosen_name, chosen_text, chosen_scores = baseline_row

    diagnostics = {
        "chosen_source": chosen_name,
        "resolved_leaning": leaning,
        "baseline_scores": b_scores,
        "chosen_scores": chosen_scores,
        "vsr_report_fitness": report.get("best_fitness"),
        "score_gain_vs_baseline": round(chosen_scores["total"] - b_scores["total"], 4),
        "length_ratio_vs_baseline": round(
            chosen_scores["word_count"] / max(b_scores["word_count"], 1.0), 4
        ),
        "mock_mode_note": (
            "Mock mode scores structural prompt quality locally; "
            "it does not prove downstream LLM task performance."
        ),
    }
    gate = report.get("linguistic_gate") or {}
    diagnostics.update({
        "leaning_confidence": gate.get("confidence"),
        "leaning_source": gate.get("source"),
        "objective_signal": gate.get("objective_signal"),
        "registry_signal": gate.get("registry_signal"),
        "objective_leaning": gate.get("objective_leaning"),
        "registry_leaning": gate.get("registry_leaning"),
    })
    return chosen_text, diagnostics
