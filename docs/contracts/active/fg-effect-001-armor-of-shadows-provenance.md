# Contract: Preserve Armor of Shadows provenance

Contract ID: `FG-EFFECT-001`
Status: Ready
Owning domain: Fantasy Grounds Integration
Consulting domains: Combat Narrative
Created: 2026-07-28
Last updated: 2026-07-28

## Objective

Export and import the authoritative originating power for a newly applied effect
so Armor of Shadows is represented as Armor of Shadows rather than a generic
effect, without hard-coding spell or ability names in Lectern.

## Current evidence

- Test6 chat announced `Warlock1: Armor of Shadows -` immediately before the
  effect was applied.
- The exported event recorded actor `Warlock1`, target `Warlock1`, effect
  `AC: 3`, action name `Effect`, originating action `Effect`, and source
  `active_self`.
- Combat Narrative could only state that Warlock1 gained stronger protection.
- See [`../../lectern-prd.md`](../../lectern-prd.md), section 5.16.

## Authoritative behavior

The Fantasy Grounds export must preserve the actual power/action identity
available at effect application time. Lectern may display or narrate that
identity but may not derive Armor of Shadows solely from `AC: 3`.

## Scope

- Fantasy Grounds extension effect-event capture.
- Snapshot event fields needed to preserve originating action.
- Lectern import mapping for those fields.
- Narrative consumption of the authoritative action name.
- Sanitized live-shaped regression fixtures.

Snapshot schema evolution is permitted only if the existing v1 representation
cannot carry the authoritative value without ambiguity. Any contract version
change requires explicit owner approval.

## Out of scope

- Hard-coded mappings from armor-class effects to D&D powers.
- Changes to Armor of Shadows mechanics.
- General narrative style redesign.
- Live Fantasy Grounds verification while testing is paused.

## Invariants

- Actor and target remain Warlock1.
- The applied effect remains `AC: 3` with its recorded duration.
- Unknown powers remain unknown; the importer must not guess.
- Existing effect addition, expiration, source, and target capture must continue.

## Acceptance criteria

1. A live-shaped Armor of Shadows fixture imports with `Armor of Shadows` as its
   originating action.
2. The narrative names Armor of Shadows and describes its defensive result
   without numerical mechanics.
3. A generic `AC: 3` effect without authoritative action metadata remains generic.
4. Existing effect lifecycle regressions pass.

## Required verification

- Focused test: new Armor of Shadows provenance regression.
- Related regressions: effect lifecycle, Fantasy Grounds sync, Combat Narrative.
- Full suite: required because shared import semantics change.
- Manual check: representative narrative output review.
- Live Fantasy Grounds test: deferred.

## Deliverables

- Implementation in extension export and/or Lectern import as evidence requires.
- Sanitized regression fixture and automated assertions.
- Updated PRD, changelog, and integration documentation.
- No build artifact unless separately authorized.

## Delivery authority

| Action | Authorized? |
|---|---|
| Edit repository files | Yes |
| Modify database schema | No |
| Modify snapshot contract | No, unless owner approves |
| Modify extension source | Yes |
| Install extension | No |
| Run live Fantasy Grounds test | No |
| Build application or extension | No |
| Build installer | No |
| Commit | No |
| Merge | No |
| Push | No |

## Dependencies and coordination

Coordinate the resulting event shape with the Combat Narrative agent. Avoid
overlapping edits with the concentration contract in shared parser code.

## Completion record

- Result:
- Verification evidence:
- Commit(s):
- Artifact(s) and hash:
- Remaining risks:
- PRD/Changelog updates:
