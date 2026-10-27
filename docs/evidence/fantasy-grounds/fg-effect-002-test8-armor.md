# FG-EFFECT-002 Test8 Armor live evidence

Contract: `FG-EFFECT-002`
Lectern Sync: 1.4.12
Encounter: `Test8 Armor`
Date: 2026-07-28

## Authoritative observation

The owner started a fresh, isolated encounter and invoked Warlock1's Armor of
Shadows feature. Fantasy Grounds displayed the owning feature and then applied
its linked spell effect:

```text
Warlock1: Armor of Shadows -
Effect ['AC: 3; [D: 8 hours]'] -> [to Warlock1]
```

After import, Lectern preserved actor, target, duration, and mechanical effect,
but named the Action `Mage Armor`. Combat Narrative consequently said:

```text
Warlock1 invokes Mage Armor, reinforcing Warlock1's defenses.
```

This is improved over the generic `Effect` result from Test7 Armor, but it does
not preserve the owning feature Fantasy Grounds displayed.

## Campaign-record structure

The sanitized character hierarchy establishes the authoritative relationship:

```text
Warlock1
└─ powers
   ├─ Armor of Shadows
   │  ├─ group: Eldritch Invocations (Warlock)
   │  ├─ executable actions: none
   │  └─ description link: Spell: Mage Armor
   └─ Mage Armor
      ├─ group: Eldritch Invocations (Warlock)
      └─ effect action: AC: 3
```

Armor of Shadows and Mage Armor are sibling power records in the same group.
The feature's formatted description links Mage Armor; the Mage Armor record
owns the executable effect action. The prior correction selected only the
executable power record and therefore stopped one level short of the
authoritative feature provenance.

## Required correction

When an executed power has one unique, non-executable sibling in the same
power group whose authoritative description references that executed power,
Lectern Sync may use the sibling as the owning power. If the relationship is
absent or ambiguous, it must retain the executed power name. The correction
must not derive Armor of Shadows from `AC: 3`, duration, class, or D&D rules.

## Automated fixture

`scripts/fantasy_grounds_live_effect_provenance_test.py` models:

```text
Armor of Shadows -> Mage Armor -> AC: 3
```

It also retains the generic-effect control so raw armor mechanics cannot be
renamed without authoritative provenance.

## Acceptance status

Test8 is a failing live-evidence case. A fresh Test9 Armor session using the
corrected package must show `Armor of Shadows` in the imported Action column
and narrative while retaining Warlock1 as actor and target and keeping the
mechanical numbers out of the prose.
