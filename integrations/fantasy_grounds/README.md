# Lectern Sync for Fantasy Grounds

This directory contains the implementation workspace for one-way Fantasy Grounds Unity 5E to Lectern synchronization.

The extension is versioned with the snapshot contract and supports the Fantasy Grounds Unity `5E` ruleset. Version 1.1.1 exports loaded class, subclass, species/race, feat, and background records; player characters; prepared encounters with participant statistics; live Combat Tracker state; and a deduplicated journal of combat actions, applied damage, healing, turns, effects, and confirmed outcomes.

```text
extension/LecternSync/  Unpacked Fantasy Grounds extension source
```

Use [Install-FantasyGroundsExtension.ps1](../../scripts/Install-FantasyGroundsExtension.ps1) to install the unpacked extension locally. See [FANTASY_GROUNDS_MILESTONE_1_1.md](../../docs/FANTASY_GROUNDS_MILESTONE_1_1.md) for combat-event scope and [FANTASY_GROUNDS_RUN_TOGETHER.md](../../docs/FANTASY_GROUNDS_RUN_TOGETHER.md) for the intended workflow.

Build a distributable `LecternSync.ext` with:

```powershell
.\scripts\Build-FantasyGroundsExtension.ps1
```

Do not place Fantasy Grounds campaign exports or commercial module data in this repository.
