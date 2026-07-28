# FG-EFFECT-002 Test7 Armor live evidence

Recorded: 2026-07-28
Ruleset: Fantasy Grounds Unity 5E, 2024 player content
Lectern Sync: 1.4.11
Session: `Test7 Armor`

## Fantasy Grounds evidence

The host used Warlock1's Armor of Shadows action. Fantasy Grounds displayed:

```text
Warlock1: Armor of Shadows -
Effect ['AC: 3; [D: 8 hours]']
-> [to Warlock1]
```

The Combat Tracker showed `AC: 3` on Warlock1.

## Imported event

The isolated live session contained three events:

1. Encounter Start — `Test7 Armor`
2. Effect — actor Warlock1, target Warlock1, Action `Effect`,
   `Effect added to Warlock1: AC: 3; [D: 8 hours]`
3. Encounter End — unresolved

The exported/imported effect did not retain Armor of Shadows as
`action_name` or `originating_action`.

## Narrative result

```text
Warlock1 gains stronger protection against attack.
```

The narrative remained mechanically grounded but could not name Armor of
Shadows because the authoritative event lacked that provenance.

## Acceptance conclusion

`FG-EFFECT-001` passed automated verification but failed this fresh live
acceptance. `FG-EFFECT-002` must reproduce the actual Fantasy Grounds
announcement/effect ordering and preserve the named power without deriving it
from `AC: 3`.

## Automated remediation

Inspection of the installed 5E and CoreRPG rule sources confirmed that live
effect powers travel through `PowerManager.performAction` and
`ActionEffect.getRoll`. The latter does not invoke the
`onActionPostGetRoll/effect` hook used by `FG-EFFECT-001`.

The repository correction now captures the authoritative power node at
`PowerManager.performAction` before delegating to Fantasy Grounds, then
correlates the resulting effect by actor, known self-target, action and power
paths, mechanical effect text, event sequence, and bounded timing. A dedicated
Test7 Armor-shaped regression verifies named and generic controls. All sixteen
repository regression scripts passed on 2026-07-28.

This evidence remains the original failing live observation. A fresh packaged
and installed extension must pass the owner-coordinated live check before
`FG-EFFECT-002` can be completed.
