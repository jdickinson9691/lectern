$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$PythonVersion = "3.13"
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "The Python launcher (py.exe) was not found. Install Python 3.13 for Windows with the launcher enabled, then rerun this script."
}

& py -$PythonVersion -c "import sys; assert sys.version_info[:2] == (3, 13)" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.13 was not found by the Python launcher. Install Python 3.13, then rerun this script."
}

if (Test-Path ".venv") { Remove-Item -Recurse -Force ".venv" }
& py -$PythonVersion -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
Write-Host "Development environment ready with Python $PythonVersion." -ForegroundColor Green
Write-Host "Launch with: .\scripts\Start-Lectern.ps1"
