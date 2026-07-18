# Changelog

## 2.9.5 — Workflow and Import Refinement (in progress)

- Established the v2.9.5 development baseline from the tested v2.9.4 Windows build.
- Synchronized application, package, help, and installer version metadata.
- Prepared the first one-way Fantasy Grounds Unity 5E integration milestone with a versioned snapshot contract, sanitized fixture, extension workspace, installation helper, acceptance criteria, and run-together guide.
- Implemented the Fantasy Grounds Unity 5E exporter extension with loaded-module reference discovery, character and encounter export, live Combat Tracker updates, status reporting, and the `/lectern-export` command.
- Added schema v6 external-source provenance, collision-safe entity links, transactional snapshot validation/import, sequence idempotency, and stale-record retention.
- Added the Fantasy Grounds Sync screen with campaign-folder setup, automatic polling, manual import, provenance display, and read-only Fantasy Grounds combat ownership.
- Added sanitized Fantasy Grounds integration regression coverage and packaged-extension build wiring.

## 2.9.4 — Verification and Stabilization

- Started the v2.9.4 stabilization milestone; no v3.0 feature work is in scope.
- Synchronized application, package, diagnostic, and installer version metadata.
- Restored PyInstaller build recipes to source control while keeping generated output ignored.
- Added a v2.9.4 acceptance checklist and evidence log.
- Corrected clipped `QGroupBox` titles by reserving top margin and positioning title text above the content border.
- Added campaigns, encounter assignment and outcomes, cumulative combat-log statistics, and campaign encounter history.
- Migrated existing databases to schema version 5 without discarding encounter data.
- Bundled a versioned 4,148-record monster catalog that updates both new and existing installations once.
- Reorganized navigation around campaign and combat flow, with Encounter Builder directly after Campaigns.
- Added current campaigns and their encounter counts to the main dashboard.
- Added SRD-driven species and feat ability bonuses to the player editor, including prompts for flexible feat choices.
- Corrected the global watermark by removing its opaque black background and preserving a clear translucent logo layer.
- Fixed Encounter Builder creation so every new encounter starts empty and receives a unique name instead of reusing prior combatants.
- Added reviewed character-sheet PDF import for common D&D Beyond, Roll20, and fillable-sheet fields in the Players editor.
- Corrected D&D Beyond PDF mapping by reading unregistered page widgets and rejecting adjacent printed labels as character values.
- Replaced the character PDF message preview with a scrollable dialog whose confirmation saves and opens the imported player.
- Fixed PDF-imported players failing to open by normalizing missing currency values to integers before loading spin boxes.
- Fixed Edit Selected by using unambiguous full-row selection and resetting every editor tab before loading the selected player.
- Expanded D&D Beyond PDF import to include feats, inventory, skill proficiency/expertise, saving throws, equipped items, and spellcasting ability.
- Rewrote in-app help for the current 2.9.4 workflows and added an illustrated step-by-step tutorial production outline.
- Added safe PDF portrait extraction and player thumbnails in Players, Encounter Builder, and Combat Dashboard rows.
- Built and verified the Windows executable and installer; remaining manual acceptance items are recorded in `docs/VERIFICATION_REPORT.md`.

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
