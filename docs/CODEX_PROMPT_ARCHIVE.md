# Lectern Codex Prompt Archive

Last updated: July 23, 2026.

## Purpose

This file indexes completed Codex work and holds the small set of defaults
shared by every Lectern task. Keep active milestone prompts and decisions in the
current milestone handoff instead of repeating project history here.

This archive is not an implementation source of truth. Verify current behavior
in the repository, changelog, milestone handoff, and verification report.

## Current sources of truth

- [3.1 development planning](LECTERN_3_1_DEVELOPMENT.md)
- [Development workflow](DEVELOPMENT_WORKFLOW.md)
- [Verification report](VERIFICATION_REPORT.md)
- [Project changelog](../CHANGELOG.md)
- [User help](USER_HELP.md)
- [Fantasy Grounds operating guide](FANTASY_GROUNDS_RUN_TOGETHER.md)

## Archived Codex task index

| Codex task | Primary focus | Task ID |
|---|---|---|
| Connect Lectern repo | Repository and Codex workspace setup | `019f4d92-a55a-7691-8052-a85e8d9404dd` |
| Lectern 2.9.4 | Baseline, watermark framework, CRUD verification, and release preparation | `019f4d90-481c-7f71-b26c-4b7bb66091d1` |
| Lectern 2.9.5 | Milestone execution and handoff | `019f5176-aab8-74e1-b26a-18e944c8ca6b` |
| Fantasy Grounds integration | One-way 5E integration, combat synchronization, and extension milestones | `019f5621-130a-7e73-8f98-751690009351` |
| Fantasy Grounds milestone 1.4 | Historical reprocessing, safe test-data reset, and transition to 3.0.0 | `019f7abb-efd0-7523-b4c6-433bf91adaa0` |

## Completed 3.0 work areas

The 3.0 task covered prepared/live encounter association, Fantasy Grounds live
acceptance and repairs, character equipment import, campaign statistics, local
campaign ownership and parties, guided campaign setup, the split Combat
Dashboard, installer behavior, and help content. Use the changelog and
verification report for details; do not copy this history into new prompts.

## Efficient implementation prompt

Omit a section if the active milestone handoff already defines it.

```text
Goal:
<One observable user outcome.>

Scope:
<Included workflows or screens.>

Acceptance:
- <Observable behavior>
- <Observable behavior>
- <Ownership, compatibility, or safety rule>

Verification:
<Focused checks, live scenario, or full baseline.>

Delivery:
<Source only, build, installer, commit, and/or push.>
```

For design-only work, use the session opener in
[`LECTERN_3_1_DEVELOPMENT.md`](LECTERN_3_1_DEVELOPMENT.md).

## Default task assumptions

Do not repeat these unless the task changes them:

- Repository: `D:\Ludinn\Development\Lectern`
- Primary branch: `main`
- Product: Lüdinn Entertainment Campaign Tracker for Encounters, Rules &
  Navigation
- Platform: Windows Python/PySide6 desktop application using SQLite
- Current local database schema: v10
- Current Fantasy Grounds snapshot contract: v1
- Synchronization direction: one-way from Fantasy Grounds Unity 5E to Lectern
- Local records survive synchronized-data refreshes and clearing
- Fantasy Grounds source-owned controls remain read-only in Lectern
- Existing user worktree changes must be preserved
- Builds, installers, commits, and pushes occur only when Delivery requests them

Always confirm versions, schemas, and test commands from repository files.

## Task wording

- **Feature:** state the user behavior and acceptance criteria; avoid prescribing
  internals unless required.
- **Diagnosis:** say `Diagnose and report; do not change files.`
- **Live acceptance:** provide the scenario matrix once, use short checkpoints,
  and preserve final evidence in the repository.
- **Build/release:** name the required artifacts and say whether to commit and
  push.
- **Documentation:** identify the audience and link summarized workflows to
  their authoritative source.

## Archive policy

- Keep one active task for the current milestone or related feature sequence.
- Start a new task when the goal, repository, or release line changes.
- Before archiving, preserve durable decisions, evidence, commands, and open
  issues in repository documentation.
- Do not treat archived chat text as current implementation truth.
