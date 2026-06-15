# Prompt Improvement Studio

**Recursive prompt improvement — Variation → Selection → Retention, with a linguistic gate.**

Give it a seed prompt and a goal. It runs the VSR loop offline (no API key by default), resolves language/register leanings (plain, latinate, mixed, …), and returns an improved prompt.

```bash
pip install recursive-intelligence
ri-engine improve --seed "You are a helper." --goal "When this works, the AI will resolve the task in one pass"
```

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/russfranky/recursive-intelligence)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/russfranky/recursive-intelligence/blob/main/notebooks/ri_engine_quickstart.ipynb)

**License:** [MIT](LICENSE) · **Changelog:** [CHANGELOG.md](CHANGELOG.md) · **Architecture:** [docs/technical_reference.md](docs/technical_reference.md)

---

## Install

```bash
pip install recursive-intelligence
# optional real LLM backends:
pip install "recursive-intelligence[all]"
```

From source: `git clone … && pip install -e ".[all]"`

---

## Usage

### Primary path (any prompt, any goal)

```bash
ri-engine improve \
  --seed "You are a helper." \
  --goal "When this works, the AI will produce a structured answer with measurable success criteria"
```

### Ablation / research flags

```bash
ri-engine improve --seed "…" --goal "…" --linguistic-gate auto   # default
ri-engine improve --seed "…" --goal "…" --linguistic-gate off
ri-engine improve --seed "…" --goal "…" --leaning plain
ri-engine improve --seed "…" --goal "…" --diagnostics
ri-engine improve --seed "…" --goal "…" --use-persistent-macro-registry
```

Local gate ablation (no API key): `python3 experiments/run_gate_ablation.py`

### Python API

```python
from ri_engine import improve

result = improve(
    seed_prompt="You are a helper.",
    objective="When this works, the AI will produce a structured answer.",
)
print(result.improved_prompt)
print(result.fitness)  # VSR fitness score
```

### Optional: template fixtures

Templates are pre-filled seed/objective pairs used for benchmarks and linguistic-registry pooling — not required for normal use.

```bash
ri-engine templates
ri-engine improve --template code-review
```

### Proof / benchmark

```bash
ri-engine demo
```

Runs six fixture scenarios; scores are from the internal structural rubric (`prompt_rubric.py`), not live task metrics.

### Expert / research commands

```bash
ri-engine expert benchmark
ri-engine expert pool-linguistic-registry
ri-engine expert macro-registry
ri-engine improve --seed … --goal … --expert
```

---

## How it works

```
Linguistic Gate → Macro Priors → [Membrane] → Variation → Selection → Retention → repeat
```

1. **Linguistic gate** (experimental prior) — weighted objective text + weak registry prior; defaults to mixed when confidence is low
2. **Variation** — generates prompt variants (8 strategies)
3. **Selection** — scores candidates (objective alignment, clarity, utility, coherence, register fit, simplicity)
4. **Retention** — carries winning traits forward; detects convergence
5. **Baseline check** — compares VSR output against one-shot `finalize_prompt()`; returns the simpler baseline if VSR does not win meaningfully

Default provider is **mock** (offline, deterministic). Optional: `--provider openai` or `--provider anthropic`.

**Mock mode scope:** mock mode is a deterministic offline test of the recursive improvement process. It measures structural prompt quality using local heuristics (`prompt_rubric.py`). It does **not** prove that the resulting prompt will improve downstream LLM task performance. Use real-provider evaluation for behavioral claims.

Persistent macro trait registry is **off by default**; pass `--use-persistent-macro-registry` for cross-run learning experiments.

---

## Optional providers

```bash
export OPENAI_API_KEY=sk-...
ri-engine improve --seed prompt.txt --goal "…" --provider openai
```

---

## Docs

| Doc | Contents |
|-----|----------|
| [technical_reference.md](docs/technical_reference.md) | Architecture, VSR, macro registry, Occam's razor |
| [publication.md](docs/publication.md) | API contract, limitations, red-team notes |
| [getting_started.md](docs/getting_started.md) | Step-by-step CLI walkthrough |
| [cloud_development.md](docs/cloud_development.md) | Codespaces + Colab |

---

*General-purpose prompt improvement. You bring the seed and goal; the engine handles language alignment and recursive refinement.*
