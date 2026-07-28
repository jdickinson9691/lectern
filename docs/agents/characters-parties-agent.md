# Characters and Parties Agent

## Mission

Maintain player-character records from creation or import through portrait
presentation and persistent-party membership.

## Owns

- Players page behavior and character CRUD.
- Character PDF import from supported exported character sheets.
- Field normalization and import diagnostics.
- Portrait extraction, conversion, storage, thumbnails, and fallback behavior.
- Character selection for persistent campaign parties.

## Does not own

- Campaign aggregate statistics.
- Combat-event actor attribution.
- General spell, equipment, or monster-library maintenance.
- OCR for scanned PDFs unless a contract explicitly adds that product scope.

## Primary implementation areas

- Character and player UI in `app/ui/main_window.py`
- `app/importers/character_pdf.py`
- `app/services/portraits.py`
- Character and portrait operations in `app/database/repositories.py`
- `scripts/portrait_workflow_test.py`

## Authoritative inputs

- User-entered character records.
- Text and embedded images actually present in imported PDFs.
- Stored character identity and party membership records.

## Invariants

- Imports do not invent missing character facts.
- Portrait failures do not block otherwise valid character imports.
- Generated thumbnails preserve aspect ratio and remain local.
- Updating a character does not silently change encounter history.
- Duplicate identity handling is explicit and recoverable.

## Required verification

- Character import and portrait workflow tests.
- Manual sample-matrix checks when adding a new PDF source or layout.
- Persistent-party round trip when membership behavior changes.

## Coordination

Consult Campaign Management for party ownership, Game Content Libraries for
reference linking, and Data, Reliability, and Release for migrations or
runtime-data policy.
