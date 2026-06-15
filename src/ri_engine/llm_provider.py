from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

from ri_engine.prompt_rubric import composite_prompt_score, score_task_prompt
from ri_engine.language_leanings import detect_linguistic_leaning, score_leaning_fit
from ri_engine.register_analysis import analyze_register
from ri_engine.prompt_synthesizer import _is_simple_task, extract_fields, synthesize_variant


class LLMProvider(Protocol):
    """Interface for language model backends."""

    def complete(self, system: str, user: str, temperature: float = 0.7) -> str:
        ...


class MockLLMProvider:
    """Deterministic offline provider that synthesizes structured prompt variants."""

    def complete(self, system: str, user: str, temperature: float = 0.7) -> str:
        if "VARIATION" in system or "Strategy:" in user:
            fields = extract_fields(user)
            compact = (
                fields.get("strategy") == "minimal_essential"
                or _is_simple_task(fields.get("parent", ""), fields.get("objective", ""))
            )
            return synthesize_variant(user, compact=compact)
        if "SELECT" in system or "Score each candidate" in user:
            return self._score(user)
        if "MEMBRANE" in system or "cross-domain" in user.lower():
            return self._bridge(user)
        if "RETENTION" in system or "Synthesize" in user:
            return self._synthesize(user)
        return user.split("\n")[-1][:500]

    @staticmethod
    def _extract_objective(user: str) -> str:
        m = re.search(r"Objective:\s*(.+?)(?:\nDomains|\nFitness|\nScore|\n##|\Z)", user, re.S)
        return m.group(1).strip() if m else ""

    def _score(self, user: str) -> str:
        blocks = re.findall(r"---CANDIDATE (\d+)---\s*(.*?)(?=---CANDIDATE|\Z)", user, re.S)
        lines = []
        objective = self._extract_objective(user)
        for cid, body in blocks:
            content = body.strip()
            rubric = score_task_prompt(content)
            reg = analyze_register(content)
            leaning = detect_linguistic_leaning(user)
            align = composite_prompt_score(content, objective, leaning=leaning)["objective_alignment"]
            reg_fit = composite_prompt_score(content, objective, leaning=leaning)["register_fit"]
            clarity = 0.5 + rubric.dimensions.get("specificity", 0) * 0.3 + rubric.dimensions.get("structure", 0) * 0.2
            novelty = 0.45 + (hash(body) % 15) / 100
            utility = 0.4 + rubric.dimensions.get("feature_coverage", 0) * 0.5
            coherence = 0.5 + rubric.dimensions.get("length", 0) * 0.2 + rubric.total * 0.3

            fit = score_leaning_fit(leaning, rubric.total, reg)
            boost = (fit - 0.5) * 0.15
            clarity = min(0.98, clarity + boost)
            utility = min(0.98, utility + boost * 0.8)
            coherence = min(0.98, coherence + boost * 0.6)

            if leaning == "latinate":
                novelty = min(0.75, novelty + reg.latinate_ratio * 0.05)
            elif leaning in ("plain", "conversational"):
                clarity = min(0.98, clarity + (1 - reg.latinate_ratio) * 0.08 + reg.readability_score * 0.06)
                utility = min(0.98, utility + reg.readability_score * 0.08)
            elif leaning == "mixed":
                mid = 1.0 - abs(reg.latinate_ratio - 0.45)
                utility = min(0.98, utility + max(0.0, mid) * 0.06)
            elif leaning == "technical":
                utility = min(0.98, utility + reg.latinate_ratio * 0.05 + min(0.05, reg.avg_word_length * 0.008))
            lines.append(
                f"CANDIDATE {cid}: clarity={min(clarity, 0.98):.2f}, "
                f"novelty={min(novelty, 0.98):.2f}, utility={min(utility, 0.98):.2f}, "
                f"coherence={min(coherence, 0.98):.2f}, "
                f"objective_alignment={align:.2f}, register_fit={reg_fit:.2f}"
            )
        return "\n".join(lines) if lines else "CANDIDATE 0: clarity=0.7, novelty=0.6, utility=0.7, coherence=0.75"

    def _bridge(self, user: str) -> str:
        if "review" in user.lower() or "code" in user.lower():
            return (
                "CORRELATION: code review ↔ immune system | STRUCTURE: clonal selection under antigen pressure | "
                "MUTATION: generate counter-arguments (adversarial test cases) for each approved pattern before finalizing review."
            )
        if "support" in user.lower():
            return (
                "CORRELATION: support triage ↔ emergency medicine | STRUCTURE: golden hour + differential diagnosis | "
                "MUTATION: classify issue severity first, then apply protocol — never start with generic empathy."
            )
        if "security" in user.lower():
            return (
                "CORRELATION: incident response ↔ epidemiology | STRUCTURE: R0 modeling + containment rings | "
                "MUTATION: map blast radius before deep analysis — contain first, investigate second."
            )
        if "sales" in user.lower():
            return (
                "CORRELATION: cold outreach ↔ mate selection signals | STRUCTURE: costly signaling vs display | "
                "MUTATION: lead with costly signal (specific research about them), not display (product features)."
            )
        if "research" in user.lower():
            return (
                "CORRELATION: Jacquard loom ↔ binary programmability | STRUCTURE: stored program separate from hardware | "
                "MUTATION: treat each research claim as a punch card — independently verifiable, composable into larger patterns."
            )
        if "coding" in user.lower():
            return (
                "CORRELATION: JIT manufacturing ↔ minimal diffs | STRUCTURE: produce only what's needed, when needed | "
                "MUTATION: every line in the diff must justify its existence — if removing it doesn't break tests, remove it."
            )
        return (
            "Latent correlation: programmable iteration (Jacquard loom ↔ software loops). "
            "Apply: treat each prompt generation as a stored program card. "
            "Selection pressure should optimize downstream task fitness, not engagement proxies."
        )

    def _synthesize(self, user: str) -> str:
        return (
            "- [TRAIT:constraint_first] Lead with hard constraints and measurable success criteria (evidence: high utility)\n"
            "- [TRAIT:failure_mode_guards] Block proxy optimization and format drift (evidence: selection survival)\n"
            "- [TRAIT:recursive_self_eval] Embed self-scoring rubric before output (evidence: next iteration hook)\n"
            "- [TRAIT:measurable_outcomes] Define quantifiable deliverables (evidence: downstream actionable)"
        )


class OpenAIProvider:
    """OpenAI API provider."""

    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError("Install with: pip install recursive-intelligence[openai]") from exc

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def complete(self, system: str, user: str, temperature: float = 0.7) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content or ""


class AnthropicProvider:
    """Anthropic API provider."""

    def __init__(self, model: str = "claude-sonnet-4-20250514", api_key: str | None = None):
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError("Install with: pip install recursive-intelligence[anthropic]") from exc

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def complete(self, system: str, user: str, temperature: float = 0.7) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
            temperature=temperature,
        )
        return response.content[0].text


def load_prompt(name: str) -> str:
    """Load a prompt template from the prompts directory."""
    from ri_engine.paths import prompts_dir

    base = prompts_dir() / f"{name}.md"
    if base.exists():
        return base.read_text(encoding="utf-8")
    fallback = prompts_dir() / f"{name}.txt"
    return fallback.read_text(encoding="utf-8") if fallback.exists() else ""


def create_provider(name: str = "mock", **kwargs: object) -> LLMProvider:
    """Factory for LLM providers."""
    if name == "mock":
        return MockLLMProvider()
    if name == "openai":
        return OpenAIProvider(**kwargs)  # type: ignore[arg-type]
    if name == "anthropic":
        return AnthropicProvider(**kwargs)  # type: ignore[arg-type]
    raise ValueError(f"Unknown provider: {name}")
