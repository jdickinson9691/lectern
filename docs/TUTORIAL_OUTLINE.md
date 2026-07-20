# Lectern Step-by-Step Tutorial Production Outline

This document prepares a separate illustrated tutorial. It defines the learner journey, required example data, screenshot plan, and acceptance checks.

## Tutorial goal

Guide a first-time user from launching Lectern through creating a campaign, importing a character, building an encounter, running combat, recording the result, and backing up the database.

## Target audience

- Dungeon Masters new to Lectern
- Users comfortable with basic Windows applications
- Users who do not need database or developer knowledge

## Example scenario

Use one consistent scenario throughout the tutorial:

- Campaign: `Shadows Over Lendover`
- Description: `A local mystery involving disappearances near the old road.`
- Player: import a reviewed D&D Beyond PDF or create `Pallor`, level 6 Cleric
- Encounter: `Old Road Ambush`
- Monsters: two suitable low-level enemies from Monster Library
- Outcome: Victory

Do not use real private player information in published screenshots. Replace player names and personal notes with tutorial-safe examples.

## Lesson sequence

### Lesson 1 - Launch and orientation

Outcome: The learner identifies navigation, Dashboard counts, and current campaigns.

Steps:

1. Launch Lectern.
2. Open Dashboard.
3. Identify the navigation bar and data counts.
4. Explain where local data and backups are maintained without exposing technical paths unnecessarily.

Screenshot checkpoint: Dashboard with navigation and campaign table visible.

### Lesson 2 - Create a campaign

Outcome: The learner creates `Shadows Over Lendover`.

Steps:

1. Open Campaigns.
2. Enter the example name and description.
3. Click Create Campaign.
4. Confirm the empty campaign summary.

Screenshot checkpoint: Newly created campaign selected.

### Lesson 3 - Add a player

Outcome: The learner has a saved player available to Encounter Builder.

Provide two paths:

Path A - PDF import:

1. Open Players.
2. Click Import Character PDF.
3. Select a fillable D&D Beyond-style PDF.
4. Review the scrollable preview.
5. Click Import Character.
6. Review every Player Character Editor tab.
7. Save corrections.

Path B - Manual entry:

1. Click + New Player.
2. Complete General and Abilities.
3. Add feats and equipment.
4. Configure Combat, Skills, and Saving Throws.
5. Save Player.

Screenshot checkpoints:

- PDF preview with fictional data
- General tab
- Abilities tab showing calculated totals
- Skills tab showing proficiency and expertise
- Saved player row

### Lesson 4 - Review reference data

Outcome: The learner can locate monsters, weapons, armor, equipment, magic items, and spells.

Steps:

1. Open Monster Library.
2. Locate one tutorial monster.
3. Briefly open Weapons, Armor, Equipment, Magic Items, and Spells.
4. Explain Add Monster for custom records.

Screenshot checkpoint: Monster Library with tutorial monster visible.

### Lesson 5 - Build an encounter

Outcome: The learner creates a clean encounter with players and monsters.

Steps:

1. Open Encounter Builder.
2. Enter `Old Road Ambush`.
3. Click Create New Encounter.
4. Add the tutorial player.
5. Add two monsters.
6. Review the combatant table.
7. Click Roll Initiative / Start.

Screenshot checkpoints:

- Empty newly created encounter
- Completed combatant list before initiative
- Initiative results

### Lesson 6 - Run combat

Outcome: The learner advances turns and records combat events.

Steps:

1. Open Combat Dashboard.
2. Identify the active combatant and round.
3. Log an attack.
4. Apply damage.
5. Advance the turn.
6. Apply healing.
7. Continue until the encounter ends.

Screenshot checkpoints:

- Initial turn order
- Damage entry and updated HP
- Action log containing several event types

### Lesson 7 - Record the campaign result

Outcome: The encounter appears in campaign history and cumulative statistics.

Steps:

1. Open Campaigns.
2. Add `Old Road Ambush` to the campaign.
3. Choose Victory.
4. Click Complete Encounter.
5. Review encounter count, rounds, actions, damage, healing, and history.
6. Return to Dashboard and confirm the campaign encounter count.

Screenshot checkpoints:

- Completed campaign history row
- Dashboard campaign encounter count

### Lesson 8 - Export and protect data

Outcome: The learner creates a database backup and understands CSV export.

Steps:

1. Open Data Workflow.
2. Create a database backup.
3. Open CSV Import/Export.
4. Validate a tutorial CSV without importing it.
5. Export one table.
6. Explain restore, reset, and reseed cautions.

Screenshot checkpoints:

- Successful backup status
- CSV validation preview

### Lesson 9 - Troubleshooting and logs

Outcome: The learner can gather useful diagnostic information.

Steps:

1. Open Error Logs.
2. Refresh the list.
3. Select the latest log.
4. Explain what to include in a support report.

Screenshot checkpoint: Error Logs screen with non-sensitive example content.

## Tutorial writing conventions

- Start each lesson with a concrete outcome.
- Use exact control labels from the application.
- Keep each numbered step to one user action.
- Put warnings immediately before destructive actions.
- Use callouts for expected results after important steps.
- Avoid developer terminology and database implementation details.
- Use fictional, non-sensitive character and campaign data.

## Screenshot standards

- Use the current 3.0.0 build.
- Capture the entire relevant panel with enough navigation context to orient the reader.
- Crop out unrelated desktop content.
- Use consistent window dimensions and Windows display scaling.
- Ensure the watermark is visible but does not obscure values.
- Remove real names, file paths, notes, tokens, and personal campaign information.
- Add numbered annotations only after preserving an unannotated source screenshot.

## Tutorial acceptance checklist

- All navigation labels match the current build.
- Every screenshot matches the written step immediately beside it.
- A clean user can complete the tutorial without Workbook Import.
- PDF import includes preview, confirmation, database persistence, and post-import review.
- Encounter creation demonstrates that new encounters start empty.
- Campaign results include encounter count and cumulative combat data.
- Backup instructions precede restore/reset/reseed warnings.
- No private user or character information appears in the final guide.
