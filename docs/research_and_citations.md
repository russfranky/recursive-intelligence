# Research & Citations

This project started from public writing by **Raymond Uzwyshyn Ph.D.** on agentic AI, recursion, and **Darwinian selection environments** — especially the **Variation → Selection → Retention (VSR)** loop as an executable pattern for software and prompts, not only biology.

The earliest repo fixtures (`config/example.yaml`, `config/use_cases/research_analyst.yaml`) cite:

> Uzwyshyn — Agentic AI, Recursion, Biology and Selection Environments

---

## Primary inspiration (LinkedIn)

| Title | Author | Date | Link |
|-------|--------|------|------|
| **The AI Agentic Substrate: Life Inside the Recursive Zone** | Raymond Uzwyshyn Ph.D. | Feb 2026 | [LinkedIn Pulse](https://www.linkedin.com/pulse/ai-agentic-substrate-life-inside-recursive-zone-uzwyshyn-ph-d--zohyc) |
| **Agentic AI, Recursion, Biology and Our New Selection Environments** | Raymond Uzwyshyn Ph.D. | Feb 2026 | [Author articles](https://www.linkedin.com/in/rayuzwyshyn/recent-activity/articles/) |

From *The AI Agentic Substrate*, the engine takes these ideas directly:

1. **Selection environment** — pressures that determine which variants survive (in biology: ecology; here: fitness scoring and goal alignment).
2. **Recursive reality** — output becomes the next input (here: retained traits and plateau re-seeding).
3. **Darwinian logic** — **Variation** (generate candidates) → **Selection** (score and rank) → **Retention** (carry forward winners) → repeat.

The Jacquard loom ↔ binary programmability example in that article is also reflected in the research-analyst use case and membrane-bridge cross-domain prompts.

**Author profile:** [linkedin.com/in/rayuzwyshyn](https://www.linkedin.com/in/rayuzwyshyn)

---

## What this repository implements

| Concept (from inspiration) | Implementation in `ri-engine` |
|----------------------------|-------------------------------|
| VSR loop | `variation.py` → `selection.py` → `retention.py` → repeat |
| Selection environment design | `RunConfig`, fitness weights, rubric, Occam's razor |
| Hyper-accelerated iteration | Mock/offline loop; optional real LLM providers |
| Cross-domain “membrane” | `membrane.py`, domain hints in YAML configs |
| Linguistic / register context | `language_leanings.py` (experimental; ablation in `experiments/`) |
| Macro trait memory | `macro_registry.py` (run-local by default) |

This is an **engineering experiment**, not a reproduction of Uzwyshyn's full agentic-substrate thesis. Mock mode scores **structural prompt quality** locally; it does **not** prove downstream LLM task success.

---

## Related work — prompt optimization & recursive improvement

The VSR loop sits in a broader literature on **search-based prompt improvement**:

| Work | Reference | Relation to this repo |
|------|-----------|------------------------|
| **Automatic Prompt Engineer (APE)** | Zhou et al., [arXiv:2211.01910](https://arxiv.org/abs/2211.01910) (2022) | Generate + select prompt candidates |
| **PromptBreeder** | Fernando et al., [arXiv:2309.16797](https://arxiv.org/abs/2309.16797) (2023) | Evolutionary prompt mutation and selection |
| **OPRO** | Yang et al., [arXiv:2306.03435](https://arxiv.org/abs/2306.03435) (2023) | LLM-as-optimizer over prompt space |
| **DSPy** | Khattab et al., [dspy.ai](https://dspy.ai/) | Compile / optimize prompt modules |
| **PRefLexOR** | Liedtke et al., [npj AI](https://www.nature.com/articles/s44387-025-00003-z) (2025) | Recursive preference-based language refinement |

**Generalized selection / VSR beyond biology:** selection as variation + retention of what works appears in complex-systems and cognitive-science writing (e.g. generalized Darwinism and ESS stability). Uzwyshyn's LinkedIn framing connects that logic to agentic AI at human-readable speed.

---

## Linguistic gate (register research)

The **plain / Latinate / mixed** register axis and pooled linguistic registry are **local research extensions** — inspired by readability and plain-language practice, not claimed as validated in Uzwyshyn's original posts.

Status: **experimental prior** (see `experiments/run_gate_ablation.py`). Ablation is required before treating register selection as a core advantage.

---

## How to cite this project

```bibtex
@software{recursive_intelligence_2026,
  title  = {Recursive Intelligence Engine (ri-engine)},
  author = {russfranky},
  year   = {2026},
  url    = {https://github.com/russfranky/recursive-intelligence},
  note   = {Prompt improvement via Variation-Selection-Retention;
            inspired by Raymond Uzwyshyn's writing on agentic AI and selection environments}
}
```

If you use ideas from the primary inspiration, please also cite Raymond Uzwyshyn's LinkedIn articles listed above.

---

## Acknowledgments

- **Raymond Uzwyshyn Ph.D.** — original public framing of agentic AI, recursion, biology, and selection environments (LinkedIn, 2026), which seeded this codebase's VSR architecture and naming.
- **Charles Darwin / generalized selection** — VSR as executable iteration logic (variation, selection, retention).
- **Open-source prompt-optimization community** — APE, PromptBreeder, OPRO, DSPy, and related work cited above.
