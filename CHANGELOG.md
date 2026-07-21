# Changelog

## 3.0.0 — Workflow and Import Refinement (in progress)

- Established the v3.0.0 development baseline from the completed v2.9.5 Fantasy Grounds synchronization and campaign-statistics work.
- Synchronized application, package, help, release manifest, baseline, and installer version metadata.
- Added `docs/LECTERN_3_0_0_KICKOFF.md` as the authoritative starting point for the next development session.

### Prepared and live encounter workflow

- Fantasy Grounds prepared encounters and their live-combat sessions are now associated when their name and roster produce one unambiguous match; ambiguous sessions remain safely unlinked.
- Encounter selectors label synchronized records as **Prepared** or **Live combat** and show the linked counterpart, while contextual notices explain which view contains the roster versus the combat journal.
- A successful manual or automatic Fantasy Grounds import now selects the newly updated live-combat session in Encounter Builder and Combat Dashboard.
- The relationship uses existing synchronization metadata, so database schema v9 and snapshot contract v1 remain unchanged.

### Fantasy Grounds damage types

- Added a Campaign Dashboard **Party Damage Type Leaders** table for all 13 standard 5E damage types, including cumulative applied damage, contributing event counts, and tied leaders.
- Added Lectern Sync 1.4.1 authoritative post-resolution damage capture with mixed damage components and rolled, applied, resisted, and vulnerability amounts.
- Fixed empty event metadata being exported as a JSON array; Lectern also recovers affected 1.4.0 snapshots without losing their combat events.
- Added schema-v9 normalized damage types and component JSON to combat-log rows, plus a **Damage Type** column and damage-type-aware search on the Combat Dashboard.
- Historical Fantasy Grounds log reprocessing now recovers recognizable damage types from preserved metadata or `[TYPE: ...]` descriptions; manual or unavailable types remain `unknown`.

### Fantasy Grounds test-data reset

- Added a previewed **Clear Selected FG Import** action that backs up the database, removes only selected Fantasy Grounds-linked campaigns, encounters, combatants, combat logs, player copies, and sync metadata, and preserves local Lectern data.
- Added Lectern Sync 1.3.1 `/lectern-reset confirm` to safely clear a closed extension session and accumulated exported event journal; open encounters must be ended first.
- Automatic import is disabled after clearing so a stale snapshot cannot immediately repopulate the database.

### Fantasy Grounds explicit encounter lifecycle

- Added Lectern Sync 1.3.0 `/lectern-start [name]` and `/lectern-end outcome` commands, with `/lectern-outcome` retained as a compatibility alias.
- Persisted session identity, name, state, timestamps, event sequence, and accumulated journal data in the Fantasy Grounds campaign handoff folder so an extension reload resumes the same encounter.
- Added open/closed encounter status to the Sync screen, explicit lifecycle log events, stable named encounter import, and final-roster retention after Combat Tracker clearing.
- Updated the user help, run-together guide, integration readme, handoff notes, snapshot contract, and regression coverage for the explicit lifecycle.

### Combat Dashboard incomplete-event display fix

- Preserved available raw die totals when older Fantasy Grounds events lack actor, target, action, or result data, and labeled each unavailable structured field explicitly after reprocessing.
- Made the Combat Dashboard prefer active encounters on initial load instead of a newer completed historical log with no combatant snapshot, and added a clear notice for log-only Fantasy Grounds encounters.
- Corrected the application database schema-version constant to match the schema-v8 combat-statistics migration.

### Campaign party combat statistics

- Added party DPR, party HPR, critical-hit leader, critical-miss leader, tie handling, and data-coverage reporting to the selected Campaign Dashboard.
- Added normalized combat-log actor identity, party affiliation, applied amount, result, and natural-roll fields with schema-v8 migration support.
- Updated local and Fantasy Grounds logging plus historical reprocessing to populate the normalized fields without guessing unattributed history.
- Added focused repository and offscreen UI regression coverage for round-weighted averages, hostile/manual exclusions, ties, and coverage counts.

### Fantasy Grounds historical combat-log reprocessing

- Added a previewable **Reprocess Imported Combat Logs** workflow that creates a safety backup and rebuilds only linked Fantasy Grounds log rows from preserved raw events.
- Reused the current Fantasy Grounds event formatter for new imports and historical rows, with idempotent updates, explicit unavailable values, transaction rollback, and updated/unchanged/incomplete/failed reporting.
- Added focused regression coverage for restored rolls and defenses, damage adjustments, healing, authoritative natural-roll outcomes, manual wound changes, local-row preservation, repeat processing, and rollback safety.

### Encounter Builder and Fantasy Grounds bug fixes

- Fixed monster selection so Encounter Builder refreshes preserve the selected database record instead of falling back to the first alphabetical monster (`A-mi-kuk`).
- Made local multi-monster additions atomic and consistently ordered, and made Fantasy Grounds-owned encounters read-only in Encounter Builder.
- Updated Fantasy Grounds Sync 1.1.1 to carry prepared-encounter participant AC, HP, and initiative into Lectern.
- Made the spacing between sections on every application screen respond to its content and the available window height.
- Replaced the Encounter Builder's tiny native monster-quantity spinner controls with reliable, accessible increase and decrease arrow buttons.
- Grouped Monster Browser search and quantity controls into a compact top section instead of distributing empty space between them.
- Updated Lectern Sync 1.1.3 for Fantasy Grounds 2024 character AC fields, excluded unnamed placeholder characters and module reference battles, and accepted Fantasy Grounds UTF-8 BOM snapshots.

## 2.9.5 — Workflow and Import Refinement (in progress)

- Established the v2.9.5 development baseline from the tested v2.9.4 Windows build.
- Synchronized application, package, help, and installer version metadata.
- Prepared the first one-way Fantasy Grounds Unity 5E integration milestone with a versioned snapshot contract, sanitized fixture, extension workspace, installation helper, acceptance criteria, and run-together guide.
- Implemented the Fantasy Grounds Unity 5E exporter extension with loaded-module reference discovery, character and encounter export, live Combat Tracker updates, status reporting, and the `/lectern-export` command.
- Added schema v6 external-source provenance, collision-safe entity links, transactional snapshot validation/import, sequence idempotency, and stale-record retention.
- Added the Fantasy Grounds Sync screen with campaign-folder setup, automatic polling, manual import, provenance display, and read-only Fantasy Grounds combat ownership.
- Added sanitized Fantasy Grounds integration regression coverage and packaged-extension build wiring.
- Added Fantasy Grounds Sync 1.1 combat-session journals for dice actions, applied damage, healing, turn changes, temporary hit points, and explicit encounter outcomes.
- Added schema v7 external-event receipts and transactional, duplicate-safe import into `turn_log`, preserving Campaign Dashboard damage and healing totals.
- Added `/lectern-outcome`, session-separated synchronized encounters, an expanded snapshot v1 contract, sanitized event fixtures, and Milestone 1.1 runtime acceptance guidance.

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
