# Running Fantasy Grounds and Lectern Together

This guide describes the Milestone 1 one-way Fantasy Grounds Unity 5E to Lectern workflow.

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
3. Roll initiative and run combat normally in Fantasy Grounds.
4. Keep Lectern's **Combat Dashboard** or **Fantasy Grounds Sync** screen open as a companion view.

HP, initiative, turns, participants, and effects originate in Fantasy Grounds. Milestone one does not allow editing synchronized combat values in Lectern.

## Ending a session

1. End or clear combat in Fantasy Grounds normally.
2. Wait until Lectern displays the newest sequence and sync time.
3. Close either application in any order.

The newest snapshot stays in the Fantasy Grounds campaign folder for Lectern's next startup.

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
