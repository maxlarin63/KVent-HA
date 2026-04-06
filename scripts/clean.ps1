# clean.ps1 - remove Python caches and build artefacts (Windows)
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force
foreach ($dir in @(".pytest_cache", ".ruff_cache", "dist", "build")) {
    if (Test-Path $dir) { Remove-Item -Recurse -Force $dir }
}
Write-Host "Clean complete."
