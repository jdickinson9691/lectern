# Development Workflow

For a condensed history of completed Codex work and reusable prompt templates, see [CODEX_PROMPT_ARCHIVE.md](CODEX_PROMPT_ARCHIVE.md).

This folder is the canonical evolving source tree for Lectern: **Lüdinn Entertainment Campaign Tracker for Encounters, Rules & Navigation**.

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
   `.venv\Scripts\python.exe scripts\campaign_dashboard_stats_test.py`

   The Fantasy Grounds regression covers event validation, duplicate suppression, explicit durable encounter sessions, final-roster retention, authoritative mixed damage types/components, dashboard-compatible damage and healing rows, and encounter outcomes. The Campaign Dashboard regression covers DPR/HPR, critical leaders, all 13 standard damage-type leaders, ties, and legacy single-type fallback. Complete the live checklist in `docs\FANTASY_GROUNDS_RUN_TOGETHER.md` before release.
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

- Version: 3.0.0 Workflow and Import Refinement (in progress)
- Baseline: completed v2.9.5 Fantasy Grounds synchronization and campaign-statistics work
- Scope: define and implement the next major Lectern workflow, analytics, usability, documentation, and release improvements.
- Acceptance evidence: `docs/VERIFICATION_REPORT.md`.
