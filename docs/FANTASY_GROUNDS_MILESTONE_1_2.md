# Fantasy Grounds Integration - Milestone 1.2

## Objective

Improve live 5E combat fidelity without changing the one-way ownership boundary: Fantasy Grounds remains authoritative and Lectern records resolved outcomes.

## Delivered behavior

- Attack events are captured from Fantasy Grounds' `onAttackPostResolve` event.
- Natural 1, natural 20, expanded critical ranges, effect-adjusted attack totals, and effect-adjusted defense use the result already calculated by the 5E ruleset.
- Attack metadata retains the natural die, final total, final defense, attack-effect adjustment, defense-effect adjustment, and authoritative result.
- Damage rolls retain raw dice, the complete Fantasy Grounds modifier value, and the net roll.
- Applied damage comes from Combat Tracker state changes rather than the unapplied roll.
- When applied damage differs from the roll, Lectern reports the reduction, negation, or increase.
- Damage and healing attribution must match a recent roll type and target. Context expires after ten seconds and is cleared after use.
- Manual or stale Combat Tracker changes are labeled `Manual / Unattributed`.

## Automated acceptance

The Fantasy Grounds synchronization regression covers:

1. A normal authoritative hit.
2. A natural-20 critical hit even when the total is below the target defense.
3. A natural-1 automatic miss even when the total exceeds the target defense.
4. Raw dice plus entity/effect modifiers producing the net attack and damage totals.
5. Damage reduced between roll and application.
6. Manual damage remaining unattributed.
7. Snapshot replay deduplication and separate combat-session ownership.

## Live 5E acceptance

Use the sanitized `Test` campaign after installing Lectern Sync 1.2.0:

1. Restart Fantasy Grounds and confirm Lectern Sync 1.2.0 is enabled.
2. Run `/lectern-export`, then enable automatic import in Lectern.
3. Roll a normal attack that hits and one that misses.
4. Roll a natural 20 and confirm `Critical Hit` is imported regardless of target AC.
5. Roll a natural 1 and confirm `Automatic Miss` is imported regardless of bonuses.
6. Apply damage to a resistant or otherwise adjusted target and confirm rolled versus applied damage is shown.
7. Apply damage that is fully negated and confirm zero applied damage is recorded when the Combat Tracker changes expose it.
8. Apply healing and confirm actor, target, amount, and resulting HP.
9. Edit wounds manually after the roll context expires and confirm the row says `Manual / Unattributed`.
10. Exercise temporary HP and a multi-target action; record any remaining ruleset-specific gaps for the next milestone.

## Known boundary

Combat Tracker wound deltas are the final authority for applied damage and healing. A change fully absorbed by temporary HP may be represented as a temporary-HP state change rather than a wounds event. Multi-target attribution is limited by the target context Fantasy Grounds exposes to the extension's roll callback and remains a live acceptance focus.
