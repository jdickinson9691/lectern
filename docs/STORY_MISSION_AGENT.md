# Story and Mission agent

The agent drafts campaign Stories (`DOC-COMP-...`) and Missions (`MIS-COMP-...`) in Lectern's canonical database. It uses the existing Story creation workflow and approval gates. It never approves a draft or exports a module.

The **Story & Mission Drafts** screen displays only approved player-visible facts from selected source entities. Creating a draft requires at least one such source, stores a provenance link, and separates player text from GM notes. A Mission may link to an existing Story. Both new records start in draft status and remain absent from player exports.

Use **Canon Review (GM)** for any new or conflicting fact suggested while writing. `StoryMissionAgent.submit_canon_fact(...)` puts the suggestion in the durable review queue without altering approved canon. The GM can accept it as a draft or reject it. Existing Story approval remains on the Stories screen.

The **Missions** screen reviews and edits Mission title, player briefing, and private GM notes. Approval requires nonempty player briefing. A title or briefing edit returns an approved Mission to draft; changing only GM notes preserves player approval. The screen can preview approved player content and export the same Fantasy Grounds module used by Stories. Returning a Mission to draft removes it from the player projection immediately. Approved Missions currently appear as records in the adapter's Ashen Company Story group; a distinct Fantasy Grounds Quest mapping is future adapter work.

The agent does not generate narrative text on its own. The author supplies the player text and private notes using the approved context shown on screen; human review remains responsible for claims in that prose.
