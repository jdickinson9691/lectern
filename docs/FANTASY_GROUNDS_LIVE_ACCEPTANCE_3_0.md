# Fantasy Grounds Live Acceptance — Lectern 3.0.0

Executed July 20, 2026 (America/Chicago) against the local sanitized `Test` campaign.

## Environment

- Lectern: 3.0.0 from source
- Lectern Sync: 1.4.1; installed files matched the repository exactly
- Fantasy Grounds Unity: 5E ruleset
- Snapshot contract: v1
- Lectern database schema: v9
- Acceptance session: `Lectern 3.0 Acceptance`
- Fantasy Grounds snapshot sequence: 275
- Lectern encounter: ID 28, completed, victory, round 10
- Imported encounter events: 101
- Import result: sequence 275 applied with no reported sync error
- Safety backup: `campaign_manager_backup_20260720_202244.db`

## Result summary

| Scenario | Result | Live evidence |
|---|---|---|
| Resistance | Pass | 10 fire rolled against Goblin Minion 1; 5 applied and 5 resisted. The first roll was performed while the wrong Combat Tracker actor was active, so the applied row was correctly left manual/unattributed. |
| Immunity | Pass with display gap | Wizard1 rolled 2 fire against Goblin Minion 2; 0 applied and 2 negated with matched attribution. The formatted applied row says `0 damage applied from 0 rolled` even though component evidence retains 2 rolled. |
| Vulnerability | Pass | Clean repeat against a 30-HP Goblin Minion 3: 1 fire rolled, 2 applied, and 1 added by vulnerability with matched attribution and matching HP change. |
| Mixed damage | Pass with persistence gap | Fighter1 Greatsword plus `DMG: 1d6 fire` produced fire and slashing components and 15 applied damage. The final snapshot contains component data on the roll event, but Lectern had already imported an earlier form of that event, leaving the stored Damage Roll row as `unknown`; the applied Damage row is correct. |
| Healing | Pass | Cleric1 Healing Word removed 6 wounds from Fighter1, producing 10/10 HP with correct actor, target, action, and amount. |
| Critical hit | Pass | Manually entered natural 20 produced authoritative `Critical Hit`, 25 vs AC 12. |
| Critical miss | Pass | Manually entered natural 1 produced authoritative `Automatic Miss`, 6 vs AC 12. |
| Temporary HP | Pass with display gap | Fighter1 temporary HP changed 0→5; 3 piercing damage changed it 5→2 while HP remained 10/10. Actor, target, applied amount, component, and temporary-HP state were preserved, but the formatted applied row says `3 damage applied from 0 rolled`. |
| Multi-target action | Partial / release blocker | One Burning Hands roll changed both Goblin Minion 3 and Goblin Minion 4. The first target retained Wizard1/Burning Hands attribution; the second target imported as `Manual / Unattributed`. |

## Additional observation

The first vulnerability attempt rolled 6 fire against a 7-HP target. Fantasy Grounds resolved 12 after vulnerability, but the actual wound increase was capped at 7. The event retained component `applied: 12` while its amount and HP change were 7. Campaign damage-type analytics use component applied totals, so overkill can overstate actual HP damage.

## Defects to resolve before release clearance

1. Preserve one roll context for every target affected by a multi-target action instead of consuming it after the first target.
2. Reconcile already-imported event IDs when Fantasy Grounds enriches the same event in a later snapshot; do not leave the stored roll row incomplete or typed as `unknown`.
3. Format negated and temporary-HP-only damage from component rolled totals when the top-level roll total is zero or unavailable.
4. Decide whether applied component totals should be capped to the target's actual HP change for campaign analytics, and implement the chosen rule consistently.

## Automated regression evidence

After the live session, all documented baseline checks passed:

- Campaign Dashboard statistics
- Fantasy Grounds synchronization
- Fantasy Grounds historical reprocessing
- Combat Log UI
- Adaptive layout
- Encounter Builder
- Seeded-database smoke test

## Release decision

The requested live acceptance pass is complete and evidence is recorded. Lectern 3.0.0 is **not yet release-clear** because multi-target attribution is incomplete and the listed event-persistence, display, and overkill-total issues can affect combat-log or campaign-stat accuracy.

## Remediation status — July 21, 2026

All four recorded blockers are fixed in source with Lectern Sync 1.4.2. Roll context is retained per target; later enriched forms of an imported event update the existing combat-log row; component roll totals replace misleading zero-roll displays; and applied component totals are capped proportionally to actual HP loss. The focused synchronization regression and the complete seven-check automated baseline pass. Release clearance still requires installing 1.4.2 and repeating the affected live Fantasy Grounds scenarios.
