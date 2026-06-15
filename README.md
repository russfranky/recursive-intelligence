# Prompt Improvement Studio

**Turn rough AI prompts into production-ready ones — automatically.**

Improve system prompts for **ChatGPT**, **Claude**, **Copilot**, **Cursor**, and any AI agent. No API key required. One command, copy-paste result.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/russfranky/recursive-intelligence)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/russfranky/recursive-intelligence/blob/main/notebooks/ri_engine_quickstart.ipynb)

**Try in 60 seconds (offline):**

```bash
pip install recursive-intelligence && ri-engine improve --template customer-support
```

Copy the improved prompt into ChatGPT, Claude, Cursor, or your AI tool. [Full discoverability guide →](docs/discoverability.md)

**Run in the cloud (free tier):** [Codespaces + Colab guide](docs/cloud_development.md) — use Colab for quick API experiments, Codespaces for the full CLI, runbook, and plateau workflow.

**License:** [MIT](LICENSE) · **Changelog:** [CHANGELOG.md](CHANGELOG.md) · **Grow usage:** [discoverability guide](docs/discoverability.md)

---

## Who it's for

| You are… | Start here |
|----------|------------|
| Developer (Cursor, Copilot, etc.) | `ri-engine improve --template coding-assistant` |
| Support or ops lead | `ri-engine improve --template customer-support` |
| Evaluating the tool (no API key) | `ri-engine demo` |
| Python integrator | `from ri_engine import improve` |

---

## Install (2 minutes)

**From PyPI (recommended):**

```bash
pip install recursive-intelligence
ri-engine improve --template customer-support
```

**From source:**

```bash
git clone https://github.com/russfranky/recursive-intelligence.git
cd recursive-intelligence
pip install -e ".[all]"
```

Works offline immediately — no API key needed for the built-in demo.

**Repository setup:** see [docs/standalone_repo.md](docs/standalone_repo.md) — clone, Codespaces, or `./scripts/publish-private-repo.sh` for mirrors.

---

## 3-Step Quick Start

### 1. See what's available

```bash
ri-engine templates
```

### 2. Improve a prompt

```bash
ri-engine improve --template customer-support
```

Or use your own starting prompt:

```bash
ri-engine improve \
  --seed "You are a helper. Answer questions." \
  --goal "Help customers resolve billing issues in one conversation"
```

### 3. Copy the result

The tool shows **Your Improved Prompt — Copy This**. Paste it into your AI assistant as the system prompt. Done.

Results are also saved to `output/your_improved_prompt.json`.

---

## See the proof

```bash
ri-engine demo
```

Runs 6 real business scenarios (support, sales, security, coding, research, code review) and shows before/after quality — no jargon.

---

## Ready-made templates

| Template | Best for |
|----------|----------|
| `customer-support` | Help desks and support teams |
| `code-review` | Engineering teams reviewing pull requests |
| `coding-assistant` | Developers using Cursor, Copilot, and similar coding agents |
| `sales-outreach` | Sales emails that get replies |
| `security-response` | Security alert triage and response |
| `research-analyst` | Structured research and analysis |
| `publication-agent` | Preparing a repo for public GitHub release |
| `discoverability-agent` | Growing repo adoption — README, keywords, CTAs |
| `occams-razor` | Add simplicity pressure across the VSR loop |

```bash
ri-engine improve --template occams-razor
```

---

## Using your own AI provider (optional)

For semantic rewrites with GPT or Claude:

```bash
pip install -e ".[openai]"
export OPENAI_API_KEY=sk-...
ri-engine improve --template sales-outreach --provider openai
```

---

## What happens behind the scenes (plain English)

You don't need to watch or understand this — but for the curious:

1. **Style match** — We pick the best writing tone for your task (clear, friendly, formal, etc.)
2. **Try versions** — The system drafts multiple improved versions of your prompt
3. **Pick the best** — Each version is scored for clarity, usefulness, and completeness
4. **Keep what works** — Winning patterns carry forward to the next round
5. **Deliver** — You get one polished prompt, ready to paste

---

## For developers & power users

```bash
ri-engine improve --template customer-support --expert   # technical output
ri-engine expert benchmark                               # full benchmark
```

### Python API

```python
from ri_engine import improve

result = improve(
    seed_prompt="You are a helper.",
    objective="Help customers resolve billing issues in one conversation.",
)
print(result.improved_prompt)
```

See [docs/publication.md](docs/publication.md) for the publication guide, red-team review, and API reference.

See [docs/technical_reference.md](docs/technical_reference.md) for architecture, VSR loop, and research background.

---

## Support

```bash
ri-engine              # welcome & quick help
ri-engine templates    # list templates
ri-engine demo         # see proof it works
```

**Quality guarantee:** Every template scenario in our demo improves from failing grade (F) to production-ready (A).

---

*Powered by recursive improvement research. Built for teams who need results, not jargon.*
