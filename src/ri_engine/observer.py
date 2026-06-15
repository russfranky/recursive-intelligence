from __future__ import annotations

from typing import Protocol

from ri_engine.events import RunEvent


class RunObserver(Protocol):
    def on_event(self, event: RunEvent) -> None:
        ...


class NullObserver:
    def on_event(self, event: RunEvent) -> None:
        pass


class EventCollector:
    """Collects events for testing and reporting."""

    def __init__(self) -> None:
        self.events: list[RunEvent] = []

    def on_event(self, event: RunEvent) -> None:
        self.events.append(event)

    def of_kind(self, kind: str) -> list[RunEvent]:
        return [e for e in self.events if e.kind.value == kind]
