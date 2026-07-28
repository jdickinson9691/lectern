# Contract: <short task name>

Contract ID: `<DOMAIN-NNN>`
Status: Draft
Owning domain: `<one domain from docs/agents/README.md>`
Assigned agent: `<domain agent or unassigned>`
Consulting domains: `<none or named domains>`
Execution order: `<independent, sequence position, or prerequisite>`
Created: `<YYYY-MM-DD>`
Last updated: `<YYYY-MM-DD>`

## Objective

State one observable outcome. Avoid combining unrelated defects or feature
requests in a single contract.

## Current evidence

- Link sanitized screenshots, logs, fixtures, issue identifiers, or PRD sections.
- Separate observed facts from hypotheses.
- Record the current repository, application, schema, extension, and contract
  versions when they affect reproduction.

## Authoritative behavior

Describe what Lectern must preserve or report. Identify the authoritative source
for actor, action, target, sequence, damage type, outcome, and other relevant data.

## Scope

- List behavior that may be changed.
- List expected implementation areas.
- State whether schema or contract evolution is permitted.

## Out of scope

- List adjacent behavior that must not be redesigned.
- List deferred work and unsupported assumptions.

## Invariants

- List existing behavior that must not regress.
- Include product-wide invariants from `docs/lectern-prd.md`.

## Acceptance criteria

1. Write measurable pass/fail behavior.
2. Require a regression reproducing the original defect.
3. Require preservation of relevant existing behavior.

## Required verification

- Focused test:
- Related regression tests:
- Full suite:
- Manual check:
- Live Fantasy Grounds test:

Use `Not authorized`, `Not required`, or `Deferred` where appropriate.

## Deliverables

- Implementation:
- Regression:
- Documentation:
- Build or artifact:

## Delivery authority

| Action | Authorized? |
|---|---|
| Edit repository files | Yes/No |
| Modify database schema | Yes/No |
| Modify snapshot contract | Yes/No |
| Modify extension source | Yes/No |
| Install extension | Yes/No |
| Run live Fantasy Grounds test | Yes/No |
| Build application or extension | Yes/No |
| Build installer | Yes/No |
| Commit | Yes/No |
| Merge | Yes/No |
| Push | Yes/No |

## Dependencies and coordination

Record prerequisite contracts, consulting domains, and file-overlap risks.

## Completion record

Complete this section before moving the contract to `completed`.

- Result:
- Verification evidence:
- Commit(s):
- Artifact(s) and hash:
- Remaining risks:
- PRD/Changelog updates:
