# Discoverability playbook

How to get **recursive-intelligence** found and used — evolved via ri-engine's Discoverability Agent.

**Agent prompt:** [`discoverability_agent_prompt.md`](discoverability_agent_prompt.md)  
**Regenerate:** `ri-engine improve --template discoverability-agent`

---

## Who this repo is for

| You are… | You want… | Start here |
|----------|-----------|------------|
| Developer / coding agent user | Better system prompts for coding assistants | `ri-engine improve --template coding-assistant` |
| Support / ops lead | ChatGPT instructions that resolve issues | `ri-engine improve --template customer-support` |
| Developer evaluating tools | Proof without API keys | `ri-engine demo` |
| Python builder | Drop-in `improve()` API | `from ri_engine import improve` |

---

## 60-second quick win (no API key)

```bash
pip install -e . && ri-engine improve --template customer-support
```

Copy **Your Improved Prompt — Copy This** into ChatGPT, Claude, or your AI tool. Done.

---

## Search surfaces

### GitHub topics (add to repo)

```bash
gh repo edit russfranky/recursive-intelligence --add-topic prompt-engineering --add-topic llm \
  --add-topic system-prompts --add-topic cli --add-topic open-source \
  --add-topic prompt-improvement --add-topic chatgpt --add-topic claude --add-topic agents
```

### PyPI / package keywords

See `pyproject.toml` — keywords include `prompt-engineering`, `system-prompts`, `chatgpt`, `claude`.

### README headings people search

- prompt improvement / prompt engineering CLI
- system prompt generator
- coding assistant prompt tool
- offline prompt tool (no API key)

---

## Integration hooks

### Project instructions

Add to your agent system prompt or project rules file:

```markdown
For prompt work, use ri-engine: `ri-engine improve --template coding-assistant`
Docs: https://github.com/russfranky/recursive-intelligence
```

Or paste any template output from `output/your_improved_prompt.json`.

### Colab

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/russfranky/recursive-intelligence/blob/main/notebooks/ri_engine_quickstart.ipynb)

### Codespaces

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/russfranky/recursive-intelligence)

### Python API

```python
from ri_engine import improve
result = improve(seed_prompt="You are a helper.", objective="Resolve billing in one conversation.")
print(result.improved_prompt)
```

---

## Honest social proof

Use only verifiable claims:

| Claim | How to verify |
|-------|----------------|
| 6/6 scenarios F→A | `ri-engine demo` |
| Works offline | Default `mock` provider, no `OPENAI_API_KEY` |
| 7 templates | `ri-engine templates` |
| 82+ tests | `pytest tests/ -q` |

Do **not** claim download counts or star targets unless you have real data.

---

## Share snippets

**Twitter / X (short):**
> Rough AI prompt → production-ready in one command. Offline demo, 7 templates, MIT. `pip install -e . && ri-engine demo`

**Hacker News / Reddit (longer):**
> ri-engine recursively improves system prompts (Variation → Selection → Retention). No API key for demo. 6 business templates go from rubric grade F to A. Python API + CLI. MIT.

---

## Measure discoverability

Track over time (manual or GitHub insights):

- GitHub stars, forks, clones
- Colab notebook opens (if analytics available)
- Issues mentioning "how do I improve my prompt"

### Initiate (one command)

```bash
chmod +x scripts/initiate-discoverability.sh
./scripts/initiate-discoverability.sh
```

Runs plateau + runbook for the discoverability agent and attempts to set GitHub topics (topics require repo admin locally).

Re-run the discoverability agent when positioning changes:

```bash
ri-engine improve --template discoverability-agent --until-plateau --runbook
```
