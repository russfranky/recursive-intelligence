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


def adjust_fitness(base: float, content: str, *, weight: float = 0.12) -> float:
    """Blend task fitness with simplicity (Occam's razor)."""
    sim = composite_simplicity(content)
    return base * (1.0 - weight) + sim * weight


def apply_occam_to_candidates(candidates: list[Candidate], *, weight: float = 0.12) -> list[Candidate]:
    for c in candidates:
        if c.fitness is None:
            continue
        c.scores = dict(c.scores)
        c.scores["simplicity"] = composite_simplicity(c.content)
        c.fitness = adjust_fitness(c.fitness, c.content, weight=weight)
        c.metadata["occam_simplicity"] = c.scores["simplicity"]
    return candidates


def rank_with_occam_tiebreak(candidates: list[Candidate]) -> list[Candidate]:
    """Sort by fitness desc; tie-break toward shorter prompts (Occam's razor)."""
    return sorted(
        candidates,
        key=lambda c: (-(c.fitness or 0.0), len(c.content.split()), len(c.content)),
    )


def select_survivors_occam(
    ranked: list[Candidate],
    survivors_count: int,
    *,
    tie_threshold: float = 0.01,
) -> list[Candidate]:
    """Pick survivors; when fitness is within threshold, prefer simpler prompts."""
    if not ranked:
        return []
    ordered = rank_with_occam_tiebreak(ranked)
    survivors: list[Candidate] = []
    for c in ordered:
        if len(survivors) >= survivors_count:
            break
        if not survivors:
            survivors.append(c)
            continue
        if abs((c.fitness or 0) - (survivors[-1].fitness or 0)) <= tie_threshold:
            # Occam tie-break already applied via rank_with_occam_tiebreak ordering
            survivors.append(c)
        elif (c.fitness or 0) >= (survivors[-1].fitness or 0) - tie_threshold:
            survivors.append(c)
        else:
            break
    while len(survivors) < survivors_count and len(survivors) < len(ordered):
        for c in ordered:
            if c not in survivors:
                survivors.append(c)
                break
    return survivors[:survivors_count]
