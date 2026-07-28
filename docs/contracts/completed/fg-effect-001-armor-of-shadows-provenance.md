# Contract: Preserve Armor of Shadows provenance

Contract ID: `FG-EFFECT-001`
Status: Complete
Owning domain: Fantasy Grounds Integration
Assigned agent: Fantasy Grounds Integration Agent
Consulting domains: Combat Narrative
Execution order: 3 of 3; `FG-LINK-001` and `FG-CONC-001` completed
Created: 2026-07-28
Completed: 2026-07-28
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

Combat Narrative consumes the same authoritative event fields. Shared extension
work was sequenced after `FG-CONC-001`.

## Completion record

- Result: Complete. The authoritative effect action is now queued before the
  previous Fantasy Grounds post-roll handler applies the Combat Tracker effect.
  The existing v1 metadata fields carry the originating action; no schema or
  snapshot-contract change was needed.
- Verification evidence: The source-order regression failed before the
  correction and passed afterward. Live-shaped import assertions preserve
  Armor of Shadows while a generic `AC: 3` event remains generic. Related
  effect-lifecycle, sync, and Combat Narrative regressions passed. All fifteen
  automated repository regression scripts passed on 2026-07-28.
  Representative narrative output names Armor of Shadows in grounded defensive
  prose without exposing `AC: 3` or its duration.
- Commit(s): None; commit authority was not granted.
- Artifact(s) and hash: None; build authority was not granted.
- Remaining risks: Live Fantasy Grounds verification is deferred. Previously
  imported Test6 events cannot safely gain provenance that their raw event did
  not capture; verify with a fresh export when testing resumes.
- PRD/Changelog updates: `docs/lectern-prd.md`, `CHANGELOG.md`,
  `docs/FANTASY_GROUNDS_RUN_TOGETHER.md`, and `docs/USER_HELP.md`.
