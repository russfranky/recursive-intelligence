"""
Macro-scale trait registry — internal recursive learning across runs.

When prompts are selected (high fitness survivors), Retention traits are parsed
and pooled locally by objective class. Future runs merge priors into Variation
and lineage insight — macro recursion, not public-facing sync.

Registry: ``config/macro_trait_registry.json`` (gitignored in production use).
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ri_engine.models import Candidate, RunConfig
from ri_engine.trait_parser import ParsedTrait, parse_traits
from ri_engine.paths import config_dir, workspace_dir

DEFAULT_REGISTRY_PATH = workspace_dir() / "config" / "macro_trait_registry.json"
DEFAULT_EXPORT_DIR = workspace_dir() / "output" / "traits"

FORBIDDEN_EXPORT_FIELDS = (
    "seed_prompt",
    "objective_verbatim",
    "customer_names",
    "raw_variants",
    "improved_prompt",
    "prompt",
)

MIN_FITNESS_TO_RECORD = 0.65
MAX_TRAITS_PER_CLASS = 12

OBJECTIVE_CLASSES: dict[str, tuple[str, ...]] = {
    "customer-support": (
        "support", "customer", "ticket", "billing", "help desk", "resolve",
    ),
    "code-review": ("code review", "pull request", "pr review", "reviewer", "lint"),
    "sales-outreach": ("sales", "outreach", "email", "prospect", "pipeline"),
    "research": ("research", "analyze", "investigate", "report", "synthesis"),
    "operations": ("ops", "operational", "incident", "runbook", "on-call"),
    "security": ("security", "vulnerability", "threat", "audit", "compliance"),
}


@dataclass
class TraitRecord:
    name: str
    instruction: str
    evidence: str = ""
    selection_count: int = 0
    fitness_sum: float = 0.0
    last_fitness: float = 0.0
    last_selected_at: str = ""

    @property
    def avg_fitness(self) -> float:
        if self.selection_count <= 0:
            return 0.0
        return self.fitness_sum / self.selection_count

    @property
    def weight(self) -> float:
        return self.selection_count * self.avg_fitness

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TraitRecord:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ObjectiveClassEntry:
    objective_class: str
    traits: dict[str, TraitRecord] = field(default_factory=dict)
    selection_runs: int = 0
    best_fitness: float = 0.0
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective_class": self.objective_class,
            "traits": {k: v.to_dict() for k, v in self.traits.items()},
            "selection_runs": self.selection_runs,
            "best_fitness": self.best_fitness,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ObjectiveClassEntry:
        traits = {
            k: TraitRecord.from_dict(v)
            for k, v in (data.get("traits") or {}).items()
        }
        return cls(
            objective_class=data.get("objective_class", "general"),
            traits=traits,
            selection_runs=int(data.get("selection_runs", 0)),
            best_fitness=float(data.get("best_fitness", 0.0)),
            updated_at=data.get("updated_at", ""),
        )


@dataclass
class MacroPriorReport:
    objective_class: str
    trait_count: int
    selection_runs: int
    strategy_order: list[str]
    brief: str
    source: str  # registry | none
    fitness_weights: dict[str, float] = field(default_factory=dict)


@dataclass
class TraitExportBundle:
    """Opt-in trait export — no raw prompt text."""

    schema_version: int
    trait_id: str
    objective_class: str
    fitness: float
    fitness_delta: float
    cycles: int
    plateaued: bool
    exported_at: str
    traits: list[dict[str, Any]]
    forbidden_omitted: list[str] = field(default_factory=lambda: list(FORBIDDEN_EXPORT_FIELDS))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MacroTraitRegistry:
    """Local pooled traits from selected prompts — internal macro memory."""

    def __init__(self, path: Path | None = None):
        self.path = path or DEFAULT_REGISTRY_PATH
        self.version = 1
        self.timestamp = ""
        self.entries: dict[str, ObjectiveClassEntry] = {}

    def load(self) -> MacroTraitRegistry:
        if not self.path.exists():
            return self
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.version = int(data.get("version", 1))
        self.timestamp = data.get("timestamp", "")
        self.entries = {
            k: ObjectiveClassEntry.from_dict(v)
            for k, v in (data.get("entries") or {}).items()
        }
        return self

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now(timezone.utc).isoformat()
        payload = {
            "version": self.version,
            "timestamp": self.timestamp,
            "description": "Internal macro trait pool — patterns from selected prompts, not raw text.",
            "entries": {k: v.to_dict() for k, v in self.entries.items()},
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def upsert_traits(
        self,
        objective_class: str,
        traits: list[ParsedTrait],
        fitness: float,
        *,
        min_fitness: float = MIN_FITNESS_TO_RECORD,
    ) -> bool:
        """Record traits from a selection event. Returns True if stored."""
        if fitness < min_fitness or not traits:
            return False

        entry = self.entries.get(objective_class)
        if entry is None:
            entry = ObjectiveClassEntry(objective_class=objective_class)
            self.entries[objective_class] = entry

        entry.selection_runs += 1
        entry.best_fitness = max(entry.best_fitness, fitness)
        entry.updated_at = datetime.now(timezone.utc).isoformat()
        now = entry.updated_at

        for trait in traits:
            key = trait.normalized_name()
            if not key:
                continue
            rec = entry.traits.get(key)
            if rec is None:
                rec = TraitRecord(name=trait.name, instruction=trait.instruction, evidence=trait.evidence)
                entry.traits[key] = rec
            rec.selection_count += 1
            rec.fitness_sum += fitness
            rec.last_fitness = fitness
            rec.last_selected_at = now
            if trait.evidence:
                rec.evidence = trait.evidence
            if len(trait.instruction) > len(rec.instruction):
                rec.instruction = trait.instruction[:200]

        self._prune_traits(entry)
        self.save()
        return True

    def _prune_traits(self, entry: ObjectiveClassEntry) -> None:
        if len(entry.traits) <= MAX_TRAITS_PER_CLASS:
            return
        ranked = sorted(entry.traits.items(), key=lambda kv: kv[1].weight, reverse=True)
        entry.traits = dict(ranked[:MAX_TRAITS_PER_CLASS])

    def lookup(self, objective_class: str) -> ObjectiveClassEntry | None:
        return self.entries.get(objective_class)

    def top_traits(self, objective_class: str, limit: int = 6) -> list[TraitRecord]:
        entry = self.lookup(objective_class)
        if not entry or not entry.traits:
            return []
        ranked = sorted(entry.traits.values(), key=lambda t: t.weight, reverse=True)
        return ranked[:limit]

    def strategy_order(self, objective_class: str) -> list[str]:
        """Variation strategies ranked by macro selection evidence."""
        entry = self.lookup(objective_class)
        if not entry:
            return []
        ranked = sorted(entry.traits.values(), key=lambda t: t.weight, reverse=True)
        names: list[str] = []
        for rec in ranked:
            slug = re.sub(r"[^a-z0-9_]+", "_", rec.name.lower()).strip("_")
            if slug and slug not in names:
                names.append(slug)
        return names[:8]

    def build_brief(self, objective_class: str) -> str:
        traits = self.top_traits(objective_class)
        if not traits:
            return ""
        lines = [
            "## Macro lineage (selected patterns from prior high-score runs)",
            f"Objective class: {objective_class}",
            "",
        ]
        for rec in traits:
            ev = f" (evidence: {rec.evidence})" if rec.evidence else ""
            lines.append(
                f"- [TRAIT:{rec.name}] {rec.instruction}{ev} "
                f"[selected {rec.selection_count}x, avg fitness {rec.avg_fitness:.0%}]"
            )
        return "\n".join(lines)


def classify_objective(objective: str, metadata: dict[str, Any] | None = None) -> str:
    """Map objective text to a coarse class for macro pooling."""
    meta = metadata or {}
    if template := meta.get("template") or meta.get("template_id"):
        return str(template).strip().lower().replace(" ", "-")
    if category := meta.get("category"):
        slug = re.sub(r"[^a-z0-9]+", "-", str(category).lower()).strip("-")
        if slug:
            return slug

    text = objective.lower()
    best_class = "general"
    best_hits = 0
    for cls, keywords in OBJECTIVE_CLASSES.items():
        hits = sum(1 for kw in keywords if kw in text)
        if hits > best_hits:
            best_hits = hits
            best_class = cls
    return best_class


def record_selection(
    config: RunConfig,
    best: Candidate,
    lineage: str,
    fitness: float,
    *,
    registry: MacroTraitRegistry | None = None,
    min_fitness: float = MIN_FITNESS_TO_RECORD,
) -> bool:
    """Persist traits when a prompt is selected at macro scale."""
    meta = config.metadata or {}
    if meta.get("enable_macro_learning") is False:
        return False

    traits = parse_traits(lineage)
    if not traits and best.metadata.get("strategy"):
        traits = [
            ParsedTrait(
                name=str(best.metadata.get("strategy", "selected")),
                instruction=f"Winning strategy at fitness {fitness:.0%}",
                evidence="selection survivor",
            )
        ]

    objective_class = classify_objective(config.objective, meta)
    reg = registry or MacroTraitRegistry().load()
    return reg.upsert_traits(objective_class, traits, fitness, min_fitness=min_fitness)


def apply_macro_priors(config: RunConfig) -> tuple[RunConfig, MacroPriorReport]:
    """Inject pooled trait priors before a VSR run."""
    meta = dict(config.metadata or {})
    if meta.get("enable_macro_learning") is False:
        return config, MacroPriorReport("general", 0, 0, [], "", "none")

    objective_class = classify_objective(config.objective, meta)
    reg = MacroTraitRegistry().load()
    entry = reg.lookup(objective_class)

    if entry is None or not entry.traits:
        # Fall back to general pool
        objective_class = "general" if objective_class != "general" else objective_class
        entry = reg.lookup("general")
    if entry is None or not entry.traits:
        return config, MacroPriorReport(objective_class, 0, 0, [], "", "none")

    brief = reg.build_brief(objective_class)
    strategies = reg.strategy_order(objective_class)
    meta["macro_trait_brief"] = brief
    meta["macro_strategy_order"] = strategies
    meta["macro_objective_class"] = objective_class
    meta["macro_selection_runs"] = entry.selection_runs

    weights: dict[str, float] = {}
    if entry.selection_runs >= 1:
        weights = dict(config.fitness_weights or {
            "clarity": 0.25, "novelty": 0.25, "utility": 0.30, "coherence": 0.20,
        })
        weights["utility"] = min(0.45, float(weights.get("utility", 0.30)) + 0.03)
        total = sum(weights.values()) or 1.0
        weights = {k: v / total for k, v in weights.items()}
        meta["macro_fitness_weights"] = weights

    cfg = replace(config, metadata=meta)
    if weights:
        cfg = replace(cfg, fitness_weights=weights)

    return cfg, MacroPriorReport(
        objective_class=objective_class,
        trait_count=len(entry.traits),
        selection_runs=entry.selection_runs,
        strategy_order=strategies,
        brief=brief,
        source="registry",
        fitness_weights=weights,
    )


def registry_summary(path: Path | None = None) -> dict[str, Any]:
    """Stats for expert inspection."""
    reg = MacroTraitRegistry(path).load()
    return {
        "path": str(reg.path),
        "classes": len(reg.entries),
        "entries": {
            k: {
                "selection_runs": e.selection_runs,
                "best_fitness": e.best_fitness,
                "trait_count": len(e.traits),
                "top_traits": [t.name for t in reg.top_traits(k, 3)],
            }
            for k, e in reg.entries.items()
        },
    }


def export_trait_bundle(
    *,
    objective_class: str,
    fitness: float,
    traits: list[ParsedTrait] | list[dict[str, Any]],
    cycles: int = 1,
    plateaued: bool = True,
    fitness_delta: float = 0.0,
    export_dir: Path | str | None = None,
    registry: MacroTraitRegistry | None = None,
) -> Path:
    """
    Write opt-in trait JSON bundle (no raw prompts). Also upserts macro registry.
    """
    export_base = Path(export_dir) if export_dir else DEFAULT_EXPORT_DIR
    export_base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    trait_id = f"{objective_class}-{ts}"

    trait_rows: list[dict[str, Any]] = []
    parsed: list[ParsedTrait] = []
    for t in traits:
        if isinstance(t, ParsedTrait):
            parsed.append(t)
            trait_rows.append({
                "name": t.name,
                "instruction": t.instruction,
                "evidence": t.evidence,
                "source_generation": 0,
            })
        else:
            trait_rows.append({
                "name": t.get("name", ""),
                "instruction": t.get("instruction", ""),
                "evidence": t.get("evidence", ""),
                "source_generation": int(t.get("source_generation", 0)),
            })
            parsed.append(
                ParsedTrait(
                    name=str(t.get("name", "")),
                    instruction=str(t.get("instruction", "")),
                    evidence=str(t.get("evidence", "")),
                )
            )

    bundle = TraitExportBundle(
        schema_version=1,
        trait_id=trait_id,
        objective_class=objective_class,
        fitness=fitness,
        fitness_delta=fitness_delta,
        cycles=cycles,
        plateaued=plateaued,
        exported_at=datetime.now(timezone.utc).isoformat(),
        traits=trait_rows,
    )

    out = export_base / f"{trait_id}.json"
    out.write_text(json.dumps(bundle.to_dict(), indent=2), encoding="utf-8")

    reg = registry or MacroTraitRegistry().load()
    reg.upsert_traits(objective_class, parsed, fitness)
    return out
