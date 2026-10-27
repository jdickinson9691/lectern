# Lectern

**Lüdinn Entertainment Campaign Tracker for Encounters, Rules & Navigation**

**Version:** 3.0.4 — Campaign Workflow
**Milestone:** 3.0.4
**Database schema:** v12 (campaign roots and canon workflow over the existing v11 layer)

Lectern is a single evolving Python/PySide6 Windows desktop codebase for D&D 5E campaign planning, combat tracking, and campaign analysis. This package is a clean, Git-ready source baseline.

## Supported Development Environment

- Windows 10/11
- Python 3.13
- PowerShell 5.1 or later

Python 3.13 is the supported development and packaging interpreter. Python 3.14 remains excluded until the complete dependency, GUI, and PyInstaller verification suite passes on it.

## Fresh Setup

```powershell
cd "D:\Ludinn\Development\Lectern"
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

With Inno Setup 6 installed, run `.\build\Build-Installer.ps1` to create the Windows installer under `release/`.

## Development checkout and Git

`D:\Ludinn\Development\Lectern` is the maintained local checkout. Make source changes, run tests, build releases, and push Git commits from this folder. Its `main` branch tracks `origin/main` at the URL below. The older Desktop folder is retained as a historical checkout.

## Source repository

This source is maintained at [jdickinson9691/lectern](https://github.com/jdickinson9691/lectern). The `.gitignore` excludes virtual environments, databases, logs, backups, caches, and generated build output. Private Ashen GM material remains outside this public repository.

## Ashen Company campaign

Use **Start Ashen Company.cmd** for the isolated Ashen database. It enables the campaign canon, draft/review, player export, and Fantasy Grounds Story module workflow without changing ordinary Lectern campaign data. See [Ashen Company on Lectern 3.0](docs/ASHEN_3_0_INTEGRATION.md), the [player guide](docs/campaign/Ashen_Company_Player_Guide.docx), and [class access plan](docs/campaign/CLASS_ACCESS.md). Private GM materials and the live campaign database are kept outside this public repository.

The 3.0.4 Windows installer adds an **Ashen Company** Start menu shortcut and an optional desktop shortcut. It can install the currently approved player Story module into the Fantasy Grounds `modules` folder alongside Lectern Sync in `extensions`. The bundled module is a release snapshot; use **Review & Publish** in Lectern to publish later approvals. The installer does not include the live campaign database or GM guide. The current D: executable and installer are built with the project's Python 3.13 environment. The Campaign Dashboard opens the isolated Ashen workspace or a content window for the selected campaign. Campaign roots use permanent IDs; authoring, review, and player export stay scoped to that root.

## Product and Agent Documentation

The current product status, feature backlog, durable decisions, and delivery
constraints are maintained in [`docs/lectern-prd.md`](docs/lectern-prd.md).

Future agents should begin with:

1. [`docs/agents/README.md`](docs/agents/README.md) for domain ownership.
2. [`docs/contracts/active/`](docs/contracts/active/) for authorized work.
3. [`docs/contracts/templates/agent-contract-template.md`](docs/contracts/templates/agent-contract-template.md)
   when creating a new task contract.
4. [`docs/evidence/README.md`](docs/evidence/README.md) for sanitized acceptance
   evidence rules.

## Current Milestone

Version 3.0.0 begins from the completed 2.9.5 Fantasy Grounds synchronization and campaign-statistics baseline. The kickoff state, verification commands, known behaviors, and first decisions are documented in `docs/LECTERN_3_0_0_KICKOFF.md`.

## Fantasy Grounds Integration

One-way Fantasy Grounds Unity 5E to Lectern synchronization is documented in `docs/FANTASY_GROUNDS_MILESTONE_1.md`. Installation and combined-session operation are covered in `docs/FANTASY_GROUNDS_RUN_TOGETHER.md`. Fantasy Grounds remains the source of truth for imported rules, characters, encounters, and live combat.

## Watermark Coverage

Every navigation page is wrapped by `WatermarkedPage`, which provides a centered, proportional watermark behind that page. Current coverage includes Dashboard, Encounter Builder, Combat Dashboard, Players, Monster Library, Add Monster, Weapons, Armor, Equipment, Magic Items, Spells, Workbook Import, CSV Import/Export, Data Workflow, Error Logs, and Help.
