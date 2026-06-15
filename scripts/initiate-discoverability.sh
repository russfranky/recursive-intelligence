#!/usr/bin/env bash
# Initiate discoverability: runbook entry + GitHub topics (topics need repo admin).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PATH="${HOME}/.local/bin:${PATH}"

echo "═══ ri-engine discoverability initiation ═══"
echo ""

# 1. Evolve and approve discoverability prompt to runbook
echo "→ Running discoverability agent (plateau + runbook)…"
ri-engine improve \
  --template discoverability-agent \
  --until-plateau \
  --runbook \
  --runbook-name discoverability-agent \
  --max-cycles 3 \
  --quiet

echo ""
echo "→ Runbook: runbook/RUNBOOK.md"
ri-engine runbook list 2>/dev/null || true

echo ""
# 2. GitHub topics (requires admin token)
echo "→ Setting GitHub topics…"
if "${ROOT}/scripts/set-repo-topics.sh"; then
  echo "✓ Topics applied"
else
  echo "⚠ Topics skipped — run locally as repo admin:"
  echo "  ./scripts/set-repo-topics.sh"
fi

echo ""
echo "═══ Next steps for visitors ═══"
echo "  1. pip install -e ."
echo "  2. ri-engine improve --template customer-support"
echo "  3. Share: docs/discoverability.md"
echo ""
echo "Agent prompt: docs/discoverability_agent_prompt.md"
