"""Occam's razor — simplicity pressure across Variation → Selection → Retention."""

from __future__ import annotations

import re

from ri_engine.models import Candidate, RunConfig

# Words in a task prompt; peak simplicity in this band
_OPTIMAL_WORDS_LO = 80
_OPTIMAL_WORDS_HI = 600
_BLOAT_WORDS = 1200


def occams_enabled(config: RunConfig) -> bool:
    meta = config.metadata or {}
    if "enable_occams_razor" in meta:
        return bool(meta["enable_occams_razor"])
    return True


def simplicity_score(content: str) -> float:
    """Score 0.0–1.0 — prefer minimal sufficient prompts."""
    words = len(content.split())
    if words < _OPTIMAL_WORDS_LO:
        return max(0.5, 0.6 + words / 200)
    if words <= _OPTIMAL_WORDS_HI:
        return 1.0
    if words <= _BLOAT_WORDS:
        return max(0.65, 1.0 - (words - _OPTIMAL_WORDS_HI) / 1200)
    return max(0.4, 0.65 - (words - _BLOAT_WORDS) / 2000)


def section_redundancy_penalty(content: str) -> float:
    """Penalize prompt bloat from too many sections."""
    headers = len(re.findall(r"^##\s+", content, re.MULTILINE))
    if headers <= 8:
        return 0.0
    return min(0.25, (headers - 8) * 0.04)


def composite_simplicity(content: str) -> float:
    raw = simplicity_score(content) - section_redundancy_penalty(content)
    return max(0.0, min(1.0, raw))


def adjust_fitness(
    base: float,
    content: str,
    *,
    weight: float = 0.12,
    utility: float | None = None,
) -> float:
    """Blend task fitness with simplicity (Occam's razor).

    Skips simplicity penalty when utility < 0.7 — never sacrifice sufficiency for brevity.
    """
    if utility is not None and utility < 0.7:
        return base
    sim = composite_simplicity(content)
    return base * (1.0 - weight) + sim * weight


def apply_occam_to_candidates(candidates: list[Candidate], *, weight: float = 0.12) -> list[Candidate]:
    for c in candidates:
        if c.fitness is None:
            continue
        c.scores = dict(c.scores)
        c.scores["simplicity"] = composite_simplicity(c.content)
        utility = c.scores.get("utility")
        c.fitness = adjust_fitness(
            c.fitness,
            c.content,
            weight=weight,
            utility=utility,
        )
        c.metadata["occam_simplicity"] = c.scores["simplicity"]
    return candidates


_OCCAM_STRATEGY_PRIORITY = (
    "minimal_essential",
    "constraint_first",
    "measurable_outcomes",
    "failure_mode_guards",
    "recursive_self_eval",
    "adversarial_critique",
    "cross_domain_metaphor",
    "membrane_dissolution",
)


def occam_strategy_order(base: list[str]) -> list[str]:
    """Bias variation toward minimal strategies when Occam is enabled."""
    seen: set[str] = set()
    ordered: list[str] = []
    for name in _OCCAM_STRATEGY_PRIORITY:
        if name in base and name not in seen:
            ordered.append(name)
            seen.add(name)
    for name in base:
        if name not in seen:
            ordered.append(name)
    return ordered


def prune_lineage_traits(lineage: str, *, max_traits: int = 6) -> str:
    """Cap retention output and drop duplicate trait names (Occam's razor)."""
    from ri_engine.trait_parser import parse_traits

    traits = parse_traits(lineage)
    if not traits:
        return lineage
    seen_names: set[str] = set()
    kept: list[str] = []
    for t in traits:
        key = t.normalized_name()
        if key in seen_names:
            continue
        seen_names.add(key)
        instr = t.instruction[:80].rstrip()
        ev = f" (evidence: {t.evidence[:60]})" if t.evidence else ""
        kept.append(f"- [TRAIT:{t.name}] {instr}{ev}")
        if len(kept) >= max_traits:
            break
    return "\n".join(kept) if kept else lineage


def rank_with_occam_tiebreak(candidates: list[Candidate]) -> list[Candidate]:
    """Sort by fitness desc; tie-break toward shorter prompts (Occam's razor)."""
    return sorted(
        candidates,
        key=lambda c: (-(c.fitness or 0.0), len(c.content.split()), len(c.content)),
    )
