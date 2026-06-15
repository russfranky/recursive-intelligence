# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a vulnerability

If you believe you have found a security vulnerability, please **do not** open a public GitHub issue.

Instead, report it privately to the repository maintainers via GitHub's **Private vulnerability reporting** (Security → Advisories → Report a vulnerability) on the project repository, or contact the maintainer listed in [pyproject.toml](pyproject.toml).

Include:

- Description of the issue and potential impact
- Steps to reproduce
- Affected versions and components (CLI, API, provider adapters)

We aim to acknowledge reports within **7 days** and provide a remediation plan or status update as soon as practicable.

## Scope notes

- **API keys:** `ri-engine` reads `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` from the environment when using real providers. Do not commit secrets or log them in diagnostics output.
- **Mock mode:** Default offline provider does not call external services.
- **Macro registry / trait export:** Persistent learning features are opt-in; review exported trait JSON before sharing across environments.

## Safe defaults

- Persistent macro trait registry: **off** by default
- Linguistic gate: experimental prior; use ablation flags for research runs
- Mock mode: structural rubric only — not a substitute for production LLM evaluation
