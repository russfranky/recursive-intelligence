# Changelog

All notable changes to this project are documented here.

## [0.1.9] - 2026-06-15

### Added

- Claude Code **middle-loop self-test**: `ri-engine real-world workflow`
- `config/workflow_self_test.yaml` — session config for workflow validation
- `config/workflow_self_test_tasks.yaml` — falsifiable structural task battery (8 checks)
- Task battery scoring integrated into `real-world run` when `metadata.task_battery` is set
- **docs/diagrams.md** — Mermaid charts (VSR, validation loops, Claude Code, collective intelligence)

## [0.1.8] - 2026-06-15

### Added

- Claude Code handoff setting (default **off**): `ri-engine config claude-code on|off`
- Per-run overrides: `--claude-code`, `--no-claude-code`
- Docs: [claude_code_integration.md](docs/claude_code_integration.md)

## [0.1.7] - 2026-06-15

### Fixed

- Compact finalize for simple seed+goal tasks (no benchmark boilerplate bloat)
- Duplicate linguistic leaning: skip register block when gate clause already in objective
- CLI/visualizer: "fitness" not "quality"; remove "production prompt out" copy
- Client summary: mock-mode scope note and baseline-vs-VSR in "what changed"

## [0.1.6] - 2026-06-15

### Fixed

- PyPI publish: bump version after history rewrite (0.1.5 already on PyPI; retagged publishes were failing)
- Publish workflow: verify git tag matches `pyproject.toml` version before upload

## [0.1.5] - 2026-06-15

### Added

- Institutional repo organization: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CREDITS.md`, `CITATION.cff`
- Documentation hub: `docs/README.md`, `config/README.md`, `experiments/README.md`
- GitHub PR template and issue templates (bug, feature)

### Changed

- README restructured for professional overview, project layout, and governance links
- PyPI documentation URL points to `docs/README.md`

## [0.1.4] - 2026-06-15

### Added

- `docs/research_and_citations.md` — credits Raymond Uzwyshyn Ph.D., related prompt-optimization work, BibTeX

### Changed

- Linguistic gate ablation API: `--linguistic-gate`, `--leaning`, `--no-linguistic-gate`, `--diagnostics`
- Baseline vs VSR comparison (`pick_improved_prompt`) with minimum gain and length guardrails
- Rubric: objective alignment, register fit, instruction economy; reduced self-eval weight
- Local ablation experiment: `experiments/run_gate_ablation.py` + fixture cases YAML

### Changed

- Auto gate uses weighted objective (55%) + registry prior (25%) + context (15%); low confidence → mixed
- Persistent macro trait registry disabled by default (`--use-persistent-macro-registry` to enable)
- Selection fitness weights: objective_alignment 0.30, novelty 0.03
- Plateau cycling default max cycles capped at 3
- Mock mode scope disclaimer in README and diagnostics output

## [0.1.3] - 2026-06-15

### Changed

- Refocus README and CLI on seed+goal and VSR + linguistic gate (not persona templates)
- Stop stripping linguistic gate clauses from improved prompt output
- Replace "production-ready" messaging with fitness/VSR terminology

## [0.1.2] - 2026-06-15

### Fixed

- PyPI publish workflow: add `contents: read` permission for private repo checkout

## [0.1.1] - 2026-06-15

### Fixed

- Repo root path resolution for editable installs and CI (`paths.py`)
- PyPI publish workflow now also triggers on `v*` tag push

## [0.1.0] - 2026-06-14

### Added

- Public `improve()` API and `ri-engine` CLI for task prompt improvement
- Seven plug-and-play templates (six business roles + publication agent)
- Offline mock provider — no API key required for demo and templates
- Plateau cycling with session resume and local runbook compilation
- Benchmark demo (`ri-engine demo`) proving F→A quality gains across 6 scenarios
- GitHub Actions CI, devcontainer for Codespaces, and publication documentation
