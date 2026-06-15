from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ri_engine.events import EventKind, RunEvent
from ri_engine.llm_provider import LLMProvider, create_provider
from ri_engine.membrane import MembraneBridge
from ri_engine.models import Candidate, GenerationResult, RunConfig
from ri_engine.observer import NullObserver, RunObserver
from ri_engine.retention import RetentionEngine
from ri_engine.selection import SelectionEnvironment
from ri_engine.variation import VariationEngine

DEFAULT_FITNESS_WEIGHTS = {
    "objective_alignment": 0.30,
    "clarity": 0.20,
    "utility": 0.20,
    "coherence": 0.15,
    "simplicity": 0.10,
    "register_fit": 0.05,
    "novelty": 0.03,
}


class RecursiveIntelligenceEngine:
    """
    Self-automated prompt engine implementing recursive intelligence iteration.

    Core loop (20ms-scale agentic iteration, human-scale configurable):
        Variation → Selection → Retention → (output → input) → repeat
    """

    def __init__(self, llm: LLMProvider | None = None, observer: RunObserver | None = None):
        self.observer = observer or NullObserver()
        self.llm = llm or create_provider("mock")
        self.variation = VariationEngine(self.llm, observer=self.observer)
        self.selection = SelectionEnvironment(self.llm, observer=self.observer)
        self.retention = RetentionEngine(self.llm, observer=self.observer)
        self.membrane = MembraneBridge(self.llm, observer=self.observer)

    def _emit(
        self,
        kind: EventKind,
        message: str,
        *,
        generation: int = 0,
        phase: str = "",
        progress: float | None = None,
        **data: object,
    ) -> None:
        self.observer.on_event(
            RunEvent(
                kind=kind,
                message=message,
                generation=generation,
                phase=phase,
                progress=progress,
                data=dict(data),
            )
        )

    def run(self, config: RunConfig) -> dict:
        """Execute full recursive improvement loop."""
        gate_report: dict | None = None
        macro_report: dict | None = None
        meta = config.metadata or {}
        if meta.get("apply_linguistic_gate", True):
            from ri_engine.language_leanings import apply_linguistic_gate

            config, gate = apply_linguistic_gate(config)
            gate_report = {
                "leaning": gate.leaning,
                "confidence": gate.confidence,
                "source": gate.source,
                "registry_id": gate.registry_id,
                "rationale": gate.rationale,
                "objective_signal": gate.objective_signal,
                "registry_signal": gate.registry_signal,
                "objective_leaning": gate.objective_leaning,
                "registry_leaning": gate.registry_leaning,
            }
            self._emit(
                EventKind.INFO,
                f"linguistic gate → {gate.leaning} ({gate.confidence:.0%} via {gate.source})",
                progress=0.0,
                data={**gate_report, "leaning": gate.leaning},
            )

        if meta.get("enable_macro_learning", False):
            from ri_engine.macro_registry import apply_macro_priors

            config, macro = apply_macro_priors(config)
            if macro.source == "registry":
                macro_report = {
                    "objective_class": macro.objective_class,
                    "trait_count": macro.trait_count,
                    "selection_runs": macro.selection_runs,
                    "strategy_order": macro.strategy_order,
                }
                self._emit(
                    EventKind.INFO,
                    f"macro priors → {macro.objective_class} ({macro.trait_count} traits, "
                    f"{macro.selection_runs} prior runs)",
                    progress=0.0,
                    data=macro_report,
                )
            meta = config.metadata or {}

        macro_brief = (config.metadata or {}).get("macro_trait_brief", "")

        self._emit(
            EventKind.RUN_START,
            f"initializing selection environment · pop={config.population_size}",
            progress=0.0,
        )

        history: list[GenerationResult] = []
        fitness_history: list[float] = []
        parents: list[Candidate] = []
        membrane_insight = ""
        lineage_memory = ""

        for gen in range(1, config.max_generations + 1):
            self._emit(
                EventKind.GENERATION_START,
                f"generation {gen} begins",
                generation=gen,
                progress=self._overall_progress(gen, 0, config.max_generations),
            )

            if config.enable_membrane_bridge and parents:
                self._emit(
                    EventKind.PHASE_START,
                    "scanning cross-domain vector space",
                    generation=gen,
                    phase="membrane",
                    agent="MembraneBridge",
                )
                self._emit(
                    EventKind.AGENT_TASK,
                    "correlate latent structures across domains",
                    generation=gen,
                    phase="membrane",
                    agent="MembraneBridge",
                    task="vector-space correlation scan",
                )
                membrane_insight = self.membrane.discover_correlation(
                    config, parents[0].content, generation=gen
                )
                self._emit(
                    EventKind.MEMBRANE,
                    membrane_insight[:120],
                    generation=gen,
                    phase="membrane",
                )
                self._emit(
                    EventKind.PHASE_COMPLETE,
                    "membrane insight captured",
                    generation=gen,
                    phase="membrane",
                    progress=self._overall_progress(gen, 1, config.max_generations),
                )

            combined_insight = "\n".join(
                filter(None, [macro_brief, membrane_insight, lineage_memory])
            )

            self._emit(
                EventKind.PHASE_START,
                f"breeding {config.population_size} variants",
                generation=gen,
                phase="variation",
                agent="VariationEngine",
                total=config.population_size,
            )

            candidates = self.variation.generate_population(
                config, parents, gen, combined_insight
            )

            self._emit(
                EventKind.PHASE_COMPLETE,
                f"{len(candidates)} variants spawned",
                generation=gen,
                phase="variation",
                progress=self._overall_progress(gen, 2, config.max_generations),
            )

            self._emit(
                EventKind.PHASE_START,
                "applying selection pressure",
                generation=gen,
                phase="selection",
                agent="SelectionEnvironment",
            )
            self._emit(
                EventKind.AGENT_TASK,
                "score candidates on fitness dimensions",
                generation=gen,
                phase="selection",
                agent="SelectionEnvironment",
                task="multi-dimensional fitness scoring",
            )

            ranked = self.selection.evaluate(config, candidates, generation=gen)
            survivors = self.selection.select_survivors(config, ranked, generation=gen)
            best = ranked[0]

            eliminated = ranked[config.survivors_count :]
            for c in eliminated:
                self._emit(
                    EventKind.ELIMINATE,
                    f"{c.id} culled · fitness {c.fitness:.1%}",
                    generation=gen,
                    phase="selection",
                    fitness=c.fitness,
                    candidate_id=c.id,
                )

            for s in survivors:
                self._emit(
                    EventKind.SURVIVE,
                    f"{s.id} survives · fitness {s.fitness:.1%}",
                    generation=gen,
                    phase="selection",
                    fitness=s.fitness,
                    candidate_id=s.id,
                )

            self._emit(
                EventKind.PHASE_COMPLETE,
                f"selection complete · {len(survivors)}/{len(ranked)} survive",
                generation=gen,
                phase="selection",
                progress=self._overall_progress(gen, 3, config.max_generations),
            )

            self._emit(
                EventKind.PHASE_START,
                "synthesizing lineage memory",
                generation=gen,
                phase="retention",
                agent="RetentionEngine",
            )

            lineage_memory = self.retention.synthesize_lineage(config, survivors, generation=gen)
            self.retention.apply_lineage(survivors, lineage_memory)

            for line in _learning_lines(lineage_memory):
                self._emit(
                    EventKind.LEARNING,
                    line,
                    generation=gen,
                    phase="retention",
                )

            self._emit(
                EventKind.PHASE_COMPLETE,
                "lineage memory encoded",
                generation=gen,
                phase="retention",
                progress=self._overall_progress(gen, 4, config.max_generations),
            )

            fitness_history.append(best.fitness or 0)
            converged = self.retention.check_convergence(
                fitness_history,
                config.convergence_threshold,
                config.convergence_window,
            )

            self._emit(
                EventKind.CONVERGENCE,
                "fitness plateau detected" if converged else "continuing evolution",
                generation=gen,
                phase="converge",
                converged=converged,
                best_fitness=best.fitness,
            )

            result = GenerationResult(
                generation=gen,
                candidates=ranked,
                survivors=survivors,
                best=best,
                converged=converged,
                notes=lineage_memory[:200],
            )
            history.append(result)
            parents = survivors

            self._emit(
                EventKind.GENERATION_COMPLETE,
                f"gen {gen} best={best.fitness:.1%}",
                generation=gen,
                best_fitness=best.fitness,
                progress=min(99.0, gen / config.max_generations * 100),
            )

            if converged:
                break

        report = self._build_report(config, history, parents)
        if gate_report is not None:
            report["linguistic_gate"] = gate_report
        if macro_report is not None:
            report["macro_priors"] = macro_report

        if history and (config.metadata or {}).get("enable_macro_learning", False):
            from ri_engine.macro_registry import classify_objective, record_selection

            final = history[-1]
            recorded = record_selection(
                config,
                final.best,
                lineage_memory,
                final.best.fitness or 0.0,
            )
            if recorded:
                report["macro_learning"] = {
                    "recorded": True,
                    "objective_class": (config.metadata or {}).get("macro_objective_class")
                    or classify_objective(config.objective, config.metadata),
                }
                self._emit(
                    EventKind.LEARNING,
                    "macro trait registry updated from selection",
                    generation=history[-1].generation,
                    phase="macro",
                )
        if config.output_path:
            self._save_report(report, config.output_path)

        self._emit(
            EventKind.RUN_COMPLETE,
            f"evolution complete · {len(history)} generations",
            progress=100.0,
            generations=len(history),
            best_fitness=report.get("best_fitness"),
        )
        return report

    def run_single_generation(
        self,
        config: RunConfig,
        parents: list[Candidate] | None = None,
        generation: int = 1,
        membrane_insight: str = "",
        lineage_memory: str = "",
    ) -> GenerationResult:
        """Run one VSR cycle — useful for external orchestrators."""
        combined = "\n".join(filter(None, [membrane_insight, lineage_memory]))
        candidates = self.variation.generate_population(
            config, parents or [], generation, combined
        )
        ranked = self.selection.evaluate(config, candidates, generation=generation)
        survivors = self.selection.select_survivors(config, ranked, generation=generation)
        lineage = self.retention.synthesize_lineage(config, survivors, generation=generation)
        self.retention.apply_lineage(survivors, lineage)
        return GenerationResult(
            generation=generation,
            candidates=ranked,
            survivors=survivors,
            best=ranked[0],
            notes=lineage,
        )

    @staticmethod
    def _overall_progress(generation: int, phase_index: int, max_generations: int) -> float:
        phases_per_gen = 5
        unit = ((generation - 1) * phases_per_gen + phase_index) / (max_generations * phases_per_gen)
        return min(99.0, unit * 100)

    @staticmethod
    def _build_report(
        config: RunConfig,
        history: list[GenerationResult],
        final_survivors: list[Candidate],
    ) -> dict:
        return {
            "meta": {
                "engine": "recursive-intelligence",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "generations_run": len(history),
                "converged": history[-1].converged if history else False,
            },
            "config": {
                "objective": config.objective,
                "max_generations": config.max_generations,
                "population_size": config.population_size,
                "survivors_count": config.survivors_count,
                "fitness_weights": config.fitness_weights,
            },
            "best_prompt": history[-1].best.content if history else config.seed_prompt,
            "best_fitness": history[-1].best.fitness if history else None,
            "fitness_trajectory": [
                {"generation": r.generation, "fitness": r.best.fitness}
                for r in history
            ],
            "final_survivors": [
                {
                    "id": s.id,
                    "fitness": s.fitness,
                    "scores": s.scores,
                    "content": s.content,
                    "strategy": s.metadata.get("strategy"),
                }
                for s in final_survivors
            ],
            "generation_log": [
                {
                    "generation": r.generation,
                    "best_id": r.best.id,
                    "best_fitness": r.best.fitness,
                    "survivor_ids": [s.id for s in r.survivors],
                    "converged": r.converged,
                }
                for r in history
            ],
        }

    @staticmethod
    def _save_report(report: dict, path: str) -> None:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    @staticmethod
    def load_config(path: str | Path) -> RunConfig:
        import yaml

        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        meta = dict(data.get("metadata", {}))
        if "category" in data:
            meta.setdefault("category", data["category"])
        if "audience" in data:
            meta["audience"] = data["audience"]
        return RunConfig(
            seed_prompt=data["seed_prompt"],
            objective=data["objective"],
            max_generations=data.get("max_generations", 10),
            population_size=data.get("population_size", 8),
            survivors_count=data.get("survivors_count", 2),
            convergence_threshold=data.get("convergence_threshold", 0.02),
            convergence_window=data.get("convergence_window", 3),
            variation_temperature=data.get("variation_temperature", 0.7),
            enable_membrane_bridge=data.get("enable_membrane_bridge", True),
            domains=data.get("domains", []),
            fitness_weights=data.get("fitness_weights", DEFAULT_FITNESS_WEIGHTS),
            output_path=data.get("output_path"),
            metadata=meta,
        )


def _learning_lines(text: str) -> list[str]:
    lines = []
    for raw in text.replace("·", "\n").split("\n"):
        cleaned = raw.strip().lstrip("-•*()0123456789. ")
        if len(cleaned) > 12:
            lines.append(cleaned[:100])
    return lines[:4] if lines else [text[:100]]
