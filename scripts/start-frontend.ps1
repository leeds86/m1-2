$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
& (Join-Path $taskRoot '.venv\Scripts\python.exe') -m http.server 5500 --bind 127.0.0.1 --directory frontend
