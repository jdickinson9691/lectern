# Contract: Package Fantasy Grounds correction sequence

Contract ID: `REL-PACK-001`
Status: Active
Owning domain: Data, Reliability, and Release
Assigned agent: Data, Reliability, and Release Agent
Consulting domains: Fantasy Grounds Integration, Combat Narrative
Execution order: After `FG-LINK-001`, `FG-CONC-001`, and `FG-EFFECT-001`
Created: 2026-07-28
Last updated: 2026-07-28

## Objective

Review, version, verify, package, commit, and push the completed Fantasy Grounds
correction sequence, including a current application build, Lectern Sync
extension, and Windows installer.

## Current evidence

- All three prerequisite contracts are complete and automated-verified.
- All fifteen repository regression scripts passed after `FG-EFFECT-001`.
- The current branch is `main` at `8222231` with the authorized correction
  sequence uncommitted.
- The tracked installer predates these corrections.

## Authoritative behavior

The committed source, packaged extension, packaged application, and installer
must represent the same reviewed source state. Artifact hashes must be computed
from the delivered files. Runtime Fantasy Grounds data is not part of the
release.

## Scope

- Review all uncommitted contract, implementation, regression, and documentation
  changes belonging to the correction sequence.
- Synchronize Lectern Sync version metadata for the new package.
- Run the full automated regression suite.
- Build and inspect the extension, application, and Windows installer.
- Commit the complete authorized change set and push `main` to `origin/main`.

## Out of scope

- Live Fantasy Grounds testing or installing the extension.
- Product behavior beyond the completed contracts.
- Database or snapshot-contract changes.
- Publishing a formal GitHub release.

## Invariants

- Runtime databases, handoff snapshots, logs, portraits, PDFs, backups, and
  commercial module content remain untracked.
- The installer embeds the extension built from the reviewed source.
- Artifact hashes identify the exact files committed or delivered.
- No live-testing claims are made.

## Acceptance criteria

1. Review finds no unresolved correctness or safety issue in the authorized
   change set.
2. All fifteen automated regression scripts pass.
3. Lectern Sync version declarations agree.
4. `Lectern.exe`, `LecternSync.ext`, and the Windows installer build
   successfully and pass configured artifact checks.
5. The current installer and source changes are committed and pushed to
   `origin/main`.

## Required verification

- Focused test: Fantasy Grounds sync, effect lifecycle, save resolution, Combat
  Narrative, and installer configuration.
- Related regression tests: all repository `*_test.py` scripts.
- Full suite: Required.
- Manual check: inspect extension archive contents, executable presence,
  installer timestamp/size, and SHA-256 hashes.
- Live Fantasy Grounds test: Deferred.

## Deliverables

- Implementation: reviewed correction sequence with synchronized extension
  version.
- Regression: all contract regressions.
- Documentation: PRD, changelog, Help, integration guide, and completed
  contracts.
- Build or artifact: application, `LecternSync.ext`, and tracked Windows
  installer.

## Delivery authority

| Action | Authorized? |
|---|---|
| Edit repository files | Yes |
| Modify database schema | No |
| Modify snapshot contract | No |
| Modify extension source | Yes, version synchronization only |
| Install extension | No |
| Run live Fantasy Grounds test | No |
| Build application or extension | Yes |
| Build installer | Yes |
| Commit | Yes |
| Merge | Yes; no separate branch is present |
| Push | Yes, `origin/main` |

## Dependencies and coordination

Depends on the completed `FG-LINK-001`, `FG-CONC-001`, and `FG-EFFECT-001`
contracts. Feature semantics remain owned by their completed contracts.

## Completion record

- Result:
- Verification evidence:
- Commit(s):
- Artifact(s) and hash:
- Remaining risks:
- PRD/Changelog updates:
