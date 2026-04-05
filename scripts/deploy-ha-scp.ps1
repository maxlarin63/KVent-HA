# deploy-ha-scp.ps1 — deploy custom_components\kvent to HA via SCP (no WSL needed)
# Reads credentials from .env.ha (git-ignored).

$ErrorActionPreference = "Stop"

$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvFile    = Join-Path $ScriptDir "..\env.ha"   # resolved below to .env.ha
$EnvFile    = Join-Path $ScriptDir "..\.env.ha"

if (-not (Test-Path $EnvFile)) {
    Write-Error "ERROR: .env.ha not found at $EnvFile`nCopy .env.ha.example → .env.ha and fill in values."
    exit 1
}

# Parse KEY=VALUE lines; ignore comments and blanks
Get-Content $EnvFile | ForEach-Object {
    if ($_ -match '^\s*([^#\s][^=]*)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim())
    }
}

$HA_HOST     = $env:HA_HOST
$HA_USER     = if ($env:HA_USER) { $env:HA_USER } else { "root" }
$IDENTITY    = $env:HA_SSH_IDENTITY
$SRC         = Join-Path $ScriptDir "..\custom_components\kvent"
$DEST        = "/config/custom_components/kvent"

if (-not $HA_HOST) { Write-Error "HA_HOST not set in .env.ha"; exit 1 }

$SshArgs = @("-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes")
if ($IDENTITY) { $SshArgs += @("-i", $IDENTITY) }

Write-Host "Deploying to ${HA_USER}@${HA_HOST}:${DEST}"

# Ensure remote directory exists
$mkdirCmd = "mkdir -p `"$DEST`""
ssh @SshArgs "${HA_USER}@${HA_HOST}" $mkdirCmd
if ($LASTEXITCODE -ne 0) {
    Write-Error "ssh failed (exit $LASTEXITCODE). Check HA_HOST, HA_USER, and HA_SSH_IDENTITY in .env.ha."
    exit $LASTEXITCODE
}

# Copy files (scp -r) — excludes __pycache__ via a temp staging copy
$Staging = Join-Path $env:TEMP "kvent_deploy"
if (Test-Path $Staging) { Remove-Item -Recurse -Force $Staging }
Copy-Item -Recurse $SRC $Staging

# Remove __pycache__ from staging
Get-ChildItem -Recurse -Directory -Filter "__pycache__" $Staging | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Filter "*.pyc" $Staging | Remove-Item -Force

# Copy contents of staging into DEST (scp -r STAGING/ would create .../kvent/kvent_deploy/)
$ScpSource = Join-Path $Staging "."
scp @SshArgs -r $ScpSource "${HA_USER}@${HA_HOST}:${DEST}/"
if ($LASTEXITCODE -ne 0) {
    Remove-Item -Recurse -Force $Staging -ErrorAction SilentlyContinue
    Write-Error "scp failed (exit $LASTEXITCODE)."
    exit $LASTEXITCODE
}

Remove-Item -Recurse -Force $Staging

Write-Host "Deploy complete. Quick-restart HA to apply."
