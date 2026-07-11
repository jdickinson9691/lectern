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

- Version: 2.9.5 Workflow and Import Refinement (in progress)
- Baseline: tested v2.9.4 Windows executable and installer
- Scope: continued campaign workflow, player import, usability, documentation, and release refinement.
- Acceptance evidence: `docs/VERIFICATION_REPORT.md`.
