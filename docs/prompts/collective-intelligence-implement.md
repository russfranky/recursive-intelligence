# Collective Intelligence — Implementation Spec (ri-engine refined)

> Refined via ri-engine VSR + hand-merge for actionable build steps.  
> **Status:** v1–v2 implemented in this branch.

## Desired outcome

Ship internal collective intelligence: clarity gate on input, trait export on opt-in, macro registry merge on every run — no raw prompts leave the machine.

---

## 1. Problem & product promise

Vague goals produce polished but untestable prompts. Collective learning must pool **traits** (patterns), not secrets. Personal prompts stay local; macro registry makes the next run smarter for the same objective class.

## 2. User flows

**Inbound:** `assess_objective()` before `improve()`. Kickback if clarity &lt; 45; nudge if &lt; 60. Templates skip gate.

**Outbound:** After plateau + `--share-traits`, write `output/traits/{id}.json` (traits only) and upsert macro registry.

## 3. Trigger conditions

| Trigger | Action |
|---------|--------|
| `improve()` / CLI `--goal` | Clarity gate unless template / `--force-goal` |
| VSR end, fitness ≥ 0.65 | `record_selection()` → macro registry |
| `--share-traits` after plateau | `export_trait_bundle()` → JSON file |
| `--runbook` approve | Runbook + trait sidecar |

## 4. Trait export format

```json
{
  "schema_version": 1,
  "trait_id": "customer-support-20260614T120000Z",
  "objective_class": "customer-support",
  "fitness": 0.91,
  "fitness_delta": 0.05,
  "cycles": 3,
  "plateaued": true,
  "exported_at": "2026-06-14T12:00:00Z",
  "traits": [
    {
      "name": "constraint_first",
      "instruction": "Lead with measurable success criteria",
      "evidence": "utility=0.92",
      "source_generation": 4
    }
  ],
  "forbidden_omitted": ["seed_prompt", "objective_verbatim", "customer_names", "raw_variants"]
}
```

## 5. Implementation map

| File | Symbols | Role |
|------|---------|------|
| `objective_clarity.py` | `assess_objective`, `ObjectiveAssessment` | Upstream gate |
| `trait_parser.py` | `parse_traits` | Parse Retention bullets |
| `macro_registry.py` | `record_selection`, `apply_macro_priors`, `export_trait_bundle` | Pool + read |
| `engine.py` | macro priors + record on complete | VSR hooks |
| `variation.py` | `_strategies_for` | Strategy bias |
| `api.py` | clarity check in `improve()` | Public API |
| `cli.py` | `--share-traits`, `--force-goal`, kickback exit 2 | CLI |

## 6. CLI & API

```bash
ri-engine improve --seed s.txt --goal "When this works, the AI will …"
ri-engine improve --template customer-support --until-plateau --share-traits
ri-engine expert macro-registry
```

```python
from ri_engine import assess_objective, improve, export_trait_bundle

check = assess_objective("make support better")
if check.blocked:
    print(check.kickback_message)
```

## 7. Aggregation (local v2)

- Upsert by `objective_class` + trait name
- Weight = `selection_count * avg_fitness`
- Prune to top 12 traits per class
- Poisoning: min fitness 0.65; no raw text in export

## 8. Merge into VSR

```
assess_objective → apply_macro_priors → [membrane] → variation (strategy order) → selection → retention → record_selection
```

## 9. Phased rollout

| Phase | Status |
|-------|--------|
| v1 Local macro registry + export JSON | **Done** |
| v2 Clarity gate + --share-traits | **Done** |
| v3 Secure aggregation | Planned |
| v4 Encrypted sync | Planned |

## 10. Success metrics

- Clarity kickback on `"be helpful"` / pass on template objectives
- Second run same class shows `macro_priors` in report
- `export_trait_bundle` validates schema; no forbidden fields

---

## ri-engine improved operator prompt (meta)

Use when extending collective intelligence further:

```
You are the ri-engine Collective Intelligence Implementer.

Desired outcome: extend macro trait learning without exporting raw prompts.

Hard constraints:
- Traits only in exports; block seed/objective verbatim
- assess_objective gate stays user-friendly ("When this works…")
- Match macro_registry and language_leanings patterns

Output: minimal diff, tests, file path checklist.
```
