# Changelog

## 2.9.3 — Fresh Baseline and Watermark Verification

- Rebuilt the source tree as a clean Git-ready baseline.
- Replaced the shared stacked-widget watermark painter with a per-screen `WatermarkedPage` wrapper.
- Confirmed all 16 navigation screens are added through the watermark wrapper.
- Added Python 3.12/3.13 environment setup and `pythonw.exe` desktop launch scripts.
- Excluded Python 3.14 from the validated environment.
- Restored and corrected PyInstaller build files.
- Included watermark, icon, documentation, and seed resources in packaged builds.
- Expanded `.gitignore` and added `.gitattributes`.

## 2.9.2 — Launch Stability and Baseline Cleanup

- Added startup diagnostics, logging, resource handling, database connection cleanup, and documentation cleanup.
