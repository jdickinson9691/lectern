# Ashen Company on Lectern 3.0

The Ashen canon layer from the Desktop checkout has been ported onto the current Lectern 3.0 source. The GitHub `main` branch had diverged from that older checkout, so this integration preserves the existing 3.0 Fantasy Grounds Sync, combat analysis, campaigns, and character workflows.

## Data boundary

- The existing `campaigns` and combat tables remain Lectern's general campaign and Fantasy Grounds snapshot store.
- The optional `campaign_entities`, knowledge, source, relationship, audit, and review tables hold Ashen canon and publication state. Permanent IDs are stable across renames.
- Schema v11 adds that layer to Lectern schema v10. The dedicated **Start Ashen Company.cmd** launcher opts into the Ashen root record and uses its isolated user-data directory. Generic Lectern databases receive empty optional tables and no Ashen seed.
- Existing Ashen schema-v8 databases are detected by their tables and upgrade to v11 without reseeding. Before routine use, make a backup using Data Workflow.
- Player and encounter rows created in the Ashen database receive permanent links. Generic Lectern users and rules catalog rows are not automatically claimed as Ashen records.

## Two Fantasy Grounds directions

| Direction | Component | Scope |
|---|---|---|
| Lectern to Fantasy Grounds | Ashen player `.mod` adapter | Approved, player-visible Story records only |
| Fantasy Grounds to Lectern | Lectern Sync extension | Characters, prepared/live encounters, combat events, and snapshots |

Fantasy Grounds stays authoritative for live combat. Lectern stays authoritative for Ashen canon and player publication. A Fantasy Grounds Story edit does not flow back into canon. The private GM encounter and map stay in the local Fantasy Grounds campaign and outside the player module.

## Source and publication

Ashen pages now appear in the Lectern navigation: Stories; Story & Mission Drafts; Missions; Campaign NPCs, Locations, and Factions; Canon Review (GM); and Ashen Player Export. The latter previews approved content before JSON or `.mod` release. Full CSV exports still carry GM data.

The public repository includes the player guide and the working class access list. The GM guide, live database, private map, and campaign-local Fantasy Grounds files remain outside this public repository to protect unrevealed campaign details.

## Verification

The integrated source upgraded a consistent copy of the live Ashen database to v11. The seven approved player records were unchanged, all foreign keys passed, a fresh player `.mod` was generated, and the combined navigation initialized in offscreen UI testing. The Ashen automated suite covers player privacy, IDs, approval, review, content agents, and the Story export path. The Lectern 3.0 regression scripts must continue passing before a release build.

Remaining work: encode the Company ledger, class access and unlocks, roster availability, deployment validation, mission clocks, and after-action transactions. Native Fantasy Grounds Quest, NPC, image, and encounter mappings require explicit approval and visibility rules before export.
