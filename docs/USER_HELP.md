# Lectern Help

**Lüdinn Entertainment Campaign Tracker for Encounters, Rules & Navigation**

Version: 3.0.0 - Workflow and Import Refinement

Lectern organizes campaigns, player characters, encounters, combat journals, and D&D reference data in a local database. Use the navigation bar on the left to move between screens.

## Help contents

Select a title to jump directly to that section.

### Getting started

- [Choose your workflow](#choose-your-workflow)
- [Fantasy Grounds at a glance](#fantasy-grounds-at-a-glance)

### Campaign and combat screens

- [Dashboard](#dashboard)
- [Campaigns](#campaigns)
- [Encounter Builder](#encounter-builder)
- [Combat Dashboard](#combat-dashboard)
- [Combat Narrative](#combat-narrative)

### Character and reference screens

- [Players](#players)
- [Monster Library](#monster-library)
- [Add Monster](#add-monster)
- [Weapons](#weapons)
- [Armor](#armor)
- [Equipment](#equipment)
- [Magic Items](#magic-items)
- [Spells](#spells)

### Integration and data screens

- [CSV Import and Export](#csv-import-and-export)
- [Fantasy Grounds Sync](#fantasy-grounds-sync)
- [Data Workflow](#data-workflow)
- [Error Logs](#error-logs)
- [Help](#help)

### Support and safety

- [Troubleshooting](#troubleshooting)
- [Data safety and ownership](#data-safety-and-ownership)

## Choose your workflow

Lectern supports two distinct encounter workflows. Decide which application owns an encounter before preparing or running it.

### Build and run an encounter in Lectern

Use this workflow when Lectern is the source of truth:

1. Review **Dashboard**.
2. Create a local campaign in **Campaigns**.
3. Add or import characters in **Players**, then use **Manage Party** to save the campaign's regular party.
4. Select that campaign in **Encounter Builder** and create an encounter inside it.
5. Select **Add Campaign Party**, add monsters, then select **Roll Initiative / Start**.
6. Run turns, HP changes, and actions in **Combat Dashboard**.
7. Return to **Campaigns** to record the outcome and review cumulative results.
8. Use **Data Workflow** to back up the database.

A manually built Lectern encounter is local and editable. Lectern owns its roster, initiative, HP, turn order, actions, outcome, and combat journal. It is not sent to Fantasy Grounds.

### Import and run an encounter from Fantasy Grounds

Use this workflow when Fantasy Grounds is the source of truth:

1. Install and enable **Lectern Sync** in the Fantasy Grounds `5E` campaign.
2. Connect the campaign from **Fantasy Grounds Sync** and run `/lectern-export`.
3. Review imported characters in **Players** and imported encounters in **Encounter Builder**.
4. Before combat, enter `/lectern-start Encounter Name` in Fantasy Grounds.
5. Run initiative, turns, targeting, damage, healing, effects, and temporary HP in Fantasy Grounds.
6. Review the synchronized **Live combat** entry in **Combat Dashboard**.
7. Before clearing the Combat Tracker, enter `/lectern-end victory`, `/lectern-end defeat`, `/lectern-end retreat`, or `/lectern-end unresolved`.
8. Review cumulative results in **Campaigns**.

Fantasy Grounds encounters are source-owned. Their roster and combat controls are read-only in Encounter Builder and Combat Dashboard; change those values in Fantasy Grounds and import a new snapshot.

[Back to Help contents](#help-contents)

## Fantasy Grounds at a glance

Fantasy Grounds synchronization is one-way: Fantasy Grounds writes snapshots and Lectern imports them. Lectern never edits Fantasy Grounds campaign data.

The import can add or update:

- A synchronized campaign
- Player-character copies, including equipped weapons and armor
- Loaded class, subclass, species/race, feat, and background references
- Prepared encounter rosters
- Live Combat Tracker state and combat journals
- Authoritative attacks, criticals, damage types, mixed-damage components, healing, effects, temporary HP, and outcomes

The import does not add Fantasy Grounds NPCs to **Monster Library**, populate the standalone **Weapons**, **Armor**, **Equipment**, **Magic Items**, or **Spells** reference tables, or send Lectern-created records back to Fantasy Grounds.

Synchronized names use labels such as **Prepared** and **Live combat**. Local Lectern records have no Fantasy Grounds label.

[Back to Help contents](#help-contents)

## Dashboard

Dashboard is the application home screen. It displays the application version, counts for major record types, current campaigns, encounter totals, and campaign descriptions.

Use it to confirm that local and imported data are present before preparing an encounter.

### Fantasy Grounds impact

- Imported player copies, campaigns, and encounters contribute to Dashboard counts.
- Imported prepared and live encounters both count as encounters because they are separate records with different purposes.
- Dashboard does not show synchronization health or snapshot sequence; use **Fantasy Grounds Sync** for that information.
- Removing or clearing a Fantasy Grounds import changes the related counts but does not remove unrelated local records.

[Back to Help contents](#help-contents)

## Campaigns

Campaigns groups encounters and provides cumulative combat results.

### Create a campaign

1. Enter a campaign name and optional description.
2. Select **Create Campaign**.

Campaign selectors identify each record as **Local** or **Fantasy Grounds**. Local campaigns can be renamed, given a revised description, archived, or restored. Enable **Show archived** when you need to reopen an archived campaign. Fantasy Grounds campaign identity remains source-owned.

### Guided local campaign setup

Select **Guided Local Setup...** when starting a manually managed campaign. The four-step guide keeps the setup work together:

1. Name the local campaign and enter an optional description.
2. Optionally choose player and monster CSV files. Use templates exported from **CSV Import/Export** when starting from scratch.
3. Review validation. Duplicate and error rows block setup; new, modified, and unchanged rows are safe to continue.
4. Choose the regular party. Characters in the selected player CSV are checked automatically, and existing Lectern players remain available.
5. Optionally create an opening encounter. The encounter is created inside the new campaign and the checked party is added immediately.

CSV player and monster records remain reusable application data. The wizard associates the selected players with the campaign, while imported monsters become available in Monster Browser for any local encounter. Imports update matching names using the same preview and safety rules as **CSV Import/Export**. No data is imported until **Finish** is selected and validation passes again.

### Save a persistent party

1. Select a local campaign.
2. Select **Manage Party...**.
3. Check the regular player characters and save.

The saved party is campaign-level membership, not an encounter roster. In Encounter Builder, **Add Campaign Party** copies any party members not already present into the selected campaign encounter. Individual encounter rosters remain editable.

### Add or complete an encounter

1. Select the campaign and an **Unassigned local encounter**.
2. Select **Add to Campaign**. An encounter can belong to one campaign at a time.
3. To finish an encounter, choose it from **Campaign encounter**, select Victory, Defeat, Retreat, or Unresolved, and select **Complete Encounter**.

### Campaign statistics

The summary includes encounter totals, outcomes, rounds, actions, damage, healing, party DPR and HPR, critical-hit and critical-miss leaders, attribution coverage, and leaders for all 13 standard 5E damage types.

The **Party Combat Statistics** section presents Party DPR, Party HPR, critical-hit leaders, and critical-miss leaders in separate cards so each result can be scanned independently. The attribution coverage note beneath the cards explains how much of the imported or manually recorded combat data is eligible for those party metrics.

The lower section places **Party Damage Type Leaders** on the left and **Campaign Encounters** on the right. Each damage-type row uses its own thematic color—for example, red for fire, blue for cold, light green for poison, and dark green for acid—while retaining high-contrast text for readability. Damage-type totals use applied party damage. Rolled-but-unapplied damage, hostile actions, and manual or unattributed events are excluded. Mixed Fantasy Grounds damage is allocated by component after resistance, immunity, vulnerability, and similar adjustments.

### Fantasy Grounds impact

- The imported Fantasy Grounds campaign is synchronized automatically.
- **Guided Local Setup...** creates only local campaigns and never changes or extends an imported Fantasy Grounds campaign.
- Prepared and live-combat records may both appear in the encounter table. They are intentionally separate.
- Fantasy Grounds outcomes come from `/lectern-end`; Lectern does not infer an outcome when the Combat Tracker is cleared.
- Imported authoritative actor affiliation, damage, healing, natural rolls, and damage types feed campaign statistics.
- Incomplete or unattributed historical events remain visible in totals where safe but are not guessed into party leader metrics.
- A local Lectern encounter can be attached to an imported campaign. If that Fantasy Grounds import is cleared, the local encounter is preserved and detached from the removed campaign.

[Back to Help contents](#help-contents)

## Encounter Builder

Encounter Builder creates and prepares local encounters and displays imported Fantasy Grounds encounters.

### Encounter types

| Encounter type | Created from | Purpose | Editable in Lectern |
|---|---|---|---|
| Local Lectern encounter | **Create New Encounter** | Build and run a battle entirely in Lectern | Yes |
| Fantasy Grounds Prepared encounter | A Fantasy Grounds encounter/battle record | Review the planned roster before combat | No |
| Fantasy Grounds Live combat session | `/lectern-start` plus the Combat Tracker | Review synchronized initiative, HP, turns, and journal data | No |

A prepared encounter and its live session can be linked when their name and roster produce one unambiguous match. Lectern names the counterpart in the selector. If several prepared encounters match equally well, Lectern leaves them unlinked rather than guessing.

### Build a local encounter

1. Select a local campaign, or choose **Unassigned Local** for an encounter that will be assigned later.
2. Enter a unique name and select **Create New Encounter**. The encounter is created inside the selected local campaign.
3. Select **Add Campaign Party** to add the saved regular party, or check individual characters and select **Add Selected Player(s)**.
4. Search **Monster Browser**, choose quantity, and select **Add Monster(s)**.
5. Review or remove combatants.
6. Select **Roll Initiative / Start** and open **Combat Dashboard**.

Local encounters always begin empty. If a requested name already exists, Lectern creates a unique name such as `Goblin Ambush 2`.

Use the campaign selector to show all encounters, only unassigned local encounters, or one campaign's encounters. Creating a local encounter while a Fantasy Grounds campaign is selected is blocked so ownership remains clear.

### Fantasy Grounds impact

- Imported selectors label records as **Prepared** or **Live combat**.
- Prepared records show the Fantasy Grounds encounter roster. They do not contain the live combat journal.
- Live-combat records show the synchronized Combat Tracker roster and are selected automatically after an import.
- Add, remove, initiative, and start controls are disabled for Fantasy Grounds-owned encounters. Make those changes in Fantasy Grounds.
- Fantasy Grounds NPC participants do not become reusable Monster Library records.
- Local encounters remain editable and are never written back to Fantasy Grounds.

[Back to Help contents](#help-contents)

## Combat Dashboard

Combat Dashboard runs local encounters and reviews local or synchronized combat journals.

The workspace opens in two columns. **Campaign Entities** occupies the left 25% with the current encounter roster and local turn, HP, and action controls. **Combat Session Log** occupies the remaining 75% with the synchronization notice, search and result filters, and structured journal. Drag the divider when a particular encounter needs more roster or journal space.

### Run local combat

- Use the campaign selector to focus the encounter list on one campaign, all campaigns, or unassigned local encounters.
- **Previous Turn** moves backward.
- **Next / End Turn** advances and starts a new round after the final combatant.
- Select a target, enter an amount, and use **Apply Damage** or **Apply Healing**.
- Choose an action type, enter details, and use **Log Action**.

Local damage cannot reduce HP below zero, healing cannot exceed maximum HP, and both operations create combat-log entries. The active combatant is credited as actor and the selected combatant as target.

### Review the combat journal

The structured journal separates round, actor, action type, roll, target, defense or HP, named action, damage type, and result. Search and filters can narrow the journal. Double-click an event to expand its stored details and timestamp.

### Fantasy Grounds impact

- Fantasy Grounds prepared entries show a roster but no live journal. Follow the displayed counterpart link/name to the live session.
- Fantasy Grounds live sessions show synchronized turn order, initiative, AC, HP, and journal events.
- Source-owned controls are read-only. Apply turns, damage, healing, and effects in Fantasy Grounds.
- Resistance, immunity, vulnerability, temporary HP, mixed damage, and overkill are displayed from authoritative applied results. Component applied totals are capped to actual HP loss.
- Multi-target actions retain actor and action attribution for every target.
- Manual Fantasy Grounds wound edits remain **Manual / Unattributed** and use `unknown` damage type unless reliable source evidence exists.
- Natural 20 and natural 1 results retain authoritative critical-hit and automatic-miss outcomes.

[Back to Help contents](#help-contents)

## Combat Narrative

Combat Narrative retells the selected encounter as chronological, round-by-round prose derived from the authoritative Combat Session Log.

- Use the same **Campaign** and **Encounter** selectors as Combat Dashboard.
- Rounds are presented from earliest to latest so the account reads as a continuous story.
- Attacks, critical hits, misses, damage, damage types, healing, target HP, actions, notes, and unattributed changes are translated into a deterministic, gritty heroic chronicle.
- Turn-start and turn-end markers are omitted from the story.
- Source-application names, initialization noise, unresolved placeholders, and duplicate roll/damage rows are omitted so the result reads as a battle story rather than an import transcript.
- The narrative is regenerated from saved events whenever the selection or underlying log changes. It does not modify or replace the structured combat journal.

### Fantasy Grounds impact

- Prepared Fantasy Grounds encounters may have a roster but no narrative because they do not contain a live combat journal.
- Live Fantasy Grounds sessions use the synchronized authoritative rolls, results, damage, healing, and HP evidence already stored in Lectern.
- Manual or unattributed changes remain explicitly unattributed; the narrative does not invent an actor or action.
- Importing a newer snapshot refreshes the derived narrative without writing data back to Fantasy Grounds.

[Back to Help contents](#help-contents)

## Players

Players contains the character list and Player Character Editor.

### Player controls

- **+ New Player** starts a local character.
- **Import Character PDF...** previews and imports a supported fillable character sheet. The preview also shows a detected or existing portrait and lets you choose or clear an image.
- **Edit Selected**, **Duplicate**, **Delete**, **Refresh**, and **Search** manage saved characters.

The editor includes General, Abilities, Equipment, Inventory, Combat, Skills, Saving Throws, and Notes tabs. PDF imports can include names, class information, ability scores, AC, HP, initiative, feats, inventory, proficiencies, equipped items, spellcasting ability, feature notes, and an embedded portrait when the PDF contains one. A separately selected portrait is copied into Lectern's managed data, preserved at its original resolution, and displayed through a normalized thumbnail. Re-importing a sheet without a portrait preserves the character's existing image unless you explicitly clear it.

### Fantasy Grounds impact

- Fantasy Grounds character copies are imported with identity, class, level, abilities, AC, HP, initiative, feats, and equipped weapon and armor names.
- Multiple equipped weapons or armor pieces such as shields are stored as semicolon-separated names.
- If a local character has the same name, Lectern preserves it and gives the imported copy a collision-safe Fantasy Grounds suffix.
- Equipped weapons and armor are recovered from the Fantasy Grounds character inventory and matched to Lectern's SRD library names when a confident match exists. Custom or unmatched item names are preserved.
- Changes made to an imported character in Lectern can be replaced by the next Fantasy Grounds import. Edit source-owned values in Fantasy Grounds.
- Duplicating an imported character creates a local copy that can be edited independently.
- Clearing the selected Fantasy Grounds import removes only its linked player copies; same-name local players remain.

[Back to Help contents](#help-contents)

## Monster Library

Monster Library is a read-only table of bundled, CSV-imported, and manually maintained monsters. It shows primary AC, HP, challenge rating, source, and available notes.

### Fantasy Grounds impact

Fantasy Grounds NPCs used in prepared encounters or the Combat Tracker remain encounter participants only. They do not populate Monster Library and do not replace local monster records.

[Back to Help contents](#help-contents)

## Add Monster

Use Add Monster to create or edit reusable local monster records. Enter a name, type, AC, HP, challenge rating, and notes, then select **Save Monster**. Saved monsters become available in Encounter Builder.

### Fantasy Grounds impact

This screen is local-only. Saving a monster does not send it to Fantasy Grounds, and Fantasy Grounds synchronization does not overwrite it.

[Back to Help contents](#help-contents)

## Weapons

Weapons displays the local weapon reference table and supplies Player Editor suggestions.

### Fantasy Grounds impact

Fantasy Grounds synchronization imports equipped weapon names as character text but does not populate or change the Weapons reference table.

[Back to Help contents](#help-contents)

## Armor

Armor displays the local armor reference table and supplies Player Editor suggestions.

### Fantasy Grounds impact

Fantasy Grounds synchronization imports equipped armor and shield names as character text but does not populate or change the Armor reference table.

[Back to Help contents](#help-contents)

## Equipment

Equipment displays general local gear reference data.

### Fantasy Grounds impact

Fantasy Grounds inventory is not imported into this reference table. Equipped weapon and armor names appear on imported characters instead.

[Back to Help contents](#help-contents)

## Magic Items

Magic Items displays local rarity, type, attunement, and notes data.

### Fantasy Grounds impact

Fantasy Grounds synchronization does not populate or modify this table.

[Back to Help contents](#help-contents)

## Spells

Spells displays the local spell reference table.

### Fantasy Grounds impact

Fantasy Grounds synchronization can record a named spell action in a combat journal, but it does not populate or modify the Spells reference table.

[Back to Help contents](#help-contents)

## CSV Import and Export

CSV Import/Export supports Players, Monsters, Weapons, Armor, Equipment, Magic Items, Spells, and Rules Reference.

### Import safely

1. Select a table and choose **Validate / Preview CSV...**.
2. Review New, Modified, Unchanged, Duplicate, and Error statuses.
3. Correct Duplicate or Error rows before importing.
4. Choose **Import Selected CSV...** and confirm the preview.

Most tables match by Name. Rules Reference matches by Category and Name. Export controls can write one table, all supported tables, or an empty template.

### Fantasy Grounds impact

- CSV export can include imported Fantasy Grounds player copies because they are stored in the Players table.
- A CSV edit to a linked Fantasy Grounds player can be overwritten by the next synchronization. Duplicate the character first when a permanent local variant is needed.
- CSV operations do not update Fantasy Grounds and do not change the handoff snapshot.
- Fantasy Grounds loaded class, subclass, species/race, feat, and background entries are stored as synchronized reference/provenance records, not as weapon, armor, equipment, magic-item, or spell imports.

[Back to Help contents](#help-contents)

## Fantasy Grounds Sync

Fantasy Grounds Sync connects one Fantasy Grounds Unity `5E` campaign to Lectern through a local handoff folder. Fantasy Grounds remains authoritative.

### Install the extension

1. In the Fantasy Grounds launcher, use the folder button to locate its data folder.
2. During Lectern installation, choose that data folder's `extensions` subfolder when prompted. The installer uses an account-agnostic default and supports custom locations.
3. For a portable installation, copy `FantasyGrounds\LecternSync.ext` from the Lectern installation folder into the Fantasy Grounds `extensions` folder.
4. Restart Fantasy Grounds, enable **Lectern Sync**, and load the campaign as GM.

### Connect and export a campaign

1. Open **Fantasy Grounds Sync** in Lectern.
2. Select **Select Campaign Folder...** and choose the individual campaign folder beneath Fantasy Grounds `campaigns`.
3. Lectern creates or selects its `lectern-sync` handoff folder.
4. Enter `/lectern-export` in Fantasy Grounds chat.
5. Confirm campaign name, `5E` ruleset, extension version, sequence, time, and counts in Lectern.

Run `/lectern-export` after each Fantasy Grounds campaign start and after changing loaded modules.

### Start and end synchronized combat

1. Populate the Combat Tracker and prepare initiative.
2. Enter `/lectern-start Encounter Name` before the first roll.
3. Confirm the Sync screen shows the session as **Open**.
4. Run combat in Fantasy Grounds.
5. Before clearing the tracker, enter `/lectern-end victory`, `/lectern-end defeat`, `/lectern-end retreat`, or `/lectern-end unresolved`.
6. Confirm the session is **Closed**.

Only one synchronized encounter can be open. Rolls made without an open session are not added to its journal. Session identity and sequence survive a Fantasy Grounds reload.

### Automatic import

When **Automatically import new snapshots** is enabled, Lectern checks once per second. Successful imports focus the updated live session in Encounter Builder and Combat Dashboard. Later authoritative forms of an already imported event repair the existing row rather than creating a duplicate.

### Reprocess historical combat logs

Use **Reprocess Imported Combat Logs** to rebuild linked rows from preserved raw events after upgrading Lectern. Lectern previews the scope, creates a backup, and reports updated, unchanged, incomplete, and failed events. Reprocessing is repeatable and never changes local log rows.

Reprocessing cannot invent missing source evidence. Unavailable actor, target, roll, defense, action, damage type, or result fields remain explicit.

### Clear one Fantasy Grounds import

1. End any open session with `/lectern-end outcome`.
2. For a fresh test journal, enter `/lectern-reset confirm` in Fantasy Grounds.
3. Select the imported campaign in Lectern and choose **Clear Selected FG Import**.
4. Review the preview and confirm.

Lectern creates a backup, disables automatic import, and removes only linked campaign, encounter, journal, player-copy, combatant, and synchronization records. Local records are preserved.

### Sync troubleshooting

- Export error: select the campaign folder in Lectern before `/lectern-export`.
- Extension missing: confirm `LecternSync.ext` is directly inside the selected Fantasy Grounds `extensions` folder and restart Fantasy Grounds.
- No combat events: confirm the session is **Open** and `/lectern-start` was entered before rolling.
- Old events return after clearing: run `/lectern-reset confirm` before importing again.
- Data unchanged: run `/lectern-export`, then select **Import Now**.
- Modules changed: load the required modules and perform a new full export.
- Mapping or validation failure: review **Error Logs**.

[Back to Help contents](#help-contents)

## Data Workflow

Data Workflow maintains the active SQLite database.

- **Backup Database** creates a selected copy.
- **Restore Database** creates a safety backup, then replaces the active database.
- **Reset Empty Database** creates a backup and starts with an empty schema.
- **Reset and Reseed** creates a backup and reloads bundled monster and SRD reference data.

### Fantasy Grounds impact

- Database backups include imported Fantasy Grounds records, event receipts, links, and source state stored in the database.
- A backup does not copy the Fantasy Grounds campaign or its `lectern-sync` handoff folder.
- The selected handoff folder and automatic-import preference live in Lectern's separate local configuration file, not inside a database backup.
- Restoring an older database can restore an older imported sequence. Review the Sync screen and local automatic-import setting afterward.
- Resetting removes imported data from Lectern but does not alter Fantasy Grounds. Reconnect the campaign and export again to restore it.

[Back to Help contents](#help-contents)

## Error Logs

Error Logs displays Lectern application logs. Reproduce the issue, select **Refresh**, open the newest log, and include relevant details when reporting a problem.

### Fantasy Grounds impact

Snapshot validation, folder access, import, reprocessing, and automatic-sync failures are recorded here. Fantasy Grounds-side extension errors may also require reviewing Fantasy Grounds logs or chat output.

[Back to Help contents](#help-contents)

## Help

Help displays this guide. Select a linked title in **Help contents** to jump to a section. Select **Back to Help contents** from a section to return to the index. During development, select **Reload Help** after changing this file.

### Fantasy Grounds impact

The Help screen is read-only and does not trigger imports or change synchronized data.

[Back to Help contents](#help-contents)

## Troubleshooting

### PDF import finds incorrect values

Review the preview and cancel rather than importing incorrect data. Image-only PDFs may require OCR or manual entry.

Some PDF exporters, including current D&D Beyond sheets, may omit the character portrait even though it appears on the website. Use **Choose Image...** in the import preview to select a separate PNG, JPEG, WebP, or BMP file. Characters without an image display an initials-based fallback.

### A player fails to open or the wrong player is selected

Select the full row and use **Edit Selected**. Current builds normalize missing numeric and currency values and load records by database ID.

### Monsters are missing

Check the Dashboard count. Use **Reset and Reseed** only when you intend to refresh bundled local reference data. Fantasy Grounds encounter NPCs do not populate Monster Library.

### Players are missing from Encounter Builder

Save local players, then refresh or reopen Encounter Builder. For Fantasy Grounds characters, perform a new export/import and confirm the Players count increased.

### A Fantasy Grounds encounter cannot be edited

This is expected. Prepared and live-combat records are source-owned. Change them in Fantasy Grounds. Create a new local Lectern encounter when you need an independently editable version.

### A prepared encounter has no combat journal

Open its linked **Live combat** counterpart. If none exists, run `/lectern-start`, perform combat in Fantasy Grounds, and import the updated snapshot.

### Equipped weapon or armor is empty on an imported character

Confirm Lectern Sync 1.4.3 or newer is enabled, mark the item equipped in the Fantasy Grounds inventory, restart Fantasy Grounds after extension updates, and run `/lectern-export` again.

### Ability totals look wrong

Review Base, Species, and Feat values. Total is their sum, and Modifier is calculated from Total. Fantasy Grounds-imported ability values can be replaced on the next sync.

### The application will not start

Review the application log in Lectern's LocalAppData folder and verify that the latest installer completed successfully.

[Back to Help contents](#help-contents)

## Data safety and ownership

- Back up before large imports, restores, resets, or extensive character edits.
- Review PDF and CSV previews before confirming.
- Lectern-created campaigns, encounters, players, monsters, and reference data remain local.
- Fantasy Grounds-created records are imported one-way and can be refreshed or removed without writing back to Fantasy Grounds.
- Never edit the Fantasy Grounds handoff snapshot manually while automatic import is enabled.
- Generated combat logs and campaign totals depend on the underlying encounter and attribution records.
- Lectern stores user data locally and does not require a cloud connection for normal use.

[Back to Help contents](#help-contents)
