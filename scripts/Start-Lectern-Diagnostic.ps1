$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Run = Join-Path $Root "run.py"
$Log = Join-Path $Root "launch_diagnostics.txt"
if (-not (Test-Path $Python)) { throw "Run .\scripts\Setup-Development.ps1 first." }
& $Python $Run *>&1 | Tee-Object -FilePath $Log
exit $LASTEXITCODE
