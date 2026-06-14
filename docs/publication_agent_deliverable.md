## Assumptions

Repository is `russfranky/recursive-intelligence`; goal is public GitHub release with honest claims.

## Gaps found

- [x] LICENSE, CI, devcontainer, pyproject metadata
- [x] Red-team review in `docs/publication.md`
- [x] Stale monorepo URLs — fixed
- [x] `ri-engine demo` spot-check — 6/6 F→A, +385% avg
- [x] Publication agent prompt at `docs/publication_agent_prompt.md`
- [x] Seven templates documented (six business + `publication-agent`)
- [x] PR #1 merged to `main` (2026-06-14)
- [x] Colab badge URL verified
- [ ] Repo visibility **public** — blocked: integration token lacks admin (run `gh repo edit` locally)

## Changes made

| File | Change |
|------|--------|
| `docs/publication.md` | Honest checklist, release steps updated post-merge |
| `docs/publication_agent_deliverable.md` | Final deliverable (this file) |

## Proof run

- **pytest:** pass — 82 tests
- **ri-engine demo:** 6/6 F→A, +385% avg quality
- **CI:** green on Python 3.10–3.12 (PR #1)

## Claims audit

| Claim | Verdict | Notes |
|-------|---------|-------|
| Code is publication-ready on `main` | **Accurate** | All checklist items except visibility flip |
| Repo is publicly visible | **Pending** | Still private until admin runs visibility command |
| 6/6 demo F→A | **Accurate** | Reproducible via `ri-engine demo` |

## Self-eval

- clarity: 0.95
- utility: 0.95
- coherence: 0.95

## Remaining manual steps

1. **You (repo admin):** set visibility public:

```bash
gh repo edit russfranky/recursive-intelligence \
  --visibility public \
  --accept-visibility-change-consequences
```

2. **Optional:** tag `v0.1.0` on `main` (see `docs/publication.md` release steps)
