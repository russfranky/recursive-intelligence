"""Tests for client-facing presentation layer."""

from ri_engine.client_view import (
    build_client_summary,
    list_templates,
    load_template,
    template_to_metadata,
)


def test_list_templates_has_six_plug_and_play():
    templates = list_templates()
    assert len(templates) >= 6
    ids = {t["id"] for t in templates}
    assert "customer-support" in ids
    assert "code-review" in ids


def test_load_template_extends_use_case():
    data = load_template("customer-support")
    assert "seed_prompt" in data
    assert data.get("display_name") == "Customer Support Agent"


def test_template_to_metadata_sets_gate_audience():
    data = load_template("customer-support")
    meta = template_to_metadata(data)
    assert meta["audience"] == "end_user"
    assert meta["category"] == "Operations"


def test_build_client_summary_plain_language():
    report = {
        "meta": {"generations_run": 3, "converged": True},
        "best_fitness": 0.92,
        "best_prompt": "You are a helpful agent.",
        "linguistic_gate": {"leaning": "plain", "confidence": 0.85, "rationale": "plain wins"},
        "config": {"objective": "Help customers"},
    }
    summary = build_client_summary(report)
    assert "production-ready" in summary["headline"].lower() or "stronger" in summary["headline"].lower()
    assert summary["quality_score"] == "92%"
    assert "your_improved_prompt" in summary
    assert len(summary["what_we_did"]) >= 3
