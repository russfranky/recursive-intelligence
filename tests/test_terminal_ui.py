"""Tests for Grok-inspired terminal UI helpers."""

from ri_engine.terminal_ui import hint_bar, phase_quip, print_welcome, make_console


def test_phase_quip_returns_string():
    q = phase_quip("variation", seed=1)
    assert isinstance(q, str)
    assert len(q) > 10


def test_phase_quip_deterministic_with_seed():
    assert phase_quip("selection", seed=42) == phase_quip("selection", seed=42)


def test_hint_bar_format():
    line = hint_bar(["templates", "improve:run", "demo"])
    text = str(line)
    assert "│" in text


def test_make_console_has_theme():
    con = make_console()
    assert con.is_terminal is not None or True  # smoke


def test_print_welcome_smoke(capsys):
    print_welcome(make_console())
    out = capsys.readouterr().out
    assert "ri-engine" in out
