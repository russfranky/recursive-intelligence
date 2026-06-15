# Configuration

YAML configs, benchmark fixtures, and bundled registries for `ri-engine`.

## Layout

```
config/
├── example.yaml              # Reference run (VSR + membrane domains)
├── improve_system_prompts.yaml
├── linguistic_spectrum.yaml  # Category × audience register cells
├── linguistic_registry.json  # Pooled register evidence (bundled)
├── linguistic_pool_report.json
├── macro_trait_registry.json # Persistent traits (opt-in at runtime)
├── templates/                # Plug-and-play CLI templates
├── use_cases/                # Benchmark scenario definitions
├── workflow_self_test.yaml   # Claude Code middle-loop session
├── workflow_self_test_tasks.yaml  # Falsifiable task battery
├── integration.template.yaml # Copy to your repo (ri/config/…)
└── real_world/               # Session templates for plateau runs
```

## Templates (`templates/`)

Pre-filled seed/objective pairs for benchmarks and linguistic-registry pooling. **Not required** for normal use — prefer `--seed` and `--goal`.

```bash
ri-engine templates
ri-engine improve --template code-review
```

## Use cases (`use_cases/`)

Scenario configs used by `ri-engine demo` and expert benchmarks. Each defines seed, objective, domains, and fitness weights.

## Registries

| File | Purpose |
|------|---------|
| `linguistic_registry.json` | Weak prior for linguistic gate (auto mode) |
| `linguistic_spectrum.yaml` | Full-spectrum category cells |
| `macro_trait_registry.json` | Cross-run trait memory (disabled by default) |

## Example

```bash
ri-engine improve --config config/example.yaml
ri-engine real-world workflow   # Claude Code middle-loop self-test
```

See [docs/claude_code_integration.md](../docs/claude_code_integration.md) for the recursive validation loop.
See [docs/integration_patterns.md](../docs/integration_patterns.md) for monorepo integration (Hubzz case study).

See [docs/technical_reference.md](../docs/technical_reference.md) for field reference.
