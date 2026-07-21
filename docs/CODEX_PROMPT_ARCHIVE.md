# Lectern Codex Prompt Archive and Working Guide

Last updated: July 21, 2026

## Purpose

This file condenses completed Lectern Codex tasks into a durable project record. It is designed to reduce repeated setup prompts, keep decisions out of archived chat history, and make a new Codex task productive immediately.

This archive is not the product source of truth. Use the current repository, changelog, milestone documents, and verification reports for implementation status.

## Current sources of truth

- [3.0.0 kickoff](LECTERN_3_0_0_KICKOFF.md)
- [Fantasy Grounds live acceptance](FANTASY_GROUNDS_LIVE_ACCEPTANCE_3_0.md)
- [Fantasy Grounds operating guide](FANTASY_GROUNDS_RUN_TOGETHER.md)
- [Development workflow](DEVELOPMENT_WORKFLOW.md)
- [User help](USER_HELP.md)
- [Verification report](VERIFICATION_REPORT.md)
- [Project changelog](../CHANGELOG.md)

## Archived Codex task index

These completed tasks were documented here before being archived in Codex.

| Codex task | Representative opening prompt | Primary focus | Thread ID |
|---|---|---|---|
| Connect Lectern repo | “I have an existing git repo for the Lectern application. I need you to connect to it via Codex so that I can manage code updates.” | Repository and Codex workspace setup | `019f4d92-a55a-7691-8052-a85e8d9404dd` |
| Start Lectern 2.9.4 canvas | “Start a new canvas for Lectern 2.9.4 using the following summary.” | 2.9.4 baseline, watermark framework, CRUD verification, and release preparation | `019f4d90-481c-7f71-b26c-4b7bb66091d1` |
| Use this file start task Milestone 2.9.5 | “Use this file start task Milestone 2.9.5.” | 2.9.5 milestone execution and handoff | `019f5176-aab8-74e1-b26a-18e944c8ca6b` |
| Integrate Lectern with Fantasy | “Is it possible to make Lectern an extension for VTT Fantasy Grounds, connecting Lectern into the data sources and game systems within Fantasy Grounds?” | One-way Fantasy Grounds 5E integration, combat synchronization, and extension milestones | `019f5621-130a-7e73-8f98-751690009351` |
| Start Milestone 1.4 work | “Use this file to start work on Milestone 1.4.” | Historical combat-log reprocessing, safe test-data reset, and transition into 3.0.0 | `019f7abb-efd0-7523-b4c6-433bf91adaa0` |

## Consolidated 3.0.0 prompt history

The active 3.0.0 task replaced many short checkpoint prompts with the following durable work areas.

### Kickoff and prioritization

- Start Lectern 3.0.0 from the completed 2.9.5 baseline.
- Identify the next product features.
- Link Fantasy Grounds prepared encounters with their live-combat sessions without guessing ambiguous matches.

### Live Fantasy Grounds acceptance

- Complete live acceptance for resistance, immunity, vulnerability, mixed damage, healing, criticals, temporary HP, and multi-target actions.
- Record evidence after each user checkpoint such as “Resistance rolled,” “Mix damage rolled,” and “Criticals rolled.”
- Preserve the completed evidence in `docs/FANTASY_GROUNDS_LIVE_ACCEPTANCE_3_0.md` instead of relying on chat history.

### Release-blocker repair

- Preserve actor and action attribution for every target of a multi-target action.
- Reconcile later authoritative enrichment of an already imported event.
- Avoid misleading `0 rolled` text for negated and temporary-HP damage.
- Cap applied damage components to the target's actual HP loss.

### Character and dashboard refinement

- Import equipped Fantasy Grounds weapons and armor into player-character fields.
- Place Party Damage Type Leaders on the left of Campaign Encounters so all 13 standard types can display together.

### Installer and help refinement

- Prompt for the user's Fantasy Grounds `extensions` folder without embedding a developer-specific path.
- Reorganize Help around clickable section titles.
- Explain Fantasy Grounds impact on every Lectern screen.
- Clearly distinguish local Lectern encounters, Fantasy Grounds Prepared encounters, and Fantasy Grounds Live combat sessions.

### Delivery prompts

Repeated prompts such as “Build these changes,” “Merge to git,” and “Push merge to git” mean:

1. Run the documented regression baseline.
2. Build Lectern and Lectern Sync.
3. Compile the Windows installer when installer or packaged content changed.
4. Run a packaged startup check.
5. Commit only the intended files.
6. Push the current `main` branch and verify a clean synchronized worktree.

## Efficient prompt template

Use this structure for a new Lectern task:

```text
Goal:
<One concrete user-visible outcome.>

Scope:
<Screens, workflows, or integrations included.>

Acceptance:
- <Observable behavior 1>
- <Observable behavior 2>
- <Important ownership or safety rule>

Verification:
<Focused checks, live Fantasy Grounds scenario, or full baseline.>

Delivery:
<Source only, build, installer, commit, and/or push.>
```

Example:

```text
Goal:
Show synchronized Fantasy Grounds spell actions in the Campaign Dashboard.

Scope:
Fantasy Grounds import, Campaign Dashboard, Help, and regression coverage.

Acceptance:
- Existing local actions remain unchanged.
- Imported actions retain actor, target, and source encounter.
- Fantasy Grounds remains the source of truth.

Verification:
Focused import/UI regression plus the complete baseline.

Delivery:
Build the app and installer, commit, and push main.
```

## Default Lectern task assumptions

These do not need to be repeated unless a task intentionally changes them:

- Repository: `D:\Ludinn\Development\Lectern`
- Official expanded name: Lüdinn Entertainment Campaign Tracker for Encounters, Rules & Navigation
- Primary branch: `main`
- Application: Windows Python/PySide6 desktop app using SQLite
- Fantasy Grounds direction: one-way from Fantasy Grounds Unity `5E` into Lectern
- Local Lectern records must be preserved when synchronized data is refreshed or cleared
- Fantasy Grounds source-owned encounter controls remain read-only in Lectern
- Database schema and snapshot contract change only when the feature requires it
- Existing user changes in the worktree must be preserved
- Build, installer creation, commit, and push occur only when requested or included in Delivery

Always confirm current versions and test commands from repository files rather than copying version numbers from this archive.

## Prompting patterns by task type

### Feature implementation

State the desired user behavior and acceptance criteria. Avoid prescribing internal classes or database columns unless they are part of the requirement.

### Diagnosis only

Say “diagnose and report; do not change files.” This prevents a diagnosis request from becoming an implementation task.

### Live Fantasy Grounds acceptance

Provide the scenario matrix once, then use short checkpoint replies during the live run. Ask Codex to preserve final evidence in the repository.

### Build and release

Specify whether “build” means the application only or the application, extension, and Windows installer. Specify whether Codex should commit and push.

### Documentation

Identify the intended audience: end user, developer, release operator, or live-test facilitator. Require links to the authoritative source when the document summarizes another workflow.

## Archive policy

- Keep one active Codex task for the current milestone or tightly related feature sequence.
- Start a new task when the goal, repository, or release line materially changes.
- Before archiving a completed task, move durable decisions, evidence, commands, and unresolved issues into repository documentation.
- Archive completed setup and milestone tasks after their work is merged.
- Do not archive unrelated tasks merely because they are old.
- Do not treat archived chat text as current implementation truth.
