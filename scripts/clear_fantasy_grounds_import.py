from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.integrations.fantasy_grounds import FantasyGroundsSyncService
from app.paths import database_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview or clear one Fantasy Grounds import from Lectern.")
    parser.add_argument("--source-id", type=int, help="External source ID to preview or clear")
    parser.add_argument("--confirm", help="Exact campaign name required to perform the clear")
    parser.add_argument("--pause-auto-import", action="store_true", help="Persistently pause automatic snapshot import")
    args = parser.parse_args()

    service = FantasyGroundsSyncService(database_path())
    if args.pause_auto_import:
        service.set_automatic_import_enabled(False)
        print("Automatic Fantasy Grounds snapshot import is paused.")
        if args.source_id is None:
            return 0
    if args.source_id is None:
        rows = service.list_sources()
        if not rows:
            print("No Fantasy Grounds imports found.")
            return 0
        for row in rows:
            print(f"{row['id']}: {row['campaign_name']} (sequence {row['last_sequence']})")
        return 0

    preview = service.preview_clear_imported_data(args.source_id)
    print(
        f"{preview.campaign_name}: {preview.campaigns} campaign(s), {preview.encounters} encounter(s), "
        f"{preview.combatants} combatant(s), {preview.combat_log_rows} combat log row(s), "
        f"{preview.players} imported player(s), {preview.external_records} sync record(s)."
    )
    if args.confirm is None:
        print(f"Preview only. To clear, add --confirm \"{preview.campaign_name}\".")
        return 0
    if args.confirm != preview.campaign_name:
        parser.error("--confirm must exactly match the imported campaign name")
    result = service.clear_imported_data(args.source_id)
    print(f"Cleared imported data. Backup: {result.backup_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
