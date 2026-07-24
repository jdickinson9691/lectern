# Lectern 3.1 Development

Prepared July 23, 2026.

## Purpose

This is the active planning handoff for Lectern 3.1. It keeps the next design
conversation focused on user outcomes instead of repeating repository setup and
completed history.

Lectern remains version 3.0.0 until the 3.1 scope and release boundary are
approved. Do not change version metadata, database schema, the Fantasy Grounds
snapshot contract, or release artifacts during design work.

## Current status

- Branch `main` is synchronized with `origin/main` at `8da9d56`.
- The working tree was clean when this handoff was prepared.
- Application and installer metadata remain at version 3.0.0.
- Local campaign ownership, archive state, and persistent parties use database
  schema v10.
- Fantasy Grounds synchronization remains one-way, uses snapshot contract v1,
  and ships Lectern Sync 1.4.3.
- The guided local campaign setup now validates optional player and monster CSV
  files, creates a persistent party, and creates a campaign-scoped opening
  encounter.
- The Combat Dashboard now uses a draggable Campaign Entities / Combat Session
  Log workspace.
- The full automated suite, source compilation, package build, installer build,
  and packaged startup were last recorded as passing on July 21, 2026.

Authoritative implementation evidence remains in
[`CHANGELOG.md`](../CHANGELOG.md) and
[`VERIFICATION_REPORT.md`](VERIFICATION_REPORT.md).

## Recommended next steps

1. Confirm whether 3.0.0 is feature-complete or identify its remaining release
   blockers.
2. Choose one primary user outcome for 3.1 and name the users and workflow it
   serves.
3. Map that workflow from entry point to completion before discussing individual
   controls or data fields.
4. Record acceptance criteria, ownership rules, and compatibility constraints.
5. Decide whether the outcome requires a database migration or Fantasy Grounds
   contract change only after the workflow is approved.
6. Split the approved outcome into the smallest testable implementation
   milestones.

## Design-question sequence

Ask one decision at a time. Summarize the answer and its consequence before
moving to the next question.

1. **Outcome:** What should a user be able to finish in 3.1 that is difficult or
   impossible now?
2. **Audience:** Is the primary user a campaign creator, session runner, player,
   analyst, or Fantasy Grounds user?
3. **Entry point:** Where should the workflow begin?
4. **Happy path:** What is the shortest successful path from entry to result?
5. **Information:** What must the user see or provide at each step?
6. **Ownership:** Which data is local, imported, editable, read-only, or
   generated?
7. **Exceptions:** What can be missing, ambiguous, stale, duplicated, or
   interrupted?
8. **Feedback:** How does the user know progress, success, failure, and recovery
   state?
9. **Compatibility:** What existing local and Fantasy Grounds behavior must not
   change?
10. **Acceptance:** What observable checks prove the design is complete?

Defer visual styling, control selection, schema changes, and implementation
details until the outcome and happy path are agreed.

## Efficient session opener

Use this prompt to begin or resume 3.1 planning:

```text
Use docs/LECTERN_3_1_DEVELOPMENT.md as the active planning handoff.

First:
1. Verify the repository status and authoritative docs.
2. Give me a concise current-status summary.
3. Recommend the next three steps in priority order.

Then ask one design question at a time, beginning with the primary 3.1 user
outcome. Record decisions in this file. Do not implement, bump versions, change
contracts, build, commit, or push unless I explicitly expand the scope.
```

## Decision log

Add only durable, approved decisions here.

| Date | Decision | Consequence |
|---|---|---|
| 2026-07-23 | Treat 3.1 as a design milestone before implementation. | Existing version and contracts remain unchanged until scope approval. |

## Proposed 3.1 milestone roadmap

Status: **Proposed for review; not yet an approved release commitment.**

The three requested outcomes are feasible, but they do not have equal risk.
Portrait thumbnails are already partly implemented, a narrative combat recap can
be derived from existing data, and Fantasy Grounds write-back introduces a new
data-ownership and compatibility boundary. The recommended order puts visible,
low-risk value first while write-back proceeds through a guarded proof of
concept.

### Feasibility summary

| Outcome | Current foundation | Feasibility | Principal gap |
|---|---|---|---|
| Portrait thumbnails in Players | Character PDF import extracts a likely portrait to PNG; the Players table displays the saved portrait as a 40x40 icon in its first column. | High; much of the requested happy path already exists. | Verify real exports, create consistent thumbnail behavior, and provide fallback/correction when the wrong embedded image is selected. |
| Literary combat recap | The Combat Session Log already groups structured local and Fantasy Grounds events by round and preserves original details. | High for a deterministic first version; high with additional product decisions for AI-assisted prose. | Build a round-to-scene model, connect related events, and define regeneration, editing, privacy, and attribution rules. |
| Lectern-to-Fantasy Grounds updates | The extension and Lectern already exchange files in a campaign-scoped handoff folder. Fantasy Grounds extensions can read text files and, as the GM, update campaign database nodes. | Technically feasible, but high risk if broadly scoped. | Define an allowlisted command contract, stable record identity, conflicts, confirmation, acknowledgements, backups, and supported 5E paths. |

### Milestone 0 - Scope, samples, and ownership

**Goal:** make each track testable before changing schema or contracts.

- Collect representative character PDFs exported from D&D Beyond, Roll20, and
  Fantasy Grounds, including files with no portrait, several embedded images,
  transparent images, and unusually shaped portraits.
- Select one local campaign and a disposable Fantasy Grounds Unity 5E campaign
  for integration testing.
- Choose the first Fantasy Grounds write-back record type and field allowlist.
  Recommended first proof: a Lectern-owned note or other non-combat field on one
  already-linked campaign record. Do not begin with HP, initiative, active
  Combat Tracker state, or record deletion.
- Decide whether narrative prose is deterministic/offline only or may optionally
  use an AI provider. Source combat events always remain authoritative.
- Define ownership labels: Fantasy Grounds-owned, Lectern-owned, derived, and
  user-edited.

**Exit criteria**

- The sample matrix, supported/unsupported cases, write-back allowlist, and
  narrative privacy choice are recorded.
- Every writable field has a named source of truth and conflict rule.
- No production campaign data is required for testing.

### Milestone 1 - Portrait thumbnail completion

Implementation status: **Automated verification complete; manual Windows
acceptance pending.**

**Goal:** make portrait use reliable and obvious in the Players table.

- Preserve the original extracted portrait and create a normalized thumbnail
  with fixed bounds, aspect-preserving crop/fit, and transparent-background
  support.
- Continue displaying the thumbnail beside the character name in the first
  Players-table column; add a neutral fallback when no portrait is available.
- Show the detected portrait in the import preview and let the user accept,
  replace, or clear it before saving.
- Add source-specific fixtures for D&D Beyond, Roll20, and Fantasy Grounds PDFs.
  Treat unsupported image encodings and PDFs without embedded images as
  recoverable cases, not failed character imports.
- Avoid duplicate filenames when two characters share a name, and cleanly
  handle a replaced source image.

**Acceptance**

- A supported PDF with an embedded portrait produces a readable thumbnail and
  displays it in the first Players-table column after import and restart.
- Non-square and transparent portraits render without distortion.
- A PDF without a usable image still imports its character data and displays the
  fallback.
- The user can correct a wrongly detected image without re-importing the
  character.

### Milestone 2 - Narrative combat recap foundation

Implementation status: **Automated verification complete; manual Windows
acceptance pending.**

**Goal:** turn authoritative round events into a coherent, regenerable scene
summary without losing evidence.

- Create a read-only narrative model that groups events by round, actor, target,
  action, outcome, damage, healing, and defeat/recovery state.
- Link adjacent attack, damage-roll, applied-damage, healing, and turn events
  where the preserved event identity and sequence make the relationship clear.
  Mark uncertain relationships rather than inventing them.
- Add a **Narrative Recap** section beside the structured Combat Session Log.
- Generate concise offline prose from tested templates, with controls for tone
  and detail level.
- Keep links from each paragraph or round back to the source log events.
- Generate on demand at first; do not require a database migration until users
  need saved edits or multiple versions.

**Acceptance**

- The same log and settings produce the same recap.
- Hits, misses, critical hits, damage types, resistance, vulnerability, healing,
  and unattributed changes are not contradicted.
- Empty, partial, and older free-text logs degrade gracefully.
- Regenerating a recap never changes the structured combat log.

### Milestone 3 - Optional literary rewrite and editorial workflow

**Goal:** provide richer fictional prose while keeping facts and user control.

- Add an optional literary rewrite over the deterministic round summaries.
- Offer a small set of useful styles such as concise chronicle, heroic fantasy,
  and dark/gritty, plus a length control.
- Show a factual preview before replacement and flag unsupported additions.
- If an external AI service is used, require explicit configuration and explain
  what combat data leaves the device. The offline recap remains available.
- Decide whether saved narrative text is derived-only, user-editable, or
  versioned; add schema only if persistence is approved.
- Support copy/export for session notes.

**Acceptance**

- Names, targets, outcomes, quantities, and sequence remain grounded in the
  source summary.
- The user can regenerate one round without overwriting edited rounds.
- Failure or lack of network credentials falls back to the offline recap.

### Milestone 4 - Fantasy Grounds write-back proof of concept

**Goal:** prove a safe two-way handoff on one low-risk field.

- Add a separate versioned Lectern-to-Fantasy Grounds command file; do not
  repurpose snapshot contract v1.
- Include command ID, source record identity, intended field change, expected
  prior value or revision, creation time, and Lectern version.
- In the extension, expose an explicit **preview/apply** command available only
  to the GM. Never apply silently when a file changes.
- Validate the campaign identity, ruleset, record path, field allowlist, and
  current value before writing.
- Write an acknowledgement for applied, rejected, stale, unsupported, and
  partially applied commands so Lectern can show the outcome.
- Back up or otherwise provide a recoverable before-state and keep an audit
  record. Never edit `db.xml` directly.

**Acceptance**

- A permitted change reaches the intended linked record in the disposable 5E
  campaign only after GM confirmation.
- Replaying the same command is idempotent.
- A stale value, wrong campaign, missing record, unsupported field, or malformed
  file makes no campaign change and produces a useful acknowledgement.
- Existing one-way snapshot import continues to pass unchanged.

### Milestone 5 - Limited two-way integration pilot

**Goal:** expand only from evidence gathered in the proof of concept.

- Add approved low-risk fields one record type at a time.
- Show pending, applied, conflicted, and rejected changes in Lectern.
- Provide a per-field conflict choice: keep Fantasy Grounds, apply Lectern, or
  cancel. Never infer a winner for simultaneous edits.
- Separate normal campaign-record updates from live-session operations.
- Keep Combat Tracker HP, initiative, effects, targeting, and turn order
  Fantasy Grounds-owned unless a later, separately approved milestone designs a
  live remote-control workflow.
- Test against the supported Fantasy Grounds Unity and 5E ruleset versions and
  document extension-compatibility limits.

**Acceptance**

- The pilot field matrix is fully covered by round-trip, conflict, replay,
  rollback, and upgrade tests.
- Users can tell which application owns every synchronized field.
- Disabling write-back leaves the established one-way workflow intact.

### Recommended release boundary

The lowest-risk 3.1 release boundary is Milestones 0 through 2: reliable portrait
thumbnails plus an offline narrative recap. Milestone 3 can join 3.1 if its
privacy and persistence decisions are resolved without delaying the core
release. Milestones 4 and 5 should run as an experimental integration track and
enter 3.1 only after the proof of concept passes live acceptance; otherwise they
become the lead work for the next minor release.

### Decisions required before implementation

1. Which of the three outcomes is the primary 3.1 user outcome?
2. What is the first exact Fantasy Grounds record and field Lectern may update?
3. Must the narrative feature work entirely offline, or may it optionally use an
   AI provider?
4. Should generated narrative be transient, saved as one editable recap, or
   versioned?
5. May representative third-party PDFs be retained as private test fixtures, or
   must tests use synthetic equivalents?

## Definition of design-ready

Implementation can begin when this file identifies:

- one primary user outcome and audience;
- the approved workflow and exception paths;
- observable acceptance criteria;
- local and Fantasy Grounds data-ownership rules;
- compatibility and migration decisions;
- the first independently testable milestone.
