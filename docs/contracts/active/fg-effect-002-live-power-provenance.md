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
- A second isolated session, `Test8 Armor`, used packaged Lectern Sync 1.4.12.
  It improved the imported Action from generic `Effect` to `Mage Armor`, but
  still failed to preserve the owning `Armor of Shadows` feature displayed by
  Fantasy Grounds.
- Sanitized Test8 evidence:
  [`../../evidence/fantasy-grounds/fg-effect-002-test8-armor.md`](../../evidence/fantasy-grounds/fg-effect-002-test8-armor.md).

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

The first correction wrapped the authoritative 5E power-action entry point and
recorded the executable power before delegating to Fantasy Grounds. Test8
proved that the executable record can be a linked spell rather than the owning
feature.

Fantasy Grounds stores Armor of Shadows and its executable Mage Armor spell as
sibling character power records in the same group. Armor of Shadows has no
executable action and its authoritative formatted description links Mage
Armor; Mage Armor owns the `AC: 3` effect action. The next correction resolves
that unique sibling relationship before falling back to the executable power
name. It does not infer from effect mechanics, duration, class, or D&D rules.
Correlation remains bounded by actor, known self-target, action path, power
path, mechanical effect text, event sequence, and time.

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

- Test8 failed criteria 2 through 4 against packaged version 1.4.12.
- The parent-feature hierarchy regression, source correction, full suite, and
  version 1.4.13 package verification pass.
- Criterion 7 requires a fresh Test9 Armor session after installation.

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
- Build or artifact: Lectern application, Lectern Sync 1.4.13, and Windows
  installer built under the owner's one-time authorization.

## Delivery authority

| Action | Authorized? |
|---|---|
| Edit repository files | Yes, after explicit execution of `FG-EFFECT-002` |
| Modify database schema | No |
| Modify snapshot contract | No |
| Modify extension source | Yes, after explicit execution |
| Install extension | No |
| Run live Fantasy Grounds test | Owner-coordinated after automated verification |
| Build application or extension | One-time owner authorization for 1.4.13 on 2026-07-28 |
| Build installer | One-time owner authorization for 1.4.13 on 2026-07-28 |
| Commit | No |
| Merge | No |
| Push | No |

## Dependencies and coordination

Supersedes the live-verification conclusion of
[`FG-EFFECT-001`](../completed/fg-effect-001-armor-of-shadows-provenance.md)
without rewriting that completed contract. Coordinate output semantics with
Combat Narrative.

## Completion record

- Result: Reopened after Test8 live evidence showed that version 1.4.12
  retained linked `Mage Armor` rather than owning `Armor of Shadows`.
- Verification evidence: Test8 actor, target, mechanics, and qualitative prose
  passed; originating-feature attribution failed. A hierarchy-shaped focused
  regression now covers the discovered character-record structure. All sixteen
  repository regressions, extension manifest inspection, and isolated packaged
  startup pass for version 1.4.13.
- Commit(s): None; this contract does not authorize a commit.
- Artifact(s) and hash: `dist/Lectern/Lectern.exe`
  `BA495D36AAD05FC7EAF6565438885BDBD40A581B604CD6BCC2E38E2F38109CC0`;
  `dist/Lectern/FantasyGrounds/LecternSync.ext`
  `37980F7682892BB7DB9BB748978F85D8980435E57A60242280F31F2F3BF58FA3`;
  `release/Lectern_v3_0_0_Setup.exe`
  `3B6457DDF6BBD58EC3D7604A5FBCCFDB3B027A730E8901807F27E3737BBC5E31`.
- Remaining risks: Install version 1.4.13 and complete a fresh
  owner-coordinated Test9 Armor session.
- PRD/Changelog updates: Updated for the confirmed live-path root cause,
  automated implementation, and remaining live acceptance gate.
