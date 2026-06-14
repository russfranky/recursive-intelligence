from __future__ import annotations

import re

from ri_engine.events import EventKind, RunEvent
from ri_engine.llm_provider import LLMProvider, load_prompt
from ri_engine.models import Candidate, RunConfig
from ri_engine.observer import NullObserver, RunObserver


class SelectionEnvironment:
    """The Selection Environment: pressures that determine which prompts survive."""

    SYSTEM = load_prompt("selection") or (
        "You are the SELECTION operator. Score each candidate on clarity, novelty, "
        "utility, and coherence (0.0–1.0). Respond in the exact format specified."
    )

    @staticmethod
    def system_for(config: RunConfig) -> str:
        return SelectionEnvironment.SYSTEM

    def __init__(self, llm: LLMProvider, observer: RunObserver | None = None):
        self.llm = llm
        self.observer = observer or NullObserver()

    def _emit(self, kind: EventKind, message: str, generation: int = 0, **data: object) -> None:
        self.observer.on_event(
            RunEvent(kind=kind, message=message, generation=generation, phase="selection", data=dict(data))
        )

    def evaluate(
        self,
        config: RunConfig,
        candidates: list[Candidate],
        generation: int = 0,
    ) -> list[Candidate]:
        self._emit(
            EventKind.AGENT_TASK,
            f"evaluating {len(candidates)} candidates",
            generation=generation,
            agent="SelectionEnvironment",
            task="fitness scoring",
        )
        scored = self._llm_score(config, candidates, generation)
        for candidate in scored:
            candidate.fitness = self._aggregate_fitness(candidate.scores, config.fitness_weights)
            self._emit(
                EventKind.SCORE,
                f"{candidate.id} → {candidate.fitness:.1%}",
                generation=generation,
                fitness=candidate.fitness,
                scores=candidate.scores,
                candidate_id=candidate.id,
            )
        return sorted(scored, key=lambda c: c.fitness or 0, reverse=True)

    def select_survivors(
        self,
        config: RunConfig,
        ranked: list[Candidate],
        generation: int = 0,
    ) -> list[Candidate]:
        survivors = ranked[: config.survivors_count]
        cull_rate = (len(ranked) - len(survivors)) / max(len(ranked), 1) * 100
        self._emit(
            EventKind.INFO,
            f"selection pressure · {cull_rate:.0f}% culled",
            generation=generation,
            culled=len(ranked) - len(survivors),
            survived=len(survivors),
        )
        return survivors

    def _llm_score(
        self,
        config: RunConfig,
        candidates: list[Candidate],
        generation: int,
    ) -> list[Candidate]:
        blocks = []
        for i, c in enumerate(candidates):
            blocks.append(f"---CANDIDATE {i}---\n{c.content}\n")
        user = f"""# Selection Environment Evaluation
Objective: {config.objective}
Fitness dimensions: {", ".join(config.fitness_weights.keys())}

Score each candidate 0.0–1.0 on each dimension.
Penalize: engagement-bait, vague goals, missing recursive hooks, proxy metrics.
Reward: measurable outcomes, self-evaluation loops, cross-domain insight, guardrails.

{"".join(blocks)}

Respond ONLY with lines like:
CANDIDATE 0: clarity=0.85, novelty=0.70, utility=0.90, coherence=0.80"""

        response = self.llm.complete(self.system_for(config), user, temperature=0.2)
        parsed, fallback_count = self._parse_scores(candidates, response)
        if fallback_count:
            self._emit(
                EventKind.WARNING,
                f"heuristic scoring applied to {fallback_count} candidates",
                generation=generation,
                fallback_count=fallback_count,
            )
        return parsed

    def _parse_scores(
        self,
        candidates: list[Candidate],
        response: str,
    ) -> tuple[list[Candidate], int]:
        pattern = re.compile(r"CANDIDATE\s+(\d+)\s*:\s*(.+)", re.IGNORECASE)
        score_pattern = re.compile(r"(\w+)\s*=\s*([\d.]+)")
        fallback_count = 0

        for match in pattern.finditer(response):
            idx = int(match.group(1))
            if idx >= len(candidates):
                continue
            scores: dict[str, float] = {}
            for sm in score_pattern.finditer(match.group(2)):
                scores[sm.group(1).lower()] = float(sm.group(2))
            candidates[idx].scores = scores

        for c in candidates:
            if not c.scores:
                fallback_count += 1
                c.scores = {
                    "clarity": 0.5 + (hash(c.content) % 30) / 100,
                    "novelty": 0.5 + (hash(c.id) % 40) / 100,
                    "utility": 0.5 + (len(c.content) % 35) / 100,
                    "coherence": 0.55 + (hash(c.content[:50]) % 25) / 100,
                }
        return candidates, fallback_count

    @staticmethod
    def _aggregate_fitness(scores: dict[str, float], weights: dict[str, float]) -> float:
        total_weight = sum(weights.values()) or 1.0
        return sum(scores.get(k, 0.5) * w for k, w in weights.items()) / total_weight
