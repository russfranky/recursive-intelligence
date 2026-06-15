"""
Objective clarity gate — friendly kickback when goals are too vague to improve against.

Nudge: state your desired outcome first ("When this works, the AI will …").
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

CLARITY_READY = 60
CLARITY_BLOCK = 45

GENERIC_ONLY = re.compile(
    r"^(?:please\s+)?(?:help|improve|fix|optimize|make|be|do|support|assist)\b",
    re.I,
)
VAGUE_ADJECTIVES = re.compile(
    r"\b(?:good|better|best|nice|great|professional|detailed|comprehensive|helpful|quality)\b",
    re.I,
)
MEASURABLE_SIGNALS = re.compile(
    r"\b(?:when this works|must not|must|without|within|at least|no more than|"
    r"in one|single|measurable|format|steps?|checklist|escalat|resolve|deliver)\b"
    r"|\d+\s*(?:%|messages?|steps?|rounds?|minutes?|hours?|days?)",
    re.I,
)
OUTCOME_PREFIX = re.compile(r"^when this works", re.I)


@dataclass
class ObjectiveAssessment:
    """Result of assessing a user goal before VSR runs."""

    objective: str
    clarity_score: int
    ready: bool
    blocked: bool
    gaps: list[str] = field(default_factory=list)
    suggested_goals: list[str] = field(default_factory=list)
    kickback_message: str = ""
    normalized_objective: str = ""

    def to_dict(self) -> dict:
        return {
            "objective": self.objective,
            "clarity_score": self.clarity_score,
            "ready": self.ready,
            "blocked": self.blocked,
            "gaps": self.gaps,
            "suggested_goals": self.suggested_goals,
            "kickback_message": self.kickback_message,
            "normalized_objective": self.normalized_objective,
        }


def _suggest_goals(objective: str, objective_class: str = "general") -> list[str]:
    presets: dict[str, list[str]] = {
        "customer-support": [
            "When this works, the AI will resolve billing issues in one conversation without escalation.",
            "When this works, the AI will triage support tickets to the right team in under 3 messages.",
        ],
        "code-review": [
            "When this works, the AI will post a PR review with severity, one concrete fix, and a pass/fail recommendation.",
            "When this works, the AI will flag security issues with CWE references and suggested patches.",
        ],
        "sales-outreach": [
            "When this works, the AI will draft a 120-word outreach email with one clear CTA and no hype.",
        ],
        "general": [
            "When this works, the AI will complete the task in one pass with a structured output I can verify.",
            "When this works, the AI will follow 3 numbered steps and end with a summary the user can act on.",
        ],
    }
    return presets.get(objective_class, presets["general"])


def assess_objective(
    objective: str,
    *,
    metadata: dict | None = None,
    skip_for_template: bool = True,
) -> ObjectiveAssessment:
    """
    Score goal clarity 0–100. Block below CLARITY_BLOCK; warn below CLARITY_READY.

    Templates (metadata template/template_id) skip the gate by default.
    """
    meta = metadata or {}
    text = (objective or "").strip()

    if skip_for_template and (meta.get("template") or meta.get("template_id")):
        return ObjectiveAssessment(
            objective=text,
            clarity_score=100,
            ready=True,
            blocked=False,
            normalized_objective=text,
        )

    if not text:
        return ObjectiveAssessment(
            objective=text,
            clarity_score=0,
            ready=False,
            blocked=True,
            gaps=["No desired outcome provided"],
            suggested_goals=_suggest_goals("", "general"),
            kickback_message=_format_kickback(text, 0, ["No desired outcome provided"], _suggest_goals("", "general")),
        )

    score = 40
    gaps: list[str] = []

    if len(text) >= 40:
        score += 10
    if len(text) >= 80:
        score += 5
    if OUTCOME_PREFIX.search(text):
        score += 20
    elif text.lower().startswith("the ai will"):
        score += 15
    if MEASURABLE_SIGNALS.search(text):
        score += 20
    else:
        gaps.append("No measurable success signal (format, limits, or done-when criteria)")

    if GENERIC_ONLY.match(text) and len(text.split()) < 8:
        score -= 25
        gaps.append("Goal is mostly a generic verb with no specific outcome")

    if VAGUE_ADJECTIVES.search(text) and not MEASURABLE_SIGNALS.search(text):
        score -= 15
        gaps.append("Uses subjective words (good, better, professional) without testable criteria")

    if len(text.split()) < 5:
        score -= 10
        gaps.append("Too short — say what done looks like")

    score = max(0, min(100, score))

    from ri_engine.macro_registry import classify_objective

    obj_class = classify_objective(text, meta)
    suggestions = _suggest_goals(text, obj_class)

    blocked = score < CLARITY_BLOCK
    ready = score >= CLARITY_READY

    normalized = text
    if not OUTCOME_PREFIX.search(text) and ready:
        normalized = f"When this works, the AI will {text[0].lower() + text[1:] if text else text}"

    kickback = ""
    if blocked or not ready:
        kickback = _format_kickback(text, score, gaps, suggestions)

    return ObjectiveAssessment(
        objective=text,
        clarity_score=score,
        ready=ready,
        blocked=blocked,
        gaps=gaps,
        suggested_goals=suggestions,
        kickback_message=kickback,
        normalized_objective=normalized,
    )


def _format_kickback(
    objective: str,
    score: int,
    gaps: list[str],
    suggestions: list[str],
) -> str:
    lines = [
        f"Goal clarity: {score}/100 — state your desired outcome first.",
        "",
        f'Your goal: "{objective[:120]}{"…" if len(objective) > 120 else ""}"',
        "",
        "What's missing:",
    ]
    for gap in gaps[:4]:
        lines.append(f"  · {gap}")
    lines.extend([
        "",
        "Try leading with:",
        '  "When this works, the AI will [specific result] for [who], without [failure mode]."',
        "",
        "Examples:",
    ])
    for i, s in enumerate(suggestions[:3], 1):
        lines.append(f"  {i}. {s}")
    lines.extend([
        "",
        "Re-run with --goal \"When this works, the AI will …\"",
        "Or use a template: ri-engine templates",
        "Force past gate: --force-goal (expert)",
    ])
    return "\n".join(lines)
