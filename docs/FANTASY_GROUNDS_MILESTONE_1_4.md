# Fantasy Grounds Integration - Milestone 1.4

## Task title

Reprocess historical Fantasy Grounds combat logs

## Objective

Allow Lectern to rebuild previously imported Fantasy Grounds `turn_log` rows from the preserved raw event records. This lets older encounters benefit from the current actor, roll, modifier, target, defense, damage, healing, and result formatting without requiring the encounter to be replayed or exported again.

## Background

Lectern stores imported Fantasy Grounds events in `external_events.raw_json` and links each event to a `turn_log` row. The normal snapshot importer ignores event IDs that have already been imported, so installing a newer build or importing the same snapshot does not upgrade historical log rows.

The structured Combat Log UI introduced in Milestone 1.3 can display detailed fields when they exist in `turn_log.details`, but it cannot reconstruct information that was never written there. Milestone 1.4 should use the preserved raw event JSON as the source for safe, repeatable historical reprocessing.

## Required behavior

1. Add a **Reprocess Imported Combat Logs** action to the Fantasy Grounds Sync screen.
2. Inspect only Fantasy Grounds events stored in `external_events`.
3. Preview the number of affected encounters, total events, improvable events, and events missing required source data before applying changes.
4. Create a database backup before modifying historical rows.
5. Rebuild linked `turn_log` fields with the same formatter used for new Fantasy Grounds imports.
6. Preserve encounter ID, round, timestamp, event identity, and the `external_events` link.
7. Never modify locally entered or unlinked Lectern log rows.
8. Never duplicate an event or create an additional `turn_log` row for an existing event.
9. Retain incomplete events and label unavailable fields clearly instead of deleting them.
10. Refresh the Combat Log UI, Campaign Dashboard, and Fantasy Grounds Sync status after completion.
11. Show a completion summary with updated, unchanged, incomplete, and failed counts.

## Implementation guidance

- Extract the Fantasy Grounds event-to-log conversion in `app/integrations/fantasy_grounds.py` into one reusable formatter used by both new imports and historical reprocessing.
- Treat `external_events.raw_json` as immutable source evidence. Update the linked `turn_log` row, not the raw event.
- Perform the reprocessing operation in a single database transaction after the backup succeeds.
- Make the operation idempotent: running it repeatedly against unchanged raw events must produce the same rows and no duplicates.
- If one raw event is invalid, report it as failed or incomplete without silently corrupting the remaining history.
- Preserve authoritative Fantasy Grounds results such as critical hits, automatic misses, adjusted damage, healing, and manual or unattributed wound changes.
- Recalculate displayed campaign totals only through the existing `turn_log` records; do not introduce a separate statistics source.

## Safety boundaries

- Fantasy Grounds remains the source of truth.
- Do not write data back to Fantasy Grounds.
- Do not reset the imported snapshot sequence.
- Do not delete historical encounters or events.
- Do not infer bonuses, AC, damage, healing, actors, or targets when the raw export does not contain them.
- Do not alter local Lectern combat history.

## Automated acceptance tests

Add a focused test script for historical reprocessing that verifies:

1. A legacy linked log row is upgraded from its stored raw Fantasy Grounds event.
2. Actor, raw die roll, modifier, net roll, target, AC, action name, and result are restored when present.
3. Rolled versus applied damage and damage adjustments are preserved.
4. Healing and resulting HP are preserved.
5. Natural 20 and natural 1 outcomes remain authoritative.
6. Manual or unattributed wound changes remain labeled correctly.
7. Incomplete raw events remain readable and are counted as incomplete.
8. Local and unlinked `turn_log` rows remain byte-for-byte unchanged.
9. Reprocessing twice produces no duplicates and no additional changes.
10. A processing failure rolls back database changes.

Run the existing regression suites as well:

- `scripts/fantasy_grounds_sync_test.py`
- `scripts/combat_log_ui_test.py`
- `scripts/encounter_builder_test.py`
- `scripts/adaptive_layout_test.py`
- `scripts/smoke_test.py`

## Manual acceptance test

1. Back up or copy the current Lectern database.
2. Open a campaign containing combat imported by an older Lectern build.
3. Record the encounter count, event count, campaign totals, and one representative legacy row.
4. Open Fantasy Grounds Sync and select **Reprocess Imported Combat Logs**.
5. Confirm that the preview counts are reasonable and approve the operation.
6. Open the same encounter in the Combat Dashboard.
7. Verify that recoverable actor, roll, modifier, target, AC or HP, action, and result fields now populate the structured columns.
8. Verify that incomplete events remain present with clear unavailable-field labels.
9. Confirm that local Lectern log entries are unchanged.
10. Run reprocessing again and confirm that no duplicates or additional changes occur.
11. Confirm that Campaign Dashboard totals remain accurate.

## Definition of done

- Historical reprocessing is implemented with preview, confirmation, backup, transaction safety, and a completion summary.
- New imports and historical reprocessing share one event formatter.
- Automated and manual acceptance criteria pass.
- User help and handoff documentation describe the feature and its limitations.
- The Windows application and `Lectern_v2_9_5_Setup.exe` installer are rebuilt.
- Changes are committed on a `codex/` feature branch and are ready to merge into `main`.

## Suggested branch and commit

- Branch: `codex/fg-historical-log-reprocessing-1-4`
- Commit: `Implement Fantasy Grounds historical log reprocessing`

## Important limitation

Reprocessing can recover only information present in `external_events.raw_json`. Fields that were never captured by the Fantasy Grounds extension cannot be reconstructed and must remain explicitly unavailable.
