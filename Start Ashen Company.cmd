@echo off
setlocal
set "LECTERN_DATA_DIR=%LOCALAPPDATA%\DND5ECampaignManager-AshenCompany"
set "LECTERN_ASHEN_COMPANY=1"
set "LECTERN_CANON_CAMPAIGN_ID=CAM-ASHEN-0001"
cd /d "%~dp0"
if exist "Lectern.exe" (
    "Lectern.exe"
) else if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run.py
) else (
    python run.py
)
if errorlevel 1 pause
