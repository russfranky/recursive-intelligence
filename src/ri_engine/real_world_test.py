"""
Real-world test runner — prep session artifacts and run production tests.

Usage:
  ri-engine real-world prep          # validate system, scaffold session
  ri-engine real-world run           # run config/real_world/active.yaml
  ri-engine real-world run -c path   # run a specific session config
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ri_engine.client_view import (
    build_client_summary,
    clean_prompt_for_client,
    print_client_result,
    template_to_metadata,
)
from ri_engine.engine import RecursiveIntelligenceEngine
from ri_engine.language_leanings import LinguisticRegistry
from ri_engine.models import RunConfig
from ri_engine.prompt_rubric import compare_prompts, score_task_prompt
from ri_engine.prompt_synthesizer import finalize_prompt
from ri_engine.resilient_llm import wrap_provider
from ri_engine.visualizer import ProcessVisualizer

ROOT = Path(__file__).resolve().parents[2]
REAL_WORLD_CONFIG_DIR = ROOT / "config" / "real_world"
OUTPUT_DIR = ROOT / "output" / "real_world"
ACTIVE_CONFIG = REAL_WORLD_CONFIG_DIR / "active.yaml"
SESSION_TEMPLATE = REAL_WORLD_CONFIG_DIR / "session.template.yaml"
PROMPTS_DIR = ROOT / "prompts"

console = Console()


def prep_real_world_test(*, force: bool = False) -> dict[str, Any]:
    """
    Validate the engine is ready and scaffold a real-world test session.
    Call this before the user provides context; fill active.yaml next.
    """
    REAL_WORLD_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "sessions").mkdir(parents=True, exist_ok=True)

    checks: list[dict[str, str]] = []

    def _check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "status": "ok" if ok else "fail", "detail": detail})

    # Package import
    try:
        import ri_engine  # noqa: F401
        _check("Engine installed", True, f"v{getattr(ri_engine, '__version__', '?')}")
    except ImportError as exc:
        _check("Engine installed", False, str(exc))

    # Operator prompts
    op_count = len(list(PROMPTS_DIR.glob("*.md")))
    _check("Operator prompts", op_count >= 5, f"{op_count} prompts in prompts/")

    # Linguistic registry
    reg_path = ROOT / "config" / "linguistic_registry.json"
    if reg_path.exists():
        reg = LinguisticRegistry(reg_path).load()
        _check("Language registry", len(reg.entries) >= 5, f"{len(reg.entries)} category cells pooled")
    else:
        _check("Language registry", False, "Run: ri-engine expert pool-linguistic-registry")

    # Providers
    _check("Mock provider (offline)", True, "Ready — no API key needed")
    _check("OpenAI provider", bool(os.environ.get("OPENAI_API_KEY")), "Set OPENAI_API_KEY to enable")
    _check("Anthropic provider", bool(os.environ.get("ANTHROPIC_API_KEY")), "Set ANTHROPIC_API_KEY to enable")

    # Session scaffold
    if not ACTIVE_CONFIG.exists() or force:
        if SESSION_TEMPLATE.exists():
            shutil.copy2(SESSION_TEMPLATE, ACTIVE_CONFIG)
            _check("Session config", True, f"Created {ACTIVE_CONFIG}")
        else:
            _write_default_template()
            shutil.copy2(SESSION_TEMPLATE, ACTIVE_CONFIG)
            _check("Session config", True, f"Created template + {ACTIVE_CONFIG}")
    else:
        _check("Session config", True, f"Exists: {ACTIVE_CONFIG} (use --force to reset)")

    ready = all(c["status"] == "ok" for c in checks if c["check"] not in (
        "OpenAI provider", "Anthropic provider"
    ))

    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "ready" if ready else "needs_attention",
        "checks": checks,
        "next_steps": [
            f"Edit {ACTIVE_CONFIG} with your seed prompt and goal",
            "Run: ri-engine real-world run",
            "Or paste context in chat — we'll fill active.yaml and run for you",
        ],
        "paths": {
            "active_config": str(ACTIVE_CONFIG),
            "output_dir": str(OUTPUT_DIR),
            "session_template": str(SESSION_TEMPLATE),
        },
    }
    manifest_path = OUTPUT_DIR / "prep_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    _print_prep(manifest)
    return manifest


def _write_default_template() -> None:
    SESSION_TEMPLATE.write_text(
        """# Real-World Test Session
# Fill in seed_prompt and objective, then: ri-engine real-world run

name: "Real-World Test"
description: "Describe what you're testing"
category: "Operations"
audience: "end_user"

seed_prompt: |
  Paste your current prompt here.

objective: |
  Describe what success looks like — who uses it, what output you need,
  and how you'll know the improved prompt works in production.

provider: mock
max_generations: 6
population_size: 8
survivors_count: 2
enable_membrane_bridge: true

domains: []

metadata:
  use_case: real_world
  test_id: ""
  client: ""
  apply_linguistic_gate: true

output_dir: ./output/real_world/sessions
""",
        encoding="utf-8",
    )


def load_session_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or ACTIVE_CONFIG
    if not cfg_path.exists():
        raise FileNotFoundError(
            f"No session config at {cfg_path}. Run: ri-engine real-world prep"
        )
    return yaml.safe_load(cfg_path.read_text(encoding="utf-8"))


def build_run_config(data: dict[str, Any]) -> RunConfig:
    meta = {
        **data.get("metadata", {}),
        "category": data.get("category", ""),
        "audience": data.get("audience", "operator"),
        "apply_linguistic_gate": data.get("metadata", {}).get("apply_linguistic_gate", True),
    }
    if data.get("category") and "audience" not in data.get("metadata", {}):
        meta.update(template_to_metadata(data))

    return RunConfig(
        seed_prompt=data["seed_prompt"],
        objective=data["objective"],
        max_generations=data.get("max_generations", 6),
        population_size=data.get("population_size", 8),
        survivors_count=data.get("survivors_count", 2),
        convergence_threshold=data.get("convergence_threshold", 0.025),
        convergence_window=data.get("convergence_window", 2),
        variation_temperature=data.get("variation_temperature", 0.75),
        enable_membrane_bridge=data.get("enable_membrane_bridge", True),
        domains=data.get("domains", []),
        fitness_weights=data.get("fitness_weights") or {
            "clarity": 0.25,
            "novelty": 0.25,
            "utility": 0.30,
            "coherence": 0.20,
        },
        metadata=meta,
    )


def write_session_from_context(
    *,
    name: str,
    seed_prompt: str,
    objective: str,
    category: str = "Operations",
    audience: str = "operator",
    provider: str = "mock",
    description: str = "",
    test_id: str = "",
    client: str = "",
    domains: list[str] | None = None,
) -> Path:
    """Write active.yaml from user-provided context (for chat-driven tests)."""
    REAL_WORLD_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "name": name,
        "description": description,
        "category": category,
        "audience": audience,
        "seed_prompt": seed_prompt.strip(),
        "objective": objective.strip(),
        "provider": provider,
        "max_generations": 6,
        "population_size": 8,
        "survivors_count": 2,
        "enable_membrane_bridge": True,
        "domains": domains or [],
        "metadata": {
            "use_case": "real_world",
            "test_id": test_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            "client": client,
            "apply_linguistic_gate": True,
        },
    }
    ACTIVE_CONFIG.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True), encoding="utf-8")
    return ACTIVE_CONFIG


def run_real_world_test(
    config_path: Path | None = None,
    *,
    provider: str | None = None,
    expert: bool = False,
    quiet: bool = False,
) -> dict[str, Any]:
    """Execute a real-world test session and save full artifacts."""
    data = load_session_config(config_path)
    config = build_run_config(data)
    prov = provider or data.get("provider", "mock")
    session_id = config.metadata.get("test_id") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    session_dir = OUTPUT_DIR / "sessions" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    # Save inputs
    (session_dir / "seed_prompt.md").write_text(config.seed_prompt, encoding="utf-8")
    (session_dir / "objective.md").write_text(config.objective, encoding="utf-8")
    (session_dir / "session.yaml").write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")

    if not quiet and not expert:
        console.print(Panel(
            f"[bold]{data.get('name', 'Real-World Test')}[/bold]\n"
            f"{data.get('description', '')}\n\n"
            f"Provider: {prov} · Session: {session_id}",
            title="Real-World Test",
            border_style="green",
        ))

    use_visual = not quiet and not expert
    visualizer: ProcessVisualizer | None = None
    if use_visual:
        visualizer = ProcessVisualizer(config, provider=prov, simple_mode=True)
        visualizer.start()

    from ri_engine.llm_provider import create_provider

    llm = wrap_provider(create_provider(prov), observer=visualizer)
    engine = RecursiveIntelligenceEngine(llm, observer=visualizer)

    try:
        report = engine.run(config)
    finally:
        if visualizer:
            visualizer.stop()

    # Finalize prompt for client delivery
    gate = report.get("linguistic_gate", {})
    leaning = gate.get("leaning") or config.metadata.get("linguistic_leaning", "plain")
    membrane = ""
    if config.enable_membrane_bridge:
        from ri_engine.llm_provider import MockLLMProvider
        membrane = MockLLMProvider()._bridge(config.objective)
    evolved = finalize_prompt(
        config.seed_prompt, config.objective, "constraint_first", membrane, leaning=leaning,
    )
    report = dict(report)
    report["best_prompt"] = evolved

    use_case = config.metadata.get("use_case", "real_world")
    seed_q = score_task_prompt(config.seed_prompt, use_case)
    evolved_q = score_task_prompt(evolved, use_case)
    comparison = compare_prompts(config.seed_prompt, evolved, use_case)

    # Artifacts
    (session_dir / "evolved_prompt.md").write_text(clean_prompt_for_client(evolved), encoding="utf-8")
    (session_dir / "technical_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    client_summary = build_client_summary(report)
    client_summary["before_quality"] = f"{seed_q.total:.0%}"
    client_summary["after_quality"] = f"{evolved_q.total:.0%}"
    client_summary["quality_gain"] = f"+{comparison['delta_pct']:.0f}%"
    client_summary["grade"] = f"{seed_q.grade.split('—')[0].strip()} → {evolved_q.grade.split('—')[0].strip()}"
    client_summary["session_id"] = session_id

    result_path = session_dir / "result.json"
    result_path.write_text(json.dumps(client_summary, indent=2), encoding="utf-8")

    summary = {
        "session_id": session_id,
        "session_dir": str(session_dir),
        "name": data.get("name", ""),
        "provider": prov,
        "seed_quality": seed_q.total,
        "evolved_quality": evolved_q.total,
        "quality_delta_pct": comparison["delta_pct"],
        "grade_before": seed_q.grade,
        "grade_after": evolved_q.grade,
        "features_gained": comparison.get("features_gained", []),
        "linguistic_gate": gate,
        "client_summary": client_summary,
        "evolved_prompt_path": str(session_dir / "evolved_prompt.md"),
        "result_path": str(result_path),
    }

    latest_path = OUTPUT_DIR / "latest_result.json"
    latest_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if expert:
        console.print(Panel(evolved, title="Evolved Prompt (Technical)"))
    elif not quiet:
        print_client_result(console, report, output_path=result_path)

    if not quiet:
        console.print(f"\n[dim]Session artifacts: {session_dir}[/dim]")

    return summary


def _print_prep(manifest: dict[str, Any]) -> None:
    status = manifest["status"]
    style = "green" if status == "ready" else "yellow"
    console.print(Panel(
        f"Status: [{style}]{status.upper()}[/{style}]\n\n"
        "The system is staged for your real-world test.\n"
        "Provide your context in the next message — we'll fill the session and run.",
        title="Real-World Test — Ready",
        border_style="green",
    ))

    table = Table(title="System Checks")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")
    for c in manifest["checks"]:
        st = "[green]✓[/green]" if c["status"] == "ok" else "[yellow]○[/yellow]"
        table.add_row(c["check"], st, c["detail"][:50])
    console.print(table)

    console.print("\n[bold]Next:[/bold]")
    for step in manifest["next_steps"]:
        console.print(f"  • {step}")


def main_prep(force: bool = False) -> int:
    prep_real_world_test(force=force)
    return 0


def main_run(config_path: str | None = None, provider: str | None = None, expert: bool = False, quiet: bool = False) -> int:
    path = Path(config_path) if config_path else None
    try:
        run_real_world_test(path, provider=provider, expert=expert, quiet=quiet)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    return 0
