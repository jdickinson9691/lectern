# Release Manifest — Lectern 2.9.3

Milestone: **2.9.5 — Workflow and Import Refinement**

This archive contains source, documentation, seed data, application art, build scripts, and installer configuration.

Excluded from the release:

- `.venv`
- Git metadata
- Python caches
- Runtime databases and backups
- Logs and diagnostics
- PyInstaller work directories
- Compiled executables and installer output

Watermark implementation: every navigation screen is registered through `MainWindow.add_page()`, which wraps the screen in `WatermarkedPage`.
