# Technical Reference

For mainstream users, start with [getting_started.md](getting_started.md).  
For publication scope, see [publication.md](publication.md).

## Architecture

```
Linguistic Gate → Macro Priors → [Membrane Bridge] → Variation → Selection → Retention → repeat
                                                      ↓ (on selection)
                                              Macro Trait Registry
```

| Stage | Module | Role |
|-------|--------|------|
| Variation | `variation.py` | Generate prompt variants (8 strategies) |
| Selection | `selection.py` | Multi-dimensional fitness scoring |
| Retention | `retention.py` | Lineage memory + convergence |
| Membrane | `membrane.py` | Cross-domain correlation (optional) |
| Occam's razor | `occams_razor.py` | Simplicity scoring + fitness blend (default on) |
| Linguistic gate | `language_leanings.py` | Pre-VSR style resolution |
| **Macro learning** | `macro_registry.py` | **Internal** — pool traits from selected prompts; inject priors on next run |

### Macro-scale recursion (internal)

When fitness clears the selection threshold, Retention `[TRAIT:…]` bullets are parsed (`trait_parser.py`) and upserted into `config/macro_trait_registry.json` by objective class. The next run reads priors before VSR:

- **Variation** — strategy order biased toward historically winning traits
- **Lineage insight** — macro brief prepended to membrane/retention context

Not public-facing. Inspect with:

```bash
ri-engine expert macro-registry
```

Disable per run: `metadata={"enable_macro_learning": False}`.

## Public API (recommended)

```python
from ri_engine import improve

result = improve(
    seed_prompt="You are a code reviewer.",
    objective="Structured PR review with measurable output.",
    max_generations=5,
    provider="mock",
)
print(result.improved_prompt)
```

## CLI

```bash
ri-engine improve --template X              # template-based
ri-engine improve --seed s.txt --goal "..." # custom
ri-engine improve --config path.yaml        # config file
ri-engine demo                              # 6-scenario proof
```

Expert commands (research / tuning):

```bash
ri-engine expert benchmark
ri-engine expert improve-prompts
```

## Low-level engine API

```python
from ri_engine import RecursiveIntelligenceEngine, RunConfig
from ri_engine.llm_provider import create_provider

config = RunConfig(seed_prompt="...", objective="...")
report = RecursiveIntelligenceEngine(create_provider("mock")).run(config)
print(report["best_prompt"])
```

Use `improve()` unless you need full report access or custom observers.

## Client layer

`client_view.py` translates technical reports into `your_improved_prompt.json` for non-expert CLI users.

## Occam's razor (default on)

Every VSR cycle applies simplicity pressure via `occams_razor.py`:

- **Selection** scores `simplicity` and blends it into fitness (12% weight by default)
- **Tie-break** at equal fitness prefers shorter, fewer-section prompts
- **Retention** instructs trait pruning (max 6, merge duplicates)

Disable per run:

```python
improve(..., metadata={"enable_occams_razor": False})
```

Evolve Occam rules: `ri-engine improve --template occams-razor` · canonical prompt: `docs/occams_razor_agent_prompt.md`

## Research background

This engine implements **Variation → Selection → Retention** as executable prompt iteration — treating prompt improvement as a **Darwinian selection environment** for LLM instructions.

**Primary inspiration:** Raymond Uzwyshyn Ph.D., [*The AI Agentic Substrate: Life Inside the Recursive Zone*](https://www.linkedin.com/pulse/ai-agentic-substrate-life-inside-recursive-zone-uzwyshyn-ph-d--zohyc) and related LinkedIn writing on *Agentic AI, Recursion, Biology and Our New Selection Environments* (Feb 2026). Those articles describe agentic systems as hyper-accelerated VSR loops and selection environments; this repo is a practical, offline-first experiment in that pattern for **prompt** space.

Full citations, related work (APE, PromptBreeder, OPRO, DSPy), and BibTeX: **[docs/research_and_citations.md](research_and_citations.md)**.
