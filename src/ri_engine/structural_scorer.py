"""
Structural Quality Scorer — rubric-based fitness that rewards substance over bloat.

Diagnoses why hash-based mock scoring plateaus and enables substantial gains by
measuring operator-specific completeness, recursive hooks, and non-redundancy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ri_engine.system_prompt_evolver import TRANSFORMS, _has_section, _strip_generated_sections


@dataclass
class RubricResult:
    total: float
    dimensions: dict[str, float] = field(default_factory=dict)
    gaps: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


# Operator-specific required signals (beyond generic trait sections)
OPERATOR_REQUIREMENTS: dict[str, list[str]] = {
    "variation.md": [
        (r"recursive hook|next iteration|self-eval", "recursive hook for next iteration"),
        (r"programmability|stored program|software", "programmability metaphor"),
        (r"strategy|constraint_first|adversarial", "named variation strategies"),
        (r"Return ONLY|Output ONLY|output format", "strict output contract"),
        (r"proxy optimization|engagement", "anti-proxy optimization guard"),
    ],
    "selection.md": [
        (r"clarity.*novelty.*utility|fitness dimension", "multi-dimensional fitness rubric"),
        (r"CANDIDATE \d+:|0\.0–1\.0|0\.0-1\.0", "parseable score output format"),
        (r"dating app|engagement|proxy", "optimization mismatch awareness"),
        (r"penalize|anti-pattern", "explicit anti-patterns"),
        (r"wisdom under pressure|not selecting for speed", "selection environment integrity"),
    ],
    "retention.md": [
        (r"lineage|heritable|genetic memory", "lineage memory concept"),
        (r"Retention ≠ copying|not verbatim", "trait extraction not copying"),
        (r"bullet points|3–6|3-6", "structured bullet output format"),
        (r"Variation engine|next generation", "downstream consumer specified"),
        (r"Amplify winners|Prune losers", "explicit amplify/prune logic"),
    ],
    "membrane_bridge.md": [
        (r"Jacquard|binary|loom", "cross-domain correlation example"),
        (r"deep structure|latent|vector", "structural not surface correlation"),
        (r"2–4 sentences|2-4 sentences|Actionable", "concise actionable output"),
        (r"mutation pressure|Variation engine", "downstream mutation pressure"),
        (r"domain coordinates|adjacent", "domain membrane dissolution"),
    ],
    "meta_improvement.md": [
        (r"fitness_weights|fitness function", "fitness function adjustability"),
        (r"meta_generation|diagnosis", "structured YAML/meta output"),
        (r"convergence|plateau|local optimum", "convergence diagnosis"),
        (r"population_size|variation pressure", "evolution parameter control"),
        (r"optimization mismatch|proxy", "proxy optimization detection"),
    ],
}

# Tier-2 operator-specific extensions (substantial gains beyond generic traits)
OPERATOR_EXTENSIONS: dict[str, tuple[str, str, str]] = {
    "variation.md": (
        "mutation_protocol",
        "Mutation Protocol",
        """\
For each variant you produce:
1. **Identify parent coordinate** — which strategy axis are you exploring?
2. **Apply mutation** — structural change, not synonym swap
3. **Embed recursive hook** — include `<!-- RI-EVAL: rubric -->` block or explicit self-score instructions
4. **Validate** — output must be ≥20 chars, executable by an agent, and scorable by Selection

Mandatory variant anatomy:
- Objective anchor (1 line)
- Hard constraints (≥2)
- Execution steps (≥3)
- Self-evaluation rubric (≥3 dimensions)
- Output format (exact)""",
    ),
    "selection.md": (
        "cull_decision_rules",
        "Cull Decision Rules",
        """\
Apply these rules in order:
1. **Hard cull**: missing output format, conflicting goals, or engagement-bait language
2. **Soft penalty**: vague objectives (−0.15 utility), missing recursive hook (−0.20 utility)
3. **Tie-break**: prefer shorter prompt at equal fitness (Occam's razor under selection pressure)
4. **Diversity bonus**: +0.05 novelty if structurally distinct from siblings, not just word-different

Never inflate scores — compression toward 0.5 means "uncertain", not "average".""",
    ),
    "retention.md": (
        "lineage_encoding_spec",
        "Lineage Encoding Spec",
        """\
Each bullet in your output MUST follow this schema:
`- [TRAIT:<strategy_name>] <imperative instruction ≤15 words> (evidence: <why it scored high>)`

Example:
- [TRAIT:constraint_first] Lead with measurable success criteria (evidence: utility=0.92)

Maximum 6 bullets. No prose paragraphs. Traits must be heritable by Variation.""",
    ),
    "membrane_bridge.md": (
        "correlation_template",
        "Correlation Template",
        """\
Fill this template exactly:
`CORRELATION: <domain_A> ↔ <domain_B> | STRUCTURE: <shared abstraction> | MUTATION: <specific prompt change>`

Example:
`CORRELATION: immune system ↔ agent selection | STRUCTURE: clonal selection under pressure | MUTATION: generate 3 counter-arguments before final output`

One correlation per invocation. Must be non-obvious (not "both use data").""",
    ),
    "meta_improvement.md": (
        "plateau_breakers",
        "Plateau Breakers",
        """\
When fitness plateaus, diagnose which ceiling is binding:
1. **Scoring ceiling** — mock/hash fitness vs rubric fitness diverge → switch scorer
2. **Trait ceiling** — all 8 generic traits applied → add operator-specific tier-2 extensions
3. **Redundancy ceiling** — more sections = lower hash score → optimize subset, penalize bloat
4. **LLM ceiling** — offline transforms exhaust → enable OpenAI/Anthropic provider
5. **Task ceiling** — optimizing prompts, not outcomes → add downstream task benchmark

Recommend the highest-leverage breaker first.""",
    ),
}


def score_prompt(content: str, operator: str) -> RubricResult:
    """Score a prompt on structural quality (0.0–1.0)."""
    clean = _strip_generated_sections(content)
    dims: dict[str, float] = {}
    gaps: list[str] = []
    recs: list[str] = []

    # 1. Operator requirement coverage (40%)
    reqs = OPERATOR_REQUIREMENTS.get(operator, [])
    req_hits = sum(1 for pattern, _ in reqs if re.search(pattern, content, re.I | re.S))
    req_score = req_hits / max(len(reqs), 1)
    dims["operator_requirements"] = req_score
    for pattern, label in reqs:
        if not re.search(pattern, content, re.I | re.S):
            gaps.append(f"Missing: {label}")

    # 2. Generic trait coverage — optimal subset, not max (20%)
    trait_count = sum(1 for t in TRANSFORMS if _has_section(content, t.section_title))
    # Peak at 4-5 traits; penalize bloat beyond 6
    if trait_count <= 6:
        trait_score = min(trait_count / 5.0, 1.0)
    else:
        trait_score = max(0.5, 1.0 - (trait_count - 6) * 0.1)
    dims["trait_optimization"] = trait_score
    if trait_count > 6:
        recs.append(f"Reduce traits from {trait_count} to 4-5 highest-signal sections (redundancy penalty)")

    # 3. Tier-2 operator extension present (20%)
    ext = OPERATOR_EXTENSIONS.get(operator)
    ext_score = 0.0
    if ext:
        _, title, _ = ext
        ext_score = 1.0 if _has_section(content, title) else 0.0
        if not ext_score:
            gaps.append(f"Missing tier-2 extension: {title}")
            recs.append(f"Add operator-specific section: ## {title}")
    dims["tier2_extension"] = ext_score

    # 4. Non-redundancy — penalize duplicate concepts (10%)
    redundancy_penalty = _redundancy_penalty(content)
    dims["non_redundancy"] = max(0.0, 1.0 - redundancy_penalty)
    if redundancy_penalty > 0.2:
        recs.append("Consolidate duplicate sections (Failure Modes + Pre-execution overlap)")

    # 5. Length efficiency — not too short, not bloated (10%)
    length = len(clean)
    if length < 800:
        len_score = length / 800
        gaps.append("Prompt too sparse for reliable agent execution")
    elif length > 4500:
        len_score = max(0.4, 1.0 - (length - 4500) / 3000)
        recs.append(f"Compress prompt ({length} chars) — bloat reduces clarity")
    else:
        len_score = 1.0
    dims["length_efficiency"] = len_score

    weights = {
        "operator_requirements": 0.40,
        "trait_optimization": 0.20,
        "tier2_extension": 0.20,
        "non_redundancy": 0.10,
        "length_efficiency": 0.10,
    }
    total = sum(dims[k] * w for k, w in weights.items())

    return RubricResult(total=total, dimensions=dims, gaps=gaps, recommendations=recs)


def _redundancy_penalty(content: str) -> float:
    """Detect overlapping generic sections."""
    overlap_pairs = [
        ("Failure Modes to Block", "Pre-execution Check"),
        ("Self-Evaluation Rubric", "Success Metrics"),
        ("Core Directive", "Output Contract"),
        ("Structural Analog", "Cross-Operator Coordination"),
    ]
    penalty = 0.0
    for a, b in overlap_pairs:
        if _has_section(content, a) and _has_section(content, b):
            penalty += 0.15
    return min(penalty, 0.6)


def apply_extension(content: str, operator: str) -> str:
    """Apply tier-2 operator-specific extension if missing."""
    ext = OPERATOR_EXTENSIONS.get(operator)
    if not ext or _has_section(content, ext[1]):
        return content
    _, title, body = ext
    block = f"\n\n## {title}\n\n{body.strip()}\n"
    for header in ("## Output format", "## Output Format", "## Output"):
        idx = content.find(header)
        if idx != -1:
            return content[:idx].rstrip() + block + "\n\n" + content[idx:]
    return content.rstrip() + block + "\n"


def diagnose_all(prompts_dir: str) -> dict:
    """Run meta-diagnosis on all operator prompts."""
    from pathlib import Path

    results = {}
    for path in sorted(Path(prompts_dir).glob("*.md")):
        content = path.read_text(encoding="utf-8")
        rubric = score_prompt(content, path.name)
        results[path.name] = {
            "structural_score": rubric.total,
            "dimensions": rubric.dimensions,
            "gaps": rubric.gaps,
            "recommendations": rubric.recommendations,
            "chars": len(content),
            "trait_count": sum(1 for t in TRANSFORMS if _has_section(content, t.section_title)),
        }
    return results
