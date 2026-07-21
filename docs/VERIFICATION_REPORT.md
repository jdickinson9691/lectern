# Verification Report — Lectern v3.0.0

Status: **In progress**

Milestone: **Verification and Stabilization**

Database schema: **v10**

This is the acceptance record for v3.0.0. Mark an item complete only after recording its date, environment, and evidence. Automated checks do not replace manual Windows checks.

## Automated baseline

| Check | Status | Evidence |
|---|---|---|
| Source compilation | Passed | Python 3.13.14; all current application and regression modules compiled successfully on 2026-07-21. |
| Launch diagnostics | Passed | Dependencies, resources, and clean schema-v10 initialization passed on 2026-07-21. |
| Database/seed/data smoke test | Passed | The complete nine-script regression suite, including seed, campaign, combat, Fantasy Grounds, layout, Help, and installer checks, passed on 2026-07-21. |
| Qt offscreen startup | Passed | The rebuilt packaged application constructed and exited cleanly using the test autoclose hook on 2026-07-21. |
| No unresolved merge markers | Passed | Tracked source and documentation search returned no markers on 2026-07-21. |
| Version metadata consistency | Passed | Application, package, diagnostic, and installer metadata identify v3.0.0. |

## Startup and presentation

- [ ] Source starts cleanly.
- [x] Packaged executable starts cleanly.
- [x] Installed application starts cleanly.
- [x] Icon, help, seed workbook, and watermark resources load when packaged.
- [ ] All 16 screens show a centered, proportional watermark at minimum, default, and maximized sizes.
- [ ] Watermarks do not obscure controls or capture pointer input.

## Core CRUD

If an operation is not implemented, record it as a blocking defect.

| Module | Create | Read | Update | Delete | Duplicate | Search | Filter |
|---|---|---|---|---|---|---|---|
| Players | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| Monsters | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| Encounters | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |

## Data workflows and diagnostics

- [ ] Backup creates a readable copy.
- [ ] Restore creates a safety backup and restores the selected database.
- [ ] Reset creates a safety backup and an empty schema-v10 database.
- [ ] Reseed restores bundled reference data.
- [ ] CSV export works for one and all tables.
- [ ] CSV preview correctly classifies New, Modified, Unchanged, Duplicate, and Error.
- [ ] Duplicate and Error rows block CSV commit.
- [ ] Valid CSV import requires confirmation.
- [ ] Logs are generated and readable in Error Logs.
- [ ] Startup failures produce diagnostics and a user-facing error.

## Packaging and installer

- [x] `build/Build.ps1` produces `dist/Lectern/Lectern.exe`.
- [x] Packaged resources are present.
- [x] Inno Setup produces `release/Lectern_v3_0_0_Setup.exe`.
- [x] Desktop and Start Menu shortcuts are created and resolve to the installed application.

## Evidence log

| Date | Environment | Check(s) | Result / artifact / defect |
|---|---|---|---|
| 2026-07-10 | Windows workspace | Initial automated run | Blocked: `.venv` points to missing `pythoncore-3.12-64/python.exe`; commands exit 101. |
| 2026-07-10 | Windows workspace | Interpreter baseline | Project standardized on Python 3.13; environment recreation pending installation/discovery of 3.13. |
| 2026-07-10 | Windows 11, Python 3.13.14 | Environment | Recreated `.venv`; installed PySide6 6.11.1, SQLAlchemy 2.0.51, openpyxl 3.1.5, and PyInstaller 6.21.0. |
| 2026-07-10 | Windows 11, Python 3.13.14 | Automated baseline | Compilation, diagnostics, smoke test, and Qt offscreen startup all exited 0. |
| 2026-07-10 | Windows 11, PyInstaller 6.21.0 | Packaged executable | Corrected project-root calculation and added the dynamic `app.main` import; rebuild succeeded, required resources were present, and packaged startup exited 0. |
| 2026-07-10 | Windows 11, Inno Setup 6.7.3 | Installer | Compiled `Lectern_v2_9_4_Setup.exe`; isolated silent install exited 0, installed payload and both shortcuts were present, installed startup exited 0, and test uninstall exited 0. |
| 2026-07-21 | Windows 11; Python launcher 3.14.6; project Python 3.13.14; PySide6 6.11.1; PyInstaller 6.21.0; VS Code 1.129.1; Git 2.55.0; PowerShell 5.1; Inno Setup 6.7.1 | Development-tool compatibility audit | `pip check` reported no broken requirements; all nine regression scripts passed; the application and Fantasy Grounds extension rebuilt; the v3.0.0 installer compiled; and packaged startup exited 0. The project remains intentionally isolated on its validated Python 3.13 environment. |
| 2026-07-21 | Windows 11, PyInstaller 6.21.0, Inno Setup 6.7.3 | Manual-campaign foundation package | Rebuilt the application and Fantasy Grounds extension from commit `ceb8859`; packaged startup exited 0; and `Lectern_v3_0_0_Setup.exe` compiled successfully with product version 3.0.0 and SHA-256 `FEBDFA7F65B07EFA38F6B715011DBC621B03CE88E642E8E8962F3E068D311E8D`. |
| 2026-07-21 | Windows 11, Python 3.13.14, Qt offscreen | Guided local campaign setup | Player and monster CSV validation/import, duplicate blocking, persistent party selection, party-choice retention, campaign-scoped opening encounter creation, and automatic party insertion passed focused coverage. Source compilation and all nine regression scripts passed, including the unchanged Fantasy Grounds synchronization suite. |
| 2026-07-21 | Windows 11, Python 3.13.14, Qt offscreen | Combat Dashboard workspace | Verified the draggable Campaign Entities / Combat Session Log workspace opens at a 25/75 split, keeps the entity table and controls on the left, and retains structured journal search, filters, grouping, and Fantasy Grounds behavior on the right. All nine regression scripts and source compilation passed. |
| 2026-07-21 | Windows 11, PyInstaller 6.21.0, Inno Setup 6.7.3 | Combined Milestone 2 package | Rebuilt the application and Fantasy Grounds extension; packaged startup exited 0; and `Lectern_v3_0_0_Setup.exe` compiled successfully with product version 3.0.0 and SHA-256 `BDE54A91B529096B82B94C79DCE2C242A4A50E6C635E1CD6A0C3DEC7B8DC16CE`. |

## Release decision

Declare v3.0.0 complete only when all checks pass, no startup errors or syntax/merge issues remain, and every blocking defect is resolved or explicitly removed from scope.
