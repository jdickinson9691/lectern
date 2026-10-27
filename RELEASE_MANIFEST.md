# Release Manifest — Lectern 3.0.1

Milestone: **3.0.1 — Ashen Company Integration**

This archive contains source, documentation, seed data, application art, build scripts, installer configuration, and the Fantasy Grounds extension source and packaging scripts.

The Windows installer contains the packaged Lectern app, the Ashen Company launcher, the player guide, an optional approved player Story module, and the Lectern Sync extension. It does not contain the live campaign database, GM guide, or private campaign files. The player module is a snapshot of seven approved Story records at build time. The 3.0.1 executable was built with Python 3.12.10 and passed an isolated startup check; Python 3.13 packaging remains to be verified.

Excluded from the release:

- `.venv`
- Git metadata
- Python caches
- Runtime databases and backups
- Logs and diagnostics
- PyInstaller work directories
- Compiled executables and installer output

Watermark implementation: every navigation screen is registered through `MainWindow.add_page()`, which wraps the screen in `WatermarkedPage`.
