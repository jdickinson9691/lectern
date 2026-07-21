# Manual Campaign Experience Milestones

This record defines the work that improves campaigns managed directly in Lectern with player and monster data entered manually or imported from CSV. Fantasy Grounds campaigns remain source-owned and follow their existing synchronization workflow.

## Milestone 1 — Manual Campaign Foundation

Status: **Complete**

- Explicit local and Fantasy Grounds campaign ownership
- Local campaign editing, archiving, and restoration
- Persistent local campaign parties
- Campaign-scoped encounter creation and filtering
- One-step insertion of the saved party into an encounter

## Milestone 2 — Guided Local Campaign Setup

Status: **Complete and verified**

The Campaigns screen provides **Guided Local Setup...**, a four-step workflow that:

1. Creates a uniquely named local campaign.
2. Validates optional player and monster CSV files before changing data.
3. Blocks duplicate and error rows while showing new, modified, and unchanged totals.
4. Preselects player-CSV characters and allows existing players to be included in the persistent party.
5. Optionally creates a campaign-scoped opening encounter and adds the saved party.

Player and monster imports reuse Lectern's established CSV preview and upsert rules. Imported players can join the new campaign; imported monsters remain reusable global library records. The workflow does not modify Fantasy Grounds campaigns or synchronized records.

### Acceptance criteria

- Setup can be completed without CSV files by selecting existing players.
- Valid player and monster CSV files import from the same guided workflow.
- Duplicate or invalid rows prevent all guided setup actions.
- An existing campaign name cannot be reused accidentally.
- Imported player characters are checked by default for the campaign party.
- The optional opening encounter belongs to the new campaign and already contains the saved party.
- The established Fantasy Grounds synchronization regression remains green.
