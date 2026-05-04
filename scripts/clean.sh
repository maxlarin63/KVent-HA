#!/usr/bin/env bash
# clean.sh — remove Python caches and build artefacts
set -euo pipefail
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
rm -rf .pytest_cache .ruff_cache dist build
echo "OK: Clean complete."
