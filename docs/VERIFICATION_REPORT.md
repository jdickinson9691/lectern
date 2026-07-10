# Verification Report — Lectern v2.9.4

Status: **In progress**

Milestone: **Verification and Stabilization**

Database schema: **v4**

This is the acceptance record for v2.9.4. Mark an item complete only after recording its date, environment, and evidence. Automated checks do not replace manual Windows checks.

## Automated baseline

| Check | Status | Evidence |
|---|---|---|
| Source compilation | Passed | Python 3.13.14; `compileall` exited 0 on 2026-07-10. |
| Launch diagnostics | Passed | Dependencies, resources, and clean schema-v4 initialization passed on 2026-07-10. |
| Database/seed/data smoke test | Passed | Seed, CRUD, CSV, backup, and restore smoke test passed on 2026-07-10. |
| Qt offscreen startup | Passed | Main window constructed and exited cleanly using the test autoclose hook on 2026-07-10. |
| No unresolved merge markers | Passed | Tracked source and documentation search returned no markers on 2026-07-10. |
| Version metadata consistency | Passed | Application, package, diagnostic, and installer metadata identify v2.9.4. |

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
- [ ] Reset creates a safety backup and an empty schema-v4 database.
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
- [x] Inno Setup produces `release/Lectern_v2_9_4_Setup.exe`.
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

## Release decision

Declare v2.9.4 complete only when all checks pass, no startup errors or syntax/merge issues remain, and every blocking defect is resolved or explicitly removed from scope. Do not begin v3.0 work before recording that decision here.
