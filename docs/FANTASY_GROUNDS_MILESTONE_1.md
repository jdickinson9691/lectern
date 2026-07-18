# Fantasy Grounds Integration - Milestone 1

## Objective

Create a one-way Fantasy Grounds Unity 5E to Lectern integration. Fantasy Grounds is the source of truth. Lectern receives game-system reference records, prepared encounters, characters, and live Combat Tracker state without modifying the Fantasy Grounds campaign database.

## Implementation status

Implemented on the `codex/lectern-2.9.5` branch:

- Fantasy Grounds 5E extension version 1.0.0 with `/lectern-export`
- Loaded-module catalog traversal with registered mappings and 5E legacy-path fallbacks
- Character, prepared encounter, and Combat Tracker serialization
- Event-driven Combat Tracker snapshots after the initial full export
- Lectern schema v6 provenance and entity-link tables
- Contract validation, transactional import, idempotent sequences, stale records, and collision-safe names
- Fantasy Grounds Sync UI with campaign-folder setup, automatic polling, manual import, status, counts, and provenance
- Read-only controls for Fantasy Grounds-owned encounters in Lectern's Combat Dashboard
- Sanitized integration fixture and regression test
- Development install and distributable `.ext` build scripts

Runtime validation inside a locally installed Fantasy Grounds Unity campaign remains a release acceptance activity because Fantasy Grounds is not part of the automated test environment.

## Supported environment

- Fantasy Grounds Unity, host/GM session
- Fantasy Grounds `5E` ruleset
- Lectern on the same Windows computer
- One Fantasy Grounds campaign selected in Lectern at a time
- Local file handoff; no cloud account or network listener

Other Fantasy Grounds rulesets are outside this milestone. The contract is system-neutral where practical, but every ruleset requires its own source-field mapper.

## Architecture decision

The integration has two independently installable parts:

1. **Lectern Exporter for Fantasy Grounds** - a Lua/XML `.ext` package loaded by the GM. It reads Fantasy Grounds database nodes and writes snapshots beneath the current campaign folder.
2. **Fantasy Grounds Sync for Lectern** - a Python service in Lectern that watches the selected handoff folder, validates snapshots, maps 5E records, and commits them to SQLite.

The handoff location is:

```text
<Fantasy Grounds data folder>/campaigns/<campaign>/lectern-sync/
```

The extension must use Fantasy Grounds APIs such as `DB` and `File.saveTextFile`. It must not edit `db.xml` directly. Lectern treats the handoff folder as read-only.

## Snapshot protocol

Milestone one uses complete snapshots rather than a stream of mutations. Complete snapshots make restart, missed-event recovery, and debugging predictable.

```text
lectern-sync/
  snapshot.json
  status.json
```

- `snapshot.json` contains the newest complete catalog, campaign, encounter, character, and combat state.
- `status.json` contains extension version, campaign/ruleset identity, last attempted export time, last successful sequence, and an optional error.
- `sequence` increases after every successful export.
- Lectern ignores a sequence it has already applied.
- Lectern polls file metadata once per second and retries after a later file change if it observes an incomplete write.
- Lectern imports each snapshot in one SQLite transaction. Validation or mapping failure leaves the previously imported state intact.

The normative contract is [fantasy_grounds_snapshot_v1.schema.json](contracts/fantasy_grounds_snapshot_v1.schema.json). A sanitized fixture is [fantasy_grounds_snapshot_v1.example.json](contracts/fantasy_grounds_snapshot_v1.example.json).

## Included data

### Reference catalog

- Classes
- Subclasses
- Species/races
- Feats
- Backgrounds when available

Every reference record retains its Fantasy Grounds database path, module, ruleset, stable source key, display name, normalized fields, and raw fields. Only records visible to the GM from loaded modules are eligible. Lectern must not bundle or redistribute imported module content.

### Campaign records

- Player characters
- NPCs referenced by exported encounters or the Combat Tracker
- Prepared encounters (`battle` records in CoreRPG-derived rulesets)
- Encounter participants and quantities

### Live combat state

- Whether combat is active
- Round and active combatant
- Combat Tracker order
- Names, factions, initiative, armor class, hit points, temporary hit points, wounds, and visibility when present
- Effects/conditions, including source and duration when present

Fantasy Grounds database paths and field names vary by ruleset version. The exporter gathers source records; the Lectern `5E` mapper owns interpretation and normalization.

## Lectern database preparation

Do not overload `rules_reference` with sync identity. Add the following integration tables during implementation.

### `external_sources`

- `id`
- `provider` (`fantasy_grounds`)
- `campaign_key`
- `campaign_name`
- `ruleset`
- `extension_version`
- `last_sequence`
- `last_sync_at`
- `last_error`

### `external_records`

- `id`
- `source_id`
- `source_key`
- `record_type`
- `name`
- `module_name`
- `source_path`
- `content_hash`
- `raw_json`
- `last_seen_sequence`

`(source_id, source_key)` must be unique. Normalized catalog data may continue to populate `rules_reference` for existing UI lookups, while the external record remains the provenance and lossless copy.

Add nullable `external_record_id` fields to imported players, encounters, and combatants, or use mapping tables if migration risk favors less coupling.

## Sync ownership rules

- Fantasy Grounds-owned fields are refreshed on every snapshot.
- Lectern-only notes, tags, and presentation settings live in separate fields.
- A missing source record is marked stale first; it is not immediately deleted.
- A source record may be purged only through an explicit Lectern command.
- Milestone one never sends a change back to Fantasy Grounds.

## Implementation slices

### 1. Contract and fixtures - implemented

- Validate the schema and example fixture.
- Test missing fields, unsupported versions, duplicate source keys, and out-of-order sequences.
- Add representative sanitized 5E fixtures captured from a test campaign.

### 2. Fantasy Grounds discovery exporter - implemented

- Create the 5E-only extension manifest and GM-only initialization.
- Report campaign, ruleset, loaded modules, and candidate record paths.
- Add an **Export to Lectern** action and `/lectern-export` command.
- Write `status.json` even when discovery or export fails.

### 3. Catalog and encounter export - implemented

- Export classes, subclasses, species/races, feats, backgrounds, characters, battles, and referenced NPCs.
- Preserve module/path provenance and raw source values.
- Produce a complete contract-valid `snapshot.json`.

### 4. Lectern importer - implemented

- Add schema migration and repositories for external sources and records.
- Add a snapshot parser, validator, 5E mapper, and transactional importer.
- Add a Fantasy Grounds Sync screen with folder selection, connection status, last sequence, counts, errors, and **Import Now**.

### 5. Combat updates - implemented

- Register Fantasy Grounds database handlers for Combat Tracker additions, updates, and deletions.
- Reuse the cached full snapshot and export refreshed combat state when the Combat Tracker changes.
- Refresh Lectern automatically and show source/last-updated indicators.

### 6. Packaging - implemented; Fantasy Grounds runtime acceptance pending

- Package the Fantasy Grounds folder as `LecternSync.ext`.
- Include it with the Lectern release or provide it as a companion download.
- Verify clean install, upgrade, disabled-extension behavior, campaign switching, restart recovery, and malformed snapshot recovery.

## Acceptance criteria

1. A GM can install and enable the extension in a Fantasy Grounds 5E campaign.
2. Lectern can select the campaign's `lectern-sync` folder without editing configuration files.
3. One explicit export imports classes, subclasses, species/races, feats, characters, and prepared encounters.
4. Every imported record retains its Fantasy Grounds module/path provenance.
5. A Combat Tracker change is reflected in Lectern within two seconds after the export debounce interval.
6. Restarting either application recovers from the newest snapshot without duplicates.
7. An invalid, partial, or older snapshot cannot corrupt or roll back Lectern data.
8. Lectern never changes Fantasy Grounds campaign or module data.
9. Existing Lectern smoke tests pass, and integration tests use sanitized fixtures with no commercial module content.

## Explicitly deferred

- Lectern to Fantasy Grounds writes
- Remote-computer or cloud synchronization
- Player-client export
- Multiple simultaneously active campaigns
- Redistribution of Fantasy Grounds module content
- Rulesets other than 5E
- Maps, images, tokens, portraits, and line-of-sight data

## Verification evidence

Automated verification completed on 2026-07-17 using Windows 11 and Python 3.13.14:

- Source compilation passed.
- Existing Lectern data/CRUD/import/backup smoke test passed.
- Fantasy Grounds fixture validation and transactional sync regression test passed.
- Duplicate sequence, invalid snapshot rollback, source-key duplication, name collision, stale record, live HP, and effect cases passed.
- Full PySide application constructed and exited cleanly using the offscreen autoclose check.
- PyInstaller Windows distribution completed successfully.
- Packaged Lectern executable started and exited cleanly.
- `LecternSync.ext` was built with `extension.xml` at the archive root and `scripts/lectern_sync.lua` present.

Live Fantasy Grounds runtime acceptance is pending because the installed Fantasy Grounds environment has no test campaign. Follow [FANTASY_GROUNDS_RUN_TOGETHER.md](FANTASY_GROUNDS_RUN_TOGETHER.md) to complete that check before a public release.
