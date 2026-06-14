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

---

## Architecture (minimal)

```
Linguistic Gate → [Membrane] → Variation → Selection → Retention → repeat
```

Five core operator prompts: `variation`, `selection`, `retention`, `membrane_bridge`, `meta_improvement`.

Expert tooling (`ri-engine expert …`) remains for research but is not part of the public quick-start path.
