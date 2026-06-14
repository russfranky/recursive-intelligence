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


def infer_role(parent: str, objective: str) -> str:
    """Infer agent role title from seed/objective."""
    for pattern in [
        r"You are (?:a |an )?(.+?)[\.\n]",
        r"^#\s*(.+?)(?:\n|$)",
    ]:
        m = re.search(pattern, parent, re.I | re.M)
        if m:
            return m.group(1).strip().title()
    if "review" in objective.lower():
        return "Code Review Agent"
    if "support" in objective.lower():
        return "Customer Support Agent"
    if "security" in objective.lower() or "incident" in objective.lower():
        return "Security Incident Response Agent"
    if "sales" in objective.lower() or "outreach" in objective.lower():
        return "Sales Outreach Agent"
    if "research" in objective.lower():
        return "Research Analyst Agent"
    if "coding" in objective.lower():
        return "AI Coding Assistant"
    return "Task Agent"


def infer_process_steps(role: str, objective: str) -> str:
    """Generate role-specific process steps."""
    obj = objective.lower()
    role_l = role.lower()
    if "review" in obj or "review" in role_l or "code" in role_l:
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
    if "research" in obj or "research" in role_l:
        return """\
## Research Protocol
1. **Decompose**: break topic into 3-5 falsifiable sub-claims
2. **Cross-domain**: find ≥1 non-obvious correlation across 2+ fields
3. **Evidence**: cite sources, assign confidence 0.0–1.0 per claim
4. **Predictions**: include ≥1 testable prediction
5. **Gaps**: explicit open questions for next iteration
6. **Self-eval**: would a skeptical expert find this actionable?"""
    if "coding" in obj or "coding" in role_l:
        return """\
## Coding Protocol
1. **Read first**: understand existing code before editing
2. **Minimal diff**: change only what's required, match conventions
3. **Test**: run relevant tests after every change
4. **Retry**: on failure, diagnose and retry up to 3 times
5. **Commit**: clear message explaining why, not what
6. **Self-eval**: is the diff the smallest correct solution?"""
    return """\
## Execution Protocol
1. Parse input and state assumptions if ambiguous
2. Execute against the stated objective with measurable output
3. Self-evaluate before responding
4. Output in the specified format only"""


def infer_output_format(role: str, objective: str) -> str:
    obj = objective.lower()
    role_l = role.lower()
    if "review" in obj or "review" in role_l:
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
    if "research" in obj:
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
    if "coding" in obj or "coding" in role_l:
        return """\
## Output Format
1. Brief plan (≤3 bullets)
2. Code changes (minimal diff)
3. Test commands run + results
4. Self-score: correctness=X, minimalism=X"""
    return "## Output Format\nReturn structured response matching the objective. No preamble."


def _detect_register(objective: str) -> str:
    """Backward-compatible alias for linguistic leaning detection."""
    return detect_linguistic_leaning(objective)


def _leaning_block(leaning: str) -> str:
    return LEANING_BLOCKS.get(leaning, LEANING_BLOCKS["plain"])


def synthesize_variant(user: str) -> str:
    """Generate a structured production-grade prompt variant."""
    fields = extract_fields(user)
    strategy = fields.get("strategy", "constraint_first")
    parent = fields.get("parent", "")
    objective = fields.get("objective", "Complete the task effectively.")
    membrane = fields.get("membrane", "")
    leaning = detect_linguistic_leaning(objective)

    role = infer_role(parent, objective)
    strategy_block = STRATEGY_BLOCKS.get(strategy, STRATEGY_BLOCKS["constraint_first"])
    process = infer_process_steps(role, objective)
    output_fmt = infer_output_format(role, objective)

    if leaning == "latinate":
        process = translate_to_latinate(process)
        strategy_block = translate_to_latinate(strategy_block)
        role = translate_to_latinate(role)

    register_block = _leaning_block(leaning)

    membrane_section = ""
    if membrane and "none yet" not in membrane.lower() and len(membrane) > 20:
        membrane_section = f"\n## Cross-Domain Insight (Membrane Bridge)\n{membrane}\n"

    prompt = f"""# {role}

You are a **{role}**. Your objective:
{objective}

{process}

{register_block}

{strategy_block}
{membrane_section}
{STRATEGY_BLOCKS['failure_mode_guards']}

{STRATEGY_BLOCKS['measurable_outcomes']}

{STRATEGY_BLOCKS['recursive_self_eval']}

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
    reg_clause = f"\n{leaning_clause(resolved)}" if leaning_clause(resolved) else ""

    user = f"""# Recursive Intelligence — Variation Pass
Generation: 99
Strategy: {strategy}
Objective: {objective}{reg_clause}

## Parent Prompt
{seed}

## Membrane Bridge Insight (latent cross-domain correlation)
{membrane or "None yet — explore non-obvious structural parallels."}

## Instructions
Produce ONE improved prompt variant using strategy "{strategy}".
Output ONLY the new prompt — no commentary."""
    return synthesize_variant(user)
