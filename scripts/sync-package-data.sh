#!/usr/bin/env bash
# Copy config/ and prompts/ into the package for PyPI wheels.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/src/ri_engine/bundled"

rm -rf "$DEST"
mkdir -p "$DEST"
cp -a "$ROOT/config" "$DEST/"
cp -a "$ROOT/prompts" "$DEST/"
rm -f "$DEST/config/macro_trait_registry.json"

echo "→ Synced package data to $DEST"
