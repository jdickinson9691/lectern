# Contract: Capture live originating power provenance

Contract ID: `FG-EFFECT-002`
Status: Active
Owning domain: Fantasy Grounds Integration
Assigned agent: Fantasy Grounds Integration Agent
Consulting domains: Combat Narrative
Execution order: Supersedes the live-unverified conclusion of `FG-EFFECT-001`
Created: 2026-07-28
Last updated: 2026-07-28

## Objective

Preserve the authoritative named Fantasy Grounds power that produces a Combat
Tracker effect when the live effect callback otherwise exposes only generic
mechanical text.

## Current evidence

- A fresh Lectern Sync 1.4.11 session named `Test7 Armor` was recorded after
  the owner resumed limited live testing.
- Fantasy Grounds chat displayed `Warlock1: Armor of Shadows -` immediately
  before applying `AC: 3; [D: 8 hours]` to Warlock1.
- The imported event retained actor and target as Warlock1, but both
  `action_name` and `originating_action` remained `Effect`.
- Combat Narrative therefore said only that Warlock1 gained stronger
  protection.
- The session contained exactly Encounter Start, the effect addition, and
  Encounter End, eliminating unrelated-event ambiguity.
- Sanitized evidence:
  [`../../evidence/fantasy-grounds/fg-effect-002-test7-armor.md`](../../evidence/fantasy-grounds/fg-effect-002-test7-armor.md).
- `FG-EFFECT-001` changed callback ordering and passed automated fixtures, but
  this live result proves that its fixture did not reproduce the authoritative
  Fantasy Grounds action-announcement path.

## Authoritative behavior

When Fantasy Grounds identifies a power by name and that power applies an
effect, the exported lifecycle event must preserve that name as its originating
action. The mechanical effect label remains separate. Lectern must not derive a
power name from `AC: 3` or any other rules text.

## Confirmed root cause

The installed 5E ruleset sends power actions through
`PowerManager.performAction`. For an effect action, that function calls
`ActionEffect.getRoll` directly. The CoreRPG effect-roll implementation does
not invoke the `onActionPostGetRoll` callback used by `FG-EFFECT-001`.
Consequently, the earlier automated fixture exercised a callback-order path
that the live Armor of Shadows action never entered.

The correction wraps the authoritative 5E power-action entry point and records
the named power before delegating to Fantasy Grounds. Correlation is bounded by
actor, known self-target, action path, power path, mechanical effect text, event
sequence, and time. The power name and mechanical effect remain separate, and
no rules inference is used.

## Scope

- Identify the Fantasy Grounds action, power, or chat-notification path that
  emits the named `Armor of Shadows` announcement.
- Correlate that authoritative announcement with the resulting effect addition
  using actor, target, action node, sequence, and bounded timing evidence.
- Preserve the originating action in existing snapshot v1 metadata when
  sufficient.
- Update import/narrative regressions to reproduce the actual live ordering and
  missing callback fields.
- Perform one owner-coordinated live Armor of Shadows verification after the
  automated correction passes.

## Out of scope

- Hard-coded `AC: 3` to Armor of Shadows mappings.
- Inference from class, spell list, duration, or D&D rules.
- General chat-log scraping unrelated to effect provenance.
- Rewriting Test6 or Test7 Armor historical events that lack the action name.
- Product-wide narrative style changes.

## Invariants

- Actor and target remain Warlock1.
- The exact mechanical effect and duration remain authoritative Fantasy Grounds
  evidence.
- Generic effects without a named source remain generic.
- Existing effect addition/removal, concentration, damage, healing, and
  prepared/live encounter corrections must not regress.
- Snapshot contract v1 remains unchanged unless the owner separately approves a
  contract revision.

## Acceptance criteria

1. A regression matching the Test7 Armor live sequence fails before the fix and
   passes afterward.
2. A fresh event exports actor and target Warlock1, originating action
   `Armor of Shadows`, and mechanical effect `AC: 3`.
3. The imported Action column names Armor of Shadows.
4. Combat Narrative names Armor of Shadows without exposing AC or duration
   numbers.
5. A generic `AC: 3` event remains generic.
6. Existing Fantasy Grounds and Combat Narrative regressions pass.
7. One fresh owner-coordinated Fantasy Grounds session passes the same log and
   narrative checks before this contract is completed.

Automated status:

- Criteria 1 through 6 pass in the repository source.
- Criterion 7 remains pending against the newly packaged and installed
  extension.

## Required verification

- Focused test: live-shaped effect-announcement and effect-add correlation.
- Related regression tests: effect lifecycle, Fantasy Grounds sync, Combat
  Narrative, historical reprocessing.
- Full suite: Required.
- Manual check: representative imported row and narrative output.
- Live Fantasy Grounds test: Required after automated correction; coordinate
  step by step with the owner.

## Deliverables

- Implementation: authoritative live power provenance capture.
- Regression: Test7 Armor-shaped fixture plus generic-effect control.
- Documentation: PRD, changelog, integration guide, and completion evidence.
- Build or artifact: Not authorized by this ready contract.

## Delivery authority

| Action | Authorized? |
|---|---|
| Edit repository files | Yes, after explicit execution of `FG-EFFECT-002` |
| Modify database schema | No |
| Modify snapshot contract | No |
| Modify extension source | Yes, after explicit execution |
| Install extension | No |
| Run live Fantasy Grounds test | Owner-coordinated after automated verification |
| Build application or extension | No |
| Build installer | No |
| Commit | No |
| Merge | No |
| Push | No |

## Dependencies and coordination

Supersedes the live-verification conclusion of
[`FG-EFFECT-001`](../completed/fg-effect-001-armor-of-shadows-provenance.md)
without rewriting that completed contract. Coordinate output semantics with
Combat Narrative.

## Completion record

- Result: Automated correction complete; contract remains active pending the
  required live Fantasy Grounds confirmation.
- Verification evidence: The focused live-effect provenance, sync,
  effect-lifecycle, historical reprocessing, and Combat Narrative tests pass.
  All sixteen repository regression scripts passed on 2026-07-28.
- Commit(s): None; this contract does not authorize a commit.
- Artifact(s) and hash: None; packaging is outside this contract's authority.
- Remaining risks: The corrected source is packaged as Lectern Sync 1.4.12 but
  has not yet been installed or confirmed in a fresh owner-coordinated Fantasy
  Grounds session.
- PRD/Changelog updates: Updated for the confirmed live-path root cause,
  automated implementation, and remaining live acceptance gate.
