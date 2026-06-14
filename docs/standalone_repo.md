# Standalone private repository

`ri-engine` lives inside `russfranky/russfranky` today as a subfolder. To move it to **its own private repo** (not nested in your profile README repo):

## One command (on your machine)

```bash
cd recursive-intelligence   # or clone cursor branch first
chmod +x scripts/publish-private-repo.sh
./scripts/publish-private-repo.sh
```

Creates **`russfranky/recursive-intelligence`** (private) by default.

### Different owner or name

```bash
GITHUB_OWNER=ThingsCorp REPO_NAME=ri-engine VISIBILITY=private \
  ./scripts/publish-private-repo.sh
```

Requires `gh auth login` with permission to create repos on that account/org.

## Why the cloud agent could not create it

This environment uses a GitHub **integration token** that can push to existing repos but **cannot** `createRepository`. You must run the script locally once (or create the empty repo in the GitHub UI, then push).

## After the repo exists

1. **Open Codespaces** from `https://github.com/russfranky/recursive-intelligence` (devcontainer is at repo root).
2. **Colab** — set `REPO_URL` in `notebooks/ri_engine_quickstart.ipynb` to the new repo URL.
3. **Optional** — remove or slim `recursive-intelligence/` from `russfranky/russfranky` and link to the new repo in your profile README.

## Install from standalone repo

```bash
git clone git@github.com:russfranky/recursive-intelligence.git
cd recursive-intelligence
pip install -e ".[all]"
ri-engine demo
```
