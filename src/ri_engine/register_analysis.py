"""
Register analysis — measure Latinate vs plain Anglo-Saxon usage in prompts.

Used to prove whether register choice affects engine evolution outcomes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# Anglo-Saxon plain → Latinate formal pairs (plain, latinate)
REGISTER_PAIRS: list[tuple[str, str]] = [
    ("help", "facilitate"),
    ("use", "utilize"),
    ("end", "terminate"),
    ("start", "commence"),
    ("ask", "inquire"),
    ("show", "demonstrate"),
    ("find", "identify"),
    ("check", "verify"),
    ("fix", "remediate"),
    ("make", "implement"),
    ("get", "obtain"),
    ("give", "provide"),
    ("think", "consider"),
    ("try", "attempt"),
    ("need", "require"),
    ("about", "regarding"),
    ("before", "prior to"),
    ("after", "subsequent to"),
    ("buy", "purchase"),
    ("speed", "velocity"),
    ("fire", "terminate"),
    ("king", "monarch"),
    ("write", "compose"),
    ("read", "perceive"),
    ("learn", "acquire"),
    ("strong", "robust"),
    ("clear", "unambiguous"),
    ("short", "concise"),
    ("big", "substantial"),
    ("fast", "expeditious"),
]

LATINATE_WORDS: set[str] = {lat for _, lat in REGISTER_PAIRS} | {
    "methodology", "comprehensive", "evaluation", "assessment", "classification",
    "implementation", "verification", "protocol", "criteria", "subsequently",
    "accordingly", "establish", "maintain", "conduct", "investigate", "analyze",
    "correlate", "synthesize", "prioritize", "determine", "indicate", "ensure",
    "objective", "parameter", "configuration", "optimization", "functionality",
    "capability", "infrastructure", "architecture", "specification", "documentation",
    "validation", "authorization", "authentication", "mitigation", "containment",
    "escalation", "resolution", "intervention", "correlation", "inference",
}

PLAIN_WORDS: set[str] = {plain for plain, _ in REGISTER_PAIRS} | {
    "run", "fix", "test", "block", "merge", "help", "stop", "go", "do", "say",
    "tell", "work", "break", "build", "ship", "push", "pull", "cut", "keep",
}


@dataclass
class RegisterMetrics:
    latinate_count: int = 0
    plain_count: int = 0
    latinate_ratio: float = 0.0
    avg_word_length: float = 0.0
    token_estimate: int = 0
    readability_score: float = 0.0
    register_label: str = "mixed"
    latinate_words_found: list[str] = field(default_factory=list)
    plain_words_found: list[str] = field(default_factory=list)


def analyze_register(text: str) -> RegisterMetrics:
    """Analyze register composition of a prompt."""
    words = re.findall(r"[a-zA-Z]+", text.lower())
    if not words:
        return RegisterMetrics()

    lat_found = [w for w in words if w in LATINATE_WORDS]
    plain_found = [w for w in words if w in PLAIN_WORDS]
    lat_count = len(lat_found)
    plain_count = len(plain_found)
    total_marked = lat_count + plain_count
    lat_ratio = lat_count / total_marked if total_marked > 0 else 0.0

    avg_len = sum(len(w) for w in words) / len(words)

    # Token estimate: Latinate words typically 1.5x tokens vs plain (subword BPE)
    token_est = sum(1.3 if w in LATINATE_WORDS else 1.0 for w in words)

    # Simplified readability: shorter words + shorter sentences = higher
    sentences = max(1, len(re.split(r"[.!?]+", text)))
    avg_sentence_len = len(words) / sentences
    readability = max(0.0, min(1.0, 1.0 - (avg_len - 4.5) * 0.15 - (avg_sentence_len - 20) * 0.01))

    if lat_ratio >= 0.65:
        label = "latinate"
    elif lat_ratio <= 0.35:
        label = "plain"
    else:
        label = "mixed"

    return RegisterMetrics(
        latinate_count=lat_count,
        plain_count=plain_count,
        latinate_ratio=lat_ratio,
        avg_word_length=avg_len,
        token_estimate=int(token_est),
        readability_score=readability,
        register_label=label,
        latinate_words_found=sorted(set(lat_found)),
        plain_words_found=sorted(set(plain_found)),
    )


def translate_to_latinate(text: str) -> str:
    """Convert plain Anglo-Saxon words to Latinate equivalents in text."""
    result = text
    for plain, lat in sorted(REGISTER_PAIRS, key=lambda x: -len(x[0])):
        result = re.sub(rf"\b{plain}\b", lat, result, flags=re.I)
    return result


def translate_to_plain(text: str) -> str:
    """Convert Latinate words to plain Anglo-Saxon equivalents."""
    result = text
    for plain, lat in sorted(REGISTER_PAIRS, key=lambda x: -len(x[1])):
        result = re.sub(rf"\b{lat}\b", plain, result, flags=re.I)
    return result


def composite_task_score(utility: float, register: RegisterMetrics, target: str = "plain") -> float:
    """
    Composite score weighting task utility vs register appropriateness.
    target: 'plain' | 'latinate' | 'neutral' | 'mixed'
    """
    if target == "plain":
        register_fit = 1.0 - register.latinate_ratio * 0.5 + register.readability_score * 0.3
    elif target == "latinate":
        register_fit = register.latinate_ratio * 0.7 + (1.0 - register.readability_score) * 0.1
    elif target == "mixed":
        mid = 1.0 - abs(register.latinate_ratio - 0.45) * 1.2
        register_fit = max(0.0, mid) * 0.6 + register.readability_score * 0.4
    else:
        register_fit = 0.5

    register_fit = max(0.0, min(1.0, register_fit))
    return utility * 0.75 + register_fit * 0.25
