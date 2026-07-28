# Lectern Agent Directory

This directory defines durable ownership domains for agents working on Lectern.
The domains are organized around shared product behavior and data boundaries,
not individual screens.

Every agent must begin with:

1. [`../lectern-prd.md`](../lectern-prd.md), the current product authority.
2. [`../../CHANGELOG.md`](../../CHANGELOG.md), the implementation history.
3. The relevant domain definition below.
4. The active task contract in [`../contracts/active/`](../contracts/active/).

## Domain ownership

| Domain | Definition | Primary feature areas |
|---|---|---|
| Campaign Management | [`campaign-management-agent.md`](campaign-management-agent.md) | Dashboard, Campaigns, parties, campaign analytics |
| Encounter and Local Combat | [`encounter-combat-agent.md`](encounter-combat-agent.md) | Encounter Builder, Combat Dashboard, structured combat log |
| Combat Narrative | [`combat-narrative-agent.md`](combat-narrative-agent.md) | Narrative normalization, beats, language, regression fixtures |
| Fantasy Grounds Integration | [`fantasy-grounds-agent.md`](fantasy-grounds-agent.md) | Lectern Sync, import, reprocessing, FG event provenance |
| Characters and Parties | [`characters-parties-agent.md`](characters-parties-agent.md) | Players, PDF import, portraits, party membership |
| Game Content Libraries | [`content-libraries-agent.md`](content-libraries-agent.md) | Monsters, equipment, magic items, spells, CSV content transfer |
| Data, Reliability, and Release | [`data-release-agent.md`](data-release-agent.md) | Schema, workflow safety, logs, Help, tests, installer |

## Operating model

- One domain agent owns the final implementation for a contract.
- A contract may name consulting domains, but consulting agents do not make
  overlapping edits unless the contract explicitly divides the files.
- Cross-domain behavior is coordinated through authoritative data contracts,
  regression fixtures, and acceptance criteria.
- Page ownership does not override data ownership. For example, Fantasy Grounds
  event attribution belongs to the Fantasy Grounds domain even when the defect
  first appears on the Combat Narrative page.
- Agents do not gain build, commit, merge, push, release, live-testing, or
  external-write authority merely by being assigned a domain.
- Completed contracts move from `active` to `completed` only after their
  acceptance criteria and required documentation updates are satisfied.

## Shared rules

All domain agents must:

- preserve unrelated user work and inspect repository status before editing;
- prefer authoritative structured evidence over inferred intent;
- add a regression for every corrected defect;
- keep derived views from mutating authoritative records;
- update the PRD when feature status, known defects, or durable decisions change;
- avoid committing runtime data, logs, portraits, PDFs, snapshots, backups, or
  commercial module content;
- honor the current pause on further live Fantasy Grounds testing;
- stop and request direction when a task requires authority outside its contract.

## Contract lifecycle

1. Copy [`../contracts/templates/agent-contract-template.md`](../contracts/templates/agent-contract-template.md).
2. Assign one owning domain and list any consulting domains.
3. Record authoritative evidence and measurable acceptance criteria.
4. Place the contract in [`../contracts/active/`](../contracts/active/).
5. Implement and verify only the authorized scope.
6. Record results, commit identifiers when applicable, and remaining risks.
7. Move the contract to [`../contracts/completed/`](../contracts/completed/).
