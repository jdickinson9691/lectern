# Player approval and export

The Ashen publication layer is schema v11 on Lectern 3.0. Its original standalone migration called this schema v7. Publication is explicit. An entity is included only when its visibility is `player` and its status is `approved`. A knowledge field also needs audience `player` and status `approved`. A relationship needs visibility `player`, status `approved`, and two included endpoints. Existing relationships migrate as drafts.

The **Ashen Player Export** screen changes visibility, approves or returns records to draft, and saves player JSON or a Fantasy Grounds Story module after preview. The **Stories** screen also offers a reviewed module export. The existing CSV actions remain full GM data transfers and should not be used as player handouts.

The JSON contains only `id`, `kind`, `name`, approved player `knowledge`, and approved player-visible `relationships`. It is built from the canonical campaign tables. Legacy Lectern rows, GM/internal knowledge, import sources, and audit details are never read into the projection.

`CampaignRepository` provides the authoring and approval API for knowledge and relationships. `set_knowledge` and `add_relationship` create drafts; `approve_player_knowledge` and `approve_player_relationship` release them. `revoke_entity`, `revoke_player_knowledge`, and `revoke_player_relationship` withdraw approval. Name, visibility, knowledge-content, or relationship changes revoke the affected approval through database triggers, including edits made outside the repository API.

`PlayerExportService.export_json(path)` writes a consistent snapshot to a temporary file and replaces the chosen destination only after the JSON is complete. This is a player data export foundation; Fantasy Grounds module packaging is a separate adapter step.
