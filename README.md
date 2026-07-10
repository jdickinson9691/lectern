# Lectern — D&D Campaign Manager

**Version:** 2.9.3 — Fresh Baseline and Watermark Verification  
**Database schema:** v4

Lectern is a single evolving Python/PySide6 Windows desktop codebase. This package is a clean, Git-ready source baseline.

## Supported Development Environment

- Windows 10/11
- Python 3.12 or 3.13
- PowerShell 5.1 or later

Python 3.14 is intentionally excluded from the validated baseline.

## Fresh Setup

```powershell
cd "C:\Users\jdick\OneDrive\Desktop\Lectern"
powershell -ExecutionPolicy Bypass -File .\scripts\Setup-Development.ps1
```

## Launch

```powershell
.\scripts\Start-Lectern.ps1
```

This uses `pythonw.exe` so a separate Python console is not opened. For captured console diagnostics, use:

```powershell
.\scripts\Start-Lectern-Diagnostic.ps1
```

## Verification

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Diagnose-Launch.ps1
```

## Windows Build

```powershell
.\build\Build.ps1
.\dist\Lectern\Lectern.exe
```

## Git Initialization

```powershell
git init
git add .
git commit -m "Lectern v2.9.3 fresh baseline"
git branch -M main
git remote add origin <YOUR-REPOSITORY-URL>
git push -u origin main
```

The `.gitignore` excludes virtual environments, databases, logs, backups, caches, and generated build output.

## Watermark Coverage

Every navigation page is wrapped by `WatermarkedPage`, which provides a centered, proportional watermark behind that page. Current coverage includes Dashboard, Encounter Builder, Combat Dashboard, Players, Monster Library, Add Monster, Weapons, Armor, Equipment, Magic Items, Spells, Workbook Import, CSV Import/Export, Data Workflow, Error Logs, and Help.
