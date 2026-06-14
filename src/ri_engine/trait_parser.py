"""Parse [TRAIT:name] bullets from Retention lineage output."""

from __future__ import annotations

import re
from dataclasses import dataclass

TRAIT_LINE = re.compile(
    r"^\s*[-*•]?\s*\[TRAIT:([^\]]+)\]\s*(.+?)(?:\s*\(evidence:\s*(.+?)\))?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True)
class ParsedTrait:
    name: str
    instruction: str
    evidence: str = ""

    def normalized_name(self) -> str:
        return re.sub(r"[^a-z0-9_]+", "_", self.name.lower()).strip("_")


def parse_traits(text: str) -> list[ParsedTrait]:
    """Extract structured traits from retention lineage text."""
    if not text or not text.strip():
        return []
    traits: list[ParsedTrait] = []
    for match in TRAIT_LINE.finditer(text):
        traits.append(
            ParsedTrait(
                name=match.group(1).strip(),
                instruction=match.group(2).strip().rstrip("(").strip(),
                evidence=(match.group(3) or "").strip(),
            )
        )
    if traits:
        return traits
    # Fallback: bullet lines without strict schema
    for line in text.splitlines():
        cleaned = line.strip().lstrip("-*• ").strip()
        if len(cleaned) < 20 or cleaned.lower().startswith("#"):
            continue
        name = "learned_pattern"
        if cleaned.lower().startswith("[trait:"):
            continue
        traits.append(ParsedTrait(name=name, instruction=cleaned[:120]))
    return traits[:6]
