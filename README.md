# Recursive Intelligence Engine

**Open-source recursive prompt improvement — Variation → Selection → Retention (VSR), with an experimental linguistic gate.**

[![CI](https://github.com/russfranky/recursive-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/russfranky/recursive-intelligence/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/recursive-intelligence.svg)](https://pypi.org/project/recursive-intelligence/)

Give a **seed prompt** and a **goal**. The engine runs an offline VSR loop (no API key by default), resolves register leanings (plain, latinate, mixed, …), and returns an improved prompt.

```bash
pip install recursive-intelligence
ri-engine improve \
  --seed "You are a helper." \
  --goal "When this works, the AI will produce a structured answer with measurable success criteria"
```

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/russfranky/recursive-intelligence)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/russfranky/recursive-intelligence/blob/main/notebooks/ri_engine_quickstart.ipynb)

---

## Overview

| | |
|---|---|
| **Package** | `recursive-intelligence` |
| **CLI** | `ri-engine` |
| **Python API** | `from ri_engine import improve` |
| **Default provider** | Mock (deterministic, offline) |
| **License** | [MIT](LICENSE) |

Research inspiration: **Raymond Uzwyshyn Ph.D.** — agentic AI, recursion, and selection environments. See [CREDITS.md](CREDITS.md) and [docs/research_and_citations.md](docs/research_and_citations.md).

---

## Features

- **VSR loop** — generate variants, score fitness, retain winners, repeat until convergence
- **Linguistic gate** (experimental) — weighted register prior; ablation modes via CLI
- **Baseline comparison** — VSR output vs one-shot finalize; returns simpler result when VSR does not win
- **Objective alignment scoring** — rubric weights goal fit over structural bloat
- **Template fixtures** — optional benchmark configs; primary path is `--seed` + `--goal`
- **Local ablation** — `experiments/run_gate_ablation.py` (no API key)

---

## Installation

```bash
pip install recursive-intelligence

# Optional real LLM backends:
pip install "recursive-intelligence[all]"
```

**From source:**

```bash
git clone https://github.com/russfranky/recursive-intelligence.git
cd recursive-intelligence
pip install -e ".[all]"
```

Requirements: Python 3.10+

---

## Quick start

### CLI

```bash
ri-engine improve \
  --seed "You are a helper." \
  --goal "When this works, the AI will resolve the task in one pass"
```

### Python

```python
from ri_engine import improve

result = improve(
    seed_prompt="You are a helper.",
    objective="When this works, the AI will produce a structured answer.",
)
print(result.improved_prompt)
print(result.fitness)
```

### Research flags

```bash
ri-engine improve --seed "…" --goal "…" --linguistic-gate auto   # default
ri-engine improve --seed "…" --goal "…" --linguistic-gate off
ri-engine improve --seed "…" --goal "…" --leaning plain
ri-engine improve --seed "…" --goal "…" --diagnostics
```

Full walkthrough: [docs/getting_started.md](docs/getting_started.md)

---

## How it works

```
Linguistic Gate → [Macro Priors] → [Membrane] → Variation → Selection → Retention → repeat
                                                      ↓
                                            Baseline vs VSR pick
```

1. **Linguistic gate** — experimental prior; defaults to mixed when confidence is low
2. **Variation** — eight mutation strategies
3. **Selection** — objective alignment, clarity, utility, coherence, register fit, simplicity
4. **Retention** — lineage memory and convergence detection
5. **Baseline check** — compare against one-shot `finalize_prompt()`

Architecture details: [docs/technical_reference.md](docs/technical_reference.md)

---

## Project structure

```
recursive-intelligence/
├── src/ri_engine/          # Core library and CLI
├── tests/                  # Pytest suite
├── docs/                   # Documentation index → docs/README.md
├── config/                 # Templates, use cases, registries → config/README.md
├── experiments/            # Local ablation scripts → experiments/README.md
├── examples/               # Sample scripts
├── prompts/                # VSR operator prompts (bundled into package)
├── CONTRIBUTING.md         # Contribution guidelines
├── CREDITS.md              # Attribution
├── CITATION.cff            # Machine-readable citation
└── CHANGELOG.md            # Release history
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [**docs/README.md**](docs/README.md) | **Documentation hub** |
| [getting_started.md](docs/getting_started.md) | Install and first run |
| [technical_reference.md](docs/technical_reference.md) | Architecture and API |
| [research_and_citations.md](docs/research_and_citations.md) | Related work and BibTeX |
| [publication.md](docs/publication.md) | Scope, limitations, release notes |
| [cloud_development.md](docs/cloud_development.md) | Codespaces and Colab |

---

## Scope and limitations

**Mock mode** (default) is a deterministic offline test of the recursive improvement process. It measures structural prompt quality using local heuristics (`prompt_rubric.py`). It does **not** prove that the resulting prompt will improve downstream LLM task performance.

Use `--provider openai` or `--provider anthropic` with appropriate API keys for semantic rewriting. Evaluate task outcomes separately.

Persistent macro trait registry is **off by default** (`--use-persistent-macro-registry` to enable).

---

## Optional providers

```bash
export OPENAI_API_KEY=sk-...
ri-engine improve --seed prompt.txt --goal "…" --provider openai
```

---

## Contributing

Contributions welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

```bash
pytest tests/ -q
```

Report security issues per [SECURITY.md](SECURITY.md).

---

## Citation

See [CITATION.cff](CITATION.cff) and [docs/research_and_citations.md](docs/research_and_citations.md).

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
