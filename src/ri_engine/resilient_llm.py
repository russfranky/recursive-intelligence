from __future__ import annotations

import time

from ri_engine.events import EventKind, RunEvent
from ri_engine.observer import NullObserver, RunObserver


class ResilientLLMProvider:
    """Wraps an LLM provider with retry logic and event emission."""

    def __init__(
        self,
        inner: object,
        observer: RunObserver | None = None,
        max_retries: int = 3,
        base_delay: float = 0.15,
        simulate_failures: bool = False,
    ):
        self.inner = inner
        self.observer = observer or NullObserver()
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.simulate_failures = simulate_failures
        self._call_count = 0

    def complete(self, system: str, user: str, temperature: float = 0.7) -> str:
        self._call_count += 1
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            if self.simulate_failures and self._should_simulate_failure(attempt):
                self._emit(
                    EventKind.ERROR,
                    f"LLM timeout on attempt {attempt}/{self.max_retries}",
                    {"attempt": attempt, "operator": self._operator(system, user)},
                )
                last_error = TimeoutError("simulated LLM timeout")
                if attempt < self.max_retries:
                    self._emit(
                        EventKind.RETRY,
                        f"retrying in {self.base_delay * attempt:.1f}s…",
                        {"attempt": attempt + 1},
                    )
                    time.sleep(self.base_delay * attempt)
                    continue
                # Final attempt after simulated failures: fall through to real call

            try:
                result = self.inner.complete(system, user, temperature)
                if not result or not result.strip():
                    raise ValueError("empty LLM response")
                return result
            except Exception as exc:
                last_error = exc
                self._emit(
                    EventKind.ERROR,
                    f"{type(exc).__name__}: {exc}",
                    {"attempt": attempt},
                )
                if attempt < self.max_retries:
                    self._emit(
                        EventKind.RETRY,
                        f"retry {attempt + 1}/{self.max_retries} after {type(exc).__name__}",
                        {"attempt": attempt + 1, "delay": self.base_delay * attempt},
                    )
                    time.sleep(self.base_delay * attempt)

        raise RuntimeError(f"LLM failed after {self.max_retries} retries") from last_error

    def _should_simulate_failure(self, attempt: int) -> bool:
        # Fail early attempts on every 7th call to demo retry visuals
        return self._call_count % 7 == 3 and attempt < self.max_retries

    @staticmethod
    def _operator(system: str, user: str) -> str:
        if "VARIATION" in system:
            return "variation"
        if "SELECTION" in system:
            return "selection"
        if "RETENTION" in system:
            return "retention"
        if "MEMBRANE" in system:
            return "membrane"
        return "llm"

    def _emit(self, kind: EventKind, message: str, data: dict | None = None) -> None:
        self.observer.on_event(RunEvent(kind=kind, message=message, data=data or {}))


def wrap_provider(
    provider: object,
    observer: RunObserver | None = None,
    simulate_failures: bool = False,
) -> ResilientLLMProvider:
    return ResilientLLMProvider(
        provider,
        observer=observer,
        simulate_failures=simulate_failures,
    )
