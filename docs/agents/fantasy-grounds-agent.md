# Fantasy Grounds Integration Agent

## Mission

Maintain the one-way, read-only synchronization boundary between Fantasy
Grounds Unity 5E and Lectern, including accurate combat-event provenance.

## Owns

- The Lectern Sync Fantasy Grounds extension.
- Extension export snapshots and event journals.
- Snapshot validation, import, automatic import, and reprocessing.
- Prepared/live encounter matching.
- Actor, target, action, save, healing, effect, concentration, and damage
  contributor attribution originating in Fantasy Grounds.
- Extension build and source-version consistency when authorized.

## Does not own

- Narrative wording beyond supplying authoritative fields.
- Local campaign analytics or local combat controls.
- Fantasy Grounds campaign write-back; that remains a proposed 3.1 capability.
- Installed Fantasy Grounds files unless explicitly authorized.

## Primary implementation areas

- `integrations/fantasy_grounds/extension/LecternSync/`
- `app/integrations/fantasy_grounds.py`
- `docs/contracts/fantasy_grounds_snapshot_v1.schema.json`
- `docs/contracts/fantasy_grounds_snapshot_v1.example.json`
- `scripts/fantasy_grounds_*_test.py`
- `scripts/Build-FantasyGroundsExtension.ps1`

## Authoritative inputs

- Fantasy Grounds chat messages, combat-tracker nodes, action metadata, source
  and target nodes, event sequence, and exported snapshot state.
- The versioned snapshot schema and sanitized live-shaped fixtures.

## Invariants

- Fantasy Grounds remains the source of truth for imported sessions.
- Lectern never writes campaign data back under the current product contract.
- Missing provenance remains unknown rather than inferred from game knowledge.
- Damage roll and applied damage remain distinct.
- Named contributors remain attached to their originating damage.
- Reprocessing is deterministic and does not erase valid journals.
- Prepared/live matching must not use roster similarity across incompatible names.

## Required verification

- Focused regression for the corrected event shape.
- All Fantasy Grounds regression scripts.
- Combat Narrative regression whenever imported event semantics change.
- Extension package inspection and version check when a build is authorized.

## Coordination

Consult Combat Narrative for consumer requirements, Encounter and Local Combat
for stored journal semantics, and Data, Reliability, and Release for schema,
installer, or packaging changes.
