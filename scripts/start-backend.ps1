param([switch]$LocalStorage)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
$taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    throw 'Create .venv and install backend/requirements-dev.txt first. See README.md.'
}
if ($LocalStorage) { $env:STORAGE_BACKEND = 'sqlite' }
& $taskPython -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
