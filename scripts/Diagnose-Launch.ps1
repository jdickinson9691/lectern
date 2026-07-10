$ErrorActionPreference = 'Continue'
Set-Location (Join-Path $PSScriptRoot '..')
$log = Join-Path (Get-Location) 'launch_diagnostics.txt'
"Lectern launch diagnostic - $(Get-Date -Format o)" | Set-Content $log

$python = Join-Path (Get-Location) '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    "[FAIL] Virtual environment Python not found: $python" | Tee-Object -FilePath $log -Append
    "Create it with: .\scripts\Setup-Development.ps1 (requires Python 3.13)" | Tee-Object -FilePath $log -Append
    exit 2
}

& $python scripts\diagnose_launch.py 2>&1 | Tee-Object -FilePath $log -Append
$diagCode = $LASTEXITCODE
if ($diagCode -ne 0) {
    "Diagnostic checks failed with exit code $diagCode" | Tee-Object -FilePath $log -Append
    exit $diagCode
}

"Launching GUI with captured output..." | Tee-Object -FilePath $log -Append
& $python run.py 2>&1 | Tee-Object -FilePath $log -Append
exit $LASTEXITCODE
