# Experiments

Reproducible **local** experiments — no API key required (mock provider).

## Linguistic gate ablation

Tests whether register selection measurably changes prompt fitness under the engine's offline rubric.

```bash
python3 experiments/run_gate_ablation.py
```

| File | Description |
|------|-------------|
| `gate_ablation_cases.yaml` | Five seed/goal fixtures with expected leanings |
| `run_gate_ablation.py` | Runs 8 gate conditions × 5 cases; writes summary |
| `gate_ablation_results.json` | Generated output (gitignored) |

### Conditions

`off`, `neutral`, `auto`, `plain`, `latinate`, `mixed`, `technical`, `conversational`

### Honest scope

Ablation results reflect **structural rubric scores**, not live LLM task success. Use outcomes to tune or simplify the linguistic gate — not as product claims.

See [docs/research_and_citations.md](../docs/research_and_citations.md).
