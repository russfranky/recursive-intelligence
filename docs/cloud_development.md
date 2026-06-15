# Cloud development — Codespaces + Colab in tandem

Use **GitHub Codespaces** for the full CLI experience and **Google Colab** for quick Python/API experiments. Same repo, same engine, different surfaces.

---

## GitHub Codespaces (CLI + full repo)

Best for: terminal UI, runbook, plateau cycling, macro registry, committing changes.

### Steps

1. Open the repo on GitHub: [github.com/russfranky/recursive-intelligence](https://github.com/russfranky/recursive-intelligence)
2. Click **Code** → **Codespaces** → **Create codespace on main**
3. Wait for the dev container to build (`pip install -e ".[all]"` runs automatically)
4. In the terminal:

```bash
ri-engine templates
ri-engine improve --template customer-support
ri-engine improve --template customer-support --until-plateau --runbook
ri-engine runbook list
```

### What persists in a Codespace

| Path | Persists until… |
|------|-----------------|
| `output/` | Codespace deleted or rebuilt |
| `runbook/` | Same |
| `config/macro_trait_registry.json` | Same |

Download artifacts before deleting a codespace if you need them locally.

### Optional: real LLM provider

```bash
export OPENAI_API_KEY=sk-...
ri-engine improve --template sales-outreach --provider openai
```

Add the key under **Codespaces secrets** (repo or user) for reuse across sessions.

---

## Google Colab (Python API + notebooks)

Best for: sharing demos, calling `improve()` from cells, quick experiments without a local install.

### Steps

1. Open the notebook:
   - [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/russfranky/recursive-intelligence/blob/main/notebooks/ri_engine_quickstart.ipynb)
   - Or upload `notebooks/ri_engine_quickstart.ipynb` manually
2. **Runtime → Run all** (first run clones the repo and installs)
3. Edit seed/objective cells and re-run improvement cells

Default provider is **mock** (offline, no API key).

### Optional: OpenAI in Colab

```python
import os
from google.colab import userdata
os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY")
# then improve(..., provider="openai")
```

Store the key in Colab **Secrets** (key icon in the left sidebar).

---

## Using both in tandem (recommended workflow)

```mermaid
flowchart LR
  A[Colab notebook] -->|prototype objective + seed| B[improve API]
  B -->|copy improved_prompt| C[Codespaces CLI]
  C -->|plateau + runbook| D[runbook/RUNBOOK.md]
  D -->|commit or download| E[Next AI session]
```

| Task | Use |
|------|-----|
| Draft desired outcome + test `improve()` quickly | **Colab** |
| Run terminal UI, plateau, runbook | **Codespaces** |
| Inspect macro trait pool | **Codespaces** — `ri-engine expert macro-registry` |
| Share a demo link with non-developers | **Colab** badge |
| Edit engine code + run tests | **Codespaces** — `pytest tests/ -q` |

### Handoff: Colab → Codespaces

1. In Colab, copy `result.improved_prompt` and your objective string.
2. In Codespaces, save seed to a file and continue with CLI:

```bash
cat > my_seed.txt << 'EOF'
<paste improved prompt from Colab>
EOF

ri-engine improve \
  --seed my_seed.txt \
  --goal "When this works, the AI will resolve billing in one conversation" \
  --until-plateau --runbook --runbook-name billing-support
```

### Handoff: Codespaces → Colab

1. Download `output/your_improved_prompt.json` or copy from terminal.
2. Paste into Colab as the next `seed_prompt` for another API pass or comparison.

---

## Free tier notes

| Platform | Cost | Limits |
|----------|------|--------|
| **Codespaces** | Free monthly quota for personal accounts | Hours/month; sleeps when idle |
| **Colab** | Free CPU runtime | Session timeouts; GPU not needed for mock provider |

Both work with the **mock provider** at $0 API cost.

---

## Troubleshooting

**Codespaces: `ri-engine: command not found`**  
Re-run: `pip install -e ".[all]"` from the repo root.

**Colab: clone fails**  
Check repo is public or Colab has access; update `REPO_URL` in the notebook if you forked.

**Colab: package not found after install**  
Restart runtime after install cell, then re-run import cells.

**Different results Colab vs Codespaces**  
Same code + same `provider` + same seed/objective should match. Mock LLM uses deterministic fallbacks; set explicit `--rounds` / `max_generations` for parity.
