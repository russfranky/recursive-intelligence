#!/usr/bin/env bash
# Push a clean copy of recursive-intelligence to a GitHub repo.
# Use for forks, org mirrors, or changing visibility (private | public).
#
# Run on your Mac with your GitHub login:
#   cd path/to/recursive-intelligence
#   ./scripts/publish-private-repo.sh
#
# Optional env:
#   GITHUB_OWNER=russfranky          # or ThingsCorp, etc.
#   REPO_NAME=recursive-intelligence
#   VISIBILITY=private               # private | public

set -euo pipefail

OWNER="${GITHUB_OWNER:-russfranky}"
REPO="${REPO_NAME:-recursive-intelligence}"
VISIBILITY="${VISIBILITY:-public}"
WORKDIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "→ Publishing $WORKDIR to $OWNER/$REPO ($VISIBILITY)"

if ! command -v gh >/dev/null; then
  echo "Install GitHub CLI: https://cli.github.com/"
  exit 1
fi

gh auth status >/dev/null

BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "$BUILD_DIR"' EXIT

rsync -a \
  --exclude '.pytest_cache' \
  --exclude '__pycache__' \
  --exclude '*.egg-info' \
  --exclude 'output/*' \
  --exclude 'prompts/.backup' \
  --exclude 'config/macro_trait_registry.json' \
  "$WORKDIR/" "$BUILD_DIR/"

mkdir -p "$BUILD_DIR/output"
touch "$BUILD_DIR/output/.gitkeep"

cd "$BUILD_DIR"
git init -b main
git add -A
git commit -m "Initial import: ri-engine prompt improvement studio"

if gh repo view "$OWNER/$REPO" >/dev/null 2>&1; then
  echo "→ Repo exists; pushing to origin"
  git remote add origin "https://github.com/$OWNER/$REPO.git"
  git push -u origin main
else
  echo "→ Creating $OWNER/$REPO"
  gh repo create "$OWNER/$REPO" \
    "--$VISIBILITY" \
    --description "Prompt Improvement Studio — recursive VSR engine (ri-engine)" \
    --source=. \
    --remote=origin \
    --push
fi

echo ""
echo "✓ Done: https://github.com/$OWNER/$REPO"
echo "  Codespaces: https://codespaces.new/$OWNER/$REPO"
echo "  Colab: update REPO_URL in notebooks/ri_engine_quickstart.ipynb"
