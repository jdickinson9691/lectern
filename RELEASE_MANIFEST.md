# Release Manifest — Lectern 3.0.2

Milestone: **3.0.2 — Ashen Company Workspace**

This archive contains source, documentation, seed data, application art, build scripts, installer configuration, and the Fantasy Grounds extension source and packaging scripts.

The Windows installer contains the packaged Lectern app, the Ashen Company launcher, the player guide, an optional approved player Story module, and the Lectern Sync extension. It does not contain the live campaign database, GM guide, or private campaign files. The player module is a snapshot of seven approved Story records at build time. The 3.0.2 executable is built on D: with Python 3.13.14. The dedicated Ashen workspace receives a visible Campaign Dashboard row without copying it into unrelated Lectern databases. The package includes Lectern Sync 1.4.13; its live Test9 Armor acceptance remains pending.

Excluded from the release:

- `.venv`
- Git metadata
- Python caches
- Runtime databases and backups
- Logs and diagnostics
- PyInstaller work directories
- Compiled executables and installer output

Watermark implementation: every navigation screen is registered through `MainWindow.add_page()`, which wraps the screen in `WatermarkedPage`.
