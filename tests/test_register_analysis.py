"""Tests for register analysis utilities."""

from ri_engine.register_analysis import (
    analyze_register,
    composite_task_score,
    translate_to_latinate,
    translate_to_plain,
)


def test_translate_to_latinate_shifts_vocabulary():
    plain = "Use this to help check and fix the issue before you start."
    latinate = translate_to_latinate(plain)
    assert "utilize" in latinate.lower() or "facilitate" in latinate.lower()
    assert "help" not in latinate.lower()


def test_translate_to_plain_reverses_latinate():
    latinate = "Utilize this to facilitate verification and remediation prior to commencement."
    plain = translate_to_plain(latinate)
    assert "use" in plain.lower()
    assert "utilize" not in plain.lower()


def test_analyze_register_detects_latinate():
    text = "Implement comprehensive verification protocol and assess remediation methodology."
    metrics = analyze_register(text)
    assert metrics.latinate_ratio > 0.5
    assert metrics.register_label in ("latinate", "mixed")
    assert len(metrics.latinate_words_found) >= 3


def test_analyze_register_detects_plain():
    text = "Use short words. Help the user fix bugs. Check tests before you merge."
    metrics = analyze_register(text)
    assert metrics.plain_count >= 3
    assert metrics.readability_score > 0.3


def test_composite_task_score_prefers_plain_for_plain_target():
    from ri_engine.register_analysis import RegisterMetrics

    plain_reg = RegisterMetrics(latinate_ratio=0.2, readability_score=0.8)
    lat_reg = RegisterMetrics(latinate_ratio=0.7, readability_score=0.4)
    assert composite_task_score(0.8, plain_reg, "plain") > composite_task_score(0.8, lat_reg, "plain")
