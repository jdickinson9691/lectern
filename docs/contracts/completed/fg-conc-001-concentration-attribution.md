# Contract: Correct concentration-check attribution

Contract ID: `FG-CONC-001`
Status: Complete
Owning domain: Fantasy Grounds Integration
Assigned agent: Fantasy Grounds Integration Agent
Consulting domains: Combat Narrative
Execution order: 2 of 3; `FG-LINK-001` completed
Created: 2026-07-28
Completed: 2026-07-28
Last updated: 2026-07-28

## Objective

Attribute a concentration check to the creature actually making the check and
preserve its authoritative DC, total, and outcome when Fantasy Grounds exposes
them.

## Current evidence

- In Test6, Bandit damaged Ranger1.
- Ranger1 rolled the concentration check successfully.
- The exported event used Bandit as both actor and target because the generic
  dice handler fell back to the current active combatant.
- The imported log and narrative therefore attributed the check to Bandit.
- See [`../../lectern-prd.md`](../../lectern-prd.md), section 5.16.

## Authoritative behavior

The actor is the creature whose concentration is being tested. The triggering
attacker may be recorded as causal context but must not replace the roller.
Save/concentration DC, total, and success or failure must come from explicit
Fantasy Grounds evidence. If an outcome is unavailable, it remains unreported.

## Scope

- Fantasy Grounds concentration-event capture.
- Resolution of actor and target nodes in the dice/chat callback.
- Association with the immediately relevant damage target when authoritative.
- Import mapping for concentration DC, total, and outcome.
- Narrative consumption of the corrected event.

## Out of scope

- Inferring concentration success from D&D rules when Fantasy Grounds does not
  report the DC or outcome.
- Altering concentration mechanics.
- Retrofitting unsanitized runtime logs.
- Live Fantasy Grounds verification while testing is paused.

## Invariants

- The attacker remains attached to its attack and damage events.
- The damaged target remains attached to the applied-damage event.
- Save total, DC, and outcome are never fabricated.
- General saving-throw provenance must not regress.

## Acceptance criteria

1. A live-shaped Bandit-to-Ranger1 damage sequence attributes the subsequent
   concentration check to Ranger1.
2. The event preserves the reported total and uses the reported DC/outcome when
   available.
3. Missing DC or outcome remains explicitly unreported.
4. Narrative describes Ranger1's concentration check, not Bandit's.
5. Existing save-resolution and damage-attribution regressions pass.

## Required verification

- Focused test: new concentration attribution regression.
- Related regressions: save resolution, Fantasy Grounds sync, damage
  contributors, Combat Narrative.
- Full suite: required because shared event attribution changes.
- Manual check: representative log and narrative output.
- Live Fantasy Grounds test: deferred.

## Deliverables

- Corrected extension and/or import attribution logic.
- Sanitized live-shaped fixture and automated assertions.
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

Combat Narrative consumes the same authoritative event semantics. Shared parser
work was sequenced after `FG-LINK-001` and before `FG-EFFECT-001`.

## Completion record

- Result: Complete. Concentration actor resolution now uses the roll database
  node, then the recent authoritative damage target, and otherwise leaves the
  actor unresolved. It no longer falls back to the active attacker.
- Verification evidence: The live-shaped source regression failed before the
  correction and passed afterward. Focused save/import, sync, damage
  contributor, and Combat Narrative regressions passed. All fifteen automated
  repository regression scripts passed on 2026-07-28. Representative imported
  log details preserve `Ranger1 | Against DC 10 | Concentration | Success`;
  the narrative credits Ranger1 with holding concentration and never credits
  Bandit.
- Commit(s): None; commit authority was not granted.
- Artifact(s) and hash: None; build authority was not granted.
- Remaining risks: Live Fantasy Grounds verification is deferred. The
  previously imported Test6 event cannot be repaired safely because its raw
  actor was already wrong; verify with a fresh export when testing resumes.
- PRD/Changelog updates: `docs/lectern-prd.md`, `CHANGELOG.md`,
  `docs/FANTASY_GROUNDS_RUN_TOGETHER.md`, and `docs/USER_HELP.md`.
