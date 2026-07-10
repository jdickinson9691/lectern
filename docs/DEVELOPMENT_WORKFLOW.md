# Development Workflow

This folder is now the canonical evolving source tree for the Lectern - D&D Campaign Manager.

## Daily workflow

1. Extract or open this source tree in a stable folder, for example:
   `C:\Users\jdick\OneDrive\Desktop\CampaignManager`
2. Make all future changes inside this same folder.
3. Run from source during development:
   `build\RunFromSource.bat`
4. Build only when ready to test the packaged executable:
   `build\Build.ps1`
5. Launch the built app:
   `dist\Lectern\Lectern.exe`

## Important rules

- Do not mix files from older ZIPs into this folder.
- Do not run the executable from an older `dist` folder.
- If a build behaves strangely, remove generated `dist` and `.pyinstaller_build` output, then run `build\Build.ps1` again.
- Keep the bundled spreadsheet in `seeds/` until the app has a dedicated data updater.

## Current baseline

- Version: 2.9.4 Verification and Stabilization (in progress)
- Baseline: v2.9.3 Fresh Baseline and Watermark Verification
- Scope: startup, watermark, core CRUD, data workflow, logging, executable, and installer verification only.
- Acceptance evidence: `docs/VERIFICATION_REPORT.md`.
