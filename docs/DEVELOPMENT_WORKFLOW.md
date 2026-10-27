# Development Workflow

For active 3.1 design work, see
[LECTERN_3_1_DEVELOPMENT.md](LECTERN_3_1_DEVELOPMENT.md). For the completed
Codex task index and reusable implementation prompt, see
[CODEX_PROMPT_ARCHIVE.md](CODEX_PROMPT_ARCHIVE.md).

This folder is the canonical evolving source tree for Lectern: **Lüdinn Entertainment Campaign Tracker for Encounters, Rules & Navigation**.

## Daily workflow

1. Open the maintained source tree at `D:\Ludinn\Development\Lectern`.
2. Make future source changes, commits, builds, and pushes in this folder.
   Its `main` branch tracks `origin/main`.
3. Run from source during development:
   `build\RunFromSource.bat`
4. Run automated checks:
   `.venv\Scripts\python.exe scripts\smoke_test.py`
   `.venv\Scripts\python.exe scripts\encounter_builder_test.py`
   `.venv\Scripts\python.exe scripts\fantasy_grounds_sync_test.py`
   `.venv\Scripts\python.exe scripts\fantasy_grounds_live_effect_provenance_test.py`
   `.venv\Scripts\python.exe scripts\fantasy_grounds_reprocessing_test.py`
   `.venv\Scripts\python.exe scripts\campaign_dashboard_stats_test.py`

   The Fantasy Grounds regression covers event validation, duplicate suppression, explicit durable encounter sessions, final-roster retention, authoritative mixed damage types/components, dashboard-compatible damage and healing rows, and encounter outcomes. The Campaign Dashboard regression covers DPR/HPR, critical leaders, all 13 standard damage-type leaders, ties, and legacy single-type fallback. Complete the live checklist in `docs\FANTASY_GROUNDS_RUN_TOGETHER.md` before release.
5. Install the unpacked Fantasy Grounds extension into a development data folder:
   `scripts\Install-FantasyGroundsExtension.ps1 -FantasyGroundsDataPath "<path>"`
6. Build only when ready to test the packaged executable and `LecternSync.ext`:
   `build\Build.ps1`
7. Build the full Windows installer when needed:
   `build\Build-Installer.ps1`
8. Launch the built app:
   `dist\Lectern\Lectern.exe`
9. Push reviewed commits from this checkout:
   `git push origin main`

## Important rules

- Do not mix files from older ZIPs into this folder.
- Do not run the executable from an older `dist` folder.
- If a build behaves strangely, remove generated `dist` and `.pyinstaller_build` output, then run `build\Build.ps1` again.
- Keep the bundled spreadsheet in `seeds/` until the app has a dedicated data updater.

## Current baseline

- Application version: 3.0.1 Ashen Company Integration
- Planning milestone: 3.1 product design
- Database schema: v11 (optional Ashen canon layer over v10)
- Fantasy Grounds snapshot contract: v1; Lectern Sync extension 1.4.13
- Scope: confirm the 3.0 release boundary, then define one primary 3.1 user
  outcome before implementation.
- Acceptance evidence: `docs/VERIFICATION_REPORT.md`.
