# Story and Mission agent

The agent drafts campaign Stories (`DOC-COMP-...`) and Missions (`MIS-COMP-...`) in Lectern's canonical database. It uses the existing Story creation workflow and approval gates. It never approves a draft or exports a module.

The **Story & Mission Drafts** screen displays only approved player-visible facts from selected source entities. Creating a draft requires at least one such source, stores a provenance link, and separates player text from GM notes. A Mission may link to an existing Story. Both new records start in draft status and remain absent from player exports.

Use **Canon Review (GM)** for any new or conflicting fact suggested while writing. `StoryMissionAgent.submit_canon_fact(...)` puts the suggestion in the durable review queue without altering approved canon. The GM can accept it as a draft or reject it. Existing Story approval remains on the Stories screen.

The **Missions** screen separates the player briefing from a GM Mission Plan. The plan records a maximum **sum** of participating character levels, the GM's Easy/Normal/Difficult/Risky/Deadly assessment, a catalog-linked monster roster with quantities and CRs, private mission lore and loot, and future lore hooks that may link to another mission. Approved Fiction Agent background and detail facts appear as read-only context in the plan. Players choose their party makeup; the GM can record that choice in Lectern, which rejects a roster over the level cap. This is not an automatic 5E encounter-balance calculation, because the final party composition and catalog XP may be unknown.

New approval requires a nonempty player briefing, level cap, difficulty, lore, and loot entry (enter "None" when appropriate). A title, briefing, cap, difficulty, or monster-roster edit returns an approved Mission to draft. Changing private lore, loot, hooks, or GM notes preserves player approval. The approved player projection includes only the briefing, level cap, and difficulty. Existing approved missions survive schema v13 unchanged and must be completed by the GM before their next approval. The screen can preview approved player content and export the same Fantasy Grounds module used by Stories. Approved Missions currently appear in the adapter's Ashen Company Story group; a distinct Fantasy Grounds Quest mapping is future adapter work.

The agent does not generate narrative text on its own. The author supplies the player text and private notes using the approved context shown on screen; human review remains responsible for claims in that prose.
