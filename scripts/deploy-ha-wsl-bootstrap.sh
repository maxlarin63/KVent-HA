#!/usr/bin/env bash
# deploy-ha-wsl-bootstrap.sh
# Copies an SSH identity from /mnt/c (Windows FS, mode 0777) into ~/.ssh/
# with the correct permissions (0600) so OpenSSH accepts it, then delegates
# to deploy-ha-rsync.sh.
#
# Usage: called automatically by deploy-ha-wsl.ps1 — not meant to run directly.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env.ha"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found."
  exit 1
fi

# shellcheck source=/dev/null
source "$ENV_FILE"

if [[ -n "${HA_SSH_IDENTITY:-}" ]]; then
  # Convert Windows path to WSL path if needed
  WSL_KEY="${HA_SSH_IDENTITY/C:\//\/mnt\/c\/}"
  WSL_KEY="${WSL_KEY//\\/\/}"

  SAFE_KEY="$HOME/.ssh/ha_deploy_kvent"
  mkdir -p "$HOME/.ssh"
  cp "$WSL_KEY" "$SAFE_KEY"
  chmod 600 "$SAFE_KEY"

  export HA_SSH_IDENTITY="$SAFE_KEY"
fi

exec "$SCRIPT_DIR/deploy-ha-rsync.sh"
