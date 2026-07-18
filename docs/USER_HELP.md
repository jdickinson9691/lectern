# Lectern - D&D Campaign Manager Help

Version: 2.9.5 - Workflow and Import Refinement

Lectern organizes campaigns, player characters, encounters, combat logs, and D&D reference data in a local database. Use the navigation bar on the left to move through the application.

## Recommended workflow

For a new game, use Lectern in this order:

1. Review **Dashboard**.
2. Create a campaign in **Campaigns**.
3. Add or import characters in **Players**.
4. Create an encounter in **Encounter Builder**.
5. Add players and monsters, then roll initiative.
6. Run the encounter in **Combat Dashboard**.
7. Return to **Campaigns** to record the outcome and review cumulative results.
8. Use **Data Workflow** to back up the database.

## Dashboard

Dashboard is the application home screen. It displays:

- Application version
- Counts for players, monsters, encounters, combatants, weapons, armor, and spells
- Current campaigns
- Number of encounters assigned to each campaign
- Campaign descriptions

Use Dashboard to confirm that your campaign and reference data are available before preparing an encounter.

## Campaigns

Campaigns group encounters and provide cumulative combat results.

### Create a campaign

1. Open **Campaigns**.
2. Enter a campaign name.
3. Optionally enter a description.
4. Click **Create Campaign**.

### Add an encounter to a campaign

1. Select the campaign.
2. Select an encounter.
3. Click **Add Encounter**.

An encounter can belong to one campaign at a time.

### Complete an encounter

1. Select the encounter.
2. Choose **Victory**, **Defeat**, **Retreat**, or **Unresolved**.
3. Click **Complete Encounter**.

### Campaign statistics

The campaign summary includes:

- Total and completed encounters
- Victories, defeats, and retreats
- Total combat rounds
- Logged actions
- Damage and healing recorded in combat logs

The encounter history shows status, outcome, rounds, combatants, actions, and completion time.

## Encounter Builder

Encounter Builder creates encounters and prepares their combatants.

### Create an encounter

1. Enter an encounter name, such as `Goblin Ambush`.
2. Click **Create New Encounter**.
3. The new encounter becomes selected in the **Active** dropdown.

Every new encounter starts empty. If its requested name already exists, Lectern creates a unique name such as `Goblin Ambush 2` rather than reusing the previous combatants.

Use the **Active** dropdown to open an existing encounter.

### Add monsters

1. Search for a monster in **Monster Browser**.
2. Select the monster.
3. Set **Quantity**.
4. Click **Add Monster(s)**.

Each copy receives a separate combatant record.

### Add players

1. Check one or more characters in **Players**.
2. Click **Add Selected Player(s)**.

Players must be saved in the Players section before they appear here.

### Start combat

1. Review the Encounter Combatants table.
2. Remove unwanted combatants with **Remove Selected**.
3. Click **Roll Initiative / Start**.
4. Open **Combat Dashboard**.

## Combat Dashboard

Combat Dashboard runs an encounter round by round.

### Turn order

The table shows the active turn, combatant name, initiative, armor class, current HP, and maximum HP. The heading displays the current round and active combatant.

- **Previous Turn** moves backward.
- **Next / End Turn** advances to the next combatant.
- Advancing beyond the final combatant starts a new round.

### Damage and healing

1. Select a combatant. If none is selected, Lectern uses the active combatant.
2. Enter an amount.
3. Click **Apply Damage** or **Apply Healing**.

Damage cannot reduce HP below zero. Healing cannot exceed maximum HP. Both operations create combat-log entries.

### Log an action

1. Choose Attack, Spell, Save, Condition, Reaction, Lair Action, or Note.
2. Enter the action details.
3. Click **Log Action**.

Campaign statistics use the saved encounter and combat-log records.

## Players

Players contains the character list and the Player Character Editor.

### Player list controls

- **+ New Player** clears all editor tabs for a new character.
- **Import Character PDF...** extracts and previews a character-sheet PDF.
- **Edit Selected** loads the selected player from the database.
- **Duplicate** creates a copy.
- **Delete** removes the player record after confirmation.
- **Refresh** reloads the list.
- **Search** filters characters using their stored data.

The table uses single full-row selection. Selecting a player or clicking **Edit Selected** resets every editor tab and loads the selected character's saved values.

### Create a character manually

1. Click **+ New Player**.
2. Complete the editor tabs described below.
3. Click **Save Player**.

Character Name is required.

### Import a character PDF

Lectern supports common fillable D&D character sheets, including D&D Beyond-style exports and compatible Roll20 layouts.

1. Click **Import Character PDF...**.
2. Select a `.pdf` character sheet.
3. Review the extracted values in the scrollable preview.
4. Review any warnings.
5. Click **Import Character** to save the character, or **Cancel**.
6. The imported character opens in the editor for corrections.
7. Click **Save Player** after making corrections.

If a player with the same character name exists, importing updates that record.

PDF import can detect:

- Character and player names
- Species, class, level, and background
- Ability scores
- Armor class, hit points, and initiative
- Feats
- Inventory with quantities and weights
- Skill proficiencies and expertise
- Saving throw proficiencies
- Equipped weapon and armor
- Spellcasting ability
- Features and traits for character notes

Image-only or unusual PDFs may require OCR or manual correction. Always review the preview before importing.

### General tab

General stores Character Name, Player Name, Species, Class, Subclass, Background, Level, and optional portrait path.

Species, class, subclass, and background suggestions come from the imported SRD reference data. You may also type a custom value.

### Abilities tab

Each ability contains:

- **Base** - rolled, point-buy, standard-array, or imported score
- **Species** - species-based adjustment
- **Feat** - combined adjustment from selected feats
- **Total** - Base + Species + Feat
- **Modifier** - calculated D&D modifier

Selecting a species refreshes the Species column from SRD data. Under the bundled SRD 5.2.1 rules, species normally provide no direct ability-score bonuses, so these values remain zero unless the reference rule provides one.

Selecting a feat applies fixed SRD ability increases. If a feat provides a choice, Lectern asks where to apply it. Ability Score Improvement supports one ability at +2 or two abilities at +1.

You can still edit the Species and Feat values manually.

### Equipment tab

Equipment stores up to three feats, equipped weapon, equipped armor, spellcasting ability, and equipment notes. Reference dropdowns are populated from Lectern's SRD and equipment tables but accept custom text.

### Inventory tab

Inventory stores copper, silver, electrum, gold, platinum, and free-text carried items. D&D Beyond PDF imports include indexed inventory items, quantities, and weights when available.

### Combat tab

Combat stores armor class, maximum HP, current HP, and initiative. It displays calculated proficiency bonus, passive scores, attack bonus, and spell save DC.

### Skills tab

Check **Proficient** or **Expertise** for each skill. Expertise adds proficiency twice. Imported D&D Beyond proficiency markers are mapped automatically.

### Saving Throws tab

Check the saving throws in which the character is proficient. Imported D&D Beyond saving throw markers are mapped automatically.

### Notes tab

Use Notes for character details not represented elsewhere. PDF feature and trait sections are retained here when available.

### Edit, duplicate, and delete

To edit, select one row and click **Edit Selected**, make changes, then click **Save Player**.

To duplicate, select a row and click **Duplicate**. Lectern creates a uniquely named copy.

To delete, select a row, click **Delete**, and confirm. Existing combat-log text is not rewritten.

## Monster Library

Monster Library is a read-only table of imported and manually maintained monsters. The bundled catalog contains thousands of monsters and records their primary AC, HP, challenge rating, source, and available notes.

Use **Refresh** after data changes. Use **Add Monster** to create or edit a record.

## Add Monster

### Add a monster

1. Type a new name.
2. Enter type, armor class, hit points, challenge rating, and notes.
3. Click **Save Monster**.

### Edit a monster

1. Search for and select an existing monster.
2. Edit the populated fields.
3. Click **Save Monster**.

Saved monsters become available in Encounter Builder.

## Weapons, Armor, Equipment, Magic Items, and Spells

These sections display the corresponding reference tables.

- Weapons and Armor populate Player Editor dropdowns.
- Equipment provides general gear reference data.
- Magic Items displays rarity, type, attunement, and notes.
- Spells displays imported spell reference data.

Click **Refresh** after importing or restoring data.

## CSV Import/Export

CSV Import/Export supports Players, Monsters, Weapons, Armor, Equipment, Magic Items, Spells, and Rules Reference.

### Validate before importing

1. Select a table.
2. Click **Validate / Preview CSV...**.
3. Select the CSV.
4. Review every row status.

Statuses are:

- **New** - will be inserted
- **Modified** - will update a matching record
- **Unchanged** - no differences detected
- **Duplicate** - duplicate key inside the CSV
- **Error** - invalid row

Import is blocked while Duplicate or Error rows remain.

### Import a CSV

1. Select the destination table.
2. Click **Import Selected CSV...**.
3. Select the CSV.
4. Review the preview.
5. Confirm the import.

Most tables match by Name. Rules Reference matches by Category and Name.

### Export data

- **Export Selected Table...** writes one table.
- **Export All Tables...** writes every supported table to a folder.
- **Export Empty Template...** writes headers for creating a new import file.

## Fantasy Grounds Sync

Fantasy Grounds Sync receives data from a Fantasy Grounds Unity campaign using the `5E` ruleset. Fantasy Grounds remains authoritative, and Lectern never changes Fantasy Grounds campaign data.

### Install the Fantasy Grounds extension

1. Locate the Fantasy Grounds data folder using the folder button on the Fantasy Grounds launcher.
2. Copy `LecternSync.ext` from Lectern's `FantasyGrounds` installation folder into the Fantasy Grounds `extensions` folder.
3. Restart Fantasy Grounds.
4. Select a `5E` campaign and enable **Lectern Sync**.
5. Load the campaign as the GM.

Source developers can instead run `scripts\Install-FantasyGroundsExtension.ps1` to install an unpacked development extension.

### Connect a campaign

1. Load the campaign in Fantasy Grounds with **Lectern Sync** enabled.
2. Open **Fantasy Grounds Sync** in Lectern.
3. Click **Select Campaign Folder...**.
4. Select the individual folder beneath the Fantasy Grounds `campaigns` directory for the loaded campaign.
5. Lectern creates a `lectern-sync` handoff folder.
6. In Fantasy Grounds chat, enter `/lectern-export`.
7. Confirm Lectern shows the campaign name, `5E` ruleset, sequence, time, and imported counts.

Run `/lectern-export` once after each Fantasy Grounds campaign start and after changing the loaded Fantasy Grounds modules.

### Automatic updates

Keep **Automatically import new snapshots** enabled. After the initial full export, Fantasy Grounds writes an updated snapshot whenever its Combat Tracker changes. Lectern checks for changes once per second.

Synchronized Fantasy Grounds encounters are read-only in Lectern's Combat Dashboard. Change HP, initiative, effects, turns, and participants in Fantasy Grounds.

### Imported information

- Classes, subclasses, species/races, feats, and backgrounds from loaded modules
- Player characters
- Prepared encounters and their participants
- Current Combat Tracker order, round, active combatant, initiative, armor class, hit points, wounds, temporary hit points, and effects
- Combat actions, applied damage, healing, turn changes, temporary HP changes, and GM-confirmed encounter outcomes in the encounter turn log
- Fantasy Grounds module name and database path for provenance

Records that disappear from a later snapshot are marked stale rather than deleted. Commercial module content remains local and must not be redistributed.

To finish a synchronized encounter, enter `/lectern-outcome victory`, `/lectern-outcome defeat`, `/lectern-outcome retreat`, or `/lectern-outcome unresolved` in Fantasy Grounds chat. Lectern does not infer an outcome when the Combat Tracker is cleared.

### Sync troubleshooting

- If Fantasy Grounds reports an export error, select the campaign folder in Lectern before running `/lectern-export`.
- If the extension is missing, confirm `LecternSync.ext` or the unpacked `LecternSync` folder is directly beneath the Fantasy Grounds `extensions` folder.
- If data is unchanged, click **Import Now** and run `/lectern-export` again.
- If modules changed, open the required modules in Fantasy Grounds and run a new full export.
- Review **Error Logs** in Lectern and Fantasy Grounds logs for validation or mapping errors.

## Data Workflow

Use Data Workflow for database maintenance.

### Backup Database

Creates a copy of the active SQLite database at the selected location.

### Restore Database

Replaces the active database from a selected `.db` file. Lectern creates a safety backup first.

### Reset Empty Database

Creates a safety backup, then replaces the database with an empty schema.

### Reset and Reseed

Creates a safety backup, resets the database, and reloads bundled reference data, including the monster catalog and SRD character references.

## Error Logs

Error Logs displays application log files inside Lectern.

1. Reproduce the issue.
2. Open **Error Logs**.
3. Click **Refresh**.
4. Select the newest log.

Include the relevant log details when reporting a problem.

## Help

Help displays this guide. Click **Reload Help** after replacing the help file during development.

## Troubleshooting

### A PDF import finds incorrect values

- Confirm the preview identifies the expected character.
- Cancel rather than importing incorrect data.
- D&D Beyond exports store values in page widgets; current Lectern builds support this format.
- Image-only PDFs require OCR or manual entry.

### A PDF-imported player fails to open

Current builds normalize missing numeric values and safely load older empty currency fields as zero. Install the latest build and try again.

### Edit Selected shows the wrong player

Select the player's full row and click **Edit Selected**. Current builds clear all tabs and fetch the selected player by database ID.

### Monsters are missing

Open Dashboard and confirm the monster count. Use Data Workflow > Reset and Reseed only if you intend to replace the current database; a safety backup is created first.

### Players are missing from Encounter Builder

Save the player, return to Encounter Builder, and select or recreate the encounter. Switching screens refreshes the available player list.

### A new encounter contains old combatants

Use **Create New Encounter**. Current builds always create a new empty encounter and generate a unique name when necessary.

### Ability totals look wrong

Review Base, Species, and Feat values. Total is their sum, and Modifier is calculated from Total.

### The application will not start

Open **Error Logs** if possible, or review the application log under Lectern's LocalAppData folder. Verify that the latest installer completed successfully.

## Data safety

- Back up before large imports, restores, resets, or extensive character edits.
- Review PDF and CSV previews before confirming.
- Generated combat logs and campaign totals depend on the underlying encounter records.
- Lectern stores user data locally and does not require a cloud connection for normal use.
