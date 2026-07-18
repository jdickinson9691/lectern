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
- Encounter Builder and initiative-based Combat Dashboard with persistent combat logs.
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

- Existing databases migrate without discarding encounter data; current schema version is 7.
- Fantasy Grounds synchronization is host/GM-only and read-only from Lectern. Run `/lectern-export` once after loading a campaign and after changing the loaded module set.
- The automated fixture covers snapshot validation and mapping; final release acceptance still requires a live Fantasy Grounds 5E campaign.
- Imported PDF data is previewed before database persistence.
- Portrait extraction accepts distinct square or portrait-oriented images and rejects wide banners and logos. A user can always choose a portrait manually.
- A newly created encounter must be empty and uniquely named.
- Generated binaries are delivery artifacts, not tracked repository files.

## 2.9.5 baseline

The 2.9.5 milestone is named **Workflow and Import Refinement**. Version metadata is synchronized in the application, Python package, installer, help, and development documentation. The first 2.9.5 installer will be named `Lectern_v2_9_5_Setup.exe`.

## Current bug-fix release candidate

- Encounter Builder resolves the selected monster by its bound database ID and no longer substitutes the first alphabetical monster after a refresh.
- Locally built encounters add monster batches atomically; Fantasy Grounds-owned encounters remain read-only in Lectern.
- Fantasy Grounds Sync 1.1.1 carries prepared-participant combat statistics and live combat events into Lectern.
- Every navigation screen uses content-aware section spacing that tightens on crowded windows and expands within a bounded range when room is available.
- On 2026-07-18, the adaptive-layout, Encounter Builder, Fantasy Grounds Sync, and full smoke regressions passed.
- The Windows executable and Fantasy Grounds extension were rebuilt with PyInstaller 6.21.0, and Inno Setup 6.7.1 produced `release/Lectern_v2_9_5_Setup.exe`.
- An isolated silent install, installed offscreen startup, payload check, and silent uninstall passed.
- Installer SHA-256: `1A089C21DC4AD8EFC0932386813DDDA0FD88CC8ABDD65567E1293CA162A2F494`.

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
