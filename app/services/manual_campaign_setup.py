from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..database.repositories import Repository
from ..importers.csv_transfer import CsvTransferService


@dataclass(frozen=True)
class ManualCampaignSetupResult:
    campaign_id: int
    encounter_id: int | None
    players_imported: int
    monsters_imported: int
    party_members: int


class ManualCampaignSetupService:
    """Coordinate the safe, guided setup of a local campaign."""

    def __init__(self, db_path: Path):
        self.repo = Repository(db_path)
        self.csv = CsvTransferService(db_path)

    def preview(self, players_csv: Path | None = None, monsters_csv: Path | None = None) -> dict[str, list[dict]]:
        previews: dict[str, list[dict]] = {}
        if players_csv:
            previews["players"] = self.csv.preview_table("players", players_csv)
        if monsters_csv:
            previews["monsters"] = self.csv.preview_table("monsters", monsters_csv)
        return previews

    @staticmethod
    def blocking_rows(previews: dict[str, list[dict]]) -> list[dict]:
        return [
            {"table": table, **row}
            for table, rows in previews.items()
            for row in rows
            if row["status"] in {"Error", "Duplicate"}
        ]

    def party_choices(self, previews: dict[str, list[dict]]) -> list[tuple[str, bool]]:
        incoming = {
            str(row["key"])
            for row in previews.get("players", [])
            if row["status"] not in {"Error", "Duplicate"} and str(row["key"]).strip()
        }
        names = {str(row["name"]) for row in self.repo.list_players()} | incoming
        return [(name, name in incoming) for name in sorted(names, key=str.casefold)]

    def execute(
        self,
        name: str,
        description: str = "",
        players_csv: Path | None = None,
        monsters_csv: Path | None = None,
        party_names: list[str] | None = None,
        encounter_name: str = "",
    ) -> ManualCampaignSetupResult:
        campaign_name = name.strip()
        if not campaign_name:
            raise ValueError("Campaign name is required.")
        if self.repo.get_campaign_by_name(campaign_name):
            raise ValueError("A campaign with this name already exists.")

        previews = self.preview(players_csv, monsters_csv)
        blocking = self.blocking_rows(previews)
        if blocking:
            first = blocking[0]
            raise ValueError(
                f"{first['table'].title()} CSV row {first['row_number']} is {first['status']}: {first['message']}"
            )

        players_imported = self.csv.import_table("players", players_csv) if players_csv else 0
        monsters_imported = self.csv.import_table("monsters", monsters_csv) if monsters_csv else 0
        campaign_id = self.repo.create_campaign(campaign_name, description.strip())

        requested_names = {value.strip().casefold() for value in (party_names or []) if value.strip()}
        player_ids = [
            int(player["id"])
            for player in self.repo.list_players()
            if str(player["name"]).casefold() in requested_names
        ]
        self.repo.set_campaign_party(campaign_id, player_ids)

        encounter_id = None
        if encounter_name.strip():
            encounter_id = self.repo.create_encounter(encounter_name.strip(), campaign_id)
            self.repo.add_campaign_party_to_encounter(campaign_id, encounter_id)

        return ManualCampaignSetupResult(
            campaign_id=campaign_id,
            encounter_id=encounter_id,
            players_imported=players_imported,
            monsters_imported=monsters_imported,
            party_members=len(player_ids),
        )
