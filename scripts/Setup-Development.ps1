$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = $null
foreach ($Version in @("3.12", "3.13")) {
    & py -$Version -c "import sys" 2>$null
    if ($LASTEXITCODE -eq 0) { $Python = $Version; break }
}
if (-not $Python) {
    throw "Python 3.12 or 3.13 is required. Install Python 3.12, then rerun this script."
}

if (Test-Path ".venv") { Remove-Item -Recurse -Force ".venv" }
& py -$Python -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
Write-Host "Development environment ready with Python $Python." -ForegroundColor Green
Write-Host "Launch with: .\scripts\Start-Lectern.ps1"
