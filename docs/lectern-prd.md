# Lectern Product Requirements and Development Status

Last updated: July 28, 2026
Repository baseline: implementation and installer commit `858175b`, with the
REL-PACK-001 completion record applied afterward
Document status: Current product and agent handoff authority
Filename: `lectern-prd.md`

## 1. Purpose

This document is the primary product-status handoff for future Lectern agents
and agent contracts. It records:

- the current product boundary and authoritative versions;
- every user-facing feature area and its development status;
- verified behavior and the evidence supporting it;
- known defects and deferred testing;
- unresolved product, ownership, privacy, and compatibility questions;
- constraints that future agents must preserve.

Use this document to decide what is true now and what work remains. Use
[`CHANGELOG.md`](../CHANGELOG.md) for implementation history and the specialized
documents linked below for detailed acceptance evidence.

When another document conflicts with this one, verify the implementation and
update both documents. Do not silently copy stale values forward.

## 2. Product summary

Lectern is a local-first Windows desktop application for D&D 5E campaign
planning, encounter preparation, combat tracking, campaign analysis, character
and reference management, and review of synchronized Fantasy Grounds combat.

Lectern supports two ownership models:

1. **Local Lectern workflows:** campaigns, parties, encounters, combat actions,
   and reference data managed directly in Lectern.
2. **Fantasy Grounds workflows:** Fantasy Grounds Unity 5E remains the source
   of truth. Lectern imports characters, prepared encounters, Combat Tracker
   state, and authoritative combat events for read-only review and analysis.

Combat Narrative is generated locally from authoritative structured events
using a versioned phrase library. It does not use an external LLM or API.

## 3. Current authoritative baseline

| Item | Current value | Notes |
|---|---|---|
| Product version | 3.0.0 | Release name: Workflow and Import Refinement |
| Release status | In progress; not release-clear | FG-EFFECT-002 is corrected, packaged, and automated-verified; fresh installed live acceptance and broader manual acceptance remain |
| Planned milestone | 3.1 design and staged implementation | Some originally proposed 3.1 work has already been implemented without changing product version |
| Database schema | v10 | Local campaign ownership, archive state, and persistent parties |
| Fantasy Grounds snapshot contract | v1 | One-way import only |
| Lectern Sync extension | 1.4.12 | Packaged in the current installer |
| Combat Narrative library schema | v1 | Current content version: `2026.07.28.1` |
| Supported Python | 3.13 | Python 3.14 is not approved for packaging |
| Supported desktop platform | Windows 10/11 | PySide6 desktop application |
| Baseline commit | `858175b` | FG-LINK-001, FG-CONC-001, FG-EFFECT-001, and rebuilt installer |
| Current installer | `release/Lectern_v3_0_0_Setup.exe` | SHA-256 `F1BD85F6A1C3AE3B2C855A276D15C24AA7FD9FA85AD2144FED0516365C3B7B0B` |

The root [`README.md`](../README.md) still reports database schema v9 and some
older documents report prior extension or commit versions. Those values are
stale. Synchronizing existing documentation is an open maintenance task.

## 4. Status vocabulary

| Status | Meaning |
|---|---|
| Complete | Implemented and supported within the stated scope |
| Verified | Relevant automated or live acceptance evidence has passed |
| Partial | Useful behavior exists, but part of the intended workflow is absent or unverified |
| Blocked | A known defect prevents acceptance or release clearance |
| Proposed | Designed or discussed, but not implemented |
| Deferred | Deliberately paused by product-owner decision |

Automated verification does not replace the unchecked manual Windows acceptance
items in [`VERIFICATION_REPORT.md`](VERIFICATION_REPORT.md).

## 5. Feature status

### 5.1 Application shell, navigation, and presentation

**Status:** Complete; automated layout verification passed; full visual
acceptance remains partial.

Implemented:

- Eighteen navigation pages in a single PySide6 desktop application.
- Dark desktop theme, responsive bounded spacing, and minimum window sizing.
- Centered proportional watermark wrapper on every registered page.
- Packaged application icon and bundled Help.
- Local diagnostic and error-log workflows.

Verified:

- Adaptive layout regression.
- Help content and navigation regression.
- Packaged application and installer builds.

Remaining bugs or questions:

- Complete the manual watermark and resizing matrix at minimum, default, and
  maximized sizes.
- Confirm all controls remain readable at supported Windows scaling values.
- Decide whether the Dashboard should show milestone/version health and known
  integration warnings.

### 5.2 Campaign management

**Status:** Complete and automated-verified for the current local scope.

Implemented:

- Explicit local and Fantasy Grounds campaign ownership.
- Local campaign creation, editing, archiving, and restoration.
- Campaign-scoped encounters and encounter completion outcomes.
- Persistent local campaign parties.
- Party combat statistics across campaign encounters.
- Guided Local Setup with optional validated player and monster CSV files,
  party selection, and optional opening encounter creation.

Known limitations and questions:

- Fantasy Grounds campaigns are read-only in Lectern.
- Two-way field ownership and conflict rules are not designed.
- Confirm whether archived campaigns need export, permanent deletion, or
  retention-policy controls.
- Decide whether the guided workflow should support additional source formats.

Reference:
[`MANUAL_CAMPAIGN_MILESTONES.md`](MANUAL_CAMPAIGN_MILESTONES.md).

### 5.3 Persistent parties

**Status:** Complete and automated-verified.

Implemented:

- Save a regular party per local campaign.
- Manage party membership and ordering.
- Add the saved party to an encounter in one action.
- Use party identity for campaign damage, healing, and leader statistics.

Open questions:

- Whether parties need named variants or multiple active rosters per campaign.
- Whether imported Fantasy Grounds parties should ever become editable local
  copies through an explicit clone operation.

### 5.4 Encounter Builder

**Status:** Complete for local encounters; read-only for Fantasy Grounds-owned
encounters.

Implemented:

- Create uniquely named local encounters.
- Add selected players, the persistent campaign party, and monster quantities.
- Remove combatants, roll initiative, and start local combat.
- Display prepared/live Fantasy Grounds ownership and counterpart context.
- Require compatible normalized prepared/live encounter names before roster
  overlap may select an unambiguous counterpart.
- Preserve meaningful encounter-number suffixes so Test5 and Test6 remain
  distinct identities.
- Reconcile a stale counterpart association during same-sequence import without
  changing the combat journal.

Open UX question:

- A prepared encounter intentionally has no combat journal, but this can look
  like data loss. Decide whether to add an explicit **Open Live Combat Log**
  action or automatically switch after reprocessing/import.

### 5.5 Local Combat Dashboard

**Status:** Complete and automated-verified for the current scope.

Implemented:

- Campaign and encounter selection.
- Initiative order, active turn, previous/next turn controls.
- Applied damage and healing controls.
- Manual structured action logging.
- Read-only entity state and structured combat journal.
- Draggable Campaign Entities / Combat Session Log split.

Open questions:

- Whether local combat should gain first-class structured spell, save, effect,
  resistance, and damage-component entry instead of relying on manual details.
- Whether completed local encounters should permit corrections through an
  audited edit workflow.

### 5.6 Combat Session Log

**Status:** Complete with known upstream Fantasy Grounds attribution defects.

Implemented:

- Round grouping and expandable source details.
- Search by actor, target, action, damage type, or result.
- Action-type and result filters.
- Optional hiding of turn markers.
- Highlighted hits, misses, critical results, damage, and healing.
- Separate rolled and applied damage.
- Normalized actor side, results, damage types, and component evidence.
- Historical reprocessing from immutable imported raw events with a safety
  backup.

Clarification:

- The Test5 live encounter stores 66 records: 34 combat events plus 16 turn
  starts and 16 turn ends. With **Hide turn markers** selected, the UI correctly
  shows 34 events.

Known defects:

- Generic effect actions can lose the originating ability; see
  **FG-EFFECT-002**. This supersedes the live-unverified conclusion of
  **FG-EFFECT-001**.
- Prepared encounters show zero journal events by design, but the UI does not
  yet provide a strong enough transition to the linked live journal.

### 5.7 Combat Narrative

**Status:** Implemented and extensively automated-verified; live acceptance is
partial and blocked by one upstream capture defect.

Implemented:

- A dedicated page below Combat Dashboard with the same campaign and encounter
  selectors.
- Read-only, chronological, round-by-round narrative generated from the
  authoritative Combat Session Log.
- Entirely offline deterministic generation.
- Versioned and validated `heroic_military` phrase library.
- Coalescing of strongly linked attack, save, damage, healing, and effect events.
- Named damage contributors including Sneak Attack, Hunter's Mark, and Divine
  Smite when present in source evidence.
- Qualitative damage, healing, resistance, vulnerability, temporary vitality,
  defeat, and recovery language without mechanical quantities in prose.
- Grounded condition, effect addition/removal, mark, inspiration, class-feature,
  and concentration language.
- Neutral self-target phrasing.
- No references to Lectern or Fantasy Grounds in the story.
- No invented spells, abilities, conditions, equipment, injuries, deaths,
  motives, or events.

Latest live Test6 passes:

- Innate Sorcery and Bardic Inspiration language.
- Hunter's Mark application, named force-damage contribution, helper
  suppression, and removal.
- Correct separation of a Light Crossbow attack from mistakenly rolled Scimitar
  damage.
- Correct self-target sentence: Bard1 was struck by Bard1's own Dagger.
- Correct unresolved outcome.

Test6 and Test7 verification status:

- **FG-CONC-001:** Corrected and automated-verified on July 28, 2026. A
  concentration check now uses its roll database node, then the authoritative
  target of immediately preceding damage, and otherwise remains unattributed.
  Test7 live verification correctly attributed the check to Ranger1.
- **FG-EFFECT-001:** Automated verification completed, but fresh Test7 Armor
  evidence still imported Armor of Shadows as generic `Effect`. The live defect
  was reopened as **FG-EFFECT-002**. Its source correction now captures the
  actual 5E power-action entry point; fresh packaged live confirmation remains.

Historical-data rule:

- Reprocessing may reinterpret retained evidence but must never invent missing
  provenance. Old Test5 data cannot be made to name Armor of Shadows if the raw
  event never captured it.

Open product questions:

- Should generated prose remain transient, be saved as one editable recap, or
  support versions?
- Should users be able to regenerate one round without replacing edited rounds?
- Should the product add other original style profiles and a detail-length
  control?
- Should the narrative link each sentence or beat back to source events?
- What copy/export formats are required?

Reference:
[`COMBAT_NARRATIVE_LIBRARY.md`](COMBAT_NARRATIVE_LIBRARY.md).

### 5.8 Campaign analytics

**Status:** Complete and automated-verified; accuracy depends on source
attribution quality.

Implemented:

- Party damage per round and healing per round.
- Applied damage and healing totals.
- Critical-hit and critical-miss leaders, including ties.
- Party leaders for all thirteen standard 5E damage types.
- Attribution-coverage reporting.
- Conservative fallback for older single-type rows.
- Completed encounter history, rounds, outcomes, combatants, and actions.

Known limitations:

- Unattributed events are excluded from party metrics.
- Upstream capture defects can reduce coverage until corrected and re-imported.
- Decide whether analytics should expose a drill-down from each aggregate to
  source events.

### 5.9 Players and character records

**Status:** Complete for current editor and import scope; broad manual source
matrix remains partial.

Implemented:

- Create, view, edit, duplicate, and delete player records.
- General details, player name, species, class, subclass, background, and level.
- Ability bases and bonuses, combat values, equipment, inventory, currency,
  skills, expertise, saving throws, feats, spellcasting ability, and notes.
- SRD-driven species bonuses and feat ability choices.
- Character PDF preview before persistence.
- Common D&D Beyond, Roll20, Fantasy Grounds, and fillable-sheet mappings.
- Matching-name re-import updates while retaining a safe portrait choice.

Known limitations and questions:

- Image-only PDFs require OCR or manual entry; OCR is not implemented.
- Source layouts change and require continuing real-export validation.
- Complete the supported/unsupported sample matrix across D&D Beyond, Roll20,
  and Fantasy Grounds.
- Decide whether private third-party PDF samples may be retained as fixtures or
  whether all committed fixtures must be synthetic.
- Never commit user PDFs or extracted personal character data.

### 5.10 Player portraits and thumbnails

**Status:** Automated verification complete; representative manual acceptance
has passed for imported characters, but the full source matrix remains open.

Implemented:

- Extract likely embedded portraits from supported PDFs.
- Preserve an original managed portrait and generate a normalized thumbnail.
- Preview, replace, or clear the portrait before saving.
- Retain a safe portrait during character re-import.
- Display a 40x40 portrait in the first Players-table column.
- Display portraits or initials fallbacks in encounter and combat views.
- Avoid filename collisions.

Known limitations and questions:

- PDFs with no usable embedded image fall back without blocking character import.
- Wrong embedded-image selection requires user correction.
- Confirm transparent, unusually shaped, and high-resolution portraits across
  the complete sample matrix.

### 5.11 Monsters

**Status:** Partial.

Implemented:

- Versioned 4,148-record monster catalog.
- Monster Library browsing table.
- Add Monster form.
- CSV import/export support.
- Reusable global monster records for local encounters.
- Fantasy Grounds monster/combatant imports remain source-owned.

Remaining questions:

- Direct edit, delete, duplicate, search, and filter workflows are not fully
  represented in the current Monster Library UI.
- Decide whether catalog records should be immutable with user-created overlays
  or directly editable.
- Complete the manual CRUD matrix in the verification report.

### 5.12 Reference libraries

**Status:** Operational read/browse and CSV transfer; direct UI editing is
partial.

Libraries:

- Weapons
- Armor
- Equipment
- Magic Items
- Spells
- Rules/reference and imported Fantasy Grounds catalog records in storage

Implemented:

- Bundled seed data.
- Browsing tables.
- CSV import/export, validation, and templates.
- Fantasy Grounds provenance and stale/current tracking.

Open questions:

- Whether each reference library needs direct create/edit/delete/search controls.
- How user-authored records should coexist with imported module records.
- Whether duplicate names from different sources should remain separate instead
  of being normalized by name.

### 5.13 Workbook and CSV data transfer

**Status:** CSV workflow complete and automated-verified; workbook UI is
unclear/dormant.

Implemented:

- Export one table or all supported tables.
- Export empty templates.
- Validate and preview New, Modified, Unchanged, Duplicate, and Error rows.
- Block commit when duplicate or error rows exist.
- Confirm valid imports before mutation.
- Guided campaign setup reuses player and monster CSV validation/upsert rules.

Known maintenance issue:

- A workbook-import page class remains in source but is not registered in the
  current navigation. Documentation and product scope must decide whether to
  restore it, remove dead UI code, or formally keep workbook import limited to
  seeding/internal workflows.

Manual acceptance still required for the full CSV and data-safety matrix.

### 5.14 Data Workflow and safety

**Status:** Implemented; automated coverage exists; manual acceptance remains
partial.

Implemented:

- Database backup.
- Restore with safety backup.
- Reset to empty schema.
- Reset and reseed.
- Automatic backups before destructive Fantasy Grounds clear/reprocess actions.
- Local runtime databases, logs, portraits, backups, and exports under the
  application data directory.

Remaining acceptance:

- Manually open and verify created backups.
- Verify restore/reset/reseed on representative user data.
- Confirm interrupted operations recover safely.

### 5.15 Error Logs and Help

**Status:** Complete for current documented workflows.

Implemented:

- In-app error-log display and refresh.
- Packaged Markdown Help with internal heading navigation.
- Workflow guidance for campaigns, local combat, Fantasy Grounds, character
  imports, data safety, and troubleshooting.

Known maintenance issue:

- Help and several milestone documents still contain older extension-version or
  schema statements. Documentation synchronization is required after the three
  Test6 defects are fixed.

### 5.16 Fantasy Grounds synchronization

**Status:** Broad one-way integration implemented; not release-clear because
FG-EFFECT-002 remains open after fresh live verification.

Supported boundary:

- Fantasy Grounds Unity, host/GM, `5E` ruleset.
- Campaign-scoped file handoff.
- Snapshot schema/contract v1.
- Fantasy Grounds remains authoritative.
- No Lectern-to-Fantasy Grounds writes.

Implemented:

- Imported characters and current/older 5E armor-class paths.
- Equipped weapon and armor inventory recovery.
- Loaded class, subclass, species/race, feat, background, and reference records.
- Prepared encounters without flooding Lectern with module reference battles.
- Explicit durable live sessions:
  `/lectern-start`, `/lectern-end`, and `/lectern-reset confirm`.
- Persistent event journal and final roster.
- Automatic and manual imports.
- Idempotent sequence/event handling and enrichment of existing event IDs.
- Stale-record tracking and collision-safe external links.
- Authoritative attacks and saves.
- Mixed damage components and named contributors.
- Resistance/reduction, vulnerability, temporary-HP absorption, actual HP loss,
  and overkill kept separate.
- Dice-based and fixed healing attribution, including Lay on Hands.
- Effect addition and removal lifecycle events.
- Safe clear and historical reprocessing with backup.

Latest Test6 passes:

- Hunter's Mark source, target, helper, mixed damage, contributor, and both
  removal events.
- Effect removal can be exported silently even when Fantasy Grounds adds no chat
  message.
- Bardic Inspiration actor and target.
- Innate Sorcery identity.
- Self-target attack/damage capture.

Release-blocking defects:

#### FG-EFFECT-001 — Generic originating action for Armor of Shadows

**Status:** Automated-complete on July 28, 2026; fresh live acceptance failed
and is superseded by FG-EFFECT-002.

Test6 sequence 8 originally recorded:

- actor: Warlock1;
- target: Warlock1;
- effect: `AC: 3`;
- `action_name`: `Effect`;
- `originating_action`: `Effect`;
- source attribution: active self.

Fantasy Grounds applies the Combat Tracker effect while its previous post-roll
handler runs. Lectern Sync previously queued the originating action only after
that handler returned, which was too late for the effect-add hook. It now queues
the authoritative action and power-node identity before delegating. The
live-shaped fixture therefore imports `Armor of Shadows` as the originating
action while keeping `AC: 3` as the mechanical effect. A matching generic
effect with no authoritative action metadata remains generic.

No spell or ability name is inferred from `AC: 3`, and snapshot contract v1
already carries the required fields. Historical Test6 data remains unchanged
because its raw event lacks the provenance. However, the fresh isolated Test7
Armor session still exported the action as generic `Effect`, proving this
callback-order fixture did not reproduce the actual named-power announcement
path. See
[`FG-EFFECT-001`](contracts/completed/fg-effect-001-armor-of-shadows-provenance.md).

#### FG-EFFECT-002 — Live named-power announcement not correlated

**Status:** Active; automated correction and packaging complete on July 28,
2026, with fresh installed live acceptance pending.

In the isolated `Test7 Armor` session, Fantasy Grounds displayed Warlock1 using
Armor of Shadows immediately before applying `AC: 3; [D: 8 hours]` to
Warlock1. Lectern imported the correct actor, target, mechanical effect, and
duration, but both the action and originating action remained generic
`Effect`. Combat Narrative could therefore describe stronger protection but
could not authoritatively name Armor of Shadows.

Inspection of the installed 5E and CoreRPG rule sources confirmed the live path:
`PowerManager.performAction` calls `ActionEffect.getRoll` directly for effect
powers, and that effect-roll path does not invoke the
`onActionPostGetRoll/effect` hook used by FG-EFFECT-001.

The repository correction wraps the authoritative 5E power-action entry point
and captures the named power before Fantasy Grounds applies the effect.
Correlation is bounded by actor, known self-target, action and power paths,
mechanical effect text, event sequence, and time. It does not infer a name from
`AC: 3`, duration, class, spell list, or D&D rules. The focused live-path
regression and all sixteen repository regression scripts pass. A fresh
owner-coordinated Fantasy Grounds confirmation against the newly packaged
extension is still required. See
[`FG-EFFECT-002`](contracts/active/fg-effect-002-live-power-provenance.md) and
the
[`Test7 Armor evidence`](evidence/fantasy-grounds/fg-effect-002-test7-armor.md).

#### FG-CONC-001 — Concentration uses the active attacker

**Status:** Corrected, automated-verified, and live-verified on July 28, 2026.

The live-shaped regression reproduces Test6: Bandit damages Ranger1 and the
subsequent concentration roll has no resolvable database node. Lectern Sync now
resolves the roll's creature from the database node first, then from the recent
authoritative applied-damage target. If neither is available, actor and target
remain unresolved instead of inheriting the active attacker. A DC and
success/failure are preserved only when Fantasy Grounds reports them
explicitly. Import and narrative regressions confirm that Ranger1, not Bandit,
is credited in the corrected sequence.

Historical Test6 data is not rewritten because the stored raw event already
contains the wrong actor. Test7 live evidence imported Ranger1 as actor and
target with the authoritative total; Fantasy Grounds did not report a DC or
success/failure, so Lectern correctly left those fields unresolved. See
[`FG-CONC-001`](contracts/completed/fg-conc-001-concentration-attribution.md).

#### FG-LINK-001 — Roster-only prepared/live association

**Status:** Corrected, automated-verified, and live-verified on July 28, 2026.

The matcher now requires compatible normalized encounter names before roster
overlap can select an unambiguous prepared counterpart. Encounter-name
normalization preserves meaningful numbers. A same-sequence import reconciles
an existing stale association without changing imported events. After
installation and import, Test6 displayed as `Test6 · Live combat` without a
Test5 association and retained its journal.

Completed contract:
[`FG-LINK-001`](contracts/completed/fg-link-001-prepared-live-matching.md).

Live-testing decision:

- Limited Test7 verification resumed on July 28, 2026.
- Further live action must be tied to an explicitly executed contract and
  coordinated with the owner.
- FG-EFFECT-002 requires one fresh live confirmation after its automated
  correction passes.

Reference:
[`FANTASY_GROUNDS_RUN_TOGETHER.md`](FANTASY_GROUNDS_RUN_TOGETHER.md).

### 5.17 Two-way Fantasy Grounds integration

**Status:** Proposed; not implemented or approved for production.

Feasibility:

- Technically possible through a separate command/acknowledgement handoff and
  GM-approved extension writes.
- High risk because it changes ownership, conflict, recovery, and compatibility
  boundaries.

Required decisions before implementation:

1. The first exact record type and field allowlist.
2. Source of truth for every writable field.
3. Conflict behavior for simultaneous changes.
4. GM preview/confirmation requirements.
5. Idempotency and stale-value handling.
6. Acknowledgements and audit records.
7. Backup/recovery behavior.
8. Supported Fantasy Grounds/5E versions.

Guardrails:

- Do not begin with HP, initiative, effects, targeting, turn order, record
  deletion, or other live Combat Tracker mutation.
- Do not edit Fantasy Grounds `db.xml` directly.
- Keep the current one-way snapshot import working when write-back is disabled.

### 5.18 Packaging and installer

**Status:** Complete and recently verified.

Implemented:

- PyInstaller build at `dist/Lectern/Lectern.exe`.
- Packaged Lectern Sync extension at
  `dist/Lectern/FantasyGrounds/LecternSync.ext`.
- Inno Setup installer at `release/Lectern_v3_0_0_Setup.exe`.
- Installer prompt for the user's Fantasy Grounds `extensions` directory.
- Desktop and Start Menu shortcuts.

Repository convention:

- `dist` and ordinary generated release output are ignored.
- The current installer executable is already tracked and is intentionally
  replaced and committed when the owner explicitly requests an installer push.
- Do not assume that building an application also builds the installer; both
  `build/Build.ps1` and Inno Setup compilation are required.

Open maintenance question:

- Reconcile [`RELEASE_MANIFEST.md`](../RELEASE_MANIFEST.md), which says compiled
  outputs are excluded, with the established practice of tracking the current
  installer.

## 6. Current verification state

All sixteen automated regression scripts passed on July 28, 2026 after the
FG-EFFECT-002 source correction. The suite includes a dedicated live-path
provenance regression in addition to the prior fifteen checks:

- adaptive layout;
- campaign dashboard statistics;
- combat-log UI;
- Combat Narrative;
- Encounter Builder;
- Fantasy Grounds damage contributors;
- Fantasy Grounds effect lifecycle;
- Fantasy Grounds live effect provenance;
- Fantasy Grounds healing attribution;
- Fantasy Grounds historical reprocessing;
- Fantasy Grounds authoritative saves;
- Fantasy Grounds synchronization;
- Help content/navigation;
- installer configuration;
- portrait workflow;
- seeded-database smoke test.

The current installer was built and verified with narrative library content
version `2026.07.28.1` and Lectern Sync 1.4.12. The packaged application
started successfully in an isolated offscreen check.

The original automated tests did not catch the three live Test6 defects because:

- effect provenance assertions validated intended source structure but not the
  Fantasy Grounds ordering where the feature announcement follows application;
  FG-EFFECT-001 added a regression, but Test7 Armor proved it still does not
  reproduce the live named-power path;
- the concentration fixture supplied the correct actor rather than exercising
  the live database-node fallback; this gap is now covered by FG-CONC-001;
- prepared/live tests did not cover a differently named session with a uniquely
  overlapping roster. This gap is now covered by FG-LINK-001.

Automation is green for the actual 5E power-action capture path. Test7 live
verification passed FG-LINK-001 and FG-CONC-001 and supplied the failing
evidence for FG-EFFECT-002. A new package and owner-coordinated live session are
still required to clear its final acceptance criterion.

## 7. Release blockers and prioritized backlog

### Priority 0 — Release blockers

1. Install the current package and start one isolated owner-coordinated
   session.
2. Apply Armor of Shadows, import the session, and confirm the Action column and
   Combat Narrative name the power while retaining the mechanical effect.
3. Close FG-EFFECT-002 only after that live evidence passes.

### Priority 1 — Product completion

1. Complete unchecked manual acceptance in
   [`VERIFICATION_REPORT.md`](VERIFICATION_REPORT.md).
2. Synchronize stale schema, extension, suite-count, and artifact statements
   across README, Help, milestone documents, and the verification report.
3. Decide Combat Narrative persistence, editing, source links, and export.
4. Complete the PDF/portrait source sample matrix.
5. Resolve the workbook-import product boundary.

### Priority 2 — 3.1 design decisions

1. Approve the 3.1 release boundary.
2. Complete Fantasy Grounds write-back allowlist and ownership rules.
3. Define write-back conflicts, acknowledgements, and recovery.
4. Decide whether representative third-party PDFs may be retained privately.
5. Decide direct CRUD scope for monsters and reference libraries.

## 8. Durable product decisions

These decisions remain binding until the product owner changes them:

1. Fantasy Grounds is the source of truth for imported campaign and combat data.
2. Current integration is one-way and read-only from Lectern.
3. Combat Narrative is fully offline and uses the internal versioned library.
4. Narrative facts must preserve authoritative actor, action, target, sequence,
   damage type, and outcome.
5. Narrative must not invent spells, abilities, conditions, equipment,
   injuries, deaths, motives, or events.
6. Mechanical quantities do not appear in narrative prose, except numbered
   round headings and digits that are part of names.
7. Missing provenance remains unknown; reprocessing cannot invent it.
8. Generated narrative never modifies the structured combat log.
9. Live Combat Tracker HP, initiative, effects, targeting, and turn order remain
   Fantasy Grounds-owned unless a separately approved future milestone changes
   that boundary.
10. Live Fantasy Grounds testing is owner-coordinated and contract-scoped.

## 9. Data ownership matrix

| Data | Owner | Lectern behavior |
|---|---|---|
| Local campaigns, parties, encounters, and local logs | Lectern/user | Editable through local workflows |
| Imported Fantasy Grounds records | Fantasy Grounds | Read-only synchronized copies |
| Imported Fantasy Grounds combat events | Fantasy Grounds | Immutable raw evidence; normalized rows may be reprocessed |
| Normalized event interpretation | Lectern-derived | Regenerable from raw evidence |
| Combat Narrative | Lectern-derived | Regenerable and currently not user-persisted |
| Portrait selection and managed thumbnail | User/Lectern | User may accept, replace, or clear |
| Bundled narrative phrase library | Lectern application | Versioned with source and installer |
| Future write-back commands | Undecided | Not implemented |

## 10. Privacy and security

- Lectern operates locally and does not send campaign, combat, PDF, portrait, or
  narrative data to an AI service.
- Runtime databases, backups, logs, exports, portraits, and Fantasy Grounds
  handoff snapshots must not be committed.
- Live acceptance should use disposable campaigns and sanitized/open content.
- Commercial module text must not be added to fixtures or documentation.
- Future write-back requires explicit GM confirmation, validation, audit, and
  recovery before any campaign mutation.

## 11. Agent contract

Every future agent working on Lectern must:

1. Read this document, [`CHANGELOG.md`](../CHANGELOG.md), the
   [`agent directory`](agents/README.md), the assigned domain definition, and
   the active contract before acting.
2. Check Git status and preserve unrelated user changes.
3. Verify current implementation rather than trusting stale version statements.
4. Keep authoritative and derived data clearly separated.
5. Never invent missing combat provenance or use D&D knowledge to overwrite
   contradictory source evidence.
6. Add a regression that reproduces each corrected bug.
7. Run the focused test and the full sixteen-script suite for changes affecting
   shared combat, data, or UI behavior.
8. Do not bump product version, database schema, snapshot contract, or extension
   version unless the requested change requires it and the owner approves it.
9. Do not build, commit, merge, push, alter installed Fantasy Grounds files, or
   create a release artifact unless the owner requests that action.
10. When asked for an installer, build the application and extension first,
    compile the Inno Setup installer, validate its bundled versions, and report
    the installer hash.
11. Run live Fantasy Grounds testing only when an active contract requires it
    and the owner coordinates the session.
12. Update this PRD whenever a feature changes status, a bug is discovered or
    resolved, or a durable product decision is made.

The seven durable ownership domains are defined in
[`docs/agents/`](agents/README.md). A domain definition describes long-lived
responsibility; it does not itself authorize a particular change.

## 12. Agent contract structure

Every implementation task should use
[`agent-contract-template.md`](contracts/templates/agent-contract-template.md)
and be stored according to its lifecycle:

- [`contracts/active/`](contracts/active/) for ready or in-progress work;
- [`contracts/completed/`](contracts/completed/) after acceptance is recorded;
- [`contracts/templates/`](contracts/templates/) for reusable contract forms.

A contract assigns one owning domain and may name consulting domains. It must
state the objective, authoritative evidence, scope, exclusions, invariants,
acceptance criteria, verification, deliverables, and explicit delivery
authority. Build, commit, merge, push, installer, release, external-write, and
live-testing permissions are never implied.

The initial contract sequence covered the three Test6 blockers:

- [`FG-CONC-001`](contracts/completed/fg-conc-001-concentration-attribution.md)
  is implemented, automated-verified, and live-verified.
- [`FG-EFFECT-001`](contracts/completed/fg-effect-001-armor-of-shadows-provenance.md)
  is implemented and automated-verified, but its live conclusion is superseded
  by [`FG-EFFECT-002`](contracts/active/fg-effect-002-live-power-provenance.md).
- [`FG-LINK-001`](contracts/completed/fg-link-001-prepared-live-matching.md) is
  implemented, automated-verified, and live-verified.

`FG-EFFECT-002` is active. Its source correction, automated verification, and
[`REL-PACK-002`](contracts/completed/rel-pack-002-fg-effect-002.md) package are
complete, but installed live acceptance is pending.

Sanitized contract and release evidence belongs under
[`docs/evidence/`](evidence/README.md).

## 13. Supporting documents

- [`CHANGELOG.md`](../CHANGELOG.md) — implementation history
- [`LECTERN_3_1_DEVELOPMENT.md`](LECTERN_3_1_DEVELOPMENT.md) — 3.1 roadmap and
  decisions
- [`COMBAT_NARRATIVE_LIBRARY.md`](COMBAT_NARRATIVE_LIBRARY.md) — narrative
  ownership, constraints, and sample matrix
- [`FANTASY_GROUNDS_RUN_TOGETHER.md`](FANTASY_GROUNDS_RUN_TOGETHER.md) —
  installation and operating workflow
- [`FANTASY_GROUNDS_LIVE_ACCEPTANCE_3_0.md`](FANTASY_GROUNDS_LIVE_ACCEPTANCE_3_0.md)
  — earlier live acceptance and remediation
- [`MANUAL_CAMPAIGN_MILESTONES.md`](MANUAL_CAMPAIGN_MILESTONES.md) — local
  campaign milestones
- [`VERIFICATION_REPORT.md`](VERIFICATION_REPORT.md) — release acceptance
  checklist and evidence
- [`USER_HELP.md`](USER_HELP.md) — packaged user guidance
- [`DEVELOPMENT_WORKFLOW.md`](DEVELOPMENT_WORKFLOW.md) — development and build
  workflow
- [`agents/README.md`](agents/README.md) — durable product-domain ownership
- [`contracts/README.md`](contracts/README.md) — integration and agent contract
  lifecycle
- [`evidence/README.md`](evidence/README.md) — sanitized acceptance-evidence
  policy

## 14. Handoff summary

Lectern is a substantial working local-first campaign and combat application,
not a prototype. Local campaigns, persistent parties, guided setup, encounter
building, combat logging, campaign analytics, character PDF import, portraits,
CSV transfer, data safety, one-way Fantasy Grounds synchronization, and offline
Combat Narrative are implemented.

FG-LINK-001 and FG-CONC-001 are implemented, packaged, automated-verified, and
live-verified. FG-EFFECT-002 is corrected, packaged, and automated-verified
after Test7 Armor exposed the live-path gap; a fresh installed live confirmation
remains release-blocking. Broader 3.1
work—especially two-way Fantasy Grounds
integration—must remain a separate product-design decision rather than being
inferred from the existing one-way handoff.
