# Game Content Libraries Agent

## Mission

Maintain reusable D&D reference records and consistent workflows for browsing,
importing, editing, validating, and selecting game content.

## Owns

- Monster Library and Add Monster.
- Weapons, armor, equipment, magic items, and spells.
- CSV import/export behavior for reference content.
- Search, filtering, validation, duplicate handling, and source attribution.
- Reference-content selection used by encounter and character workflows.

## Does not own

- Character-sheet PDF interpretation.
- Combat resolution or narrative wording.
- Fantasy Grounds snapshot import.
- Campaign and encounter lifecycle.

## Primary implementation areas

- Content-library UI in `app/ui/main_window.py`
- `app/importers/monster_catalog.py`
- `app/importers/csv_transfer.py`
- Reference repositories in `app/database/repositories.py`
- Reference tables in `app/database/schema.py`

## Authoritative inputs

- User-entered records.
- Validated CSV rows.
- Bundled seed data with permitted provenance.

## Invariants

- Imported content retains source attribution when available.
- Validation errors identify the failing record without corrupting prior data.
- Duplicate handling is deterministic.
- Commercial module text is never copied into fixtures or documentation.
- Removing reference content does not corrupt historical encounters.

## Required verification

- Focused CSV round-trip and validation tests.
- Manual CRUD/search checks for the affected content type.
- Encounter selection checks when monster behavior changes.

## Coordination

Consult Encounter and Local Combat for encounter selection, Characters and
Parties for character-reference links, and Data, Reliability, and Release for
schema changes.
