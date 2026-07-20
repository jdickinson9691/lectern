# Release Manifest — Lectern 3.0.0

Milestone: **3.0.0 — Workflow and Import Refinement**

This archive contains source, documentation, seed data, application art, build scripts, installer configuration, and the Fantasy Grounds extension source and packaging scripts.

Excluded from the release:

- `.venv`
- Git metadata
- Python caches
- Runtime databases and backups
- Logs and diagnostics
- PyInstaller work directories
- Compiled executables and installer output

Watermark implementation: every navigation screen is registered through `MainWindow.add_page()`, which wraps the screen in `WatermarkedPage`.
