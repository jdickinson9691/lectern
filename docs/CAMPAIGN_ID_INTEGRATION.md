# Campaign IDs and Lectern links

On Lectern 3.0 these historical Ashen schema-v5/v6 capabilities are installed together as optional schema v11. The dedicated Ashen launcher opts into the campaign root; generic Lectern databases are not seeded with Ashen records or links.

In the dedicated Ashen database, permanent IDs are assigned as campaign records are written. Existing players and encounters receive IDs when an existing database opts into Ashen. Monsters receive campaign IDs when their `source` is `manual` or `campaign`; imported SRD/reference monsters, spells, equipment, and rules remain generic.

| Lectern record | Canonical ID |
|---|---|
| Player | `PC-COMP-0001` |
| Encounter | `ENC-COMP-0001` |
| Manual or campaign monster | `CRE-COMP-0001` |

Numbers are tied to Lectern row IDs where available and may have gaps. IDs remain fixed when names change. Duplicate players get new IDs. Deleting a linked Lectern row archives its canonical entity, records an audit event, and removes the now-invalid link.

Player and monster CSV exports include an `entity_id` column. On import, a supplied ID updates its linked row, including a name change. A missing ID uses Lectern's existing name-based upsert and creates an ID for new campaign records. Unknown IDs abort the import transaction. CSV imports record provenance in `entity_sources` and retain Lectern's `import_history`.

The link repository checks the target table, entity kind, and row existence. Schema v6 adds database triggers to enforce those checks for direct SQL writes and to remove links when legacy rows are deleted. Migration validates pre-existing v5 links before backfilling; an invalid link stops the upgrade without changing the schema version.

Other campaign concepts such as factions, locations, and missions do not yet have Lectern tables or UI write paths. They can use `CampaignRepository.create_entity` now; UI and import adapters for those types remain future work.
