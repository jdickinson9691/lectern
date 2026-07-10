# Verification Report — Lectern v2.9.2

## Automated checks completed

- `python -m compileall app scripts run.py`
- `python scripts/diagnose_launch.py`
- `python scripts/smoke_test.py`
- Qt offscreen launch with `LECTERN_TEST_AUTOCLOSE_MS` to construct and display the main window, then exit cleanly.
- Clean database initialization and schema-v4 migration metadata.
- Seed workbook/resource/help/icon/watermark path checks.
- Watermark image load check through `QPixmap`.
- Release archive content audit for excluded caches and runtime files.

## Startup defect diagnosis

The uploaded source package exits immediately when its active Python environment does not contain PySide6. Its original `run.py` imported the GUI module before logging was configured, so this failure produced only a console traceback and no application log or dialog. The package also omitted `app/resources` from the PyInstaller specification, which would prevent the watermark and icon from loading in a packaged build.

v2.9.2 corrects both defects and adds a PowerShell diagnostic workflow.

## Windows commands to complete acceptance

```powershell
cd "C:\Users\jdick\OneDrive\Desktop\Lectern"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\scripts\Diagnose-Launch.ps1
```

After source launch succeeds:

```powershell
.\build\Build.ps1
.\dist\Lectern\Lectern.exe
```

Then compile `installer\CampaignManager.iss` in Inno Setup and launch the installed application.

## Pending manual verification

- Player CRUD through the GUI.
- Monster CRUD through the GUI.
- Encounter CRUD through the GUI.
- Backup/restore/reset/reseed through the GUI.
- CSV preview/import through the GUI.
- In-app log viewer.
- Windows executable and installer behavior.
- Watermark appearance at multiple resolutions.

These checks cannot be conclusively certified in a non-Windows execution environment.
