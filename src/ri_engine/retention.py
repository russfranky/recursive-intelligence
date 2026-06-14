from __future__ import annotations

from ri_engine.events import EventKind, RunEvent
from ri_engine.llm_provider import LLMProvider, load_prompt
from ri_engine.models import Candidate, RunConfig
from ri_engine.observer import NullObserver, RunObserver


class RetentionEngine:
    """Darwinian Retention: preserve winning traits and synthesize lineage memory."""

    SYSTEM = load_prompt("retention") or (
        "You are the RETENTION operator. Synthesize winning traits from survivors "
        "into a concise lineage brief for the next generation."
    )

    def __init__(self, llm: LLMProvider, observer: RunObserver | None = None):
        self.llm = llm
        self.observer = observer or NullObserver()

    def _emit(self, kind: EventKind, message: str, generation: int = 0, **data: object) -> None:
        self.observer.on_event(
            RunEvent(kind=kind, message=message, generation=generation, phase="retention", data=dict(data))
        )

    def synthesize_lineage(
        self,
        config: RunConfig,
        survivors: list[Candidate],
        generation: int = 0,
    ) -> str:
        if not survivors:
            return ""

        self._emit(
            EventKind.AGENT_TASK,
            f"encoding traits from {len(survivors)} survivors",
            generation=generation,
            agent="RetentionEngine",
            task="lineage synthesis",
        )

        blocks = []
        for s in survivors:
            blocks.append(
                f"--- {s.id} (fitness={s.fitness:.3f}) ---\n{s.content}\n"
                f"Scores: {s.scores}\nStrategy: {s.metadata.get('strategy', 'unknown')}\n"
            )

        user = f"""# Retention — Lineage Synthesis
Objective: {config.objective}

Extract the fittest traits from these survivors for breeding the next generation.
Focus on: what to keep, what to amplify, what constraints proved effective.

{"".join(blocks)}

Output a brief (3–6 bullet points) lineage memory for the Variation engine."""

        lineage = self.llm.complete(self.SYSTEM, user, temperature=0.3).strip()
        self._emit(
            EventKind.INFO,
            "lineage memory synthesized",
            generation=generation,
            survivor_count=len(survivors),
        )
        return lineage

    def apply_lineage(self, survivors: list[Candidate], lineage: str) -> list[Candidate]:
        for s in survivors:
            s.metadata["lineage_memory"] = lineage
        return survivors

    def check_convergence(
        self,
        history: list[float],
        threshold: float,
        window: int,
    ) -> bool:
        if len(history) < window + 1:
            return False
        recent = history[-window:]
        delta = max(recent) - min(recent)
        return delta < threshold
