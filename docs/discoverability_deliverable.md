## Assumptions

Target repo is `russfranky/recursive-intelligence`; goal is more finds and first-time usage without fake metrics.

## Audience & search intent

| Audience | Query / entry point | README hook |
|----------|---------------------|-------------|
| Developers using AI coding tools | system prompt, agent instructions | `coding-assistant` template + 60s install block |
| Support leads | ChatGPT custom instructions | `customer-support` template |
| Tool evaluators | prompt engineering CLI offline | `ri-engine demo` — 6/6 F→A |
| Python devs | improve prompt API | `from ri_engine import improve` |

## Changes made

| File | Change | Why it helps discovery |
|------|--------|------------------------|
| `docs/discoverability_agent_prompt.md` | ri-engine evolved + curated discoverability protocol | Reusable agent for future growth passes |
| `config/templates/discoverability-agent.yaml` | New template | `ri-engine improve --template discoverability-agent` |
| `docs/discoverability.md` | Playbook: topics, hooks, share snippets | Maintainer + advocate reference |
| `README.md` | 60s quick win, who-it's-for table, keywords in hook | First-screen conversion + SEO |
| `pyproject.toml` | Expanded keywords (`system-prompts`, `chatgpt`, etc.) | PyPI/search indexing |

## 60-second quick win

```bash
pip install -e . && ri-engine improve --template customer-support
```

## Integration hooks

- **Project instructions:** `ri-engine improve --template coding-assistant` → paste into ChatGPT, Claude, or your agent system prompt
- **Colab:** badge in README → `notebooks/ri_engine_quickstart.ipynb`
- **Codespaces:** badge in README → devcontainer auto-install
- **Python API:** `from ri_engine import improve`

## Social proof (honest)

- Demo metric: 6/6 scenarios F→A, +385% avg (`ri-engine demo`)
- Template count: 8 via `ri-engine templates`
- Tests: 82 passing

## GitHub topics / keywords

`prompt-engineering`, `llm`, `system-prompts`, `cli`, `open-source`, `prompt-improvement`, `chatgpt`, `claude`, `copilot`, `agents`

## Self-eval

- clarity: 0.95
- utility: 0.95
- coherence: 0.95

## Next CTA for visitors

1. `pip install -e .`
2. `ri-engine improve --template customer-support` (or your role)
3. Copy improved prompt into your AI tool
4. Run `ri-engine demo` if you need proof first

## Initiation status (2026-06-14)

- [x] PR #3 merged to `main`
- [x] Discoverability agent runbook approved (`runbook/RUNBOOK.md`)
- [x] `scripts/initiate-discoverability.sh` added
- [ ] GitHub topics — run `./scripts/set-repo-topics.sh` as repo admin
- [ ] Repo visibility public — run `gh repo edit ... --visibility public` as admin
