# Documentation

Central index for **Recursive Intelligence Engine** (`ri-engine`).

## Diagrams

**[diagrams.md](diagrams.md)** — Mermaid charts for users and contributors:

- What you do in 30 seconds (seed + goal → improved prompt)
- VSR pipeline and Occam guardrail
- Recursive validation loops (inner / middle / outer)
- Claude Code handoff sequence
- Workflow task battery and collective intelligence phases

## Start here

| Document | Audience | Description |
|----------|----------|-------------|
| [getting_started.md](getting_started.md) | Users | Install, first `improve` run, CLI walkthrough |
| [diagrams.md](diagrams.md) | Users | Visual overview (Mermaid) |
| [technical_reference.md](technical_reference.md) | Developers | VSR architecture, modules, API, Occam's razor |
| [research_and_citations.md](research_and_citations.md) | Researchers | Inspiration, related work, how to cite |
| [publication.md](publication.md) | Maintainers | Release scope, API contract, limitations |

## User guides

| Document | Description |
|----------|-------------|
| [getting_started.md](getting_started.md) | Step-by-step CLI and Python API |
| [cloud_development.md](cloud_development.md) | GitHub Codespaces and Google Colab |
| [claude_code_integration.md](claude_code_integration.md) | Claude Code handoff toggle |
| [agent_integration.md](agent_integration.md) | Embed the engine in agent workflows |
| [use_cases.md](use_cases.md) | Benchmark fixtures and scenario notes |

## Architecture & reference

| Document | Description |
|----------|-------------|
| [technical_reference.md](technical_reference.md) | Pipeline stages, fitness weights, expert commands |
| [publication.md](publication.md) | Public API contract and honest scope |
| [../config/README.md](../config/README.md) | YAML configs, templates, registries |
| [../experiments/README.md](../experiments/README.md) | Local ablation experiments |

## Research

| Document | Description |
|----------|-------------|
| [research_and_citations.md](research_and_citations.md) | Attribution (Raymond Uzwyshyn Ph.D.), BibTeX, related papers |
| [../CITATION.cff](../CITATION.cff) | Machine-readable citation metadata |
| [../CREDITS.md](../CREDITS.md) | Credits and license |

## Governance

| Document | Description |
|----------|-------------|
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | How to contribute |
| [../CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md) | Community standards |
| [../SECURITY.md](../SECURITY.md) | Vulnerability reporting |
| [../CHANGELOG.md](../CHANGELOG.md) | Version history |

## Maintainer & internal artifacts

These files support repo maintenance, agent-assisted evolution, and one-off deliverables. They are not required for normal use of `ri-engine`.

| Document | Description |
|----------|-------------|
| [discoverability.md](discoverability.md) | Discoverability playbook |
| [discoverability_agent_prompt.md](discoverability_agent_prompt.md) | Agent prompt for discoverability passes |
| [occams_razor_agent_prompt.md](occams_razor_agent_prompt.md) | Occam's razor integration spec |
| [publication_agent_prompt.md](publication_agent_prompt.md) | Publication checklist agent |
| [standalone_repo.md](standalone_repo.md) | Private repo publish notes |
| [prompts/](prompts/) | Historical agent prompt seeds |

## Scope reminder

**Mock mode** (default provider) measures structural prompt quality via local heuristics. It does **not** prove downstream LLM task performance. Use real providers and task-specific evaluation for behavioral claims.
