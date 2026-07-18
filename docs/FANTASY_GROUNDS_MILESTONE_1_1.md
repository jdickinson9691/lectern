# Fantasy Grounds Integration - Milestone 1.1

## Objective

Extend the one-way Fantasy Grounds Unity 5E integration with a durable combat event journal. Lectern imports Fantasy Grounds actions, applied damage, healing, turn changes, temporary hit-point changes, and GM-confirmed encounter outcomes into the synchronized encounter's `turn_log`.

## Data flow

Fantasy Grounds remains authoritative. The extension observes dice events and Combat Tracker changes, adds stable event IDs to the complete `snapshot.json`, and never writes to Fantasy Grounds database nodes. Lectern validates the journal and imports each event in the same transaction as the combat snapshot.

- Dice landing events become `Attack`, `Save`, `Spell`, or general `Action` log entries.
- Increased Combat Tracker wounds become `Damage`.
- Decreased Combat Tracker wounds become `Healing`.
- Temporary hit-point changes become `Effect` entries.
- Active-combatant changes become `Turn Start` and `Turn End` entries.
- `/lectern-outcome victory|defeat|retreat|unresolved` creates an `Outcome` entry and completes the synchronized encounter.

Damage and healing are derived from applied Combat Tracker state, not chat text or an unapplied damage roll. Attribution is retained only when Fantasy Grounds supplies it; Lectern does not invent an attacker for an unattributed HP change.

## Contract compatibility

The snapshot remains schema version 1. The new `events` collection and the combat `session_key`, `outcome`, and `completed_at` properties are optional so Lectern 1.1 can still read milestone-one fixtures. Extension 1.1 always emits them.

Each event contains:

- Stable `event_id` and monotonic event `sequence`
- Timestamp, combat round, and combat-session source key
- Event type, actor, target, amount, and description
- Lossless metadata for diagnostics and future mapping improvements

The extension retains the newest 1,000 events for the running Fantasy Grounds session. Lectern's `external_events` table records every imported event ID, its destination encounter and `turn_log` row, raw JSON, and import sequence. `(source_id, event_key)` is unique, preventing duplicates after polling, restart, or snapshot replay.

## Encounter sessions and outcomes

A new Combat Tracker session receives a new source key. This prevents later combats from appending to a previously completed Lectern encounter. If Lectern first connects after an earlier session has ended but its events remain in the journal, the importer creates a completed historical encounter for those events.

Outcomes require a GM decision because Fantasy Grounds has no ruleset-independent victory signal. Clearing the tracker does not infer victory. The explicit command records the selected outcome and completion time.

## Acceptance criteria

1. A landed attack, save, spell, or other roll appears once in the synchronized encounter's turn log.
2. An applied wound increase appears as `Damage: <amount>` and contributes to Campaign Dashboard damage totals.
3. An applied wound decrease appears as `Healing: <amount>` and contributes to healing totals.
4. Reimporting a snapshot or a later snapshot containing old journal entries never duplicates log rows.
5. Separate Combat Tracker sessions remain separate Lectern encounters.
6. A valid `/lectern-outcome` command completes the encounter and creates one `Outcome` log entry.
7. Invalid events roll back the entire snapshot import.
8. Milestone-one snapshots without events remain valid.

## Runtime acceptance checklist

Use a sanitized Fantasy Grounds 5E test campaign:

1. Start both applications and run `/lectern-export`.
2. Add two combatants, advance a turn, make an attack roll, and apply damage.
3. Apply healing and change temporary HP.
4. Run `/lectern-outcome victory`.
5. Confirm Lectern shows the expected rows once and the Campaign Dashboard totals match.
6. Click **Import Now**, restart Lectern, and confirm no rows duplicate.
7. Clear and repopulate the Combat Tracker, then confirm the new session creates a different Lectern encounter.

Automated tests use sanitized fixture data. Live Fantasy Grounds runtime acceptance remains required before release.
