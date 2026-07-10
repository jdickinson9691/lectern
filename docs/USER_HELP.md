# Lectern - D&D Campaign Manager Help Guide

Version: 2.8 Stability + Data Workflow

This help guide walks through every screen currently available in the application. The app is organized around a left navigation bar. Select a section from the left, then work in the main panel on the right.

## 1. Dashboard

The Dashboard is the starting screen.

### What it shows

The Dashboard displays the application name, current version, and live database counts for major records such as players, monsters, encounters, combatants, weapons, armor, and spells.

### How to use it

1. Open the app.
2. Select **Dashboard** from the left navigation.
3. Review the count summary.
4. If counts are zero, import seed/reference data using **Workbook Import** or **CSV Import/Export**.

### Typical use

Use the Dashboard as a quick health check. If monsters, weapons, armor, or spells are missing, the database has not been populated yet.

---

## 2. Players

The Players section is where player characters are created, edited, duplicated, deleted, and searched. Saved players become available in the Encounter Builder.

### Main controls

- **+ New Player** clears the editor so you can create a new character.
- **Edit Selected** loads the selected table row into the editor.
- **Duplicate** copies the selected character.
- **Delete** removes the selected character from the player database.
- **Refresh** reloads the player list from the database.
- **Search** filters the visible player list by character name, class, species, background, equipment, notes, or other stored text.

### Creating a player

1. Select **Players** from the left navigation.
2. Click **+ New Player**.
3. Enter **Character Name**. This is required.
4. Enter **Player Name** if desired.
5. Select or type **Species / Race**.
6. Select or type **Class**.
7. Select or type **Subclass** if applicable.
8. Select or type **Background**.
9. Select up to three feats using **Feat 1**, **Feat 2**, and **Feat 3**.
10. Select a primary **Weapon**.
11. Select equipped **Armor**.
12. Enter carried **Equipment** as free text.
13. Set **Level**.
14. Set **Armor Class**.
15. Set **Max HP** and **Current HP**.
16. Review the **Initiative Modifier**. It automatically follows Dexterity modifier unless manually changed afterward.
17. Add notes if desired.
18. Enter ability scores in the **Ability Scores** area.
19. Click **Save Player**.

### Editing a player

1. Select **Players**.
2. Click a character row in the table.
3. The editor loads the selected character automatically.
4. Change the desired fields.
5. Click **Save Player**.

### Duplicating a player

1. Select a player row.
2. Click **Duplicate**.
3. A copied record is created.
4. Select the copied record.
5. Change the character name and any other details.
6. Click **Save Player**.

### Deleting a player

1. Select a player row.
2. Click **Delete**.
3. Confirm the deletion.

Deleting a player removes the player record from the player database. Existing combat log entries are not rewritten.

### Ability scores

Each ability has three editable columns:

- **Base** is the character's rolled, array, point-buy, or manually assigned score.
- **Race Bonus** is the bonus from species/race or lineage.
- **Feat Bonus** is the bonus from feats or other selected character options.

The application calculates:

- **Total** = Base + Race Bonus + Feat Bonus.
- **Modifier** = standard D&D ability modifier from the total score.

### Ability modifier examples

- Score 8 gives -1.
- Score 10 gives +0.
- Score 12 gives +1.
- Score 14 gives +2.
- Score 16 gives +3.
- Score 18 gives +4.
- Score 20 gives +5.

### Race and feat bonus handling

The current version does not automatically parse every rule text choice from imported species and feat records. If a race or feat offers a choice, enter the chosen bonus manually in the correct Race Bonus or Feat Bonus field.

Example:

1. Base Dexterity is 14.
2. Species grants +2 Dexterity.
3. Feat grants +1 Dexterity.
4. Enter Base 14, Race Bonus 2, Feat Bonus 1.
5. Total becomes 17 and modifier becomes +3.

### Equipment fields

The player editor currently includes:

- **Weapon**: a dropdown/type-ahead field populated from the weapons table.
- **Armor**: a dropdown/type-ahead field populated from the armor table.
- **Equipment**: a free-text box for packs, tools, adventuring gear, treasure, and other carried items.

### Making players available for encounters

After saving a player:

1. Go to **Encounter Builder**.
2. Find the player in the Players list.
3. Check the player.
4. Click **Add Selected Player(s)**.

---

## 3. Monster Library

The Monster Library is a read-only table view of the monster database.

### What it shows

The table displays imported and manually created monster records. Columns may include name, size, type, alignment, armor class, hit points, speed, challenge rating, XP, ability scores, source, and notes.

### How to use it

1. Select **Monster Library** from the left navigation.
2. Review available monsters.
3. Click **Refresh** to reload the table.
4. Use this screen to verify that the monster database has been populated.

### Adding or editing monsters

Use **Add Monster**, not Monster Library, to create or edit monster records.

---

## 4. Add Monster

The Add Monster screen creates or updates monster records.

### Main fields

- **Monster Name**: searchable type-ahead field populated from the monster database.
- **Type**: creature type or description.
- **Armor Class**: monster AC.
- **Hit Points**: average or chosen HP.
- **Challenge**: challenge rating.
- **Notes**: short notes.

### Adding a new monster

1. Select **Add Monster** from the left navigation.
2. Type a new monster name in **Monster Name**.
3. Enter Type, Armor Class, Hit Points, Challenge, and Notes.
4. Click **Save Monster**.

### Editing an existing monster

1. Select **Add Monster**.
2. Start typing the monster name.
3. Select the monster from the type-ahead dropdown.
4. The known values fill in automatically.
5. Change the desired fields.
6. Click **Save Monster**.

### Using monsters in encounters

Saved monsters appear in the Encounter Builder Monster Browser.

---

## 5. Encounter Builder

The Encounter Builder is where you create encounters and add combatants.

### Basic workflow

1. Select **Encounter Builder**.
2. Enter an encounter name such as `Goblin Ambush`.
3. Click **New / Select Encounter**.
4. Add monsters from the Monster Browser.
5. Add players from the Players list.
6. Review the Encounter Combatants table.
7. Click **Roll Initiative / Start**.
8. Open **Combat Dashboard** to run the encounter.

### Creating or selecting an encounter

1. Type the encounter name in the field at the top.
2. Click **New / Select Encounter**.
3. The encounter becomes active in the **Active** dropdown.

If you already have encounters, use the **Active** dropdown to switch between them.

### Adding monsters

1. In **Monster Browser**, start typing a monster name.
2. Select the monster from the dropdown.
3. Set **Quantity**.
4. Click **Add Monster(s)**.

If Quantity is 4 and the monster is Goblin, four separate combatants are added to the encounter.

### Adding players

1. In the **Players** box, check one or more player characters.
2. Click **Add Selected Player(s)**.
3. The selected players appear in the Encounter Combatants table.

Players must be created and saved in the Players section before they appear here.

### Reviewing combatants

The Encounter Combatants table shows:

- Name
- Initiative
- Armor Class
- Current HP
- Max HP
- Source Type

### Removing a combatant

1. Select a combatant row.
2. Click **Remove Selected**.

### Rolling initiative and starting combat

1. Confirm that all players and monsters are in the encounter.
2. Click **Roll Initiative / Start**.
3. The app rolls initiative and sorts turn order.
4. Open **Combat Dashboard**.

---

## 6. Combat Dashboard

The Combat Dashboard is where combat is run round by round.

### Selecting an encounter

1. Select **Combat Dashboard**.
2. Use the **Encounter** dropdown to select the active encounter.
3. Confirm that the turn order table is populated.

### Understanding the combat board

The combat board displays:

- **Turn**: marks the active combatant with an arrow.
- **Name**: combatant name.
- **Init**: initiative score.
- **AC**: armor class.
- **HP**: current hit points.
- **Max**: maximum hit points.

The round and active combatant appear near the top.

### Advancing turns

- Click **Next / End Turn** to move to the next combatant.
- Click **Previous Turn** to move backward.

When the active index passes the final combatant, the round counter advances.

### Applying damage

1. Select the target combatant row. If no row is selected, the active combatant is used.
2. Enter the damage amount in **Amount**.
3. Click **Apply Damage**.
4. HP decreases but will not go below zero.
5. A damage entry is added to the action log.

### Applying healing

1. Select the target combatant row. If no row is selected, the active combatant is used.
2. Enter the healing amount in **Amount**.
3. Click **Apply Healing**.
4. HP increases but will not exceed max HP.
5. A healing entry is added to the action log.

### Logging actions

1. Select an action type from the dropdown.
2. Enter details in the text field.
3. Click **Log Action**.

Available action types currently include:

- Attack
- Spell
- Save
- Condition
- Reaction
- Lair Action
- Note

### Recommended combat procedure

1. Confirm initiative order.
2. On each turn, select the acting combatant or leave the active combatant selected.
3. Log attacks, spells, saves, or notes.
4. Apply damage or healing to targets.
5. Click **Next / End Turn**.
6. Continue until the encounter ends.

---

## 7. Weapons

The Weapons screen is a table view of the weapons database.

### How to use it

1. Select **Weapons**.
2. Review the list of available weapons.
3. Click **Refresh** after importing new data.

Weapons populate the Player editor Weapon dropdown.

---

## 8. Armor

The Armor screen is a table view of the armor database.

### How to use it

1. Select **Armor**.
2. Review the armor list.
3. Click **Refresh** after importing new data.

Armor populates the Player editor Armor dropdown.

---

## 9. Equipment

The Equipment screen is a table view of general equipment.

### How to use it

1. Select **Equipment**.
2. Review available equipment records.
3. Click **Refresh** after importing new data.

The Player editor currently stores equipment as free text. Future versions may allow multi-select equipment assignment from this table.

---

## 10. Magic Items

The Magic Items screen is a table view of imported magic items.

### How to use it

1. Select **Magic Items**.
2. Review available magic item records.
3. Click **Refresh** after importing new data.

Future versions may add direct magic item assignment to player inventory.

---

## 11. Spells

The Spells screen is a table view of imported spells.

### How to use it

1. Select **Spells**.
2. Review spell records.
3. Click **Refresh** after importing new data.

Future versions may add character spellbook and prepared-spell management.

---

## 12. Workbook Import

Workbook Import loads the D&D Combat Tracker Excel workbook into the SQLite database.

### When to use it

Use Workbook Import when:

- The app database is empty.
- You have updated the master Excel workbook.
- You want to repopulate reference tables from the workbook database tabs.

### Importing a workbook

1. Select **Workbook Import**.
2. Click **Import Workbook...**.
3. Select the `.xlsx` workbook.
4. Wait for the import to complete.
5. Review the completion message.
6. Go to Dashboard or reference screens to verify row counts.

### Imported data usage

Imported data feeds:

- Monster Library
- Add Monster type-ahead
- Encounter Builder Monster Browser
- Player species/race dropdowns
- Player class/subclass/background dropdowns
- Player feat dropdowns
- Player weapon dropdown
- Player armor dropdown
- Reference table screens

---

## 13. CSV Import/Export

CSV Import/Export allows database tables to be exported, edited externally, and imported back.

### Supported tables

The currently supported CSV tables include:

- Players
- Monsters
- Weapons
- Armor
- Equipment
- Magic Items
- Spells
- Rules Reference

### Exporting one table

1. Select **CSV Import/Export**.
2. Choose a table from the **Table** dropdown.
3. Click **Export Selected Table...**.
4. Choose a save location.
5. Open the CSV in Excel or another editor.

### Exporting all tables

1. Select **CSV Import/Export**.
2. Click **Export All Tables...**.
3. Select a folder.
4. The app writes one CSV per supported table.

### Exporting an empty template

1. Select a table.
2. Click **Export Empty Template...**.
3. Save the template.
4. Fill in rows using the existing column headers.
5. Import the completed CSV later.

### Importing an updated CSV

1. Select the target table from the **Table** dropdown.
2. Click **Import Selected CSV...**.
3. Select the edited CSV file.
4. Confirm the import.
5. The app updates existing rows with matching keys and inserts new rows where appropriate.

### Matching behavior

- Most tables match rows by **Name**.
- Rules Reference rows match by **Category + Name**.

### CSV safety tips

- Export before importing so you have a backup.
- Do not rename required columns.
- Keep IDs unchanged unless you know the database structure.
- For major edits, export all tables first.
- After import, check the row counts and open the relevant screen to confirm the data.

---

## 14. Help

The Help screen displays this guide inside the app.

### How to use it

1. Select **Help** from the left navigation.
2. Scroll through the guide.
3. Use the content as a step-by-step reference while running the application.

---

## 15. Recommended setup sequence for a new database

Follow this sequence when starting fresh:

1. Launch the application.
2. Open **Dashboard** and check counts.
3. If counts are empty, open **Workbook Import**.
4. Import the D&D Combat Tracker workbook.
5. Open **Players**.
6. Create player characters.
7. Open **Add Monster** or **Monster Library** to verify monster data.
8. Open **Encounter Builder**.
9. Create an encounter.
10. Add players.
11. Add monsters.
12. Roll initiative.
13. Open **Combat Dashboard**.
14. Run combat.
15. Use **CSV Import/Export** to back up or bulk-edit data.

---

## 16. Troubleshooting

### No monsters appear

1. Open **Dashboard**.
2. Check the monster count.
3. If it is zero, open **Workbook Import** and import the workbook.
4. If using CSV, open **CSV Import/Export** and import the monsters CSV.

### No players appear in Encounter Builder

1. Open **Players**.
2. Create and save at least one player.
3. Return to **Encounter Builder**.
4. Click refresh if needed or switch screens to reload.

### Player dropdowns are empty

1. Confirm that workbook or CSV reference data has been imported.
2. Check Weapons, Armor, and other reference screens.
3. If reference screens are empty, import the workbook again.

### Ability modifiers look wrong

1. Check Base score.
2. Check Race Bonus.
3. Check Feat Bonus.
4. Confirm the Total score.
5. The modifier is calculated from the Total score.

### The executable does not reflect a new build

1. Close all running CampaignManager processes.
2. Delete the old `dist` folder.
3. Run `build\Build.ps1` again.
4. Launch the executable from the new `dist\Lectern` folder.

### Build fails from the wrong folder

Run the build command only from the extracted `CampaignManager` folder:

```powershell
.\build\Build.ps1
```

You should see folders such as `app`, `build`, `docs`, `scripts`, and `seeds` in the current directory before running the build.


# Data Workflow

Use **Data Workflow** for database maintenance.

## Backup Database

1. Open **Data Workflow**.
2. Click **Backup Database**.
3. Choose a destination file.
4. Confirm the backup was created.

## Restore Database

1. Open **Data Workflow**.
2. Click **Restore Database**.
3. Select a `.db` backup file.
4. Confirm the restore.

Lectern creates a safety backup before replacing the active database.

## Reset Empty Database

Use this when you want a clean empty schema. A safety backup is created first.

## Reset and Reseed

Use this when you want a clean database reloaded from the bundled D&D 5E seed workbook.

# CSV Validation and Preview

Before importing a CSV, use **Validate / Preview CSV**. The preview shows one row per imported CSV row.

Statuses:

- **New** — row will be inserted.
- **Modified** — row matches an existing record and will update it.
- **Unchanged** — row matches an existing record with no detected changes.
- **Duplicate** — duplicate key found inside the CSV file. Resolve before import.
- **Error** — row cannot be imported. Resolve before import.

CSV import is blocked when Duplicate or Error rows are present.

# Error Logs

Open **Error Logs** to view recent application log files without leaving the app. Use **Refresh** after reproducing an issue.
