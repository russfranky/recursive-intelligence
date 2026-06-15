# Repository setup

`recursive-intelligence` is the standalone home for **ri-engine** (Prompt Improvement Studio).

## Quick start

```bash
git clone https://github.com/russfranky/recursive-intelligence.git
cd recursive-intelligence
pip install -e ".[all]"
ri-engine demo
```

Or open a **Codespace** from the repo page — the devcontainer installs dependencies automatically.

---

## Publishing to a new GitHub repo

Use the publish script when you need to push a clean copy to a fresh repo (e.g. fork, org mirror, or visibility change).

```bash
chmod +x scripts/publish-private-repo.sh
./scripts/publish-private-repo.sh
```

Defaults: **`russfranky/recursive-intelligence`** (public by default in publish script).

### Custom owner, name, or visibility

```bash
GITHUB_OWNER=ThingsCorp REPO_NAME=ri-engine VISIBILITY=public \
  ./scripts/publish-private-repo.sh
```

Requires `gh auth login` with permission to create repos on that account/org.

### Why the cloud agent cannot create repos

GitHub integration tokens in cloud agents can push to existing repos but **cannot** `createRepository`. Run the script locally once, or create an empty repo in the GitHub UI and push.

---

## After publishing

1. **Codespaces** — `https://codespaces.new/<owner>/<repo>`
2. **Colab** — set `REPO_URL` in `notebooks/ri_engine_quickstart.ipynb` if the URL changed
3. **CI** — GitHub Actions runs on push/PR (see `.github/workflows/ci.yml`)
4. **Public release** — follow the checklist in [publication.md](publication.md)

---

## Install from any clone

```bash
git clone git@github.com:russfranky/recursive-intelligence.git
cd recursive-intelligence
pip install -e ".[all]"
ri-engine demo
```

## Install from PyPI

```bash
pip install recursive-intelligence
ri-engine improve --template customer-support
```
