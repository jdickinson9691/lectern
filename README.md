# Lectern — D&D Campaign Manager

**Version:** 2.9.5 — Workflow and Import Refinement
**Milestone:** 2.9.5 (in progress)
**Database schema:** v6

Lectern is a single evolving Python/PySide6 Windows desktop codebase. This package is a clean, Git-ready source baseline.

## Supported Development Environment

- Windows 10/11
- Python 3.13
- PowerShell 5.1 or later

Python 3.13 is the supported development and packaging interpreter. Python 3.14 remains excluded until the complete dependency, GUI, and PyInstaller verification suite passes on it.

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

## Current Milestone

Version 2.9.5 continues refinement of Lectern's campaign workflow, player import, reference data, documentation, and Windows delivery. The starting state is documented in `docs/LECTERN_2_9_5_HANDOFF.md`.

## Fantasy Grounds Integration

One-way Fantasy Grounds Unity 5E to Lectern synchronization is documented in `docs/FANTASY_GROUNDS_MILESTONE_1.md`. Installation and combined-session operation are covered in `docs/FANTASY_GROUNDS_RUN_TOGETHER.md`. Fantasy Grounds remains the source of truth for imported rules, characters, encounters, and live combat.

## Watermark Coverage

Every navigation page is wrapped by `WatermarkedPage`, which provides a centered, proportional watermark behind that page. Current coverage includes Dashboard, Encounter Builder, Combat Dashboard, Players, Monster Library, Add Monster, Weapons, Armor, Equipment, Magic Items, Spells, Workbook Import, CSV Import/Export, Data Workflow, Error Logs, and Help.
