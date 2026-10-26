# Fantasy Grounds player module adapter

Lectern exports a read-only 5E `.mod` from the existing approved player snapshot. The archive contains `definition.xml` and `client.xml` at its root. `client.xml` contains Story records for approved, player-visible campaign entities, their approved player knowledge, and approved relationships whose endpoints are also exported. Each Story stores its permanent Lectern ID in a non-displayed `lecternid` field. Record node names derive from that ID, so adding other records does not rename existing nodes. DOC Story bodies display approved player text without technical labels.

The adapter reads `PlayerExportService.snapshot()` only. It does not query legacy Lectern tables, GM or internal knowledge, source citations, or audit rows. No database schema change is needed. Export fails when there are no approved records; an existing destination is replaced only after a complete archive has been built and checked.

In Lectern, open **Ashen Player Export** or **Stories**, approve the intended records and player knowledge, preview the player release, then choose **Export Fantasy Grounds Module...**. Put the generated `.mod` in the Fantasy Grounds modules folder, start a 5E campaign, and load the module from Activation. The exported records appear under **Story → Group → Ashen Company**. Review them before sharing with players.

## Scope and next work

This first adapter publishes plain Story text and relationship summaries. It does not import Story edits back from Fantasy Grounds, emit NPC/item/spell ruleset records, copy images, create clickable links, or install modules automatically. Lectern Sync is a separate inbound extension that imports Fantasy Grounds character, encounter, and combat snapshots into Lectern 3.0. It does not approve Ashen canon or replace this outbound player module.

## Runtime checks (2026-10-26)

The approved Ashen Company module was opened in the local `Lectern Adapter Check` 5E campaign. Seven Story records appeared in the **Ashen Company** group. The private Weirhouse Story, encounter, and map are campaign-local and are not packaged in the player module. The integrated Lectern 3.0 source upgraded a copy of the live Ashen database to schema v11, preserved the seven-record player snapshot, and generated a fresh module with zero foreign-key violations. Automated tests check the Story path and exclude GM-only text. A connected-player distribution check remains to be done.

Dedicated FG record mappings, asset packaging, and module update/version handling remain future work.

Format references: [Fantasy Grounds database guide](https://www.fantasygrounds.com/modguide/database.xcp), [module distribution types](https://www.fantasygrounds.com/forums/showthread.php?6446-How-do-players-see-my-modules-Module-data-types-and-distribution=).
