# Lectern Sync for Fantasy Grounds

This directory contains the implementation workspace for one-way Fantasy Grounds Unity 5E to Lectern synchronization.

The extension is versioned with the snapshot contract and supports the Fantasy Grounds Unity `5E` ruleset. Version 1.4.10 exports loaded class, subclass, species/race, feat, and background records; complete player characters using both legacy and 2024 5E armor-class paths plus equipped weapon and armor inventory entries; campaign-owned prepared encounters without flooding Lectern with module reference battles; and durable explicit Combat Tracker sessions started with `/lectern-start` and closed with `/lectern-end`. Session identity and event sequence survive extension reloads, snapshots retain the accumulated event journal, and `/lectern-reset confirm` clears a closed journal for fresh testing. Attack and save rows use Fantasy Grounds' authoritative post-resolution results; the generic dice hook is suppressed for those saves so each target appears once. Damage rows distinguish actual HP damage, resistance or numerical reduction, vulnerability increases, temporary-HP absorption, and overflow beyond remaining HP. Resolved damage retains eligible named effect contributors such as Sneak Attack, Hunter's Mark, and Divine Smite, including one-roll effects consumed immediately before damage resolution. Healing rows preserve the originating actor and named spell or ability for both rolled healing and fixed healing such as Lay on Hands; manual HP edits remain unattributed. Combat Tracker effect additions and removals resolve source paths to named combatants and retain both the originating power, spell, or ability and the exact mechanical effect label. Concentration rolls are recorded as self-referential concentration checks rather than inheriting the actor's selected target. A disappearing effect is recorded as removed without guessing why it ended. Manual or stale changes remain unattributed and use an unknown damage type.

```text
extension/LecternSync/  Unpacked Fantasy Grounds extension source
```

Use [Install-FantasyGroundsExtension.ps1](../../scripts/Install-FantasyGroundsExtension.ps1) to install the unpacked extension locally. See [FANTASY_GROUNDS_MILESTONE_1_1.md](../../docs/FANTASY_GROUNDS_MILESTONE_1_1.md) for combat-event scope and [FANTASY_GROUNDS_RUN_TOGETHER.md](../../docs/FANTASY_GROUNDS_RUN_TOGETHER.md) for the intended workflow.

Build a distributable `LecternSync.ext` with:

```powershell
.\scripts\Build-FantasyGroundsExtension.ps1
```

Do not place Fantasy Grounds campaign exports or commercial module data in this repository.
