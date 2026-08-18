from __future__ import annotations

import json
from pathlib import Path

from ri_engine.unix_compound import (
    check_module,
    classify_domain,
    diminishing_returns,
    lock_goal,
    render_sidecar,
    run_until_idle,
    start,
    step,
    vsr_build,
)


def test_classify_known_domains():
    assert classify_domain("help me get healthier") == "health"
    assert classify_domain("personal daily operating system") == "daily"
    assert classify_domain("refactor a chaotic prompt library") == "prompt"
    assert classify_domain("ship a new feature research design implement") == "feature"


def test_start_proposes_measurable_criteria(tmp_path: Path):
    session = start("daily operating system ≤15 minutes", path=tmp_path / "s.json")
    assert session.phase == "goal"
    assert 3 <= len(session.criteria) <= 5
    assert any(c.kind == "constraint" for c in session.criteria)
    sidecar = render_sidecar(session)
    assert "unix-compound · sidecar" in sidecar
    assert "goal" in sidecar


def test_full_run_locks_modules_and_stops(tmp_path: Path):
    path = tmp_path / "s.json"
    session = start("refactor a messy prompt library", path=path)
    session = lock_goal(session, path=path)
    session = run_until_idle(session, path=path)
    assert session.modules
    assert any(m.status == "locked" for m in session.modules)
    assert session.decision in {"terminate", "continue"}
    assert session.baseline is not None
    saved = json.loads(path.read_text())
    assert saved["domain"].startswith("refactor")


def test_vsr_prefers_simple_over_bloated(tmp_path: Path):
    session = start("clean up my prompt library", path=tmp_path / "s.json")
    session = lock_goal(session, path=tmp_path / "s.json")
    session = step(session, path=tmp_path / "s.json")  # skeleton
    session = step(session, path=tmp_path / "s.json")  # sequence
    target = session.modules[0]
    vsr_build(session, target)
    ids = [v["id"] for v in target.variants]
    assert "bloated" in ids
    assert target.lineage[0] != "bloated"
    ok, _ = check_module(session, target)
    assert ok


def test_provisional_lock_after_two_proposes(tmp_path: Path):
    from ri_engine.unix_compound import propose_again

    path = tmp_path / "s.json"
    session = start("something vague about life", path=path)
    session = propose_again(session, path=path)
    assert session.goal_locked
    assert session.goal_provisional


def test_diminishing_returns_rule():
    from ri_engine.unix_compound import Criterion, Session

    s = Session(domain="x", low_impact_streak=2)
    s.criteria = [
        Criterion(text="a", status="met"),
        Criterion(text="b", status="met"),
        Criterion(text="c", status="deferred"),
    ]
    s.residuals = ["optional polish"]
    assert diminishing_returns(s)


def test_resource_constraint_prunes_daily_skeleton(tmp_path: Path):
    path = tmp_path / "s.json"
    session = start("daily operating system that must fit in 15 minutes", path=path)
    session = lock_goal(session, path=path)
    from ri_engine.unix_compound import run_skeleton

    session = run_skeleton(session, path=path)
    assert len(session.modules) <= 4
