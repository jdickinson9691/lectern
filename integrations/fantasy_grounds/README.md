# Lectern Sync for Fantasy Grounds

This directory contains the implementation workspace for one-way Fantasy Grounds Unity 5E to Lectern synchronization.

The extension is versioned with the snapshot contract and supports the Fantasy Grounds Unity `5E` ruleset. Version 1.4.8 exports loaded class, subclass, species/race, feat, and background records; complete player characters using both legacy and 2024 5E armor-class paths plus equipped weapon and armor inventory entries; campaign-owned prepared encounters without flooding Lectern with module reference battles; and durable explicit Combat Tracker sessions started with `/lectern-start` and closed with `/lectern-end`. Session identity and event sequence survive extension reloads, snapshots retain the accumulated event journal, and `/lectern-reset confirm` clears a closed journal for fresh testing. Attack rows use Fantasy Grounds' authoritative post-resolution result, natural die, effect-adjusted total, and final defense. Damage rows distinguish actual HP damage, resistance or numerical reduction, vulnerability increases, temporary-HP absorption, and overflow beyond remaining HP. Resolved damage retains eligible named effect contributors such as Sneak Attack, Hunter's Mark, and Divine Smite without assigning a contributor merely from extra dice or a damage type. Healing rows preserve the originating actor and named spell or ability for both rolled healing and fixed healing such as Lay on Hands; manual HP edits remain unattributed. Saving-throw rows use the 5E post-resolution source and target, originating spell or ability, save ability, final DC, final total, and success or failure; every target of a multi-target power receives its own authoritative row. Damage rows use authoritative post-resolution component results to retain mixed types plus rolled, applied, resisted, and vulnerability amounts. Combat Tracker effect additions and removals retain their label, target, duration, source reference or name, and source-attribution method. A disappearing effect is recorded as removed; the extension does not guess whether it expired naturally, was consumed, lost concentration, or was manually cleared. Multi-target actions retain context for every target, and later authoritative resolution can enrich an earlier form of the same event. Manual or stale changes remain unattributed and use an unknown damage type.

```text
extension/LecternSync/  Unpacked Fantasy Grounds extension source
```

Use [Install-FantasyGroundsExtension.ps1](../../scripts/Install-FantasyGroundsExtension.ps1) to install the unpacked extension locally. See [FANTASY_GROUNDS_MILESTONE_1_1.md](../../docs/FANTASY_GROUNDS_MILESTONE_1_1.md) for combat-event scope and [FANTASY_GROUNDS_RUN_TOGETHER.md](../../docs/FANTASY_GROUNDS_RUN_TOGETHER.md) for the intended workflow.

Build a distributable `LecternSync.ext` with:

```powershell
.\scripts\Build-FantasyGroundsExtension.ps1
```

Do not place Fantasy Grounds campaign exports or commercial module data in this repository.
