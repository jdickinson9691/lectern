# Contract: Require compatible names for prepared/live matching

Contract ID: `FG-LINK-001`
Status: Ready
Owning domain: Fantasy Grounds Integration
Consulting domains: Encounter and Local Combat, Campaign Management
Created: 2026-07-28
Last updated: 2026-07-28

## Objective

Prevent a live Fantasy Grounds session from linking to an older prepared
encounter merely because the two sessions reuse the same roster.

## Current evidence

- Test6 live combat was displayed as prepared from Test5.
- The prepared/live matcher currently accepts either compatible encounter names
  or sufficient roster overlap.
- Test5 and Test6 reused a similar roster, allowing the incorrect association.
- See [`../../lectern-prd.md`](../../lectern-prd.md), section 5.16.

## Authoritative behavior

Prepared/live linking requires compatible normalized encounter names before
roster similarity may disambiguate candidates. Roster overlap alone is not
proof that two encounters are the same.

## Scope

- Prepared/live encounter candidate selection.
- Name normalization and compatibility rules.
- Roster similarity as a secondary signal.
- Repair or removal of the incorrect Test6-to-Test5 association when safely
  reproducible in a sanitized test database.

## Out of scope

- Renaming existing encounters.
- Fuzzy matching across clearly different encounter names.
- Automatic deletion of prepared or live encounters.
- Live Fantasy Grounds verification while testing is paused.

## Invariants

- Exact and safely normalized same-name prepared/live sessions continue to link.
- Multiple candidates remain deterministic and auditable.
- A failed match creates or retains a distinct live session without losing events.
- Reprocessing remains idempotent.

## Acceptance criteria

1. Test5 and Test6 with identical rosters do not link.
2. Prepared and live Test6 sessions with compatible normalized names do link.
3. Roster comparison is evaluated only after name compatibility.
4. Existing reprocessing and encounter-import regressions pass.
5. Correcting the association does not erase Test6's event journal.

## Required verification

- Focused test: new incompatible-name/same-roster regression.
- Related regressions: Fantasy Grounds reprocessing, sync, Encounter Builder,
  and campaign encounter assignment.
- Full suite: required because encounter identity is shared behavior.
- Manual check: prepared/live labels in Combat Dashboard.
- Live Fantasy Grounds test: deferred.

## Deliverables

- Corrected matching implementation.
- Regression fixtures covering same roster/different name and same name/valid match.
- Safe repair behavior or documented manual remediation for the existing link.
- Updated PRD, changelog, and integration documentation.
- No build artifact unless separately authorized.

## Delivery authority

| Action | Authorized? |
|---|---|
| Edit repository files | Yes |
| Modify database schema | No |
| Modify snapshot contract | No |
| Modify extension source | No |
| Install extension | No |
| Run live Fantasy Grounds test | No |
| Build application or extension | No |
| Build installer | No |
| Commit | No |
| Merge | No |
| Push | No |

## Dependencies and coordination

Consult Encounter and Local Combat for stored encounter identity and Campaign
Management for campaign assignment. Avoid automatic repair against the owner's
runtime database without explicit authorization.

## Completion record

- Result:
- Verification evidence:
- Commit(s):
- Artifact(s) and hash:
- Remaining risks:
- PRD/Changelog updates:
