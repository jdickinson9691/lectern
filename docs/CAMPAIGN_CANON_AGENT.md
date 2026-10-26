# Campaign Canon agent, first implementation

The Campaign Canon agent is a sourced drafting and review service over Lectern's existing campaign database. It does not create a second canon store. `CampaignCanonAgent.dossier(entity_id)` reads an entity's facts, relationships, sources, and audit trail for GM review. `propose_fact(...)` writes one audience-specific draft fact with a required source reference and an audit event in one transaction.

The agent refuses to overwrite a different approved fact. A person must resolve that conflict, make any deliberate edit, and use Lectern's existing approval operations. Draft proposals never enter the player export or Fantasy Grounds module. The agent can read GM and internal material, so its dossier must only be presented in a GM context.

## GM review

Schema v8 adds a private `canon_proposals` queue. The **Canon Review (GM)** screen can submit sourced proposals, compare them beside the current fact, and accept or reject them with an optional audit note. A proposal stores the fact as it stood when submitted. If canon changes before acceptance, the screen refuses the stale acceptance so the GM can review it again. Rejection leaves canon untouched. Acceptance writes the proposed fact as a draft and records its source; player export remains gated by the existing approval workflow.

Current boundary: the agent works with existing campaign entities and one fact per audience/key. It does not infer facts from documents, adjudicate contradictions across different keys or entities, approve content, or create new entities. A future content agent can submit through the same review queue.
