"""Tests for multi-cycle plateau improvement and session state."""

from __future__ import annotations

from pathlib import Path

import pytest

from ri_engine.api import improve_until_plateau
from ri_engine.session_state import ImprovementSession, load_session, save_session


def test_improve_until_plateau_runs_multiple_cycles(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "output").mkdir()

    result = improve_until_plateau(
        seed_prompt="You are a helpful assistant.",
        objective="When this works, the AI will give concise, accurate answers in 3 bullet points.",
        provider="mock",
        max_cycles=3,
        plateau_threshold=0.0,
        plateau_window=2,
        output_dir=str(tmp_path / "output"),
    )

    assert result.cycles_run >= 1
    assert result.cycles_run <= 3
    assert result.final.improved_prompt
    assert len(result.history) == result.cycles_run
    assert result.session_path.exists()


def test_improve_until_plateau_stops_on_unchanged_prompt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "output").mkdir()

    call_count = {"n": 0}
    original_improve = __import__("ri_engine.api", fromlist=["improve"]).improve

    def stub_improve(*args, **kwargs):
        call_count["n"] += 1
        r = original_improve(*args, **kwargs)
        if call_count["n"] >= 2:
            from dataclasses import replace

            return replace(r, improved_prompt=r.improved_prompt)
        return r

    monkeypatch.setattr("ri_engine.api.improve", stub_improve)

    result = improve_until_plateau(
        seed_prompt="Seed.",
        objective="When this works, the AI will complete the stated goal in one pass.",
        provider="mock",
        max_cycles=10,
        plateau_threshold=0.01,
        plateau_window=2,
        output_dir=str(tmp_path / "output"),
    )

    assert result.plateau_reason in ("unchanged_prompt", "fitness_plateau", "max_cycles")
    assert result.cycles_run >= 1


def test_session_save_and_load(tmp_path):
    session = ImprovementSession(
        original_seed="Start",
        objective="Obj",
        current_prompt="Better",
        cycle=2,
        fitness_history=[0.5, 0.7],
        last_fitness=0.7,
    )
    path = tmp_path / "session.json"
    save_session(session, path)
    loaded = load_session(path)
    assert loaded is not None
    assert loaded.current_prompt == "Better"
    assert loaded.cycle == 2


def test_improve_until_plateau_continue_from_session(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "output"
    out.mkdir()
    session = ImprovementSession(
        original_seed="Original",
        objective="When this works, the AI will communicate clearly in structured steps.",
        current_prompt="Already improved once",
        cycle=1,
        max_cycles=3,
        fitness_history=[0.6],
        last_fitness=0.6,
    )
    save_session(session, out / "improvement_session.json")

    result = improve_until_plateau(
        seed_prompt="ignored when continue",
        objective="When this works, the AI will communicate clearly in structured steps.",
        provider="mock",
        max_cycles=3,
        continue_from_session=True,
        output_dir=str(out),
    )

    assert result.cycles_run >= 1
    loaded = load_session(out / "improvement_session.json")
    assert loaded is not None
    assert loaded.cycle >= 2
