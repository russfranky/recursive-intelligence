# Contributing

Thank you for your interest in **Recursive Intelligence Engine** (`ri-engine`). This project is a research-oriented, open-source prompt-improvement library. Contributions that improve clarity, test coverage, ablation rigor, and documentation are welcome.

## Before you start

1. Read [docs/research_and_citations.md](docs/research_and_citations.md) for project scope and attribution.
2. Read [docs/technical_reference.md](docs/technical_reference.md) for architecture (VSR loop, linguistic gate, rubric).
3. Mock mode scores **structural prompt quality** locally; do not claim downstream LLM task success without real-provider evaluation.

## Development setup

```bash
git clone https://github.com/russfranky/recursive-intelligence.git
cd recursive-intelligence
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[all]"
pytest tests/ -q
```

## Making changes

1. **Branch** from `main`: `cursor/<short-description>-a42c` or a descriptive feature branch name.
2. **Keep scope focused** — one logical change per pull request.
3. **Match existing style** — read surrounding modules before adding helpers or abstractions.
4. **Run tests** before opening a PR:

   ```bash
   pytest tests/ -q
   ri-engine templates
   ```

5. **Update docs** when you change CLI flags, public API (`ri_engine.improve`), or default behavior.
6. **Update [CHANGELOG.md](CHANGELOG.md)** under `[Unreleased]` or the next version section.

## Pull requests

- Describe **what** changed and **why**.
- Note any breaking changes to `improve()` kwargs or CLI flags.
- Link related issues when applicable.
- Ensure CI passes (Python 3.10–3.12).

## Research contributions

For linguistic-gate or rubric changes:

- Prefer **ablation evidence** (`experiments/run_gate_ablation.py`) over fixture-only claims.
- Document honest scope: mock rubric ≠ live task performance.
- Do not overweight novelty or structural bloat in selection fitness.

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By participating, you agree to uphold it.

## Questions

Open a [GitHub issue](https://github.com/russfranky/recursive-intelligence/issues) for bugs, feature requests, or design discussion.
