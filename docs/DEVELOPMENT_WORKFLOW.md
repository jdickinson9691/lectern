# Development Workflow

This folder is now the canonical evolving source tree for the Lectern - D&D Campaign Manager.

## Daily workflow

1. Extract or open this source tree in a stable folder, for example:
   `C:\Users\jdick\OneDrive\Desktop\CampaignManager`
2. Make all future changes inside this same folder.
3. Run from source during development:
   `build\RunFromSource.bat`
4. Build only when ready to test the packaged executable:
   `build\Build.bat`
5. Launch the built app:
   `dist\Lectern\Lectern.exe`

## Important rules

- Do not mix files from older ZIPs into this folder.
- Do not run the executable from an older `dist` folder.
- If a build behaves strangely, delete `dist`, `.pyinstaller_build`, and `.venv`, then run `build\Build.bat` again.
- Keep the bundled spreadsheet in `seeds/` until the app has a dedicated data updater.

## Current baseline

- Version: 2.6.1 Codebase Baseline
- Base feature set: Combat UX, Player Manager, equipment fields, ability scores, responsive UI, CSV import/export.
- Immediate fix included: `Build.bat` escaped the `D&D` ampersand so Windows batch does not try to run a stray `D` command.
