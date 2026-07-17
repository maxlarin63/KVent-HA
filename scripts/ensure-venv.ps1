# Ensure a working .venv (Python 3.12) at the repo root.
# - No-op if .venv\Scripts\python.exe already exists.
# - Prefers uv (fast, and installs are hardlinked from the shared uv cache —
#   keep UV_CACHE_DIR on the same drive as the repo or uv falls back to copies).
# - Falls back to `py -3.12 -m venv` + pip when uv is not installed.
# Used as a `dependsOn` for the "Run tests" and "Lint (ruff)" tasks so a fresh
# checkout works without manual setup.

$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $RepoRoot '.venv'
$VenvPython = Join-Path $Venv 'Scripts\python.exe'
$Requirements = Join-Path $RepoRoot 'requirements-dev.txt'

if (Test-Path $VenvPython) {
    Write-Host ".venv present, skipping setup."
    exit 0
}

if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "Creating .venv (Python 3.12, via uv) at $Venv ..."
    & uv venv --python 3.12 $Venv
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & uv pip install --python $VenvPython -r $Requirements
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "Creating .venv (Python 3.12, via py launcher) at $Venv ..."
    & py -3.12 -m venv $Venv
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create .venv with 'py -3.12 -m venv'. Install uv (https://docs.astral.sh/uv/) or Python 3.12."
        exit 1
    }

    & $VenvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & $VenvPython -m pip install -r $Requirements
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "OK: .venv ready."
