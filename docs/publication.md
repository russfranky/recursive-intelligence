# Publication Guide

Recursive Intelligence is a **task prompt improvement** engine: turn rough AI prompts into production-ready ones via recursive Variation → Selection → Retention.

---

## Product focus

| In scope | Out of scope (removed) |
|----------|------------------------|
| Task/agent prompts (support, sales, code review, etc.) | Game NPC / raw system prompt mode |
| 6 business templates + demo proof | Client-specific lore or hardcoded domain templates |
| Offline mock provider (default) | Ollama / extra provider routing layers |
| Single `improve()` API | Parallel NPC rubrics and operator variants |

---

## Public API

```python
from ri_engine import improve, improve_template, list_templates

# Custom prompt
result = improve(
    seed_prompt="You are a helper.",
    objective="Resolve billing issues in one conversation.",
)
print(result.improved_prompt)   # production-ready (finalized)
print(result.engine_prompt)     # raw VSR winner (inspect/debug)
print(result.to_dict())         # JSON-serializable for REST handlers

# Built-in template (same ids as `ri-engine templates`)
result = improve_template("customer-support")

# Discovery
for t in list_templates():
    print(t["id"], t["name"])
```

### API surface

| Function | Purpose |
|----------|---------|
| `improve(seed, objective, **opts)` | Core entry — custom prompts |
| `improve_template(template_id, **opts)` | Template parity with CLI |
| `improve_until_plateau(seed, objective, **opts)` | Multi-cycle until fitness plateaus |
| `list_templates()` | Discover built-in scenarios |
| `ImproveResult.to_dict()` | REST/logging payload |
| `PlateauImproveResult.to_dict()` | Multi-cycle summary payload |

### CLI equivalent

```bash
ri-engine improve --template customer-support
ri-engine improve --template customer-support --until-plateau --runbook
ri-engine improve --continue --until-plateau
ri-engine improve --seed prompt.txt --goal "Your success criteria"
ri-engine runbook list
ri-engine demo
```

### Plateau cycling and runbook

Run improvement repeatedly until gains taper off, then optionally publish the winner locally for the next AI session:

```python
from ri_engine import improve_until_plateau

result = improve_until_plateau(
    seed_prompt="You are a helper.",
    objective="Resolve billing issues in one conversation.",
    max_cycles=10,
    approve_to_runbook=True,
    runbook_name="customer-support",
)
print(result.final.improved_prompt)
print(result.plateau_reason)  # fitness_plateau | unchanged_prompt | max_cycles
```

Session state is saved to `output/improvement_session.json` after each cycle. Resume with:

```bash
ri-engine improve --continue --until-plateau
```

Approved prompts compile to `runbook/RUNBOOK.md` — point your next AI at that file before executing tasks.

---

## Publication surface

| Audience | Entry point |
|----------|-------------|
| End user | `ri-engine improve --template X` |
| Developer | `from ri_engine import improve` |
| Evaluator | `ri-engine demo` + `output/benchmark/benchmark_results.json` |
| Researcher | `ri-engine expert benchmark` + `docs/technical_reference.md` |

---

## Proof artifacts

| Artifact | Metric |
|----------|--------|
| `output/benchmark/benchmark_results.json` | 6/6 scenarios F→A, +385% avg quality |
| `output/evolved_prompts/evolution_summary.json` | 5 operator prompts at 95%+ composite |
| `tests/test_api.py` | Public API contract |

Generate locally (not committed — see `.gitignore`):

```bash
ri-engine demo                        # benchmark proof
ri-engine expert improve-prompts        # operator prompt evolution
```

---

## Red-team review

Independent review of claims, scope, and risks before public release.

### Claims audit

| Claim | Verdict | Notes |
|-------|---------|-------|
| "F→A grade improvement" on 6 templates | **Accurate** | Scored by `prompt_rubric.py` (10-feature checklist). Reproducible via `ri-engine demo`. |
| "+385% average quality" | **Accurate** | Aggregate of rubric scores (21% → 100%). Percent change is relative to baseline, not absolute LLM performance. |
| "Works offline, no API key" | **Accurate** | Default `mock` provider uses deterministic `prompt_synthesizer.py`. |
| "Production-ready prompts" | **Qualified** | Output is structurally complete per rubric. Real-world fitness still depends on your domain and LLM backend. |
| "Every template improves" | **Accurate** | All 6 built-in scenarios reach 10/10 rubric features with mock provider. |

### Limitations (disclose to users)

1. **Mock vs real LLM** — Offline mode proves the VSR loop and rubric; semantic rewrites with GPT/Claude (`--provider openai`) may differ in style and require API keys.
2. **Rubric ≠ downstream success** — Scores measure prompt *structure* (constraints, format, self-eval hooks), not live task completion rates.
3. **Deterministic synthesis** — Mock provider applies strategy blocks from `prompt_synthesizer.py`; it is not a substitute for human prompt engineering review on sensitive domains.
4. **Expert commands** — `ri-engine expert …` exposes internal research tooling; not covered by the public API contract in `tests/test_api.py`.

### Privacy and data handling

| Data | Leaves machine? |
|------|-----------------|
| Seed prompts, objectives, customer text | **Never** (local only) |
| Session state (`output/improvement_session.json`) | **Never** |
| Trait export (`--share-traits`) | **Opt-in only** — structural patterns, no raw prompts |
| Macro trait registry (`config/macro_trait_registry.json`) | **Local only** — gitignored |

### Security posture

- No network calls with default mock provider.
- API keys are read from environment variables only; never written to output files.
- No telemetry or external analytics.
- `output/` and `runbook/` are gitignored — users control what they commit.

### Recommended public messaging

- Lead with **"structured prompt improvement"**, not "autonomous AGI."
- Show `ri-engine demo` as reproducible proof, not a one-time marketing screenshot.
- Document that OpenAI/Anthropic providers are optional upgrades for semantic variation.

---

## Publication checklist

Use this before tagging a release or flipping repo visibility to public.

- [x] `LICENSE` (MIT) at repo root
- [x] `README.md` — install, quick start, templates, API pointer
- [x] `docs/getting_started.md` — non-technical onboarding
- [x] `docs/publication.md` — this file (API + red-team + checklist)
- [x] `docs/technical_reference.md` — architecture for developers
- [x] `docs/cloud_development.md` — Codespaces + Colab (standalone repo URLs)
- [x] `.github/workflows/ci.yml` — tests on Python 3.10–3.12
- [x] `.devcontainer/devcontainer.json` — one-click Codespaces
- [x] `pyproject.toml` — version, license, classifiers, entry point
- [x] `tests/` — 80+ passing tests including public API contract
- [ ] Run `ri-engine demo` locally and spot-check evolved prompts
- [ ] Set repo visibility to **public** (if desired) via GitHub settings or `VISIBILITY=public ./scripts/publish-private-repo.sh`
- [ ] Update Colab badge URL if repo name or owner changes

---

## Architecture (minimal)

```
Linguistic Gate → [Membrane] → Variation → Selection → Retention → repeat
```

Five core operator prompts: `variation`, `selection`, `retention`, `membrane_bridge`, `meta_improvement`.

Expert tooling (`ri-engine expert …`) remains for research but is not part of the public quick-start path.
