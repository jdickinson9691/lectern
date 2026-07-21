# Lectern 3.0.0 Development Kickoff

Prepared on July 19, 2026, for work beginning July 20, 2026.

## Purpose

This document is the authoritative starting point for Lectern 3.0.0. The version bump does not introduce a database migration or change the Fantasy Grounds snapshot contract. The working release name remains **Workflow and Import Refinement** until the 3.0 product scope is named.

## Source baseline

- Repository: `jdickinson9691/lectern`
- Development branch: `codex/lectern-3-0-0-kickoff`
- Completed 2.9.5 baseline on `main`: `b89da37`
- Fantasy Grounds metadata repair: `5f7b34d`
- Application version: 3.0.0
- Database schema: v9
- Fantasy Grounds snapshot schema: v1
- Lectern Sync extension: 1.4.2
- Supported runtime: Python 3.13 on Windows 10/11
- Expected installer: `release/Lectern_v3_0_0_Setup.exe`

## Stable capabilities carried into 3.0

- One-way Fantasy Grounds Unity 5E catalog, character, prepared-encounter, Combat Tracker, and combat-event synchronization.
- Explicit `/lectern-start`, `/lectern-end`, `/lectern-reset confirm`, and `/lectern-export` workflows with durable session identity.
- Historical Fantasy Grounds combat-log reprocessing and safe, backed-up clearing of imported data.
- Authoritative attack results and component-aware damage types, including applied, resisted, and vulnerability totals.
- Campaign Dashboard party DPR/HPR, critical-hit and critical-miss leaders, and leaders for all 13 standard 5E damage types.
- Windows executable, bundled help, Fantasy Grounds extension package, and Inno Setup delivery.

## Known behavior to retain or deliberately revise

- A prepared Fantasy Grounds encounter and its synchronized live combat session are separate Lectern encounters. For example, `Test1 Encounter` can contain the prepared roster while `Test Encounter 1` contains the combat journal. This is accurate in the data model but can be confusing in the dashboard.
- Campaign damage-type leaders include party-attributed applied damage only. Unknown damage and qualifiers such as `magic`, `silver`, and `adamantine` are excluded.
- Older damage rows are assigned to a type only when exactly one recognized standard damage type is available.
- Existing Lectern Sync 1.4.0 snapshots with `metadata: []` are normalized safely during import; extension 1.4.1 emits an object correctly.
- Fantasy Grounds remains the source of truth for synchronized combat fields.

## First session checklist

1. Confirm the branch and working tree:

   ```powershell
   git switch codex/lectern-3-0-0-kickoff
   git status
   git fetch origin
   ```

2. Start Lectern from source:

   ```powershell
   .\scripts\Start-Lectern.ps1
   ```

3. Verify the title and Help screen report version 3.0.0.
4. Open the imported Test campaign and confirm `Test Encounter 1` still shows its combat events and damage types.
5. Confirm the Campaign Dashboard shows all 13 damage-type rows and expected party leaders.
6. Decide the 3.0 release name and the first user-facing outcome before beginning unrelated feature work.

## Recommended first 3.0 decisions

1. **Decided and implemented:** label prepared encounters and live-combat sessions explicitly, and associate them only when the snapshot name and roster produce one unambiguous match.
2. **Decided and implemented:** a successful Fantasy Grounds import selects the newly updated live-combat encounter in Encounter Builder and Combat Dashboard.
3. Define whether Campaign Dashboard analytics need encounter, date, combatant, or party/hostile filters.
4. **Executed with follow-up defects recorded:** the live Fantasy Grounds pass covered resistance, immunity, vulnerability, mixed damage, healing, critical hits/misses, temporary HP, and multi-target damage. See `docs/FANTASY_GROUNDS_LIVE_ACCEPTANCE_3_0.md`; multi-target attribution and several accuracy/display gaps prevent release clearance.
5. Record explicit 3.0 acceptance criteria before changing the database or snapshot contract.

### First workflow acceptance criteria

- Prepared and live encounter roles are visible anywhere an encounter is selected for building, combat, or campaign review.
- A linked prepared encounter and live session name each other; an ambiguous match is never guessed.
- Manual and automatic imports focus the updated live-combat session without changing the current navigation page.
- Local Lectern encounters remain unlabeled and editable.
- Fantasy Grounds records remain read-only and source-owned.
- Database schema v9 and snapshot contract v1 remain unchanged.

## Regression baseline

Run these checks before and after the first 3.0 change:

```powershell
.venv\Scripts\python.exe scripts\campaign_dashboard_stats_test.py
.venv\Scripts\python.exe scripts\fantasy_grounds_sync_test.py
.venv\Scripts\python.exe scripts\fantasy_grounds_reprocessing_test.py
.venv\Scripts\python.exe scripts\combat_log_ui_test.py
.venv\Scripts\python.exe scripts\adaptive_layout_test.py
.venv\Scripts\python.exe scripts\encounter_builder_test.py
.venv\Scripts\python.exe scripts\smoke_test.py
```

All listed checks passed on July 19, 2026, immediately before and after the 3.0.0 version bump. The packaged application also reported version 3.0.0 during its offscreen startup check, and Inno Setup produced `release/Lectern_v3_0_0_Setup.exe`.

## Packaging

When a packaged checkpoint is needed:

```powershell
.\build\Build.ps1
& "C:\Users\jdick\AppData\Local\Programs\Inno Setup 6\ISCC.exe" .\installer\CampaignManager.iss
```

Verify that the resulting application reports 3.0.0 and that the installer is named `Lectern_v3_0_0_Setup.exe`.

## Kickoff completion criteria

- Version metadata is synchronized at 3.0.0.
- Database schema remains v9 and the Fantasy Grounds contract remains v1.
- The full regression baseline passes.
- The 3.0.0 executable and installer build successfully.
- Tomorrow's first product decision is captured here or in a dedicated 3.0 milestone document.
