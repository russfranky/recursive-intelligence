"""
Task Prompt Quality Rubric — objective scoring to prove evolution value.

Measures presence of production-grade prompt features that correlate with
downstream agent reliability.
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


# Features that distinguish production prompts from weak ones
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


def score_task_prompt(content: str, use_case: str = "") -> PromptQuality:
    """Score a task prompt 0.0–1.0 on production-readiness dimensions."""
    dims: dict[str, float] = {}
    present: list[str] = []
    missing: list[str] = []

    # Feature presence (60%)
    feature_hits = 0
    for feat_id, pattern, label in FEATURE_CHECKS:
        if re.search(pattern, content, re.I | re.S):
            feature_hits += 1
            present.append(label)
        else:
            missing.append(label)
    dims["feature_coverage"] = feature_hits / len(FEATURE_CHECKS)

    # Specificity — penalize vague openers (20%)
    vague_patterns = [
        r"^You are a \w+ agent?\.\s*(Help|Review|Analyze|Write)",
        r"politely\.?\s*$",
        r"give feedback\.?\s*$",
        r"tell me if",
    ]
    vague_hits = sum(1 for p in vague_patterns if re.search(p, content, re.I | re.M))
    dims["specificity"] = max(0.0, 1.0 - vague_hits * 0.35)

    # Structural richness (10%)
    section_count = len(re.findall(r"^#{1,3} ", content, re.M))
    bullet_count = len(re.findall(r"^[\-\*] ", content, re.M))
    numbered = len(re.findall(r"^\d+\.", content, re.M))
    structure_score = min(1.0, (section_count * 0.15 + bullet_count * 0.05 + numbered * 0.08))
    dims["structure"] = structure_score

    # Length appropriateness (10%)
    words = len(content.split())
    if words < 30:
        len_score = words / 30
    elif words > 800:
        len_score = max(0.5, 1.0 - (words - 800) / 1200)
    else:
        len_score = 1.0
    dims["length"] = len_score

    weights = {"feature_coverage": 0.60, "specificity": 0.20, "structure": 0.10, "length": 0.10}
    total = sum(dims[k] * w for k, w in weights.items())

    grade = _grade(total)
    return PromptQuality(
        total=total,
        dimensions=dims,
        features_present=present,
        features_missing=missing,
        word_count=words,
        grade=grade,
    )


def _grade(score: float) -> str:
    if score >= 0.85:
        return "A — Production Ready"
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
