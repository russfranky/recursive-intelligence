"""
Linguistic leanings registry — categorical language-direction pooling for future runs.

Full-spectrum coverage: plain, latinate, mixed, neutral, technical, conversational.
The pool command runs the engine across category × leaning cells and persists winners.
The gate resolves direction before VSR using pooled evidence.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from ri_engine.models import RunConfig
from ri_engine.register_analysis import RegisterMetrics, analyze_register, composite_task_score
from ri_engine.paths import config_dir, resolve_resource_path, workspace_dir

DEFAULT_SPECTRUM_PATH = config_dir() / "linguistic_spectrum.yaml"


def default_registry_path() -> Path:
    """Prefer a local registry in the working directory; fall back to bundled defaults."""
    local = workspace_dir() / "config" / "linguistic_registry.json"
    if local.exists():
        return local
    bundled = config_dir() / "linguistic_registry.json"
    return bundled if bundled.exists() else local

# Full linguistic direction spectrum
SPECTRUM_LEANINGS: tuple[str, ...] = (
    "plain",
    "latinate",
    "mixed",
    "neutral",
    "technical",
    "conversational",
)

LEANING_CLAUSES: dict[str, str] = {
    "plain": (
        "MANDATORY LINGUISTIC LEANING: Use plain Anglo-Saxon English throughout. "
        "Short direct words. Avoid Latinate filler (facilitate, utilize, comprehensive methodology)."
    ),
    "latinate": (
        "MANDATORY LINGUISTIC LEANING: Use formal Latinate register throughout. "
        "Prefer Latinate vocabulary (facilitate, implement, evaluate, assess, verify, protocol, remediation)."
    ),
    "mixed": (
        "MANDATORY LINGUISTIC LEANING: Use plain Anglo-Saxon for instructions and actions. "
        "Retain domain-specific technical or Latinate terms only where precision requires them."
    ),
    "neutral": "",
    "technical": (
        "MANDATORY LINGUISTIC LEANING: Use precise technical vocabulary for domain specialists. "
        "Prioritize accuracy and domain terminology over readability simplification."
    ),
    "conversational": (
        "MANDATORY LINGUISTIC LEANING: Use casual, direct, user-friendly language. "
        "Avoid jargon, formality, and Latinate filler. Write as you would speak to the user."
    ),
}

LEANING_BLOCKS: dict[str, str] = {
    "plain": """\
## Linguistic Leaning
Use plain Anglo-Saxon English throughout. Short, direct words.
Prefer: help, use, check, find, fix, end, run, block, show, ask.
Avoid Latinate filler: facilitate, utilize, implement, comprehensive methodology.""",
    "latinate": """\
## Linguistic Leaning
Use formal Latinate vocabulary throughout this prompt and all outputs it generates.
Prefer: facilitate, implement, evaluate, assess, verify, comprehensive, methodology,
protocol, classification, termination, remediation, investigation, correlation.
Avoid plain Anglo-Saxon equivalents when Latinate precision is available.""",
    "mixed": """\
## Linguistic Leaning
Use plain Anglo-Saxon for instructions, steps, and operator actions.
Keep domain-specific technical terms (MITRE, OWASP, SLA, etc.) where precision requires them.
Do not Latinate general verbs when a plain word works.""",
    "neutral": """\
## Linguistic Leaning
No register preference. Optimize for task clarity and downstream actionability.""",
    "technical": """\
## Linguistic Leaning
Use precise domain terminology throughout. Assume a specialist audience.
Prioritize technical accuracy over conversational simplification.""",
    "conversational": """\
## Linguistic Leaning
Use casual, direct, user-friendly language. Short sentences.
Avoid jargon, acronyms without explanation, and formal Latinate phrasing.""",
}

# Keyword signals for cold-start inference when registry has no match
CATEGORY_LEANING_PRIORS: dict[str, str] = {
    "software engineering": "plain",
    "agentic development": "plain",
    "operations": "conversational",
    "research & intelligence": "mixed",
    "revenue": "conversational",
    "security": "plain",
    "legal & compliance": "latinate",
    "clinical & medical": "latinate",
    "executive communications": "mixed",
}

AUDIENCE_LEANING_PRIORS: dict[str, str] = {
    "developer": "plain",
    "operator": "plain",
    "end_user": "conversational",
    "customer": "conversational",
    "prospect": "conversational",
    "researcher": "mixed",
    "regulator": "latinate",
    "clinician": "latinate",
    "executive": "mixed",
}


@dataclass
class LeaningScore:
    leaning: str
    quality: float
    composite: float
    fitness: float = 0.0
    latinate_ratio: float = 0.0
    readability: float = 0.0
    token_estimate: int = 0
    register_label: str = ""


@dataclass
class LanguageLeaningEntry:
    """Pooled categorical registration for one category × audience cell."""

    id: str
    category: str
    audience: str
    task_type: str
    recommended_leaning: str
    confidence: float
    spectrum_scores: dict[str, dict[str, float]]
    alternatives: list[str] = field(default_factory=list)
    rationale: str = ""
    evidence_runs: int = 0
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LanguageLeaningEntry:
        return cls(**data)


@dataclass
class LinguisticGateResult:
    leaning: str
    confidence: float
    source: str  # registry | prior | inference | override | probe | auto | off
    registry_id: str | None = None
    clause_applied: str = ""
    rationale: str = ""
    objective_signal: float = 0.0
    registry_signal: float = 0.0
    objective_leaning: str = ""
    registry_leaning: str = ""


def leaning_clause(leaning: str) -> str:
    return LEANING_CLAUSES.get(leaning, "")


def detect_linguistic_leaning(text: str) -> str:
    """Detect explicit leaning directive from objective or prompt text."""
    obj = text.lower()
    checks = [
        ("latinate", ("latinate register", "formal latinate", "latinate english", "linguistic leaning: use formal latinate")),
        ("plain", ("plain anglo-saxon", "plain language", "short words", "linguistic leaning: use plain")),
        ("mixed", ("mixed leaning", "plain anglo-saxon for instructions", "linguistic leaning: use plain anglo-saxon for instructions")),
        ("technical", ("technical vocabulary", "specialist audience", "linguistic leaning: use precise technical")),
        ("conversational", ("user-friendly language", "conversational", "linguistic leaning: use casual")),
        ("neutral", ("no register preference", "linguistic leaning: no register")),
    ]
    for leaning, phrases in checks:
        if any(p in obj for p in phrases):
            return leaning
    return "plain"


def leaning_register_target(leaning: str) -> str:
    """Map leaning to composite_task_score target."""
    if leaning in ("plain", "latinate", "neutral"):
        return leaning
    if leaning == "mixed":
        return "mixed"
    if leaning == "technical":
        return "latinate"  # partial — technical correlates with domain Latinate terms
    if leaning == "conversational":
        return "plain"
    return "neutral"


def score_leaning_fit(
    leaning: str,
    utility: float,
    register: RegisterMetrics,
) -> float:
    """Score how well output fits a linguistic leaning."""
    target = leaning_register_target(leaning)
    base = composite_task_score(utility, register, target=target)

    if leaning == "mixed":
        # Reward moderate latinate ratio (domain terms without full formalization)
        mid = 1.0 - abs(register.latinate_ratio - 0.45) * 1.5
        return max(0.0, min(1.0, base * 0.7 + max(0.0, mid) * 0.3))
    if leaning == "technical":
        length_bonus = min(0.15, (register.avg_word_length - 4.5) * 0.03)
        return max(0.0, min(1.0, base + length_bonus))
    if leaning == "conversational":
        read_bonus = register.readability_score * 0.1
        plain_bonus = (1.0 - register.latinate_ratio) * 0.08
        return max(0.0, min(1.0, base + read_bonus + plain_bonus))
    return base


class LinguisticRegistry:
    """Persistent pool of categorical language leanings."""

    def __init__(self, path: Path | None = None):
        self.path = path or default_registry_path()
        self.version = 1
        self.timestamp = ""
        self.entries: dict[str, LanguageLeaningEntry] = {}

    def load(self) -> LinguisticRegistry:
        if not self.path.exists():
            return self
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.version = data.get("version", 1)
        self.timestamp = data.get("timestamp", "")
        self.entries = {
            k: LanguageLeaningEntry.from_dict(v)
            for k, v in data.get("entries", {}).items()
        }
        return self

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now(timezone.utc).isoformat()
        payload = {
            "version": self.version,
            "timestamp": self.timestamp,
            "spectrum_leanings": list(SPECTRUM_LEANINGS),
            "entries": {k: v.to_dict() for k, v in self.entries.items()},
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def upsert(self, entry: LanguageLeaningEntry) -> None:
        self.entries[entry.id] = entry

    def lookup(
        self,
        *,
        category: str = "",
        audience: str = "",
        task_type: str = "",
        use_case_id: str = "",
    ) -> LanguageLeaningEntry | None:
        keys = []
        if category and audience:
            norm = _normalize_key(category, audience)
            keys.append(norm)
        if use_case_id and audience:
            keys.append(f"{use_case_id}:{audience}")
        if use_case_id:
            keys.append(use_case_id)
        for key in keys:
            if key in self.entries:
                return self.entries[key]
        # Fuzzy category match
        cat_l = category.lower()
        for entry in self.entries.values():
            if entry.category.lower() == cat_l and (
                not audience or entry.audience.lower() == audience.lower()
            ):
                return entry
        return None


def _normalize_key(category: str, audience: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", category.lower()).strip("_")
    aud = re.sub(r"[^a-z0-9]+", "_", audience.lower()).strip("_")
    return f"{slug}:{aud}"


def _objective_text_signal(objective: str) -> tuple[str, float]:
    """Objective-text leaning signal with confidence."""
    text = objective.lower()
    explicit_checks = [
        ("latinate", ("latinate register", "formal latinate", "formal institutional", "compliance language")),
        ("plain", ("plain anglo-saxon", "plain language", "shutdown instructions", "step-by-step", "time pressure")),
        ("mixed", ("non-specialists", "formal distinctions", "plain anglo-saxon for instructions")),
        ("technical", ("stack trace", "root cause", "api error", "logs", "reproduction steps")),
        ("conversational", ("friendly", "writing coach", "supportive", "user-friendly")),
    ]
    for leaning, phrases in explicit_checks:
        if any(p in text for p in phrases):
            return leaning, 0.82
    detected = detect_linguistic_leaning(objective)
    if detected != "plain":
        return detected, 0.65
    return "plain", 0.45


def resolve_linguistic_direction(
    config: RunConfig,
    registry: LinguisticRegistry | None = None,
) -> LinguisticGateResult:
    """
    Resolve linguistic direction before VSR.

    Auto mode uses weighted objective text (55%) + weak registry prior (25%) +
    category/audience context (15%). Low confidence defaults to ``mixed``.
    """
    meta = config.metadata or {}
    if override := meta.get("linguistic_leaning"):
        return LinguisticGateResult(
            leaning=str(override),
            confidence=1.0,
            source="override",
            clause_applied=leaning_clause(str(override)),
            rationale="Explicit metadata override",
            objective_leaning=str(override),
            objective_signal=1.0,
        )

    mode = str(meta.get("linguistic_gate_mode", "auto"))
    if mode == "off":
        return LinguisticGateResult(
            leaning="neutral",
            confidence=0.0,
            source="off",
            rationale="Linguistic gate disabled",
        )
    if mode in SPECTRUM_LEANINGS and mode != "auto":
        return LinguisticGateResult(
            leaning=mode,
            confidence=1.0,
            source="override",
            clause_applied=leaning_clause(mode),
            rationale=f"Forced linguistic gate mode: {mode}",
            objective_leaning=mode,
            objective_signal=1.0,
        )

    obj_lean, obj_conf = _objective_text_signal(config.objective)
    reg = registry or LinguisticRegistry().load()
    category = str(meta.get("category", ""))
    audience = str(meta.get("audience", "operator"))
    use_case_id = str(meta.get("use_case", meta.get("use_case_id", "")))

    reg_lean, reg_conf, reg_id = "mixed", 0.0, None
    if entry := reg.lookup(category=category, audience=audience, use_case_id=use_case_id):
        reg_lean = entry.recommended_leaning
        reg_conf = min(entry.confidence, 0.75)
        reg_id = entry.id

    cat_prior = CATEGORY_LEANING_PRIORS.get(category.lower(), "")
    aud_prior = AUDIENCE_LEANING_PRIORS.get(audience.lower(), "")
    context_lean = aud_prior or cat_prior or obj_lean
    context_conf = 0.55 if aud_prior and cat_prior and aud_prior == cat_prior else 0.45

    votes: dict[str, float] = {}
    for lean, weight in (
        (obj_lean, obj_conf * 0.55),
        (reg_lean, reg_conf * 0.25),
        (context_lean, context_conf * 0.15),
    ):
        votes[lean] = votes.get(lean, 0.0) + weight

    winner = max(votes, key=votes.get)
    confidence = votes[winner]
    if confidence < 0.52:
        winner = "mixed"
        confidence = max(confidence, 0.5)
        rationale = (
            f"Low confidence ({confidence:.0%}) — defaulting to mixed. "
            f"objective={obj_lean}({obj_conf:.0%}), registry={reg_lean}({reg_conf:.0%})"
        )
    else:
        rationale = (
            f"Auto gate: objective={obj_lean}({obj_conf:.0%}), "
            f"registry={reg_lean}({reg_conf:.0%}), context={context_lean} → {winner}"
        )

    return LinguisticGateResult(
        leaning=winner,
        confidence=confidence,
        source="auto",
        registry_id=reg_id,
        clause_applied=leaning_clause(winner),
        rationale=rationale,
        objective_signal=obj_conf,
        registry_signal=reg_conf,
        objective_leaning=obj_lean,
        registry_leaning=reg_lean,
    )


def apply_linguistic_gate(
    config: RunConfig,
    registry: LinguisticRegistry | None = None,
    *,
    force: bool = False,
) -> tuple[RunConfig, LinguisticGateResult]:
    """
    Apply linguistic direction gate before engine exposure.
    Injects leaning clause into objective when not already present.
    """
    meta = dict(config.metadata or {})
    if meta.get("apply_linguistic_gate") is False and not force:
        return config, LinguisticGateResult(
            leaning="neutral",
            confidence=1.0,
            source="override",
            rationale="Gate disabled via metadata",
        )

    gate = resolve_linguistic_direction(config, registry)
    objective = config.objective.strip()
    clause = gate.clause_applied

    if clause and clause.lower() not in objective.lower():
        objective = f"{objective}\n\n{clause}"

    meta["linguistic_leaning"] = gate.leaning
    meta["linguistic_gate"] = {
        "confidence": gate.confidence,
        "source": gate.source,
        "registry_id": gate.registry_id,
        "rationale": gate.rationale,
    }

    updated = RunConfig(
        seed_prompt=config.seed_prompt,
        objective=objective,
        max_generations=config.max_generations,
        population_size=config.population_size,
        survivors_count=config.survivors_count,
        convergence_threshold=config.convergence_threshold,
        convergence_window=config.convergence_window,
        variation_temperature=config.variation_temperature,
        enable_membrane_bridge=config.enable_membrane_bridge,
        domains=config.domains,
        fitness_weights=config.fitness_weights,
        output_path=config.output_path,
        metadata=meta,
    )
    return updated, gate


def load_spectrum_entries(spectrum_path: Path | None = None) -> list[dict[str, Any]]:
    """Load full-spectrum category cells from YAML."""
    path = spectrum_path or DEFAULT_SPECTRUM_PATH
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    entries: list[dict[str, Any]] = []
    for item in data.get("entries", []):
        if source := item.get("source"):
            src_path = resolve_resource_path(source)
            uc = yaml.safe_load(src_path.read_text(encoding="utf-8"))
            item = {
                **item,
                "seed_prompt": uc["seed_prompt"],
                "objective": uc["objective"],
                "domains": uc.get("domains", []),
                "metadata": {**uc.get("metadata", {}), **item.get("metadata", {})},
            }
        entries.append(item)
    return entries


def build_registry_entry(
    cell: dict[str, Any],
    scores: list[LeaningScore],
    *,
    used_vsr: bool = False,
) -> LanguageLeaningEntry:
    """Build pooled registry entry from full-spectrum evaluation."""
    ranked = sorted(scores, key=lambda s: s.composite, reverse=True)
    winner = ranked[0]
    runner_up = ranked[1] if len(ranked) > 1 else None

    margin = winner.composite - (runner_up.composite if runner_up else 0.0)
    confidence = min(0.98, 0.55 + margin * 2.0 + (0.1 if used_vsr else 0.0))
    if winner.composite < 0.5:
        confidence = min(confidence, 0.45)

    alternatives = [s.leaning for s in ranked[1:3]]
    cat = cell.get("category", "")
    aud = cell.get("audience", "operator")
    entry_id = cell.get("id") or _normalize_key(cat, aud)

    rationale = (
        f"{winner.leaning} wins composite {winner.composite:.2f} "
        f"(quality={winner.quality:.0%}, lat_ratio={winner.latinate_ratio:.2f}, "
        f"read={winner.readability:.2f})"
    )
    if runner_up:
        rationale += f"; runner-up {runner_up.leaning} at {runner_up.composite:.2f}"

    return LanguageLeaningEntry(
        id=entry_id,
        category=cat,
        audience=aud,
        task_type=cell.get("task_type", "agent_prompt"),
        recommended_leaning=winner.leaning,
        confidence=round(confidence, 3),
        spectrum_scores={
            s.leaning: {
                "quality": round(s.quality, 4),
                "composite": round(s.composite, 4),
                "fitness": round(s.fitness, 4),
                "latinate_ratio": round(s.latinate_ratio, 4),
                "readability": round(s.readability, 4),
                "token_estimate": s.token_estimate,
            }
            for s in scores
        },
        alternatives=alternatives,
        rationale=rationale,
        evidence_runs=1,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
