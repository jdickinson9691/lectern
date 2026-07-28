# Encounter and Local Combat Agent

## Mission

Maintain encounter preparation and Lectern's authoritative local combat
workflow from roster assembly through the structured Combat Session Log.

## Owns

- Encounter Builder behavior and prepared local encounters.
- Local combatant roster, initiative, HP, armor class, and turn order.
- Previous-turn and next/end-turn controls.
- Local attack, damage, healing, and action logging.
- Combat Session Log presentation, filtering, round grouping, and turn markers.
- Encounter completion and local outcome recording.

## Does not own

- Fantasy Grounds event capture or import attribution.
- Narrative prose and phrase selection.
- Campaign-wide aggregation beyond supplying correct encounter records.
- Character PDF parsing or content-library CRUD.

## Primary implementation areas

- `app/ui/main_window.py`
- Combat and encounter operations in `app/database/repositories.py`
- Combat-related schema in `app/database/schema.py`
- `scripts/encounter_builder_test.py`
- `scripts/combat_log_ui_test.py`

## Authoritative inputs

- Local user actions and stored encounter/combatant records.
- Structured combat events with explicit actor, target, action, result, and
  round/sequence values.

## Invariants

- Event order remains stable and reproducible.
- Damage, healing, and HP changes are represented separately from rolls.
- Missing actor, target, or outcome information remains unknown.
- Prepared rosters do not masquerade as combat journals.

## Required verification

- Encounter Builder and Combat Session Log regression scripts.
- Focused checks for turn order, HP updates, event filtering, and completion.
- Narrative and campaign-statistics regressions when shared event fields change.

## Coordination

Consult Fantasy Grounds Integration for imported combat sessions, Combat
Narrative for event-consumer compatibility, and Campaign Management for
campaign assignment or aggregate behavior.
