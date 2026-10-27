$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Run .\scripts\Setup-Development.ps1 first.'
}
& $python .\scripts\installer_config_test.py
if ($LASTEXITCODE -ne 0) { throw 'Installer configuration test failed.' }
& .\build\Build.ps1
if ($LASTEXITCODE -ne 0) { throw 'Application build failed.' }

$compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if (-not $compiler) {
    $candidate = Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'
    if (Test-Path -LiteralPath $candidate) { $compiler = $candidate }
}
if (-not $compiler) { throw 'Inno Setup 6 compiler (ISCC.exe) was not found.' }
& $compiler .\installer\CampaignManager.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }
Write-Host 'Installer ready: .\release\Lectern_v3_0_2_Ashen_Company_Setup.exe' -ForegroundColor Green
