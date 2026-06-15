#!/usr/bin/env bash
# Add GitHub topics for discoverability (run locally with repo admin access).
set -euo pipefail

OWNER="${GITHUB_OWNER:-russfranky}"
REPO="${REPO_NAME:-recursive-intelligence}"

TOPICS=(
  prompt-engineering
  llm
  system-prompts
  cli
  open-source
  prompt-improvement
  chatgpt
  claude
  copilot
  agents
)

ARGS=()
for t in "${TOPICS[@]}"; do
  ARGS+=(--add-topic "$t")
done

echo "→ Adding topics to $OWNER/$REPO"
gh repo edit "$OWNER/$REPO" "${ARGS[@]}"
echo "✓ Done"
