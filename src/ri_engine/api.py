"""
Public API — single entry point for programmatic prompt improvement.

Usage:
    from ri_engine import improve, improve_template, list_templates

    result = improve(
        seed_prompt="You are a helper.",
        objective="Resolve billing issues in one conversation.",
    )
    print(result.improved_prompt)
    print(result.to_dict())  # JSON-serializable
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ri_engine.client_view import list_templates as _list_templates
from ri_engine.client_view import load_template
from ri_engine.engine import RecursiveIntelligenceEngine
from ri_engine.llm_provider import MockLLMProvider, create_provider
from ri_engine.models import RunConfig
from ri_engine.improve_pipeline import build_improve_metadata, pick_improved_prompt
from ri_engine.resilient_llm import wrap_provider


def list_templates() -> list[dict[str, str]]:
    """Return available plug-and-play template ids and metadata."""
    return _list_templates()


@dataclass
class ImproveResult:
    """Outcome of a prompt improvement run."""

    improved_prompt: str
    fitness: float
    generations: int
    converged: bool
    report: dict[str, Any]
    engine_prompt: str = field(default="")
    diagnostics: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_report(
        cls,
        report: dict[str, Any],
        *,
        improved_prompt: str,
        diagnostics: dict[str, Any] | None = None,
    ) -> ImproveResult:
        meta = report.get("meta", {})
        return cls(
            improved_prompt=improved_prompt,
            fitness=float(report.get("best_fitness", 0.0)),
            generations=int(meta.get("generations_run", 0)),
            converged=bool(meta.get("converged", False)),
            report=report,
            engine_prompt=str(report.get("best_prompt", "")),
            diagnostics=diagnostics or {},
        )

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable summary for REST handlers and logging."""
        gate = self.report.get("linguistic_gate") or {}
        return {
            "improved_prompt": self.improved_prompt,
            "engine_prompt": self.engine_prompt,
            "fitness": self.fitness,
            "generations": self.generations,
            "converged": self.converged,
            "linguistic_leaning": gate.get("leaning"),
            "fitness_trajectory": self.report.get("fitness_trajectory", []),
            "diagnostics": self.diagnostics,
        }


def _validate_inputs(seed_prompt: str, objective: str) -> None:
    if not seed_prompt or not seed_prompt.strip():
        raise ValueError("seed_prompt must be a non-empty string")
    if not objective or not objective.strip():
        raise ValueError("objective must be a non-empty string")


class ObjectiveTooVagueError(ValueError):
    """Raised when goal clarity is below threshold."""

    def __init__(self, assessment: Any) -> None:
        self.assessment = assessment
        super().__init__(getattr(assessment, "kickback_message", "Objective too vague"))


def assess_objective(objective: str, *, metadata: dict[str, Any] | None = None) -> Any:
    """Score goal clarity; see ``ri_engine.objective_clarity.ObjectiveAssessment``."""
    from ri_engine.objective_clarity import assess_objective as _assess

    return _assess(objective, metadata=metadata)


def improve(
    seed_prompt: str,
    objective: str,
    *,
    max_generations: int = 5,
    population_size: int = 6,
    survivors_count: int = 2,
    provider: str = "mock",
    enable_membrane_bridge: bool = True,
    metadata: dict[str, Any] | None = None,
    domains: list[str] | None = None,
    fitness_weights: dict[str, float] | None = None,
    skip_clarity_check: bool = False,
    force_goal: bool = False,
    linguistic_gate: str = "auto",
    leaning: str | None = None,
    enable_macro_learning: bool = False,
    return_diagnostics: bool = False,
) -> ImproveResult:
    """
    Improve a task prompt recursively (Variation → Selection → Retention).

    Returns ``improved_prompt`` with linguistic gate clauses preserved.
    Raw VSR fields: ``result.engine_prompt``, ``result.report``.

    Args:
        seed_prompt: Starting prompt text.
        objective: What the improved prompt must achieve.
        max_generations: VSR rounds (default 5).
        population_size: Variants per generation (default 6).
        survivors_count: Survivors carried to next generation (default 2).
        provider: ``mock`` (offline), ``openai``, or ``anthropic``.
        enable_membrane_bridge: Cross-domain insight injection (default True).
        metadata: Extra run metadata (category, audience, linguistic gate).
        domains: Optional domain hints for membrane cross-pollination.
        fitness_weights: Override selection dimension weights.
        linguistic_gate: ``auto``, ``off``, ``neutral``, or a forced leaning name.
        leaning: Force register leaning (overrides auto gate).
        enable_macro_learning: Persistent macro trait registry (default off).
        return_diagnostics: Include ablation/baseline diagnostics on the result.

    Returns:
        ImproveResult with ``improved_prompt`` from the VSR + finalize path.
    """
    _validate_inputs(seed_prompt, objective)

    meta = build_improve_metadata(
        metadata=metadata,
        linguistic_gate=linguistic_gate,
        leaning=leaning,
        enable_macro_learning=enable_macro_learning,
    )
    objective_text = objective.strip()

    if not skip_clarity_check and not force_goal:
        check = assess_objective(objective_text, metadata=meta)
        if check.blocked:
            raise ObjectiveTooVagueError(check)
        if check.ready and check.normalized_objective:
            objective_text = check.normalized_objective
        meta["objective_clarity_score"] = check.clarity_score

    config_fields: dict[str, Any] = {
        "seed_prompt": seed_prompt.strip(),
        "objective": objective_text,
        "max_generations": max_generations,
        "population_size": population_size,
        "survivors_count": survivors_count,
        "enable_membrane_bridge": enable_membrane_bridge,
        "domains": domains or [],
        "metadata": meta,
    }
    if fitness_weights:
        config_fields["fitness_weights"] = fitness_weights
    config = RunConfig(**config_fields)

    llm = wrap_provider(create_provider(provider))
    report = RecursiveIntelligenceEngine(llm).run(config)

    gate = report.get("linguistic_gate", {})
    resolved_leaning = gate.get("leaning") or meta.get("linguistic_leaning", "mixed")
    membrane = ""
    if config.enable_membrane_bridge:
        membrane = MockLLMProvider()._bridge(config.objective)
    improved, diagnostics = pick_improved_prompt(
        seed=config.seed_prompt,
        objective=config.objective,
        report=report,
        leaning=str(resolved_leaning),
        membrane=membrane,
    )
    if not return_diagnostics:
        diagnostics = {}

    return ImproveResult.from_report(report, improved_prompt=improved, diagnostics=diagnostics)


@dataclass
class PlateauImproveResult:
    """Outcome of multi-cycle improvement until fitness plateaus."""

    final: ImproveResult
    history: list[ImproveResult]
    cycles_run: int
    plateau_reason: str
    session_path: Path
    runbook_path: Path | None = None
    trait_export_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "improved_prompt": self.final.improved_prompt,
            "fitness": self.final.fitness,
            "cycles_run": self.cycles_run,
            "plateau_reason": self.plateau_reason,
            "fitness_history": [r.fitness for r in self.history],
            "session_path": str(self.session_path),
            "runbook_path": str(self.runbook_path) if self.runbook_path else None,
            "trait_export_path": str(self.trait_export_path) if self.trait_export_path else None,
        }


def _fitness_plateau(history: list[float], threshold: float, window: int) -> bool:
    if len(history) < window + 1:
        return False
    for i in range(len(history) - window, len(history)):
        if abs(history[i] - history[i - 1]) >= threshold:
            return False
    return True


def improve_until_plateau(
    seed_prompt: str,
    objective: str,
    *,
    max_cycles: int = 3,
    plateau_threshold: float = 0.01,
    plateau_window: int = 2,
    continue_from_session: bool = False,
    output_dir: str | Path = "output",
    approve_to_runbook: bool = False,
    runbook_name: str = "",
    runbook_dir: str | Path | None = None,
    share_traits: bool = False,
    on_cycle: Callable[[int, int, ImproveResult], None] | None = None,
    cycle_runner: Callable[[str], ImproveResult] | None = None,
    **improve_kwargs: Any,
) -> PlateauImproveResult:
    """
    Run ``improve()`` repeatedly, chaining each cycle's output as the next seed.

    Stops when fitness deltas stay below ``plateau_threshold`` for
    ``plateau_window`` consecutive cycles, the prompt stops changing, or
    ``max_cycles`` is reached. Session state is saved after every cycle so
    ``--continue`` can resume across CLI invocations.
    """
    from ri_engine.runbook import approve_prompt, compile_runbook
    from ri_engine.session_state import ImprovementSession, load_session, save_session

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    session_path = out / "improvement_session.json"

    session: ImprovementSession | None = None
    if continue_from_session:
        session = load_session(session_path)
        if session is None:
            raise ValueError(
                f"No saved session at {session_path}. Run without --continue first."
            )
        current = session.current_prompt
        objective = session.objective
        seed_prompt = session.original_seed
        start_cycle = session.cycle
        fitness_history = list(session.fitness_history)
        template = session.template
        improve_kwargs["skip_clarity_check"] = True
    else:
        _validate_inputs(seed_prompt, objective)
        if not improve_kwargs.get("force_goal") and not improve_kwargs.get("skip_clarity_check"):
            check = assess_objective(objective.strip(), metadata=improve_kwargs.get("metadata"))
            if check.blocked:
                raise ObjectiveTooVagueError(check)
        improve_kwargs["skip_clarity_check"] = True
        current = seed_prompt.strip()
        start_cycle = 0
        fitness_history = []
        template = str(improve_kwargs.pop("template", "") or "")

    history: list[ImproveResult] = []
    plateau_reason = "max_cycles"
    cycles_this_run = 0

    run_one = cycle_runner or (lambda prompt: improve(prompt, objective, **improve_kwargs))

    for cycle_idx in range(start_cycle, max_cycles):
        result = run_one(current)
        history.append(result)
        fitness_history.append(result.fitness)
        cycles_this_run += 1

        if on_cycle:
            on_cycle(cycle_idx + 1, max_cycles, result)

        session = ImprovementSession(
            original_seed=seed_prompt.strip(),
            objective=objective.strip(),
            current_prompt=result.improved_prompt,
            template=template,
            cycle=cycle_idx + 1,
            max_cycles=max_cycles,
            fitness_history=fitness_history,
            plateaued=False,
            last_fitness=result.fitness,
            metadata={"plateau_threshold": plateau_threshold, "plateau_window": plateau_window},
        )
        save_session(session, session_path)

        if result.improved_prompt.strip() == current.strip():
            plateau_reason = "unchanged_prompt"
            break

        if _fitness_plateau(fitness_history, plateau_threshold, plateau_window):
            plateau_reason = "fitness_plateau"
            break

        current = result.improved_prompt

    assert session is not None and history
    session.plateaued = plateau_reason != "max_cycles"
    save_session(session, session_path)

    runbook_path: Path | None = None
    trait_export_path: Path | None = None
    if approve_to_runbook:
        name = runbook_name.strip() or template or "custom-prompt"
        approve_prompt(
            name=name,
            objective=objective,
            prompt=history[-1].improved_prompt,
            fitness=history[-1].fitness,
            cycles=len(history),
            plateaued=session.plateaued,
            metadata={"plateau_reason": plateau_reason},
            base=runbook_dir,
        )
        runbook_path = compile_runbook(runbook_dir)

    if share_traits or approve_to_runbook:
        from ri_engine.macro_registry import classify_objective, export_trait_bundle
        from ri_engine.trait_parser import ParsedTrait

        final = history[-1]
        obj_class = classify_objective(objective, {**improve_kwargs.get("metadata", {}), "template": template})
        delta = 0.0
        if len(fitness_history) >= 2:
            delta = fitness_history[-1] - fitness_history[0]
        traits = [
            ParsedTrait(
                name="plateau_winner",
                instruction="High-score plateau-selected prompt pattern",
                evidence=f"fitness={final.fitness:.0%}",
            )
        ]
        if session.plateaued:
            traits.append(
                ParsedTrait(
                    name="constraint_first",
                    instruction="Stable outcome after macro plateau cycling",
                    evidence=plateau_reason,
                )
            )
        trait_export_path = export_trait_bundle(
            objective_class=obj_class,
            fitness=final.fitness,
            traits=traits,
            cycles=len(history),
            plateaued=session.plateaued,
            fitness_delta=delta,
        )
    elif (improve_kwargs.get("metadata") or {}).get("enable_macro_learning", False) and session.plateaued:
        from ri_engine.macro_registry import MIN_FITNESS_TO_RECORD, record_selection
        from ri_engine.models import Candidate, RunConfig

        final = history[-1]
        if final.fitness >= MIN_FITNESS_TO_RECORD:
            cfg = RunConfig(
                seed_prompt=seed_prompt.strip(),
                objective=objective.strip(),
                metadata={**improve_kwargs.get("metadata", {}), "template": template},
            )
            record_selection(
                cfg,
                Candidate(id="plateau-final", content=final.improved_prompt, generation=final.generations),
                "\n".join(
                    f"- [TRAIT:plateau_winner] High-score plateau prompt (evidence: fitness={final.fitness:.0%})"
                    for _ in [0]
                ),
                final.fitness,
            )

    return PlateauImproveResult(
        final=history[-1],
        history=history,
        cycles_run=cycles_this_run,
        plateau_reason=plateau_reason,
        session_path=session_path,
        runbook_path=runbook_path,
        trait_export_path=trait_export_path,
    )


def improve_template(
    template_id: str,
    *,
    max_generations: int = 5,
    population_size: int = 6,
    provider: str = "mock",
    **kwargs: Any,
) -> ImproveResult:
    """
    Improve a built-in template by id (same ids as ``ri-engine templates``).

    Example: ``improve_template("customer-support")``
    """
    data = load_template(template_id)
    meta = {
        **data.get("metadata", {}),
        "category": data.get("category", ""),
        "template": template_id,
        "template_id": template_id,
    }
    return improve(
        seed_prompt=data["seed_prompt"],
        objective=data["objective"],
        max_generations=max_generations,
        population_size=population_size or data.get("population_size", 6),
        survivors_count=kwargs.get("survivors_count", data.get("survivors_count", 2)),
        provider=provider,
        enable_membrane_bridge=kwargs.get("enable_membrane_bridge", data.get("enable_membrane_bridge", True)),
        metadata=meta,
        domains=data.get("domains", []),
        fitness_weights=data.get("fitness_weights"),
    )
