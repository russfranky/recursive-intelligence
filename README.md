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

1. **Linguistic gate** — picks register leaning (plain Anglo-Saxon vs latinate, etc.) from your goal and pooled registry evidence
2. **Variation** — generates prompt variants (8 strategies)
3. **Selection** — scores candidates (clarity, utility, coherence, simplicity via Occam's razor)
4. **Retention** — carries winning traits forward; detects convergence

Default provider is **mock** (offline, deterministic). Optional: `--provider openai` or `--provider anthropic`.

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
