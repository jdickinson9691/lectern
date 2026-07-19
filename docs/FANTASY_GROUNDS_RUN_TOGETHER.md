# Running Fantasy Grounds and Lectern Together

This guide describes the Milestone 1 and 1.1 one-way Fantasy Grounds Unity 5E to Lectern workflow.

## Initial setup

### 1. Locate the Fantasy Grounds data folder

Open Fantasy Grounds Unity and select the folder button on its launcher. The folder normally contains `campaigns`, `extensions`, `modules`, and `rulesets`.

Do not use the Fantasy Grounds application installation folder. The extension belongs in the separate Fantasy Grounds data folder.

### 2. Install the extension

For an installed Lectern release, copy `FantasyGrounds\LecternSync.ext` from the Lectern installation folder into:

```text
<Fantasy Grounds data folder>\extensions\LecternSync.ext
```

For source development, run:

From PowerShell in the Lectern repository, run:

```powershell
.\scripts\Install-FantasyGroundsExtension.ps1 -FantasyGroundsDataPath "C:\Path\To\Fantasy Grounds"
```

The script copies the extension to:

```text
<Fantasy Grounds data folder>\extensions\LecternSync
```

The development script installs an unpacked `LecternSync` folder. Fantasy Grounds gives that folder precedence over a packaged `.ext` with the same name.

### 3. Enable the extension

1. Close and reopen Fantasy Grounds if it was running during installation.
2. Select or create a campaign using the `5E` ruleset.
3. Enable **Lectern Sync** in the campaign extension list.
4. Start the campaign as the GM.

The first milestone is host/GM-only. Connected players do not run independent exporters.

## Normal session startup

1. Start Fantasy Grounds Unity.
2. Load the desired `5E` campaign with **Lectern Sync** enabled.
3. Start Lectern.
4. Open **Fantasy Grounds Sync** in Lectern.
5. The first time, click **Select Campaign Folder...** and select:

   ```text
   <Fantasy Grounds data folder>\campaigns\<campaign>
   ```

   Lectern creates the `lectern-sync` handoff folder beneath the campaign.

6. In Fantasy Grounds, enter `/lectern-export` in chat.
7. Confirm Lectern shows the correct campaign, `5E` ruleset, extension version, sequence, and last-sync time.
8. Leave both applications running. Fantasy Grounds remains authoritative; Lectern refreshes from later snapshots.

After the handoff folder has been created once, Lectern does not need to start first. If it starts later, it imports the newest complete snapshot. Run `/lectern-export` once after every Fantasy Grounds campaign start and again after changing the loaded module set.

## During combat

1. Build or open the encounter in Fantasy Grounds.
2. Add it to the Fantasy Grounds Combat Tracker.
3. Before the first roll, start a named synchronized encounter:

   ```text
   /lectern-start Goblin Ambush
   ```

4. Confirm Fantasy Grounds reports the encounter started and Lectern's **Fantasy Grounds Sync** screen shows the session as **Open**.
5. Roll initiative and run combat normally in Fantasy Grounds.
6. Keep Lectern's **Combat Dashboard** or **Fantasy Grounds Sync** screen open as a companion view.

Fantasy Grounds dice actions, applied damage and healing, turn changes, and temporary HP changes are appended automatically to the synchronized encounter's turn log. A damage roll is logged as an action; it becomes `Damage` only when wounds are actually applied in the Combat Tracker.

Lectern Sync 1.4.1 also records the damage types resolved by the 5E ruleset. Mixed damage remains component-aware, and expanded Combat Dashboard rows preserve rolled and applied values after resistance, immunity, vulnerability, wards, and similar adjustments. Manual wound edits are labeled with an unknown damage type.

When the encounter ends, record the GM-confirmed result in Fantasy Grounds chat:

```text
/lectern-end victory
```

The supported results are `victory`, `defeat`, `retreat`, and `unresolved`. The result captures the final roster, completes the Lectern encounter, and appears in its turn log. `/lectern-outcome` remains a compatibility alias for `/lectern-end`. Clearing the Combat Tracker alone does not guess an outcome.

The open session is persisted under `lectern-sync` and resumes after a Fantasy Grounds reload. Only one session can be open at a time. Events rolled without an open session are intentionally not journaled, and Fantasy Grounds displays a `/lectern-start` reminder.

HP, initiative, turns, participants, and effects originate in Fantasy Grounds. Synchronized encounters are read-only in Lectern's Encounter Builder and Combat Dashboard.

## Ending a session

1. Run `/lectern-end` with the encounter outcome.
2. Wait until Lectern displays the newest sequence, sync time, and **Closed** session state.
3. End or clear combat in Fantasy Grounds normally.
4. Close either application in any order.

The newest snapshot stays in the Fantasy Grounds campaign folder for Lectern's next startup.

## Resetting for a fresh test

1. End any open session with `/lectern-end outcome`.
2. Enter `/lectern-reset confirm` in Fantasy Grounds. The extension refuses this command while an encounter is open.
3. Wait for the clean snapshot to reach **Ready** in Lectern.
4. On **Fantasy Grounds Sync**, select the imported campaign and click **Clear Selected FG Import**.
5. Confirm the preview. Lectern creates a safety backup, clears only linked imported data, and turns automatic import off.
6. Begin the new test with `/lectern-start Encounter Name`, then re-enable automatic import or click **Import Now**.

The reset command clears the extension's closed session and accumulated event journal. The Lectern button removes the selected linked campaign, encounters, combatants, log rows, imported player copies, and synchronization metadata. Unlinked Lectern data is preserved.

## Developer workflow

After changing `integrations/fantasy_grounds/extension/LecternSync`, rerun the installation script. It replaces only the installed `LecternSync` development folder. Return to the Fantasy Grounds launcher and reload the campaign.

Use a dedicated test campaign and sanitized/open content. Never commit exports containing commercial Fantasy Grounds module text.

## Troubleshooting

### Lectern says the handoff folder is missing

- Confirm the 5E campaign loaded with **Lectern Sync** enabled.
- Select the individual campaign folder in Lectern so it can create `lectern-sync`.
- Run one explicit export in Fantasy Grounds.

### The extension is not listed

- Confirm `extension.xml` is directly inside `extensions\LecternSync`.
- Confirm the campaign uses the `5E` ruleset.
- Restart Fantasy Grounds after installing or replacing the extension.

### Data does not refresh

- Compare `status.json` and `snapshot.json` modification times.
- Use **Import Now** in Lectern.
- Run `/lectern-export` in Fantasy Grounds.
- Review Lectern's Error Logs and Fantasy Grounds logs.
- If Fantasy Grounds reports that the export failed, reselect the campaign folder in Lectern before running `/lectern-export`.

### An imported module record disappeared

Open the required Fantasy Grounds module in the campaign and export again. The exporter can only read module records available to the GM.

### Lectern reports an unsupported contract version

Update Lectern and the extension together. Contract version 1 uses `schema_version: 1`; unknown versions must be rejected rather than guessed.

### Combat events are missing

- Confirm the extension reports version 1.1.3 or newer.
- Run `/lectern-export` once after loading the campaign; event-driven snapshots require the initial cached full export.
- Apply damage and healing through the Combat Tracker. Unapplied roll totals are actions, not HP changes.
- Keep automatic imports enabled or click **Import Now** after the Fantasy Grounds sequence changes.
