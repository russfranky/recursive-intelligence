"""unix-compound — recursive modular process as a first-class CLI plugin.

goal → skeleton → sequence? → (build → check → sidecar)* → next

Offline-first. Deterministic heuristics so the plugin works without an API key.
Optional LLM provider can refine text; the process never depends on it.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ri_engine.occams_razor import composite_simplicity
from ri_engine.paths import workspace_dir

PLUGIN_NAME = "unix-compound"
PLUGIN_VERSION = "1.0.0"

PHASES = ("goal", "skeleton", "sequence", "build", "check", "sidecar", "next")

STATUS_OK = "OK"
STATUS_ACTIVE = ">>"
STATUS_PENDING = ".."
STATUS_DISCARD = "XX"
STATUS_RESIDUAL = "--"


# ---------------------------------------------------------------------------
# Domain catalogs (one thing each): known decompositions we validated live
# ---------------------------------------------------------------------------

_DOMAIN_SKELETONS: dict[str, list[dict[str, str]]] = {
    "daily": [
        {"name": "morning-capture", "purpose": "Rapid brain-dump of tasks, ideas, worries", "interface": "raw thoughts → timestamped inbox stream"},
        {"name": "daily-plan", "purpose": "Select 1–3 priorities from inbox + calendar", "interface": "inbox + calendar → short priority list"},
        {"name": "evening-review", "purpose": "Reflect on what moved and what carries over", "interface": "day notes → review + next-day seeds"},
        {"name": "archive-stream", "purpose": "Append the day's outputs into a durable log", "interface": "daily outputs → permanent text log"},
    ],
    "health": [
        {"name": "measure", "purpose": "Capture daily numbers as a short text stream", "interface": "raw readings → daily measure line"},
        {"name": "habit", "purpose": "Define and check off three core habits", "interface": "habit list → done/not-done checklist"},
        {"name": "review", "purpose": "Weekly summary of measurements + habit completion", "interface": "measures + habits → insight stream"},
        {"name": "adjust", "purpose": "Light next-week tweak suggestions", "interface": "weekly insight → one-line adjustment"},
    ],
    "prompt": [
        {"name": "inbox-capture", "purpose": "Accept a raw request as text", "interface": "user request → inbox item"},
        {"name": "intent-classifier", "purpose": "Classify the request into one category", "interface": "inbox item → intent tag"},
        {"name": "outline-builder", "purpose": "Produce a clean hierarchical outline", "interface": "intent + notes → outline"},
        {"name": "draft-writer", "purpose": "Expand an outline into a first draft", "interface": "outline → draft"},
        {"name": "critique-pass", "purpose": "Single-purpose critique against given criteria", "interface": "draft + criteria → critique"},
        {"name": "format-output", "purpose": "Produce the final structured text stream", "interface": "draft + critique → final text"},
    ],
    "knowledge": [
        {"name": "capture", "purpose": "Ingest raw notes, clips, and sources", "interface": "messy notes → inbox"},
        {"name": "normalize", "purpose": "Turn inbox items into atomic notes", "interface": "inbox → atomic notes"},
        {"name": "link", "purpose": "Connect notes by explicit references", "interface": "atomic notes → linked graph text"},
        {"name": "retrieve", "purpose": "Answer a query from the note stream", "interface": "query + notes → answer"},
        {"name": "daily-review", "purpose": "Surface a short review of recent notes", "interface": "recent notes → review stream"},
    ],
    "feature": [
        {"name": "research", "purpose": "Collect the smallest set of facts needed", "interface": "question → fact list"},
        {"name": "design", "purpose": "Write a one-page design with interfaces", "interface": "facts → design spec"},
        {"name": "implement", "purpose": "Build the next atomic slice", "interface": "design spec → working slice"},
        {"name": "test", "purpose": "Verify the slice against the spec", "interface": "slice + spec → pass/fail"},
        {"name": "document", "purpose": "Write the user-facing note for the slice", "interface": "slice → usage note"},
        {"name": "release", "purpose": "Ship the slice and record residuals", "interface": "slice + note → release record"},
    ],
}

_DOMAIN_HINTS: list[tuple[tuple[str, ...], str]] = [
    (("daily", "habit", "morning", "evening", "15 min", "operating system"), "daily"),
    (("health", "healthier", "sleep", "protein", "steps", "workout", "weight"), "health"),
    (("prompt", "library", "skill", "system prompt", "compose"), "prompt"),
    (("knowledge", "second brain", "notes", "zettel", "research notes"), "knowledge"),
    (("feature", "ship", "release", "implement", "sprint", "blocker"), "feature"),
]


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@dataclass
class Criterion:
    text: str
    status: str = "pending"  # pending | met | deferred | provisional
    kind: str = "binary"  # binary | numeric | longitudinal | constraint


@dataclass
class Module:
    name: str
    purpose: str
    interface: str
    status: str = "pending"  # pending | active | locked | discarded | residual
    body: str = ""
    blockers: list[str] = field(default_factory=list)
    fitness: float | None = None
    variants: list[dict[str, Any]] = field(default_factory=list)
    lineage: list[str] = field(default_factory=list)


@dataclass
class Session:
    domain: str
    phase: str = "goal"
    depth: int = 0
    cycles: int = 0
    goal_locked: bool = False
    goal_provisional: bool = False
    propose_count: int = 0
    criteria: list[Criterion] = field(default_factory=list)
    modules: list[Module] = field(default_factory=list)
    sequence: list[str] = field(default_factory=list)
    critical_path: list[str] = field(default_factory=list)
    residuals: list[str] = field(default_factory=list)
    progress_log: list[float] = field(default_factory=list)
    low_impact_streak: int = 0
    baseline: dict[str, Any] | None = None
    decision: str = "continue"
    focus: str = "Defining measurable success criteria"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def goal_progress(self) -> tuple[int, int]:
        if not self.criteria:
            return (0, 0)
        met = sum(1 for c in self.criteria if c.status in {"met", "deferred"})
        return (met, len(self.criteria))

    def goal_ratio(self) -> float:
        met, total = self.goal_progress()
        return (met / total) if total else 0.0

    def coverage(self) -> float:
        if not self.modules:
            # process coverage before modules exist
            order = {p: i for i, p in enumerate(PHASES)}
            return min(0.25, (order.get(self.phase, 0) / len(PHASES)))
        locked = sum(1 for m in self.modules if m.status == "locked")
        return locked / len(self.modules)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def default_session_path() -> Path:
    return workspace_dir() / "output" / "unix-compound-session.json"


def session_to_dict(session: Session) -> dict[str, Any]:
    data = asdict(session)
    return data


def session_from_dict(data: dict[str, Any]) -> Session:
    criteria = [Criterion(**c) for c in data.get("criteria", [])]
    modules = [Module(**m) for m in data.get("modules", [])]
    payload = dict(data)
    payload["criteria"] = criteria
    payload["modules"] = modules
    known = {f.name for f in Session.__dataclass_fields__.values()}
    return Session(**{k: v for k, v in payload.items() if k in known})


def save_session(session: Session, path: Path | None = None) -> Path:
    dest = path or default_session_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    session.updated_at = time.time()
    dest.write_text(json.dumps(session_to_dict(session), indent=2), encoding="utf-8")
    return dest


def load_session(path: Path | None = None) -> Session | None:
    src = path or default_session_path()
    if not src.exists():
        return None
    return session_from_dict(json.loads(src.read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------
# Sidecar
# ---------------------------------------------------------------------------

def _bar(ratio: float, width: int = 10) -> str:
    filled = max(0, min(width, round(ratio * width)))
    return "█" * filled + "░" * (width - filled)


def _module_mark(status: str, active_name: str, name: str) -> str:
    if name == active_name and status not in {"locked", "discarded"}:
        return STATUS_ACTIVE
    return {
        "locked": STATUS_OK,
        "active": STATUS_ACTIVE,
        "pending": STATUS_PENDING,
        "discarded": STATUS_DISCARD,
        "residual": STATUS_RESIDUAL,
    }.get(status, STATUS_PENDING)


def render_sidecar(session: Session) -> str:
    met, total = session.goal_progress()
    ratio = session.coverage()
    active = session.phase
    compact = len(session.modules) > 8

    rows: list[str] = []
    process_rows = [
        ("goal", "Propose & lock measurable success criteria", "domain → success criteria", session.goal_locked),
        ("skeleton", "Produce modular structure", "criteria → modules", bool(session.modules)),
        ("sequence", "Order + blockers", "modules → ordered list", bool(session.sequence) or (bool(session.modules) and session.phase not in {"goal", "skeleton", "sequence"})),
        ("build", "Implement next atomic module", "ordered → working module", any(m.status == "locked" for m in session.modules)),
        ("check", "QA against one-thing + goal", "module → pass/fail", any(m.status == "locked" for m in session.modules)),
        ("sidecar", "Emit terminal progress view", "state → Markdown", True),
        ("next", "Residuals + recurse/terminate", "state → decision", session.decision != "continue"),
    ]
    if compact and session.modules:
        shown = []
        locked = [m for m in session.modules if m.status == "locked"][-3:]
        shown.extend(locked)
        current = next((m for m in session.modules if m.status == "active"), None)
        if current and current not in shown:
            shown.append(current)
        pending = [m for m in session.modules if m.status == "pending"][:2]
        shown.extend(pending)
        for m in shown:
            mark = _module_mark(m.status, current.name if current else "", m.name)
            arrow = "  ← ACTIVE" if mark == STATUS_ACTIVE else ""
            name = f"**{m.name}**" if mark == STATUS_ACTIVE else m.name
            rows.append(f"| {mark} | {name} | {m.purpose} | {m.interface} |{arrow}")
    else:
        for name, purpose, interface, done in process_rows:
            if name == session.phase:
                mark = STATUS_ACTIVE
                label = f"**{name}**"
                arrow = "  ← ACTIVE"
            elif done:
                mark = STATUS_OK
                label = name
                arrow = ""
            else:
                mark = STATUS_PENDING
                label = name
                arrow = ""
            rows.append(f"| {mark} | {label} | {purpose} | {interface} |{arrow}")

    residuals = "; ".join(session.residuals) if session.residuals else "—"
    table = "\n".join(
        [
            "| S | Module | Purpose | Interface |",
            "|---|--------|---------|-----------|",
            *rows,
        ]
    )
    return (
        f"### unix-compound · sidecar\n"
        f"**Phase** {session.phase} | **Coverage** {_bar(ratio)} {int(ratio * 100)}% | **Depth** {session.depth}\n"
        f"**Active** → `{session.phase}`\n\n"
        f"{table}\n\n"
        f"**Focus** {session.focus}\n"
        f"**Goal Progress** {met}/{total}\n"
        f"**Decision** {session.decision}\n"
        f"**Residuals** {residuals}\n"
    )


def render_success_block(session: Session) -> str:
    if not session.criteria:
        return ""
    title = "locked" if session.goal_locked else "proposed"
    if session.goal_provisional and session.goal_locked:
        title = "provisional"
    lines = [f"### Success Criteria ({title})"]
    for i, c in enumerate(session.criteria, 1):
        box = "[x]" if c.status in {"met", "deferred"} else "[ ]"
        tag = f" ({c.kind})" if c.kind != "binary" else ""
        lines.append(f"{i}. {box} Done when: {c.text}{tag}")
    if not session.goal_locked:
        lines.append("→ Confirm / edit / reject?")
    else:
        met, total = session.goal_progress()
        lines.append(f"Goal Progress: {met}/{total}")
    return "\n".join(lines) + "\n"


def render_sequence_block(session: Session) -> str:
    if not session.sequence:
        return ""
    lines = ["### Sequence / Critical Path"]
    for i, name in enumerate(session.sequence, 1):
        mod = next((m for m in session.modules if m.name == name), None)
        note = ""
        if mod and mod.blockers:
            note = f"          <- blocked by {', '.join(mod.blockers)}"
        elif i == 1 and len(session.sequence) > 2:
            # first router-like module
            if "classif" in name or name.endswith("-capture") or name == "research":
                note = "          <- blocks everything after it"
        lines.append(f"{i}. {name}{note}")
    if session.critical_path:
        lines.append(f"\n**Critical path**: {' -> '.join(session.critical_path)}")
    blockers = [m for m in session.modules if m.status == "pending" and m.blockers]
    if blockers:
        items = [f"{m.name} blocked by {', '.join(m.blockers)}" for m in blockers]
        lines.append(f"**Current blockers**: {'; '.join(items)}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Heuristics
# ---------------------------------------------------------------------------

def classify_domain(domain: str) -> str:
    text = domain.lower()
    scores: dict[str, int] = {}
    for keys, label in _DOMAIN_HINTS:
        scores[label] = scores.get(label, 0) + sum(1 for k in keys if k in text)
    if not scores or max(scores.values()) == 0:
        return "generic"
    return max(scores, key=scores.get)


def extract_constraints(domain: str) -> list[Criterion]:
    found: list[Criterion] = []
    minutes = re.search(r"≤\s*(\d+)\s*min|<=\s*(\d+)\s*min|(\d+)\s*minutes", domain, re.I)
    if minutes:
        n = next(g for g in minutes.groups() if g)
        found.append(Criterion(text=f"the whole system fits in ≤{n} minutes", kind="constraint"))
    days = re.search(r"(\d+)\s*(consecutive\s+)?days", domain, re.I)
    if days:
        found.append(
            Criterion(
                text=f"ran consistently for {days.group(1)} days",
                kind="longitudinal",
                status="pending",
            )
        )
    if re.search(r"notes app|calendar|phone|cli|terminal", domain, re.I):
        found.append(Criterion(text="runs with only the tools already named in the domain", kind="constraint"))
    return found


def propose_criteria(domain: str) -> list[Criterion]:
    label = classify_domain(domain)
    constraints = extract_constraints(domain)
    catalog: dict[str, list[str]] = {
        "daily": [
            "a modular set of daily practices exists that can run in ≤15 minutes total",
            "capture, review, and planning are separate single-purpose modules that communicate via text streams",
            "the system produces a short daily text output that can be archived",
            "success is measurable by consistency (e.g. ran 5 consecutive days)",
        ],
        "health": [
            "a simple daily/weekly measurement log exists that takes ≤2 minutes to update",
            "three sustainable habits are defined with clear done-for-today checks",
            "a weekly review process shows whether the numbers are moving the right way",
            "the whole system runs with only a notes app + optional phone health data",
        ],
        "prompt": [
            "every remaining prompt/skill does exactly one thing and has a clear text in → text out interface",
            "a modular skeleton exists grouping them by purpose with explicit composition paths",
            "at least one working pipeline of 2–3 modules has been built and checked",
            "residuals (thrown-away or future prompts) are listed",
        ],
        "knowledge": [
            "raw notes can be captured as a text stream in one step",
            "notes are normalized into single-purpose atomic units",
            "a query can retrieve a short answer from the note stream",
            "a daily or weekly review stream exists",
        ],
        "feature": [
            "research, design, implement, test, document, and release are separate modules",
            "blockers and the critical path are explicit before implementation starts",
            "at least one shippable slice has been built and checked",
            "residuals for the next slice are listed",
        ],
        "generic": [
            f"the domain is decomposed into single-purpose modules that handle text streams ({domain[:80]})",
            "each module has a clear text in → text out interface",
            "at least one module has been built and checked against the goal",
            "residuals are listed and diminishing returns are respected",
        ],
    }
    texts = catalog.get(label, catalog["generic"])[:4]
    criteria = [Criterion(text=t) for t in texts]
    # merge unique constraints
    have = {c.text.lower() for c in criteria}
    for extra in constraints:
        if extra.text.lower() not in have:
            criteria.append(extra)
    if any(c.kind == "longitudinal" for c in criteria):
        for c in criteria:
            if c.kind == "longitudinal":
                c.status = "pending"
    return criteria[:5]


def propose_skeleton(session: Session) -> list[Module]:
    label = classify_domain(session.domain)
    specs = _DOMAIN_SKELETONS.get(label)
    if not specs:
        words = [w for w in re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", session.domain.lower())]
        verbs = [w for w in words if w in {
            "capture", "plan", "review", "build", "test", "ship", "write", "edit",
            "measure", "track", "sort", "tag", "search", "publish", "draft",
        }]
        if not verbs:
            verbs = ["capture", "transform", "check", "publish"]
        # Occam: 3–4
        verbs = verbs[:4]
        specs = [
            {
                "name": v if "-" in v else v,
                "purpose": f"Do {v} as a single-purpose step",
                "interface": f"{v} input → {v} output",
            }
            for v in verbs
        ]
    # apply hard time constraints immediately
    hard_time = any("minute" in c.text for c in session.criteria if c.kind == "constraint")
    if hard_time:
        specs = specs[:4]
    return [Module(name=s["name"], purpose=s["purpose"], interface=s["interface"]) for s in specs]


def derive_sequence(modules: list[Module]) -> tuple[list[str], list[str]]:
    names = [m.name for m in modules]
    if not names:
        return [], []
    # simple left-to-right with first item as router/blocker
    for i, mod in enumerate(modules):
        if i == 0 and i < len(modules) - 1:
            continue
        if i > 0:
            mod.blockers = [modules[i - 1].name]
    path = names[:]
    return names, path


def _one_thing_score(purpose: str, body: str) -> float:
    text = f"{purpose} {body}".lower()
    ands = len(re.findall(r"\band\b", text))
    commas = purpose.count(",")
    penalty = min(0.6, 0.15 * max(0, ands - 1) + 0.1 * commas)
    return max(0.2, 1.0 - penalty)


def _goal_fit(session: Session, text: str) -> float:
    if not session.criteria:
        return 0.5
    blob = text.lower()
    hits = 0
    for c in session.criteria:
        tokens = [t for t in re.findall(r"[a-z]{4,}", c.text.lower()) if t not in {
            "when", "done", "that", "this", "with", "from", "into", "have", "will",
        }]
        if any(t in blob for t in tokens[:6]):
            hits += 1
    return hits / len(session.criteria)


def vsr_build(session: Session, module: Module) -> Module:
    """Variation → Selection → Retention for one module body."""
    base = (
        f"# {module.name}\n\n"
        f"Purpose: {module.purpose}\n"
        f"Interface: {module.interface}\n\n"
        f"Contract:\n"
        f"- Input is a text stream.\n"
        f"- Output is a text stream another unknown program can consume.\n"
        f"- Does one thing. Throws away extra features.\n"
    )
    variants = [
        {
            "id": "minimal",
            "content": base + "Implementation: the shortest checklist that satisfies the interface.\n",
        },
        {
            "id": "contract-first",
            "content": base + (
                "Implementation:\n"
                "1. Validate input is text.\n"
                "2. Transform according to the purpose only.\n"
                "3. Emit the output stream. Stop.\n"
            ),
        },
        {
            "id": "bloated",
            "content": base + (
                "Implementation: also add dashboards, gamification, social sharing, "
                "and a settings panel, and rewrite the rest of the system while we are here.\n"
            ),
        },
        {
            "id": "measurable",
            "content": base + (
                "Implementation:\n"
                "- Define the done check for this module.\n"
                f"- Done when the output matches: {module.interface}.\n"
                "- Keep a one-line residual if something is out of scope.\n"
            ),
        },
    ]
    scored: list[dict[str, Any]] = []
    for v in variants:
        one = _one_thing_score(module.purpose, v["content"])
        fit = _goal_fit(session, v["content"] + " " + module.purpose)
        simple = composite_simplicity(v["content"])
        # bloat variant should lose
        if v["id"] == "bloated":
            one *= 0.4
            simple *= 0.5
        fitness = 0.40 * fit + 0.35 * one + 0.25 * simple
        scored.append({**v, "fitness": round(fitness, 4), "one_thing": one, "goal_fit": fit, "simplicity": simple})
    scored.sort(key=lambda x: (-x["fitness"], len(x["content"])))
    winner = scored[0]
    module.body = winner["content"]
    module.fitness = winner["fitness"]
    module.variants = scored
    module.lineage.append(winner["id"])
    return module


def check_module(session: Session, module: Module) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    one = _one_thing_score(module.purpose, module.body)
    if one < 0.55:
        reasons.append("fails one-thing-well (purpose is multi-job)")
    if "→" not in module.interface and "->" not in module.interface:
        reasons.append("missing text-stream interface")
    if not module.body.strip():
        reasons.append("empty body")
    hard = [c for c in session.criteria if c.kind == "constraint"]
    for c in hard:
        if "minute" in c.text and len(session.modules) > 5:
            reasons.append(f"violates resource constraint: {c.text}")
    ok = not reasons
    return ok, reasons


def baseline_oneshot(session: Session) -> dict[str, Any]:
    """Simple one-shot plan — keep this if it already meets the goal."""
    plan = (
        f"One-shot plan for: {session.domain}\n\n"
        + "\n".join(f"- {c.text}" for c in session.criteria)
        + "\n\nDo the work as a single checklist. No modules."
    )
    fit = _goal_fit(session, plan)
    simple = 1.0
    one = 0.4  # one-shot is multi-purpose by definition
    fitness = 0.40 * fit + 0.20 * one + 0.40 * simple
    locked = [m for m in session.modules if m.status == "locked" and m.fitness is not None]
    modular = sum(m.fitness or 0 for m in locked) / len(locked) if locked else 0.0
    # Prefer the simple plan only when we never needed modules.
    winner = "oneshot" if not locked else "modular"
    return {
        "plan": plan,
        "fitness": round(fitness, 4),
        "modular_fitness": round(modular, 4),
        "winner": winner,
    }


def update_goal_statuses(session: Session) -> None:
    locked_count = sum(1 for m in session.modules if m.status == "locked")
    has_skeleton = bool(session.modules)
    has_pipeline = locked_count >= 2
    for c in session.criteria:
        if c.status in {"met", "deferred"}:
            continue
        if c.kind == "longitudinal":
            c.status = "deferred"
            continue
        text = c.text.lower()
        if "decompos" in text or "modular skeleton" in text or "separate single-purpose" in text:
            if has_skeleton:
                c.status = "met"
        elif "pipeline" in text or "at least one" in text and "built" in text:
            if has_pipeline or locked_count >= 1:
                c.status = "met"
        elif "residual" in text:
            if session.residuals:
                c.status = "met"
        elif "text stream" in text or "interface" in text:
            if has_skeleton and all("→" in m.interface or "->" in m.interface for m in session.modules):
                c.status = "met"
        elif c.kind == "constraint" and "minute" in text:
            if has_skeleton and len(session.modules) <= 4:
                c.status = "met"
        elif locked_count and has_skeleton and c.kind == "binary":
            # conservative: only mark if most modules locked
            if locked_count == len(session.modules) and session.modules:
                c.status = "met"


def diminishing_returns(session: Session) -> bool:
    ratio = session.goal_ratio()
    if ratio < 0.90:
        return False
    residuals_low = not session.residuals or all(
        any(w in r.lower() for w in ("polish", "nice", "later", "optional", "micro"))
        for r in session.residuals
    )
    return residuals_low and session.low_impact_streak >= 2


# ---------------------------------------------------------------------------
# Process
# ---------------------------------------------------------------------------

def start(domain: str, *, path: Path | None = None) -> Session:
    session = Session(domain=domain.strip(), focus="Defining measurable success criteria")
    session.criteria = propose_criteria(session.domain)
    session.propose_count = 1
    session.baseline = baseline_oneshot(session)
    save_session(session, path)
    return session


def lock_goal(session: Session, *, provisional: bool = False, path: Path | None = None) -> Session:
    session.goal_locked = True
    session.goal_provisional = provisional
    for c in session.criteria:
        if provisional and c.status == "pending":
            c.status = "provisional" if c.kind != "longitudinal" else "pending"
    session.phase = "skeleton"
    session.focus = "Decomposing the domain into single-purpose modules"
    session.decision = "continue"
    save_session(session, path)
    return session


def propose_again(session: Session, *, path: Path | None = None) -> Session:
    session.propose_count += 1
    session.criteria = propose_criteria(session.domain)
    if session.propose_count >= 2:
        return lock_goal(session, provisional=True, path=path)
    save_session(session, path)
    return session


def run_skeleton(session: Session, *, path: Path | None = None) -> Session:
    if not session.goal_locked:
        raise ValueError("lock the goal before skeleton")
    session.modules = propose_skeleton(session)
    session.phase = "sequence"
    session.focus = "Ordering modules and identifying blockers"
    save_session(session, path)
    return session


def run_sequence(session: Session, *, path: Path | None = None) -> Session:
    if len(session.modules) <= 1:
        session.sequence = [m.name for m in session.modules]
        session.critical_path = session.sequence[:]
        session.phase = "build"
        session.focus = "Building the next atomic module"
        save_session(session, path)
        return session
    order, path_names = derive_sequence(session.modules)
    session.sequence = order
    session.critical_path = path_names
    session.phase = "build"
    session.focus = "Building the next atomic module"
    save_session(session, path)
    return session


def next_pending(session: Session) -> Module | None:
    order = session.sequence or [m.name for m in session.modules]
    by_name = {m.name: m for m in session.modules}
    for name in order:
        m = by_name.get(name)
        if m and m.status in {"pending", "active"}:
            # respect blockers
            if any(by_name[b].status != "locked" for b in m.blockers if b in by_name):
                continue
            return m
    return None


def run_build(session: Session, *, path: Path | None = None) -> Session:
    target = next_pending(session)
    if not target:
        session.phase = "next"
        session.focus = "No pending modules — deciding whether to stop"
        save_session(session, path)
        return session
    for m in session.modules:
        if m.status == "active":
            m.status = "pending"
    target.status = "active"
    vsr_build(session, target)
    session.phase = "check"
    session.focus = f"Checking `{target.name}` against one-thing + goal"
    save_session(session, path)
    return session


def run_check(session: Session, *, path: Path | None = None) -> Session:
    target = next((m for m in session.modules if m.status == "active"), None)
    if not target:
        session.phase = "next"
        save_session(session, path)
        return session
    ok, reasons = check_module(session, target)
    if ok:
        target.status = "locked"
        session.residuals = [r for r in session.residuals if target.name not in r]
    else:
        session.depth += 1
        if session.depth >= 3:
            target.status = "discarded"
            session.residuals.append(f"threw away {target.name}: {'; '.join(reasons)}")
        else:
            target.status = "pending"
            session.residuals.append(f"rebuild {target.name}: {'; '.join(reasons)}")
    update_goal_statuses(session)
    session.phase = "sidecar"
    session.focus = f"{'Locked' if ok else 'Failed'} `{target.name}`"
    save_session(session, path)
    return session


def run_next(session: Session, *, path: Path | None = None) -> Session:
    session.cycles += 1
    update_goal_statuses(session)
    session.baseline = baseline_oneshot(session)
    ratio = session.goal_ratio()
    prev = session.progress_log[-1] if session.progress_log else None
    session.progress_log.append(ratio)
    if prev is not None and ratio - prev < 0.05 and ratio >= 0.90:
        session.low_impact_streak += 1
    elif prev is not None and ratio <= prev + 1e-9:
        session.low_impact_streak += 1
    else:
        session.low_impact_streak = 0

    pending = next_pending(session)
    if diminishing_returns(session):
        session.decision = "terminate"
        session.phase = "next"
        session.focus = "Diminishing returns — Goal Progress ≥ 90% and residuals low-impact for 2 cycles"
    elif ratio >= 1.0 and not pending:
        session.decision = "terminate"
        session.phase = "next"
        session.focus = "All success criteria met"
    elif session.baseline and session.baseline.get("winner") == "oneshot" and ratio >= 1.0:
        session.decision = "terminate"
        session.phase = "next"
        session.focus = "Baseline one-shot already satisfies the goal — prefer simple"
    elif pending:
        session.decision = "continue"
        session.phase = "build"
        session.focus = f"Next module: `{pending.name}`"
    else:
        leftover = [m.name for m in session.modules if m.status == "pending"]
        if leftover:
            session.residuals.append("blocked modules remain: " + ", ".join(leftover))
        # Nothing left to build in this session. Remaining criteria are
        # deferred / longitudinal — stop rather than spin.
        session.decision = "terminate"
        session.phase = "next"
        session.focus = "No unblocked pending modules — session complete"
    save_session(session, path)
    return session


def step(session: Session, *, path: Path | None = None) -> Session:
    """Advance exactly one process phase."""
    if session.phase == "goal":
        if session.goal_locked:
            session.phase = "skeleton"
            return step(session, path=path)
        return session  # wait for lock
    if session.phase == "skeleton":
        return run_skeleton(session, path=path)
    if session.phase == "sequence":
        return run_sequence(session, path=path)
    if session.phase == "build":
        return run_build(session, path=path)
    if session.phase == "check":
        return run_check(session, path=path)
    if session.phase == "sidecar":
        session.phase = "next"
        session.focus = "Capturing residuals and deciding next action"
        save_session(session, path)
        return session
    if session.phase == "next":
        return run_next(session, path=path)
    return session


def run_until_idle(session: Session, *, max_steps: int = 40, path: Path | None = None) -> Session:
    """Run until the process needs a human (goal lock) or terminates."""
    steps = 0
    while steps < max_steps:
        if session.phase == "goal" and not session.goal_locked:
            break
        if session.decision == "terminate":
            break
        before = (session.phase, session.cycles, session.coverage(), session.decision)
        session = step(session, path=path)
        after = (session.phase, session.cycles, session.coverage(), session.decision)
        steps += 1
        if after == before and session.phase == "goal":
            break
    return session
