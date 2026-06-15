from __future__ import annotations

from ri_engine.events import EventKind, RunEvent
from ri_engine.llm_provider import LLMProvider, load_prompt
from ri_engine.models import RunConfig
from ri_engine.observer import NullObserver, RunObserver


class MembraneBridge:
    """Dissolve the interdisciplinary membrane via cross-domain correlation."""

    SYSTEM = load_prompt("membrane_bridge") or (
        "You are the MEMBRANE BRIDGE operator. Find non-obvious structural correlations "
        "between domains and translate them into prompt-engineering insight."
    )

    def __init__(self, llm: LLMProvider, observer: RunObserver | None = None):
        self.llm = llm
        self.observer = observer or NullObserver()

    def discover_correlation(
        self,
        config: RunConfig,
        current_best: str,
        generation: int = 0,
    ) -> str:
        domains = config.domains or [
            "biology (Darwinian selection)",
            "software (iterative loops)",
            "systems theory",
            "cognitive science",
        ]

        self.observer.on_event(
            RunEvent(
                kind=EventKind.AGENT_TASK,
                message="scanning domain coordinates for latent correlation",
                generation=generation,
                phase="membrane",
                data={"agent": "MembraneBridge", "task": "membrane dissolution", "domains": domains},
            )
        )

        user = f"""# Membrane Dissolution — Cross-Domain Correlation
Objective: {config.objective}

Current best prompt:
{current_best}

Available domain coordinates: {", ".join(domains)}

Task:
1. Find ONE latent structural correlation between two+ domains (like Jacquard loom ↔ binary programmability).
2. Translate that correlation into a concrete prompt-improvement insight.
3. Keep it actionable for the Variation engine in the next generation.

Output 2–4 sentences. No preamble."""

        return self.llm.complete(self.SYSTEM, user, temperature=0.8).strip()
