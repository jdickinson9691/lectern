# Lectern 2.9.5 Development Handoff

## Starting point

Lectern 2.9.5 starts from commit `3823433`, the tested 2.9.4 Windows baseline. The application uses Python 3.13, PySide6, SQLite schema v5, PyInstaller, and Inno Setup.

The final 2.9.4 artifacts were produced on July 11, 2026:

- `dist/Lectern/Lectern.exe`
- `release/Lectern_v2_9_4_Setup.exe`
- Installer SHA-256: `8BB7606C5F10EEB4F4BC0D7F52C9BD8596A05E74C2E2E4BBCE233100869D6BDF`
- Smoke test, executable build, silent installer deployment, installed startup, and uninstall all passed.

Generated `dist`, `release`, and PyInstaller work folders remain excluded from Git.

## Current application capabilities

- Dashboard with current campaigns and encounter counts.
- Campaign management with encounters, outcomes, history, and cumulative combat results.
- Encounter Builder and initiative-based Combat Dashboard with persistent structured combat logs, round grouping, result highlighting, combined search/filter controls, and expandable original event details.
- Player Character Editor covering general details, abilities, equipment, inventory, combat, skills, saving throws, and notes.
- SRD-driven species bonuses and feat ability choices.
- Reviewed character PDF import for common D&D Beyond, Roll20, and fillable-sheet data.
- PDF mapping for abilities, feats, inventory, proficiencies, expertise, saving throws, equipped weapon and armor, spellcasting ability, and notes.
- Safe embedded portrait extraction plus player thumbnails in Players, Encounter Builder, and Combat Dashboard.
- Monster Library seeded from a versioned 4,148-record catalog.
- Weapons, armor, equipment, magic items, spells, CSV transfer, data workflow, logs, and in-app help.
- Centered translucent watermark coverage throughout the navigation screens.
- One-way Fantasy Grounds Unity 5E synchronization for loaded reference records, characters, prepared encounters, and live Combat Tracker state.
- Fantasy Grounds source provenance, idempotent snapshot sequences, stale-record retention, and collision-safe links to Lectern entities.

## Important implementation notes

- Existing databases migrate without discarding encounter data; current schema version is 9.
- Fantasy Grounds synchronization is host/GM-only and read-only from Lectern. Run `/lectern-export` once after loading a campaign and after changing the loaded module set.
- The automated fixture covers snapshot validation and mapping; final release acceptance still requires a live Fantasy Grounds 5E campaign.
- Imported PDF data is previewed before database persistence.
- Portrait extraction accepts distinct square or portrait-oriented images and rejects wide banners and logos. A user can always choose a portrait manually.
- A newly created encounter must be empty and uniquely named.
- Generated binaries are delivery artifacts, not tracked repository files.

## 2.9.5 baseline

The 2.9.5 milestone is named **Workflow and Import Refinement**. Version metadata is synchronized in the application, Python package, installer, help, and development documentation. The first 2.9.5 installer will be named `Lectern_v2_9_5_Setup.exe`.

## Current bug-fix release candidate

- The Campaign Dashboard reports party DPR/HPR and critical-hit/miss leaders from normalized schema-v8 combat-log data, including tied leaders and attribution coverage. Fantasy Grounds imports/reprocessing and local combat actions populate the normalized statistics fields.
- Encounter Builder resolves the selected monster by its bound database ID and no longer substitutes the first alphabetical monster after a refresh.
- Locally built encounters add monster batches atomically; Fantasy Grounds-owned encounters remain read-only in Lectern.
- Fantasy Grounds Sync 1.4.0 carries prepared-participant combat statistics and live combat events into Lectern, including authoritative mixed damage types and per-component rolled/applied/resisted/vulnerability totals. Explicit `/lectern-start` and `/lectern-end` commands create durable named sessions that survive extension reloads, retain accumulated events, and preserve the final non-empty combatant roster after tracker clearing. `/lectern-reset confirm` and Lectern's previewed, automatically backed-up clear action provide a clean testing reset while preserving local data. Attack events use the 5E ruleset's authoritative post-resolution result and effect-adjusted defense; manual damage remains unattributed with an unknown type.
- Fantasy Grounds Sync can preview and safely reprocess historical linked combat logs from immutable `external_events.raw_json`, using the same formatter as new imports. It backs up the database first, preserves event identity and local rows, and reports updated, unchanged, incomplete, and failed events.
- Every navigation screen uses content-aware section spacing that tightens on crowded windows and expands within a bounded range when room is available.
- On 2026-07-19, the explicit encounter-lifecycle regression and all application regression suites passed.
- On 2026-07-19, the Milestone 1.4 historical-reprocessing test and all required regression suites passed. The Windows app and `Lectern_v2_9_5_Setup.exe` were rebuilt, and the packaged app passed its offscreen startup check.
- A live Test-campaign sequence imported one character and two Combat Tracker entries while correctly exporting zero loaded-module reference encounters.
- The Windows executable and Fantasy Grounds extension were rebuilt with PyInstaller 6.21.0, and Inno Setup 6.7.1 produced `release/Lectern_v2_9_5_Setup.exe`.
- An isolated silent install, installed offscreen startup, payload check, and silent uninstall passed.

## Recommended verification for each change

1. Run source compilation for affected modules.
2. Run `scripts/smoke_test.py`.
3. Test the affected workflow from source with representative existing and newly imported data.
4. Rebuild `dist/Lectern/Lectern.exe` before a release checkpoint.
5. Compile and test the Inno Setup installer in an isolated folder.
6. Record user-facing changes in `CHANGELOG.md` and update Help when behavior changes.

## Known follow-up work

- Complete any unchecked manual acceptance items retained in `docs/VERIFICATION_REPORT.md`.
- Produce the illustrated step-by-step tutorial described in `docs/TUTORIAL_OUTLINE.md`.
- Continue testing PDF imports across differently structured character sheets; image-only sheets still require OCR or manual correction.
