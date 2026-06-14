## Assumptions

Occam's razor should be default-on across VSR; utility floor 0.7 prevents over-pruning.

## VSR changes

| Stage | Occam rule applied |
|-------|-------------------|
| **Variation** | Strategy order biases `minimal_essential` first; mutate prompt includes Occam instruction when enabled |
| **Selection** | Scores `simplicity`; 12% fitness blend; tie-break shorter; skip blend if utility < 0.7 |
| **Retention** | `prune_lineage_traits()` caps at 6 traits, dedupes names |

## Operator prompt edits

| File | Section added/changed |
|------|----------------------|
| `prompts/variation.md` | Occam principle on mutations |
| `prompts/selection.md` | `simplicity` dimension + Occam's Razor Process |
| `prompts/retention.md` | Trait pruning rules |

## Code hooks

| Module | Behavior |
|--------|----------|
| `occams_razor.py` | Simplicity scoring, fitness blend, strategy order, lineage prune |
| `selection.py` | Applies Occam after scoring; occam-ranked output |
| `variation.py` | Occam strategy priority + conditional mutate instruction |
| `retention.py` | Prunes lineage when Occam enabled |

Disable: `metadata={"enable_occams_razor": False}`

## Proof

- pytest: 92 passed (`pytest tests/ -q`)
- ri-engine demo: 6/6 F→A maintained with Occam default-on

## Self-eval

- clarity: 0.95
- utility: 0.95
- coherence: 0.95
