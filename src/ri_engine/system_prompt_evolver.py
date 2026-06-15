from __future__ import annotations

import re
from dataclasses import dataclass

from ri_engine.models import Candidate, RunConfig
from ri_engine.selection import SelectionEnvironment
from ri_engine.llm_provider import MockLLMProvider


@dataclass
class StrategyTransform:
    name: str
    section_title: str
    content: str


TRANSFORMS: list[StrategyTransform] = [
    StrategyTransform(
        "constraint_first",
        "Output Contract",
        """\
You MUST satisfy this contract on every invocation:
1. Follow the output format exactly — no preamble, no meta-commentary unless requested.
2. If input is ambiguous, state assumptions in ≤2 lines, then proceed.
3. Never optimize for length, engagement, or verbosity over task utility.""",
    ),
    StrategyTransform(
        "recursive_self_eval",
        "Self-Evaluation Rubric",
        """\
Before finalizing output, silently score yourself 0.0–1.0 on:
- **clarity**: instructions unambiguous?
- **utility**: output advances the stated objective?
- **coherence**: no internal contradictions?
If any score < 0.7, revise once before responding.""",
    ),
    StrategyTransform(
        "failure_mode_guards",
        "Failure Modes to Block",
        """\
Explicitly avoid these failure modes:
- **Proxy optimization**: selecting for engagement/length instead of task fitness
- **Missing recursive hook**: output cannot be evaluated by the next iteration
- **Format drift**: deviating from the specified output structure
- **Safety theater**: vague guardrails without enforceable constraints""",
    ),
    StrategyTransform(
        "measurable_outcomes",
        "Success Metrics",
        """\
Your output is successful when:
- Format matches the specification exactly
- Every required field/section is present
- A downstream agent can act on the output without clarification
- The next VSR iteration can score improvement from your output""",
    ),
    StrategyTransform(
        "adversarial_critique",
        "Pre-execution Check",
        """\
Before responding, challenge your draft:
1. What is the weakest part of this output?
2. What proxy metric might this accidentally optimize for?
3. What would cause the Selection operator to cull this?
Revise to address the top issue.""",
    ),
    StrategyTransform(
        "cross_domain_metaphor",
        "Structural Analog",
        """\
Treat your operation as a control-system feedback loop:
- **Sensor**: read input state (prompt, candidates, lineage)
- **Controller**: apply operator logic (V/S/R/M)
- **Actuator**: produce structured output for the next stage
- **Feedback**: output becomes input for the next generation""",
    ),
    StrategyTransform(
        "membrane_dissolution",
        "Cross-Operator Coordination",
        """\
You are one stage in a pipeline: Membrane → Variation → Selection → Retention.
- Upstream: consume insights/lineage from prior stages without discarding them
- Downstream: produce output the next operator can parse mechanically
- Never assume human will interpret ambiguous output — be machine-actionable""",
    ),
    StrategyTransform(
        "minimal_essential",
        "Core Directive",
        """\
Distilled mandate: execute your operator role with maximum signal, minimum noise.
One pass. One format. No hedging.""",
    ),
]


def _strip_generated_sections(text: str) -> str:
    """Remove previously injected evolver sections for clean re-composition."""
    markers = [t.section_title for t in TRANSFORMS] + ["Lineage Traits to Amplify"]
    result = text
    for title in markers:
        pattern = rf"\n## {re.escape(title)}\n.*?(?=\n## |\Z)"
        result = re.sub(pattern, "", result, flags=re.S)
    return result.strip()


def _has_section(text: str, title: str) -> bool:
    return f"## {title}" in text


def _insert_before_output(base: str, block: str) -> str:
    """Insert block before the output specification section."""
    for header in ("## Output format", "## Output Format", "## Output"):
        idx = base.find(header)
        if idx != -1:
            return base[:idx].rstrip() + block + "\n\n" + base[idx:]
    return base.rstrip() + block


def apply_transform(seed: str, transform: StrategyTransform) -> str:
    base = _strip_generated_sections(seed)
    if _has_section(base, transform.section_title):
        return base

    block = f"\n\n## {transform.section_title}\n\n{transform.content.strip()}\n"
    return _insert_before_output(base, block)


def compose_from_traits(seed: str, trait_names: list[str]) -> str:
    base = _strip_generated_sections(seed)
    for name in trait_names:
        match = next((t for t in TRANSFORMS if t.name == name), None)
        if match and not _has_section(base, match.section_title):
            block = f"\n\n## {match.section_title}\n\n{match.content.strip()}\n"
            base = _insert_before_output(base, block)
    return base.strip() + "\n"


class SystemPromptEvolver:
    """Evolve operator system prompts via structured VSR (no external LLM required)."""

    STRATEGIES = [t.name for t in TRANSFORMS]

    def __init__(self) -> None:
        self.selection = SelectionEnvironment(MockLLMProvider())

    def evolve(self, seed: str, config: RunConfig) -> tuple[str, float, list[dict]]:
        history: list[dict] = []
        parents: list[Candidate] = []
        clean_seed = _strip_generated_sections(seed)
        best_fitness = 0.0
        active_traits: list[str] = []
        winning_traits: list[str] = []

        for gen in range(1, config.max_generations + 1):
            candidates: list[Candidate] = []

            candidates.append(
                Candidate(
                    id=f"g{gen}-composed",
                    content=compose_from_traits(clean_seed, active_traits) if active_traits else clean_seed,
                    generation=gen,
                    metadata={"strategy": "composed"},
                )
            )

            for i, strategy in enumerate(self.STRATEGIES):
                transform = TRANSFORMS[i]
                parent_traits = list(active_traits)
                if strategy not in parent_traits:
                    parent_traits.append(strategy)
                content = compose_from_traits(clean_seed, parent_traits)
                candidates.append(
                    Candidate(
                        id=f"g{gen}-{strategy}",
                        content=content,
                        generation=gen,
                        parent_id=parents[0].id if parents else "seed",
                        metadata={"strategy": strategy},
                    )
                )

            ranked = self.selection.evaluate(config, candidates, generation=gen)
            survivors = ranked[: config.survivors_count]
            best = ranked[0]
            fitness = best.fitness or 0

            if fitness >= best_fitness - config.convergence_threshold:
                if fitness > best_fitness:
                    best_fitness = fitness
                for s in survivors:
                    strat = s.metadata.get("strategy")
                    if strat and strat != "composed" and strat not in winning_traits:
                        winning_traits.append(strat)

            for s in survivors:
                strat = s.metadata.get("strategy")
                if strat and strat != "composed" and strat not in active_traits:
                    active_traits.append(strat)

            history.append({
                "generation": gen,
                "best_fitness": fitness,
                "best_strategy": best.metadata.get("strategy"),
                "active_traits": list(active_traits),
                "winning_traits": list(winning_traits),
                "survivor_count": len(survivors),
            })

            parents = survivors

            if gen > 2:
                recent = [h["best_fitness"] for h in history[-2:]]
                if abs(recent[-1] - recent[-2]) < config.convergence_threshold:
                    break

        final = compose_from_traits(clean_seed, winning_traits) if winning_traits else clean_seed
        return final, best_fitness, history

    def score_traits(self, clean_seed: str, traits: list[str], config: RunConfig) -> float:
        """Score a trait composition through the selection environment."""
        content = compose_from_traits(clean_seed, traits) if traits else clean_seed
        candidate = Candidate(id="score", content=content, generation=0, metadata={"strategy": "composed"})
        ranked = self.selection.evaluate(config, [candidate], generation=0)
        return ranked[0].fitness or 0.0

    def detect_traits(self, text: str) -> list[str]:
        """Detect which strategy traits are present in a prompt."""
        found = []
        for t in TRANSFORMS:
            if _has_section(text, t.section_title):
                found.append(t.name)
        return found

    def saturate_traits(self, seed: str, config: RunConfig, priority: list[str] | None = None) -> tuple[str, float, list[str]]:
        """
        Greedily accumulate traits that improve or maintain fitness.
        Never regresses — keeps best trait set found.
        """
        clean_seed = _strip_generated_sections(seed)
        order = priority or self.STRATEGIES
        best_traits = self.detect_traits(seed)
        best_fitness = self.score_traits(clean_seed, best_traits, config)

        improved = True
        while improved:
            improved = False
            for trait in order:
                if trait in best_traits:
                    continue
                candidate_traits = best_traits + [trait]
                fitness = self.score_traits(clean_seed, candidate_traits, config)
                if fitness >= best_fitness - config.convergence_threshold:
                    if fitness > best_fitness or len(candidate_traits) > len(best_traits):
                        best_fitness = fitness
                        best_traits = candidate_traits
                        improved = True

        final = compose_from_traits(clean_seed, best_traits)
        return final, best_fitness, best_traits


# Operator-specific trait priority (most critical first)
OPERATOR_PRIORITIES: dict[str, list[str]] = {
    "variation.md": [
        "constraint_first", "failure_mode_guards", "membrane_dissolution",
        "measurable_outcomes", "recursive_self_eval", "adversarial_critique",
        "cross_domain_metaphor", "minimal_essential",
    ],
    "selection.md": [
        "failure_mode_guards", "recursive_self_eval", "adversarial_critique",
        "measurable_outcomes", "membrane_dissolution", "constraint_first",
        "cross_domain_metaphor", "minimal_essential",
    ],
    "retention.md": [
        "measurable_outcomes", "recursive_self_eval", "membrane_dissolution",
        "failure_mode_guards", "cross_domain_metaphor", "adversarial_critique",
        "constraint_first", "minimal_essential",
    ],
    "membrane_bridge.md": [
        "cross_domain_metaphor", "constraint_first", "adversarial_critique",
        "failure_mode_guards", "measurable_outcomes", "recursive_self_eval",
        "membrane_dissolution", "minimal_essential",
    ],
    "meta_improvement.md": [
        "failure_mode_guards", "recursive_self_eval", "adversarial_critique",
        "measurable_outcomes", "constraint_first", "membrane_dissolution",
        "cross_domain_metaphor", "minimal_essential",
    ],
}

TRAIT_COUNT = len(TRANSFORMS)
