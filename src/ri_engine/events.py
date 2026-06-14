from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EventKind(str, Enum):
    RUN_START = "run_start"
    RUN_COMPLETE = "run_complete"
    GENERATION_START = "generation_start"
    GENERATION_COMPLETE = "generation_complete"
    PHASE_START = "phase_start"
    PHASE_COMPLETE = "phase_complete"
    AGENT_TASK = "agent_task"
    VARIANT_SPAWN = "variant_spawn"
    VARIANT_COMPLETE = "variant_complete"
    VARIANT_FALLBACK = "variant_fallback"
    SCORE = "score"
    ELIMINATE = "eliminate"
    SURVIVE = "survive"
    LEARNING = "learning"
    MEMBRANE = "membrane"
    RETRY = "retry"
    ERROR = "error"
    WARNING = "warning"
    CONVERGENCE = "convergence"
    INFO = "info"


@dataclass
class RunEvent:
    kind: EventKind
    message: str
    generation: int = 0
    phase: str = ""
    progress: float | None = None
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def time_str(self) -> str:
        return self.timestamp.strftime("%H:%M:%S")
