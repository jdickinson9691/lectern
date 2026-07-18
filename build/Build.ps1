$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Run .\scripts\Setup-Development.ps1 first." }
& $Python -m PyInstaller --noconfirm --clean --workpath .pyinstaller_build --distpath dist .\build\CampaignManager.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE." }
& .\scripts\Build-FantasyGroundsExtension.ps1 -OutputDirectory .\dist\Lectern\FantasyGrounds
if ($LASTEXITCODE -ne 0) { throw "Fantasy Grounds extension build failed with exit code $LASTEXITCODE." }
Write-Host "Build complete: .\dist\Lectern\Lectern.exe" -ForegroundColor Green
Write-Host "Fantasy Grounds companion: .\dist\Lectern\FantasyGrounds\LecternSync.ext" -ForegroundColor Green
