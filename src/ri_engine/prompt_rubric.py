"""
Task Prompt Quality Rubric — structural scoring for offline VSR selection.

Scores prompt structure and goal alignment heuristics. Does not measure live LLM
task performance.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class PromptQuality:
    total: float
    dimensions: dict[str, float] = field(default_factory=dict)
    features_present: list[str] = field(default_factory=list)
    features_missing: list[str] = field(default_factory=list)
    word_count: int = 0
    grade: str = ""


FEATURE_CHECKS: list[tuple[str, str, str]] = [
    ("measurable_outcomes", r"success (criteria|metric|when)|measurable|quantif|score|rating|severity|P[0-3]|≤\d+|under \d+ words", "Measurable outcomes defined"),
    ("output_format", r"output format|respond (only|with)|return (only|format)|```|CANDIDATE \d|yaml|json|bullet", "Explicit output format"),
    ("failure_guards", r"fail(ure|ures)|avoid|never|do not|anti-pattern|guardrail|escalat|block", "Failure mode guards"),
    ("self_eval", r"self-eval|self eval|score yourself|before (submitting|finalizing|responding)|rubric|revise once", "Self-evaluation hook"),
    ("constraints", r"must|required|mandatory|hard constraint|≤|≥|minimum|maximum|only if", "Hard constraints"),
    ("process_steps", r"step \d|phase \d|\d\.\s+\*\*|first.*then|before.*after|protocol|workflow", "Structured process steps"),
    ("anti_proxy", r"not (engagement|length|verbose|word count|time on)|proxy|optimize for (reply|resolution|task)", "Anti-proxy optimization"),
    ("downstream_actionable", r"actionable|executable|agent can|downstream|SOC|team can|developer can", "Downstream actionable"),
    ("domain_depth", r"MITRE|OWASP|CSAT|ATT&CK|Jacquard|VSR|membrane|falsif|containment", "Domain-specific depth"),
    ("recursive_hook", r"next (iteration|generation|review)|recursive|improve upon|self-improv|RI-EVAL", "Recursive improvement hook"),
]

FEATURE_WEIGHTS: dict[str, float] = {
    "measurable_outcomes": 1.0,
    "output_format": 1.0,
    "failure_guards": 1.0,
    "self_eval": 0.35,
    "constraints": 1.0,
    "process_steps": 0.75,
    "anti_proxy": 0.85,
    "downstream_actionable": 0.9,
    "domain_depth": 0.5,
    "recursive_hook": 0.35,
}

BOILERPLATE_PATTERNS: tuple[str, ...] = (
    r"be clear and concise",
    r"ensure high quality",
    r"think carefully",
    r"provide a helpful response",
    r"high quality output",
)

_STOPWORDS = frozenset({
    "when", "this", "works", "will", "that", "with", "from", "your", "have", "been",
    "what", "which", "their", "about", "would", "should", "could", "into", "through",
})


def score_task_prompt(content: str, use_case: str = "") -> PromptQuality:
    """Score a task prompt 0.0–1.0 on structural dimensions."""
    dims: dict[str, float] = {}
    present: list[str] = []
    missing: list[str] = []

    weighted_hits = 0.0
    weight_total = 0.0
    for feat_id, pattern, label in FEATURE_CHECKS:
        w = FEATURE_WEIGHTS.get(feat_id, 1.0)
        weight_total += w
        if re.search(pattern, content, re.I | re.S):
            weighted_hits += w
            present.append(label)
        else:
            missing.append(label)
    dims["feature_coverage"] = weighted_hits / max(weight_total, 1.0)

    vague_patterns = [
        r"^You are a \w+ agent?\.\s*(Help|Review|Analyze|Write)",
        r"politely\.?\s*$",
        r"give feedback\.?\s*$",
        r"tell me if",
    ]
    vague_hits = sum(1 for p in vague_patterns if re.search(p, content, re.I | re.M))
    dims["specificity"] = max(0.0, 1.0 - vague_hits * 0.35)

    section_count = len(re.findall(r"^#{1,3} ", content, re.M))
    bullet_count = len(re.findall(r"^[\-\*] ", content, re.M))
    numbered = len(re.findall(r"^\d+\.", content, re.M))
    dims["structure"] = min(1.0, (section_count * 0.15 + bullet_count * 0.05 + numbered * 0.08))

    words = len(content.split())
    if words < 30:
        len_score = words / 30
    elif words > 800:
        len_score = max(0.5, 1.0 - (words - 800) / 1200)
    else:
        len_score = 1.0
    dims["length"] = len_score

    rubric_weights = {"feature_coverage": 0.50, "specificity": 0.20, "structure": 0.10, "length": 0.10}
    total = sum(dims[k] * w for k, w in rubric_weights.items())

    return PromptQuality(
        total=total,
        dimensions=dims,
        features_present=present,
        features_missing=missing,
        word_count=words,
        grade=_grade(total),
    )


def score_objective_alignment(content: str, objective: str) -> float:
    """How well the prompt operationalizes terms from the stated objective."""
    obj_words = {w for w in re.findall(r"[a-z]{4,}", objective.lower()) if w not in _STOPWORDS}
    if not obj_words:
        return 0.5
    text = content.lower()
    hits = sum(1 for w in obj_words if w in text)
    return min(1.0, hits / len(obj_words))


def score_register_fit(content: str, leaning: str) -> float:
    """Register match — separate from structural rubric."""
    from ri_engine.register_analysis import analyze_register

    reg = analyze_register(content)
    if leaning == "plain":
        return max(0.0, min(1.0, (1.0 - reg.latinate_ratio) * 0.7 + reg.readability_score * 0.3))
    if leaning == "latinate":
        return max(0.0, min(1.0, reg.latinate_ratio * 0.85 + (1.0 - reg.readability_score) * 0.15))
    if leaning == "conversational":
        return max(0.0, min(1.0, reg.readability_score * 0.6 + (1.0 - reg.latinate_ratio) * 0.4))
    if leaning == "technical":
        return max(0.0, min(1.0, min(1.0, reg.avg_word_length / 6.0) * 0.5 + reg.latinate_ratio * 0.5))
    if leaning == "mixed":
        mid = 1.0 - abs(reg.latinate_ratio - 0.45) * 2
        return max(0.0, min(1.0, mid))
    return 0.5


def score_instruction_economy(content: str) -> float:
    """Penalize boilerplate and excessive sectioning."""
    words = max(len(content.split()), 1)
    sections = len(re.findall(r"^#{1,3} ", content, re.M))
    boiler = sum(1 for p in BOILERPLATE_PATTERNS if re.search(p, content, re.I))
    section_penalty = max(0, sections - 8) * 0.04
    boiler_penalty = boiler * 0.08
    density = min(1.0, 120 / words) if words > 120 else 1.0
    return max(0.0, min(1.0, density - section_penalty - boiler_penalty))


def composite_prompt_score(content: str, objective: str, *, leaning: str = "mixed") -> dict[str, float]:
    """Combined offline score for baseline vs VSR comparison."""
    rubric = score_task_prompt(content)
    align = score_objective_alignment(content, objective)
    reg_fit = score_register_fit(content, leaning)
    economy = score_instruction_economy(content)
    total = (
        0.30 * align
        + 0.25 * rubric.total
        + 0.20 * rubric.dimensions.get("specificity", 0.0)
        + 0.15 * economy
        + 0.05 * reg_fit
        + 0.05 * rubric.dimensions.get("feature_coverage", 0.0)
    )
    return {
        "total": round(min(1.0, total), 4),
        "rubric_score": round(rubric.total, 4),
        "objective_alignment": round(align, 4),
        "register_fit": round(reg_fit, 4),
        "instruction_economy": round(economy, 4),
        "word_count": float(rubric.word_count),
    }


def _grade(score: float) -> str:
    if score >= 0.85:
        return "A — Strong structure"
    if score >= 0.70:
        return "B — Good"
    if score >= 0.55:
        return "C — Needs Work"
    if score >= 0.40:
        return "D — Weak"
    return "F — Unusable"


def compare_prompts(seed: str, evolved: str, use_case: str = "") -> dict:
    """Compare seed vs evolved with delta metrics."""
    before = score_task_prompt(seed, use_case)
    after = score_task_prompt(evolved, use_case)
    new_features = [f for f in after.features_present if f not in before.features_present]
    return {
        "before_score": before.total,
        "after_score": after.total,
        "delta": after.total - before.total,
        "delta_pct": (after.total - before.total) / max(before.total, 0.01) * 100,
        "before_grade": before.grade,
        "after_grade": after.grade,
        "before_words": before.word_count,
        "after_words": after.word_count,
        "features_gained": new_features,
        "features_missing_remaining": after.features_missing,
        "before_features": len(before.features_present),
        "after_features": len(after.features_present),
    }
