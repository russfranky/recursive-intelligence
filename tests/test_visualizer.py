"""Tests for CLI visuals and event system."""

from ri_engine.engine import RecursiveIntelligenceEngine
from ri_engine.events import EventKind
from ri_engine.models import RunConfig
from ri_engine.observer import EventCollector
from ri_engine.resilient_llm import wrap_provider
from ri_engine.visualizer import ProcessVisualizer


def test_event_collector_captures_run_lifecycle():
    collector = EventCollector()
    engine = RecursiveIntelligenceEngine(observer=collector)
    config = RunConfig(
        seed_prompt="Test prompt.",
        objective="Improve test prompt.",
        max_generations=2,
        population_size=3,
        survivors_count=1,
        enable_membrane_bridge=False,
    )
    engine.run(config)

    kinds = {e.kind for e in collector.events}
    assert EventKind.RUN_START in kinds
    assert EventKind.RUN_COMPLETE in kinds
    assert EventKind.GENERATION_START in kinds
    assert EventKind.VARIANT_SPAWN in kinds
    assert EventKind.SCORE in kinds


def test_visualizer_renders_without_live():
    config = RunConfig(
        seed_prompt="Test.",
        objective="Test objective.",
        max_generations=3,
        population_size=4,
    )
    viz = ProcessVisualizer(config, provider="mock")
    viz.on_event(collector_event(EventKind.RUN_START, "starting"))
    viz.on_event(collector_event(EventKind.GENERATION_START, "gen 1", generation=1))
    viz.on_event(collector_event(EventKind.LEARNING, "trait preserved", generation=1))
    layout = viz.render()
    assert layout is not None
    summary = viz.render_summary()
    assert summary is not None


def test_simulated_retries_emit_events():
    collector = EventCollector()
    from ri_engine.llm_provider import MockLLMProvider

    llm = wrap_provider(MockLLMProvider(), observer=collector, simulate_failures=True)
    # Force multiple calls to trigger simulated failure path
    for i in range(8):
        llm.complete("VARIATION system", f"Generate variant {i}", 0.7)

    retry_events = collector.of_kind("retry")
    error_events = collector.of_kind("error")
    assert len(retry_events) + len(error_events) >= 1


def test_visualizer_tracks_issues_and_learnings():
    config = RunConfig(seed_prompt="x", objective="y", max_generations=2, population_size=2)
    viz = ProcessVisualizer(config)
    viz.on_event(collector_event(EventKind.RETRY, "retry 2/3", generation=1))
    viz.on_event(collector_event(EventKind.ERROR, "timeout", generation=1))
    viz.on_event(collector_event(EventKind.LEARNING, "keep constraint-first structure", generation=1))
    assert viz.state.retries == 1
    assert viz.state.errors == 1
    assert len(viz.state.learnings) == 1
    assert len(viz.state.issues) == 2


def collector_event(kind: EventKind, message: str, generation: int = 0):
    from ri_engine.events import RunEvent

    return RunEvent(kind=kind, message=message, generation=generation)
