$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$PythonW = Join-Path $Root ".venv\Scripts\pythonw.exe"
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Run = Join-Path $Root "run.py"

if (-not (Test-Path $Python)) {
    throw "Virtual environment not found. Run .\scripts\Setup-Development.ps1 first."
}

# pythonw avoids an unnecessary console window for the desktop application.
$Executable = if (Test-Path $PythonW) { $PythonW } else { $Python }
Start-Process -FilePath $Executable -ArgumentList ('"' + $Run + '"') -WorkingDirectory $Root
