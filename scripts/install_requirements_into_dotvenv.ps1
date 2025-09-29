# Requires PowerShell
# Installs project requirements into the local .venv virtual environment.
# Usage (from repository root):
#   powershell -ExecutionPolicy Bypass -File .\scripts\install_requirements_into_dotvenv.ps1

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$requirements = Join-Path $repoRoot "requirements.txt"

if (-not (Test-Path $venvPython)) {
    Write-Error ".venv not found or python.exe missing at $venvPython. Create it first, e.g.:`n  py -3.13 -m venv .venv`nThen re-run this script."
}

if (-not (Test-Path $requirements)) {
    Write-Error "requirements.txt not found at $requirements"
}

Write-Host "Upgrading pip/setuptools/wheel in .venv..." -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip setuptools wheel

Write-Host "Installing requirements from requirements.txt into .venv..." -ForegroundColor Cyan
& $venvPython -m pip install -r $requirements

Write-Host "Done. The .venv environment now has the required packages installed." -ForegroundColor Green
