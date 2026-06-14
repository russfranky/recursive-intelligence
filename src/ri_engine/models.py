from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Candidate:
    """A single variant in the selection environment."""

    id: str
    content: str
    generation: int
    parent_id: str | None = None
    fitness: float | None = None
    scores: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def lineage(self) -> str:
        if self.parent_id:
            return f"{self.parent_id} → {self.id}"
        return self.id


@dataclass
class GenerationResult:
    """Output of one VSR (Variation → Selection → Retention) cycle."""

    generation: int
    candidates: list[Candidate]
    survivors: list[Candidate]
    best: Candidate
    converged: bool = False
    notes: str = ""


@dataclass
class RunConfig:
    """Configuration for a recursive improvement run."""

    seed_prompt: str
    objective: str
    max_generations: int = 10
    population_size: int = 8
    survivors_count: int = 2
    convergence_threshold: float = 0.02
    convergence_window: int = 3
    variation_temperature: float = 0.7
    enable_membrane_bridge: bool = True
    domains: list[str] = field(default_factory=list)
    fitness_weights: dict[str, float] = field(default_factory=lambda: {
        "clarity": 0.25,
        "novelty": 0.25,
        "utility": 0.30,
        "coherence": 0.20,
    })
    output_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
