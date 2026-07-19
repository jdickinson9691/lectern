# Development Workflow

This folder is now the canonical evolving source tree for the Lectern - D&D Campaign Manager.

## Daily workflow

1. Extract or open this source tree in a stable folder, for example:
   `C:\Users\jdick\OneDrive\Desktop\CampaignManager`
2. Make all future changes inside this same folder.
3. Run from source during development:
   `build\RunFromSource.bat`
4. Run automated checks:
   `.venv\Scripts\python.exe scripts\smoke_test.py`
   `.venv\Scripts\python.exe scripts\encounter_builder_test.py`
   `.venv\Scripts\python.exe scripts\fantasy_grounds_sync_test.py`
   `.venv\Scripts\python.exe scripts\fantasy_grounds_reprocessing_test.py`

   The Fantasy Grounds regression covers event validation, duplicate suppression, dashboard-compatible damage and healing rows, and encounter outcomes. Complete the live checklist in `docs\FANTASY_GROUNDS_MILESTONE_1_1.md` before release.
5. Install the unpacked Fantasy Grounds extension into a development data folder:
   `scripts\Install-FantasyGroundsExtension.ps1 -FantasyGroundsDataPath "<path>"`
6. Build only when ready to test the packaged executable and `LecternSync.ext`:
   `build\Build.ps1`
7. Launch the built app:
   `dist\Lectern\Lectern.exe`

## Important rules

- Do not mix files from older ZIPs into this folder.
- Do not run the executable from an older `dist` folder.
- If a build behaves strangely, remove generated `dist` and `.pyinstaller_build` output, then run `build\Build.ps1` again.
- Keep the bundled spreadsheet in `seeds/` until the app has a dedicated data updater.

## Current baseline

- Version: 2.9.5 Workflow and Import Refinement (in progress)
- Baseline: tested v2.9.4 Windows executable and installer
- Scope: campaign workflow, imports, one-way Fantasy Grounds Unity 5E synchronization, usability, documentation, and release refinement.
- Acceptance evidence: `docs/VERIFICATION_REPORT.md`.
