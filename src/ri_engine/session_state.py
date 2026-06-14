"""Persist improvement sessions for --continue across runs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SESSION_PATH = ROOT / "output" / "improvement_session.json"


@dataclass
class ImprovementSession:
    """Saved state between plateau cycles or CLI invocations."""

    original_seed: str
    objective: str
    current_prompt: str
    template: str = ""
    cycle: int = 0
    max_cycles: int = 10
    fitness_history: list[float] = field(default_factory=list)
    plateaued: bool = False
    last_fitness: float = 0.0
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImprovementSession:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def save_session(session: ImprovementSession, path: Path | str | None = None) -> Path:
    out = Path(path) if path else DEFAULT_SESSION_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    session.updated_at = datetime.now(timezone.utc).isoformat()
    out.write_text(json.dumps(session.to_dict(), indent=2), encoding="utf-8")
    return out


def load_session(path: Path | str | None = None) -> ImprovementSession | None:
    p = Path(path) if path else DEFAULT_SESSION_PATH
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    return ImprovementSession.from_dict(data)


def clear_session(path: Path | str | None = None) -> None:
    p = Path(path) if path else DEFAULT_SESSION_PATH
    if p.exists():
        p.unlink()
