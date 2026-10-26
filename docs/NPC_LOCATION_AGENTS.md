# NPC and Location agents

`NPCAgent` and `LocationAgent` share one campaign-entity workflow. They write permanent `NPC-COMP-...` and `LOC-COMP-...` IDs, respectively. They do not create parallel NPC or Location databases and do not alter Lectern's creature library.

The **Campaign NPCs** and **Campaign Locations** screens show approved player-facing source context for new drafts. A new record requires at least one approved campaign source, records provenance and an audit event, and separates player text from private GM notes. NPC player text uses the `profile` field; Location player text uses `description`. Both start as drafts.

The GM can edit, approve, or return either record to draft. Approval requires nonempty player text. Changes to name or player text remove prior approval; GM-note-only changes leave it intact. The player projection and Fantasy Grounds module include only approved player text. The screens provide an export preview before module creation. Agents submit new or conflicting facts to **Canon Review (GM)** through the existing queue.

These agents organize and gate authored content; they do not automatically generate prose or decide campaign canon. Approved NPC and Location records currently appear in the Fantasy Grounds Ashen Company Story group. Dedicated Fantasy Grounds record types remain adapter work.
