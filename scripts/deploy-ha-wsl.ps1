# deploy-ha-wsl.ps1 - invoke WSL rsync deploy from PowerShell
# Calls deploy-ha-wsl-bootstrap.sh which handles the SSH key permissions fix.

$ErrorActionPreference = "Stop"

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$BootstrapSh = "$ScriptDir/deploy-ha-wsl-bootstrap.sh"

# Convert Windows path to WSL path (C:\foo -> /mnt/c/foo)
$WslPath = wsl wslpath -u $BootstrapSh.Replace("\", "/")

Write-Host "Launching WSL deploy bootstrap..."
wsl bash $WslPath

if ($LASTEXITCODE -ne 0) {
    Write-Error "WSL deploy failed (exit $LASTEXITCODE)"
    exit $LASTEXITCODE
}
