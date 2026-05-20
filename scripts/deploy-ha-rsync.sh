#!/usr/bin/env bash
# deploy-ha-rsync.sh — deploy custom_components/kvent to HA over SSH/rsync
# Reads credentials from .env.ha (git-ignored).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env.ha"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found. Copy .env.ha.example → .env.ha and fill in values."
  exit 1
fi

# shellcheck source=/dev/null
source "$ENV_FILE"

HA_HOST="${HA_HOST:?HA_HOST not set in .env.ha}"
HA_USER="${HA_USER:-root}"
DEST="/config/custom_components/kvent"

# Pin MACs=hmac-sha2-256-etm: Advanced SSH addon offers umac-128-etm first
# and some OpenSSH clients pick it by default, but that pairing reliably
# corrupts MAC mid-stream ("Corrupted MAC on input"). SHA-256 EtM is clean.
SSH_OPTS=(-o StrictHostKeyChecking=no -o BatchMode=yes -o MACs=hmac-sha2-256-etm@openssh.com)
if [[ -n "${HA_SSH_IDENTITY:-}" ]]; then
  SSH_OPTS+=(-i "$HA_SSH_IDENTITY")
fi

echo "→ Deploying to ${HA_USER}@${HA_HOST}:${DEST}"

rsync -avz --delete \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  -e "ssh ${SSH_OPTS[*]}" \
  "$SCRIPT_DIR/../custom_components/kvent/" \
  "${HA_USER}@${HA_HOST}:${DEST}/"

echo "✓ Deploy complete. Quick-restart HA to apply."
