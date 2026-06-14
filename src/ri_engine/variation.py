from __future__ import annotations

import uuid

from ri_engine.events import EventKind, RunEvent
from ri_engine.llm_provider import LLMProvider, load_prompt
from ri_engine.models import Candidate, RunConfig
from ri_engine.observer import NullObserver, RunObserver


class VariationEngine:
    """Darwinian Variation: generate diverse prompt variants from seed or survivors."""

    SYSTEM = load_prompt("variation") or (
        "You are the VARIATION operator in a recursive intelligence engine. "
        "Generate a distinct, high-quality variant. Output ONLY the new prompt text."
    )

    STRATEGIES = [
        "constraint_first",
        "adversarial_critique",
        "cross_domain_metaphor",
        "minimal_essential",
        "recursive_self_eval",
        "failure_mode_guards",
        "measurable_outcomes",
        "membrane_dissolution",
    ]

    @staticmethod
    def system_for(config: RunConfig) -> str:
        return VariationEngine.SYSTEM

    def __init__(self, llm: LLMProvider, observer: RunObserver | None = None):
        self.llm = llm
        self.observer = observer or NullObserver()

    def _emit(self, kind: EventKind, message: str, generation: int = 0, **data: object) -> None:
        self.observer.on_event(
            RunEvent(kind=kind, message=message, generation=generation, phase="variation", data=dict(data))
        )

    def generate_population(
        self,
        config: RunConfig,
        parents: list[Candidate],
        generation: int,
        membrane_insight: str = "",
    ) -> list[Candidate]:
        population: list[Candidate] = []
        seeds = parents if parents else [
            Candidate(id="seed", content=config.seed_prompt, generation=0)
        ]

        for i in range(config.population_size):
            parent = seeds[i % len(seeds)]
            strategies = self._strategies_for(config)
            strategy = strategies[i % len(strategies)]

            self._emit(
                EventKind.VARIANT_SPAWN,
                f"spawning variant {i + 1}/{config.population_size} · {strategy}",
                generation=generation,
                strategy=strategy,
                index=i,
                parent_id=parent.id,
            )
            self._emit(
                EventKind.AGENT_TASK,
                f"mutate via {strategy}",
                generation=generation,
                agent="VariationEngine",
                task=f"strategy:{strategy}",
            )

            content, used_fallback = self._mutate(
                config, parent, strategy, membrane_insight, generation, i
            )
            candidate = Candidate(
                id=f"g{generation}-v{i}-{uuid.uuid4().hex[:6]}",
                content=content,
                generation=generation,
                parent_id=parent.id,
                metadata={"strategy": strategy, "fallback": used_fallback},
            )
            population.append(candidate)

            if used_fallback:
                self._emit(
                    EventKind.VARIANT_FALLBACK,
                    f"weak LLM output · applied fallback for {candidate.id}",
                    generation=generation,
                    candidate_id=candidate.id,
                    strategy=strategy,
                )

            self._emit(
                EventKind.VARIANT_COMPLETE,
                f"{candidate.id} ready · {len(content)} chars",
                generation=generation,
                candidate_id=candidate.id,
                strategy=strategy,
            )

        return population

    def _strategies_for(self, config: RunConfig) -> list[str]:
        order = (config.metadata or {}).get("macro_strategy_order") or []
        if not order:
            return list(self.STRATEGIES)
        seen: set[str] = set()
        merged: list[str] = []
        for name in order:
            if name in self.STRATEGIES and name not in seen:
                merged.append(name)
                seen.add(name)
        for name in self.STRATEGIES:
            if name not in seen:
                merged.append(name)
        return merged

    def _mutate(
        self,
        config: RunConfig,
        parent: Candidate,
        strategy: str,
        membrane_insight: str,
        generation: int,
        index: int,
    ) -> tuple[str, bool]:
        user = f"""# Recursive Intelligence — Variation Pass
Generation: {generation}
Strategy: {strategy}
Objective: {config.objective}
Domains for cross-pollination: {", ".join(config.domains) or "any adjacent field"}

## Parent Prompt
{parent.content}

## Membrane Bridge Insight (latent cross-domain correlation)
{membrane_insight or "None yet — explore non-obvious structural parallels."}

## Instructions
Produce ONE improved prompt variant using strategy "{strategy}".
The variant must remain executable by an agent and include a hook for the next recursive iteration.
Output ONLY the new prompt — no commentary."""

        variant = self.llm.complete(
            self.system_for(config), user, temperature=config.variation_temperature
        ).strip()

        used_fallback = False
        if not variant or len(variant) < 20:
            variant = f"{parent.content}\n\n[Variant {index}: {strategy}]"
            used_fallback = True
        return variant, used_fallback
