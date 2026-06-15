"""
Structured prompt synthesizer for offline evolution demos.

Generates production-grade prompt variants from strategy + seed + objective,
enabling the benchmark to prove value without an external LLM.
"""

from __future__ import annotations

import re

from ri_engine.language_leanings import LEANING_BLOCKS, detect_linguistic_leaning, leaning_clause
from ri_engine.register_analysis import translate_to_latinate, translate_to_plain


STRATEGY_BLOCKS: dict[str, str] = {
    "constraint_first": """\
## Hard Constraints
- Follow the output format exactly — no preamble
- Optimize for task completion, NOT engagement or verbosity
- If input is ambiguous, state assumptions in ≤2 lines, then proceed""",

    "adversarial_critique": """\
## Pre-execution Self-Critique
Before responding, challenge your draft:
1. What is the weakest part of this output?
2. What proxy metric might this accidentally optimize for?
3. What would cause Selection to cull this?
Revise once to address the top issue.""",

    "cross_domain_metaphor": """\
## Structural Analog
Treat your operation as a control-system feedback loop:
- **Sensor**: read input state accurately
- **Controller**: apply domain logic
- **Actuator**: produce structured output
- **Feedback**: output becomes input for the next iteration""",

    "minimal_essential": """\
## Core Directive
Maximum signal, minimum noise. One pass. One format. No hedging.""",

    "recursive_self_eval": """\
## Self-Evaluation Rubric
Before finalizing, score yourself 0.0–1.0 on clarity, utility, and coherence.
If any score < 0.7, revise once before responding.""",

    "failure_mode_guards": """\
## Failure Modes to Block
- **Proxy optimization**: selecting for engagement/length over task fitness
- **Format drift**: deviating from specified output structure
- **Missing recursive hook**: output cannot be evaluated by next iteration
- **Safety theater**: vague guardrails without enforceable constraints""",

    "measurable_outcomes": """\
## Success Metrics
Your output succeeds when:
- Format matches specification exactly
- Every required field is present
- Downstream agent/team can act without clarification
- Next iteration can score improvement from your output""",

    "membrane_dissolution": """\
## Cross-Domain Insight
Apply non-obvious structural correlations from adjacent fields.
Do not stay in disciplinary lanes — find the deep structure shared across domains.""",
}


def extract_fields(user: str) -> dict[str, str]:
    """Parse variation pass user prompt."""
    fields: dict[str, str] = {}
    for key, pattern in [
        ("strategy", r"Strategy:\s*(\S+)"),
        ("objective", r"Objective:\s*(.+?)(?:\nDomains|\n##)"),
        ("generation", r"Generation:\s*(\d+)"),
    ]:
        m = re.search(pattern, user, re.S)
        if m:
            fields[key] = m.group(1).strip()

    parent_match = re.search(r"## Parent Prompt\n(.+?)(?:\n## |\Z)", user, re.S)
    fields["parent"] = parent_match.group(1).strip() if parent_match else ""

    membrane_match = re.search(r"## Membrane Bridge Insight.*?\n(.+?)(?:\n## |\Z)", user, re.S)
    fields["membrane"] = membrane_match.group(1).strip() if membrane_match else ""

    return fields


def _seed_title(seed: str) -> str:
    """First markdown heading or opening phrase — for length heuristics."""
    stripped = seed.strip()
    if not stripped:
        return seed
    lines = [ln.strip() for ln in stripped.splitlines() if ln.strip()]
    if lines and lines[0].startswith("#"):
        return lines[0].lstrip("#").strip()
    return " ".join(stripped.split()[:8])


def _condensed_seed(seed: str) -> str:
    """Title + first paragraph for context heuristics when seed is a long doc."""
    stripped = seed.strip()
    if not stripped:
        return seed
    lines = [ln.strip() for ln in stripped.splitlines() if ln.strip()]
    if not lines:
        return seed
    title = _seed_title(seed)
    if not lines[0].startswith("#"):
        return title
    for ln in lines[1:]:
        if ln.startswith("#"):
            break
        if ln.startswith("```") or ln.startswith("|") or ln.startswith("-"):
            continue
        return f"{title} {ln}".strip() or title
    return title


def _is_code_review_context(obj: str, role_l: str) -> bool:
    text = f"{obj} {role_l}"
    if any(
        marker in text
        for marker in (
            "code review",
            "pull request",
            "pr review",
            "reviewer",
            "merge request",
            "code reviewer",
        )
    ):
        return True
    return "review" in obj and any(x in obj for x in ("pull", " pr ", "merge", "codebase", "lint"))


def _is_research_task(obj: str, role_l: str) -> bool:
    if re.search(r"research before (editing|implement|coding|building|changing)", obj):
        return False
    text = f"{obj} {role_l}"
    if "research analyst" in text:
        return True
    if "research" in role_l:
        return True
    return "research" in obj and any(x in text for x in ("claims", "falsifiable", "cross-domain", "analyst"))


def _is_coding_task(obj: str, role_l: str) -> bool:
    text = f"{obj} {role_l}"
    return any(
        marker in text
        for marker in (
            "claude code",
            "coding assistant",
            "ai coding",
            "implement",
            "minimal diff",
            "before editing",
        )
    ) or "coding" in obj or "coding" in role_l


def infer_role(parent: str, objective: str) -> str:
    """Infer agent role title from seed/objective."""
    for pattern in [
        r"You are (?:a |an )?(.+?)[\.\n]",
        r"^#\s*(.+?)(?:\n|$)",
    ]:
        m = re.search(pattern, parent, re.I | re.M)
        if m:
            return m.group(1).strip().title()
    obj = objective.lower()
    role_hint = _condensed_seed(parent).lower()
    if _is_code_review_context(obj, role_hint):
        return "Code Review Agent"
    if "support" in obj:
        return "Customer Support Agent"
    if "security" in obj or "incident" in obj:
        return "Security Incident Response Agent"
    if "sales" in obj or "outreach" in obj:
        return "Sales Outreach Agent"
    if _is_coding_task(obj, role_hint):
        return "AI Coding Assistant"
    if _is_research_task(obj, role_hint):
        return "Research Analyst Agent"
    return "Task Agent"


def infer_process_steps(role: str, objective: str) -> str:
    """Generate role-specific process steps."""
    obj = objective.lower()
    role_l = role.lower()
    if _is_code_review_context(obj, role_l):
        return """\
## Review Protocol
1. **Scope**: identify changed files and blast radius
2. **Security**: check OWASP top 10, injection, auth, secrets exposure
3. **Logic**: verify edge cases, error handling, race conditions
4. **Tests**: confirm tests exist and cover the change
5. **Severity**: rate each finding P0 (block) / P1 (fix before merge) / P2 (should fix) / P3 (nit)
6. **Self-eval**: score completeness 0.0–1.0 before submitting"""
    if "support" in obj or "support" in role_l:
        return """\
## Resolution Protocol
1. **Triage**: classify issue (billing / technical / account / abuse)
2. **Diagnose**: ask ≤2 clarifying questions if needed, never more
3. **Resolve**: provide exact steps with knowledge base citations
4. **Escalate**: if billing dispute, legal threat, or abuse → escalate immediately
5. **Verify**: confirm issue resolved, not just acknowledged
6. **Self-eval**: success = customer can proceed without follow-up"""
    if "security" in obj or "incident" in obj or "security" in role_l:
        return """\
## Incident Response Protocol
1. **Classify**: severity P0-P3, true positive assessment with confidence %
2. **MITRE ATT&CK**: map to specific techniques (Txxxx)
3. **Contain**: immediate isolation steps in priority order
4. **Evidence**: preserve chain of custody, log all artifacts
5. **Escalate**: P0/P1 → page on-call within 5 minutes
6. **Self-eval**: is SOC team able to act on this without clarification?"""
    if "sales" in obj or "outreach" in obj or "sales" in role_l:
        return """\
## Outreach Protocol
1. **Research**: extract 1 specific signal from prospect (not generic praise)
2. **Hook**: lead with their problem, not your product (≤25 words)
3. **Value**: one concrete outcome, quantified if possible
4. **CTA**: single clear ask (15-min call, not "let me know")
5. **Constraints**: ≤120 words body, no spam trigger words
6. **Self-eval**: score for reply probability, not send volume"""
    if _is_coding_task(obj, role_l):
        return """\
## Coding Protocol
1. **Read first**: understand existing code before editing
2. **Minimal diff**: change only what's required, match conventions
3. **Test**: run relevant tests after every change
4. **Retry**: on failure, diagnose and retry up to 3 times
5. **Commit**: clear message explaining why, not what
6. **Self-eval**: is the diff the smallest correct solution?"""
    if _is_research_task(obj, role_l):
        return """\
## Research Protocol
1. **Decompose**: break topic into 3-5 falsifiable sub-claims
2. **Cross-domain**: find ≥1 non-obvious correlation across 2+ fields
3. **Evidence**: cite sources, assign confidence 0.0–1.0 per claim
4. **Predictions**: include ≥1 testable prediction
5. **Gaps**: explicit open questions for next iteration
6. **Self-eval**: would a skeptical expert find this actionable?"""
    return """\
## Execution Protocol
1. Parse input and state assumptions if ambiguous
2. Execute against the stated objective with measurable output
3. Self-evaluate before responding
4. Output in the specified format only"""


def infer_output_format(role: str, objective: str) -> str:
    obj = objective.lower()
    role_l = role.lower()
    if _is_code_review_context(obj, role_l):
        return """\
## Output Format
```markdown
## Summary
[1-2 sentences: merge recommendation block/approve/comment]

## Findings
| Severity | File:Line | Issue | Fix |
|----------|-----------|-------|-----|
| P0-P3    | path:NN   | ...   | ... |

## Self-Score
clarity=X, utility=X, completeness=X
```"""
    if "support" in obj:
        return """\
## Output Format
Return:
1. **Resolution** (exact steps)
2. **Escalation** (yes/no + reason)
3. **Sources cited**
4. **Self-score**: resolution_confidence=0.X"""
    if "security" in obj or "incident" in obj or "security" in role_l:
        return """\
## Output Format
```
SEVERITY: P0|P1|P2|P3
CONFIDENCE: 0.0-1.0
MITRE: Txxxx - technique name
CONTAINMENT: [ordered steps]
EVIDENCE: [artifacts to preserve]
ESCALATE: yes|no
```"""
    if "sales" in obj or "outreach" in obj or "sales" in role_l:
        return """\
## Output Format
```
SUBJECT: [≤8 words, no spam triggers]
BODY: [≤120 words]
CTA: [single ask]
SELF_SCORE: reply_probability=0.X, spam_risk=0.X
```"""
    if _is_coding_task(obj, role_l):
        return """\
## Output Format
1. Brief plan (≤3 bullets)
2. Code changes (minimal diff)
3. Test commands run + results
4. Self-score: correctness=X, minimalism=X"""
    if _is_research_task(obj, role_l):
        return """\
## Output Format
```markdown
## Claims
| Claim | Confidence | Evidence |
|-------|-----------|----------|

## Cross-Domain Bridge
[domain A ↔ domain B: shared structure]

## Predictions
1. [falsifiable prediction]

## Open Questions
- [for next iteration]
```"""
    return "## Output Format\nReturn structured response matching the objective. No preamble."


def _detect_register(objective: str) -> str:
    """Backward-compatible alias for linguistic leaning detection."""
    return detect_linguistic_leaning(objective)


def _leaning_block(leaning: str) -> str:
    return LEANING_BLOCKS.get(leaning, LEANING_BLOCKS["plain"])


def _objective_has_leaning_clause(text: str) -> bool:
    return "mandatory linguistic leaning" in text.lower()


def _objective_core_text(objective: str) -> str:
    """User goal text without injected gate clauses."""
    core = re.split(r"\n\nMANDATORY LINGUISTIC LEANING", objective, maxsplit=1, flags=re.I)[0]
    return core.strip()


def _goal_word_budget(core: str) -> int:
    if core.lower().startswith("when this works"):
        return 55
    return 40


def _is_simple_task(seed: str, objective: str) -> bool:
    """Short seed+goal tasks should not get full benchmark boilerplate."""
    core = _objective_core_text(objective)
    title = _seed_title(seed)
    condensed = _condensed_seed(seed)
    combined = f"{condensed} {core}".lower()
    complex_markers = (
        "mitre", "compliance", "emergency", "policy", "stack trace",
        "owasp", "att&ck", "billing", "incident", "pull request",
    )
    if any(marker in combined for marker in complex_markers):
        return False
    return len(title.split()) <= 25 and len(core.split()) <= _goal_word_budget(core)


def synthesize_variant(user: str, *, compact: bool = False) -> str:
    """Generate a structured production-grade prompt variant."""
    fields = extract_fields(user)
    strategy = fields.get("strategy", "constraint_first")
    parent = fields.get("parent", "")
    objective = fields.get("objective", "Complete the task effectively.")
    membrane = fields.get("membrane", "")
    leaning = detect_linguistic_leaning(objective)
    skip_register = _objective_has_leaning_clause(objective)
    if compact or strategy == "minimal_essential":
        compact = True

    role = infer_role(parent, objective)
    strategy_block = STRATEGY_BLOCKS.get(strategy, STRATEGY_BLOCKS["constraint_first"])
    process = infer_process_steps(role, objective)
    output_fmt = infer_output_format(role, objective)

    if compact:
        process = """\
## Execution
1. Address the objective directly.
2. Return output in the specified format only."""
        strategy_block = STRATEGY_BLOCKS["minimal_essential"]
        output_fmt = "## Output Format\nStructured response matching the objective. No preamble."

    if leaning == "latinate":
        process = translate_to_latinate(process)
        strategy_block = translate_to_latinate(strategy_block)
        role = translate_to_latinate(role)

    register_block = ""
    if not skip_register and leaning not in ("neutral",):
        register_block = _leaning_block(leaning)

    membrane_section = ""
    if (
        not compact
        and membrane
        and "none yet" not in membrane.lower()
        and len(membrane) > 20
    ):
        membrane_section = f"\n## Cross-Domain Insight (Membrane Bridge)\n{membrane}\n"

    extra_blocks = ""
    if not compact:
        extra_blocks = f"""
{STRATEGY_BLOCKS['failure_mode_guards']}

{STRATEGY_BLOCKS['measurable_outcomes']}

{STRATEGY_BLOCKS['recursive_self_eval']}
"""

    prompt = f"""# {role}

You are a **{role}**. Your objective:
{objective}

{process}

{register_block}

{strategy_block}
{membrane_section}{extra_blocks}
{output_fmt}

<!-- RI-EVAL: clarity, utility, coherence, completeness -->"""

    if leaning == "latinate":
        prompt = translate_to_latinate(prompt)
    return prompt


def finalize_prompt(
    seed: str,
    objective: str,
    strategy: str = "constraint_first",
    membrane: str = "",
    register: str = "plain",
    *,
    leaning: str | None = None,
) -> str:
    """Produce a clean finalized prompt without evolution contamination."""
    resolved = leaning or register
    objective_s = objective.strip()
    simple = _is_simple_task(seed, objective_s)
    if simple:
        strategy = "minimal_essential"

    reg_clause = ""
    if not _objective_has_leaning_clause(objective_s):
        if clause := leaning_clause(resolved):
            reg_clause = f"\n{clause}"

    user = f"""# Recursive Intelligence — Variation Pass
Generation: 99
Strategy: {strategy}
Objective: {objective_s}{reg_clause}

## Parent Prompt
{seed}

## Membrane Bridge Insight (latent cross-domain correlation)
{membrane or "None yet — explore non-obvious structural parallels."}

## Instructions
Produce ONE improved prompt variant using strategy "{strategy}".
Output ONLY the new prompt — no commentary."""
    return synthesize_variant(user, compact=simple)
