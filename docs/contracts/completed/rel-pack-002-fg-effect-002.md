# Contract: Package FG-EFFECT-002 correction

Contract ID: `REL-PACK-002`
Status: Complete
Owning domain: Data, Reliability, and Release
Assigned agent: Data, Reliability, and Release Agent
Consulting domains: Fantasy Grounds Integration, Combat Narrative
Execution order: After automated implementation of `FG-EFFECT-002`
Created: 2026-07-28
Last updated: 2026-07-28
Completed: 2026-07-28

## Objective

Review, version, verify, package, commit, and push the automated FG-EFFECT-002
correction, including a current application build, Lectern Sync extension, and
Windows installer.

## Current evidence

- FG-EFFECT-002 has a confirmed live-path root cause and source correction.
- The focused live-effect provenance regression passes.
- All sixteen repository regression scripts pass.
- The current branch is `main` at `13d4dd0` with the authorized correction
  sequence uncommitted.
- The tracked installer contains Lectern Sync 1.4.11 and predates this
  correction.

## Authoritative behavior

The committed source, packaged extension, packaged application, and installer
must represent the same reviewed source state. Artifact hashes must identify
the delivered files. Packaging does not itself satisfy the pending live
Fantasy Grounds acceptance criterion.

## Scope

- Review all uncommitted FG-EFFECT-002 implementation, regression, contract,
  evidence, and documentation changes.
- Synchronize Lectern Sync version metadata for the new package.
- Run the full automated regression suite.
- Build and inspect the extension, application, and Windows installer.
- Commit the authorized change set and push `main` to `origin/main`.
- Record the package as ready for owner-coordinated live acceptance.

## Out of scope

- Installing the extension or installer.
- Running or claiming the live Fantasy Grounds acceptance test.
- Product behavior beyond FG-EFFECT-002.
- Database or snapshot-contract changes.
- Publishing a formal GitHub release.

## Invariants

- Runtime databases, handoff snapshots, logs, portraits, PDFs, backups, and
  commercial module content remain untracked.
- The installer embeds the extension built from the reviewed source.
- Generic effects remain generic.
- Artifact hashes identify the exact delivered files.
- FG-EFFECT-002 remains active until its fresh live check passes.

## Acceptance criteria

1. Review finds no unresolved correctness or safety issue in the authorized
   change set.
2. All sixteen automated regression scripts pass.
3. Lectern Sync version declarations agree.
4. `Lectern.exe`, `LecternSync.ext`, and the Windows installer build
   successfully and pass configured artifact checks.
5. The current installer and source changes are committed and pushed to
   `origin/main`.
6. Documentation clearly distinguishes packaged readiness from live
   acceptance.

## Required verification

- Focused test: Fantasy Grounds live effect provenance, sync, effect lifecycle,
  Combat Narrative, and installer configuration.
- Related regression tests: all repository `*_test.py` scripts.
- Full suite: Required.
- Manual check: inspect extension archive contents, executable presence,
  installer timestamp/size, embedded extension version, and SHA-256 hashes.
- Live Fantasy Grounds test: Not authorized by this packaging contract.

## Deliverables

- Implementation: reviewed FG-EFFECT-002 correction with synchronized
  extension version.
- Regression: all contract regressions.
- Documentation: PRD, changelog, integration guide, verification report, and
  contract records.
- Build or artifact: application, `LecternSync.ext`, and tracked Windows
  installer.

## Delivery authority

| Action | Authorized? |
|---|---|
| Edit repository files | Yes |
| Modify database schema | No |
| Modify snapshot contract | No |
| Modify extension source | Yes, version synchronization and packaging review |
| Install extension | No |
| Run live Fantasy Grounds test | No |
| Build application or extension | Yes |
| Build installer | Yes |
| Commit | Yes |
| Merge | Yes; no separate branch is present |
| Push | Yes, `origin/main` |

## Dependencies and coordination

Depends on the active
[`FG-EFFECT-002`](../active/fg-effect-002-live-power-provenance.md) contract's completed
source correction and automated verification. Feature semantics remain owned
by FG-EFFECT-002.

## Completion record

- Result: Complete. The reviewed FG-EFFECT-002 source correction was versioned
  as Lectern Sync 1.4.12 and packaged with Lectern 3.0.0.
- Verification evidence: All sixteen repository regressions passed.
  PyInstaller 6.21.0 built the application, the extension archive contains the
  1.4.12 manifest, matching source version, and live power hook, the packaged
  application completed an isolated offscreen first-run startup check, and
  Inno Setup 6.7.3 compiled the installer.
- Commit(s): `385e7c3` contains the correction, tests, version synchronization,
  documentation, and rebuilt tracked installer. A following documentation
  commit records final package evidence and contract closure.
- Artifact(s) and hash:
  - `dist/Lectern/Lectern.exe` — SHA-256
    `F8621D53A1F6E6EC3E1FD61E706F9DD5429F5FD8E0635DB7E239B8C0068465A7`
  - `dist/Lectern/FantasyGrounds/LecternSync.ext` — SHA-256
    `92344FC40316C7E079D5A4BDE0A36C5DF1C0FF13E890AB8C30E51DBB2A22705D`
  - `release/Lectern_v3_0_0_Setup.exe` — SHA-256
    `60BF19156AE434B28E1E29CA43CF2798DBABE01DBF53C2B0D5845C129E8FA730`
- Remaining risks: Installation and the fresh live Armor of Shadows
  verification remain owned by active contract FG-EFFECT-002. Packaging did
  not establish live acceptance.
- PRD/Changelog updates: The PRD, changelog, verification report, integration
  guide, contract indexes, and evidence record identify Lectern Sync 1.4.12 and
  the outstanding live gate.
