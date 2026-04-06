# deploy-ha-scp.ps1 - deploy custom_components\kvent to HA via SCP (no WSL needed)
# Reads credentials from .env.ha (git-ignored).

$ErrorActionPreference = "Stop"

$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvFile    = Join-Path $ScriptDir "..\env.ha"   # resolved below to .env.ha
$EnvFile    = Join-Path $ScriptDir "..\.env.ha"

if (-not (Test-Path $EnvFile)) {
    Write-Error "ERROR: .env.ha not found at $EnvFile`nCopy .env.ha.example to .env.ha and fill in values."
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

$ManifestPath = Join-Path $ScriptDir "..\custom_components\kvent\manifest.json"
$Version = ""
if (Test-Path $ManifestPath) {
    try {
        $Version = (Get-Content -Raw $ManifestPath | ConvertFrom-Json).version
    } catch {
        $Version = ""
    }
}

$SshArgs = @("-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes")
if ($IDENTITY) { $SshArgs += @("-i", $IDENTITY) }

if ($Version) {
    Write-Host "Deploying KVent v$Version to ${HA_USER}@${HA_HOST}:${DEST}"
} else {
    Write-Host "Deploying to ${HA_USER}@${HA_HOST}:${DEST}"
}

# Ensure remote directory exists
$mkdirCmd = "mkdir -p `"$DEST`""
ssh @SshArgs "${HA_USER}@${HA_HOST}" $mkdirCmd
if ($LASTEXITCODE -ne 0) {
    Write-Error "ssh failed (exit $LASTEXITCODE). Check HA_HOST, HA_USER, and HA_SSH_IDENTITY in .env.ha."
    exit $LASTEXITCODE
}

# Copy files (scp -r) - excludes __pycache__ via a temp staging copy
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

Write-Host "Deploy complete."

# Optional: restart Home Assistant Core via REST API (same as UI "Restart")
$HaHttpUrl = $env:HA_HTTP_URL
$HaToken = $env:HA_TOKEN
if ($HaHttpUrl -and $HaToken) {
    $HaHttpUrl = $HaHttpUrl.TrimEnd('/')
    $uri = "$HaHttpUrl/api/services/homeassistant/restart"
    $headers = @{
        Authorization = "Bearer $HaToken"
        "Content-Type" = "application/json"
    }
    try {
        Write-Host "Restarting Home Assistant Core via $uri ..."
        # Use http:// on LAN if cert errors (Windows PowerShell 5.1 has no -SkipCertificateCheck).
        Invoke-RestMethod -Method Post -Uri $uri -Headers $headers -Body '{}'
        Write-Host "Restart requested. HA will be back in about a minute."
    } catch {
        $httpCode = $null
        if ($_.Exception.Response) {
            $httpCode = [int]$_.Exception.Response.StatusCode
        }
        $msg = $_.Exception.Message
        # HA often tears down HTTP before the proxy finishes; 502/504 or connection reset is usually fine.
        $benign = ($httpCode -eq 504 -or $httpCode -eq 502) -or
            ($msg -match '504|502|Gateway Timeout|Bad Gateway|forcibly closed|Connection reset|underlying connection')
        if ($benign) {
            Write-Host "Restart likely started (HA or proxy closed the request while restarting). Give it a minute."
        } else {
            Write-Warning "Deploy succeeded but HA restart failed: $msg. Edit HA_HTTP_URL / HA_TOKEN in .env.ha or restart manually."
            exit 1
        }
    }
} elseif ($HaHttpUrl -or $HaToken) {
    Write-Warning "Set both HA_HTTP_URL and HA_TOKEN in .env.ha for automatic restart after deploy (Profile -> Security -> Long-Lived Access Tokens)."
}
