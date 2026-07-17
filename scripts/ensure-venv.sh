#!/usr/bin/env bash
# Ensure a working .venv (Python 3.12) at the repo root.
# - No-op if .venv/bin/python already exists.
# - Prefers uv (fast, and installs are hardlinked from the shared uv cache —
#   keep UV_CACHE_DIR on the same filesystem as the repo or uv falls back to copies).
# - Falls back to `python3.12 -m venv` + pip when uv is not installed.
# Used as a `dependsOn` for the "Run tests" and "Lint (ruff)" tasks so a fresh
# checkout works without manual setup.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO_ROOT/.venv"
VENV_PYTHON="$VENV/bin/python"
REQUIREMENTS="$REPO_ROOT/requirements-dev.txt"

if [ -x "$VENV_PYTHON" ]; then
    echo ".venv present, skipping setup."
    exit 0
fi

if command -v uv >/dev/null 2>&1; then
    echo "Creating .venv (Python 3.12, via uv) at $VENV ..."
    uv venv --python 3.12 "$VENV"
    uv pip install --python "$VENV_PYTHON" -r "$REQUIREMENTS"
else
    echo "Creating .venv (Python 3.12) at $VENV ..."
    if ! command -v python3.12 >/dev/null 2>&1; then
        echo "ERROR: neither uv nor python3.12 found on PATH. Install uv (https://docs.astral.sh/uv/) or Python 3.12." >&2
        exit 1
    fi
    python3.12 -m venv "$VENV"

    "$VENV_PYTHON" -m pip install --upgrade pip
    "$VENV_PYTHON" -m pip install -r "$REQUIREMENTS"
fi

echo "OK: .venv ready."
