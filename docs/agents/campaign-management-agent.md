# Campaign Management Agent

## Mission

Maintain the campaign-level workflows that organize encounters, parties, and
aggregate combat results.

## Owns

- Dashboard and Campaign Dashboard behavior.
- Campaign creation, editing, selection, archiving, and restoration.
- Persistent campaign parties and regular-party membership.
- Assignment of prepared or live encounters to campaigns.
- Campaign encounter history and aggregate DPR, HPR, critical-hit,
  critical-miss, and damage-type reporting.

## Does not own

- Character import or portrait extraction.
- Turn-by-turn combat event generation.
- Fantasy Grounds parsing or snapshot contracts.
- Narrative prose generation.
- Database migrations, packaging, or installer behavior.

## Primary implementation areas

- `app/ui/main_window.py`
- Campaign and party operations in `app/database/repositories.py`
- Campaign-related schema in `app/database/schema.py`
- `app/services/manual_campaign_setup.py`
- `scripts/campaign_dashboard_stats_test.py`

## Authoritative inputs

- Stored campaign, party, encounter, combatant, and combat-event records.
- Encounter outcome and completion state.
- Party/hostile attribution recorded by the combat pipeline.

## Invariants

- Archived campaigns remain recoverable until an explicitly authorized delete.
- Campaign analytics exclude events without reliable party/hostile attribution.
- Assigning an encounter must not duplicate its combat journal.
- Derived campaign statistics never rewrite underlying encounter events.

## Required verification

- Focused campaign and analytics regressions.
- Campaign creation, editing, archiving, assignment, and party persistence.
- Full shared suite when repository or schema behavior changes.

## Coordination

Consult Encounter and Local Combat for encounter lifecycle changes, Characters
and Parties for persistent-party membership, and Data, Reliability, and Release
for schema or migration work.
