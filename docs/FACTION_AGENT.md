# Faction agent

`FactionAgent` uses the existing campaign entity, knowledge, source, audit, and approval tables. It creates permanent `FAC-COMP-...` IDs. The **Campaign Factions** screen provides sourced drafts, separate player overview and private GM notes, public-edit reapproval, and export preview.

Faction links are constrained to campaign NPCs (`has_member`), Locations (`active_in`), and Missions (`involved_in`). New links start as drafts. A GM can keep a link private or mark it player-visible; player approval requires the Faction and linked record to be approved and player-visible. Revoking a link or an endpoint removes it from the player projection. The existing Fantasy Grounds adapter exports approved Factions with other approved records in the Ashen Company Story group.

The agent can submit suggested facts to **Canon Review (GM)**. It does not decide canon or generate prose automatically.
