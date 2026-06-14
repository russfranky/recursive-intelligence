# Use Case Benchmark — Proof of Value

Six production use cases demonstrating the Recursive Intelligence Engine evolving weak seed prompts into **Grade A production-ready agent system prompts**.

## Run the Benchmark

```bash
ri-engine benchmark
# or
python3 examples/run_benchmark.py
```

## Results Summary

| Use Case | Before | After | Δ | Grade | Features |
|----------|--------|-------|---|-------|----------|
| **Code Review Agent** | 17% | **100%** | +488% | F→A | 0→10 |
| **Cursor Coding Agent** | 24% | **100%** | +317% | F→A | 0→10 |
| **Customer Support Agent** | 17% | **100%** | +477% | F→A | 0→10 |
| **Research Analyst** | 26% | **100%** | +280% | F→A | 0→10 |
| **Sales Outreach Agent** | 25% | **100%** | +300% | F→A | 0→10 |
| **Security Incident Response** | 18% | **100%** | +445% | F→A | 0→10 |

**Aggregate: 21% → 100% (+385%) · 60 features gained · 6/6 grade improvements**

Full metrics: `output/benchmark/benchmark_results.json`

---

## Use Case 1: Code Review Agent

**Problem:** "Review my code and give feedback" produces vague, unactionable reviews.

**Seed (17% quality):**
```
You are a code reviewer. Review the pull request and give feedback.
```

**Evolved (100% quality)** — see `output/benchmark/code_review/evolved_prompt.md`:
- 6-step Review Protocol (OWASP, P0-P3 severity, test verification)
- Structured markdown output with findings table
- Self-evaluation rubric before submit
- Cross-domain insight: code review ↔ immune system clonal selection
- Anti-proxy guards (no style nitpicks)

**Run it yourself:**
```bash
ri-engine --config config/use_cases/code_review.yaml --quiet
```

---

## Use Case 2: Cursor Coding Agent

**Problem:** Generic coding assistant over-explains and makes oversized diffs.

**Seed:** `You are a coding assistant. Help the user write and fix code.`

**Evolved gains:**
- Read-first, minimal diff protocol
- Test-after-change requirement with retry logic
- Self-eval on diff minimalism
- Membrane insight: JIT manufacturing ↔ minimal diffs

**Config:** `config/use_cases/cursor_coding_agent.yaml`

---

## Use Case 3: Customer Support Agent

**Problem:** Support bots optimize for chat length, not resolution.

**Seed:** `You are a customer support agent. Help the user with their issue politely.`

**Evolved gains:**
- Triage → diagnose → resolve → escalate protocol
- ≤2 clarifying questions max
- Success metric = issue resolved, not conversation duration
- Escalation triggers for billing/legal/abuse

**Config:** `config/use_cases/customer_support.yaml`

---

## Use Case 4: Interdisciplinary Research Analyst

**Problem:** Research prompts stay in disciplinary lanes, miss cross-domain insights.

**Seed:** Basic structured analysis template.

**Evolved gains:**
- Falsifiable sub-claims with confidence scores
- Cross-domain bridge requirement (Jacquard ↔ binary logic pattern)
- Testable predictions + open questions for next iteration
- Membrane bridge across biology, software, finance domains

**Config:** `config/use_cases/research_analyst.yaml`

---

## Use Case 5: Sales Outreach Agent

**Problem:** Generic product pitches optimize for send volume, not reply rate.

**Seed:** `Write a sales email explaining our product and asking for a meeting.`

**Evolved gains:**
- ≤120 word constraint with spam trigger avoidance
- Problem-first hook (not product-first)
- Single CTA, self-score for reply probability
- Membrane insight: costly signaling ↔ mate selection

**Config:** `config/use_cases/sales_outreach.yaml`

---

## Use Case 6: Security Incident Response

**Problem:** "Is this a real threat?" produces yes/no without actionable IR steps.

**Seed:** `Analyze this alert and tell me if it's a real threat.`

**Evolved gains:**
- P0-P3 severity classification with confidence %
- MITRE ATT&CK technique mapping
- Containment-first protocol (blast radius before deep dive)
- SOC-actionable output format with escalation triggers

**Config:** `config/use_cases/security_incident.yaml`

---

## How Quality Is Measured

The **Prompt Quality Rubric** (`prompt_rubric.py`) scores 10 production features:

1. Measurable outcomes defined
2. Explicit output format
3. Failure mode guards
4. Self-evaluation hook
5. Hard constraints
6. Structured process steps
7. Anti-proxy optimization
8. Downstream actionable
9. Domain-specific depth
10. Recursive improvement hook

Weak seeds score 0/10 features. Evolved prompts score 10/10.

---

## Artifacts Per Use Case

```
output/benchmark/<use_case_id>/
├── seed_prompt.md      # Original weak prompt
├── evolved_prompt.md   # Production-grade evolved prompt
└── run_report.json     # Full VSR evolution log
```

Deploy any `evolved_prompt.md` directly as your Cursor rule or agent system prompt.
