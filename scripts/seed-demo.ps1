$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
  throw "Python virtual environment is missing. Run .\\scripts\\setup.ps1 first."
}

Push-Location $repoRoot
try {
  & $venvPython .\seed_demo.py
}
finally {
  Pop-Location
}
