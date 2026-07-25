from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from tempfile import mkdtemp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

temp_dir = Path(mkdtemp(prefix="lectern_fg_contributors_"))
os.environ["LECTERN_DATA_DIR"] = str(temp_dir / "user-data")

from app.database.schema import connect, initialize_database
from app.integrations.fantasy_grounds import FantasyGroundsSyncService, validate_snapshot


def contributor_event(
    sequence: int,
    actor: str,
    action: str,
    contributor: str,
    damage_type: str,
    dice: str,
) -> dict:
    amount = 6 + sequence
    return {
        "event_id": f"test-contributor-session:{sequence}",
        "sequence": sequence,
        "timestamp": f"2026-07-25T22:00:0{sequence}Z",
        "round": 4,
        "encounter_source_key": "test-contributor-session",
        "type": "damage",
        "actor": {"source_key": f"5E:character:{actor.casefold()}", "name": actor},
        "target": {"source_key": f"5E:ct:kobold-{sequence}", "name": f"Kobold {sequence}"},
        "amount": amount,
        "description": "Damage resolved by Fantasy Grounds",
        "metadata": {
            "action_name": action,
            "roll_total": amount,
            "current_hp": 0,
            "maximum_hp": amount,
            "damage_types": [damage_type],
            "damage_components": [
                {"types": [damage_type], "rolled": amount, "applied": amount},
            ],
            "damage_contributors": [{
                "name": contributor,
                "effect_key": f"combattracker.list.{actor.casefold()}.effects.id-{sequence:05d}",
                "effect_label": f"{contributor}; DMG: {dice} {damage_type}",
                "effect_component": f"DMG: {dice} {damage_type}",
                "dice": dice,
                "modifier": 0,
                "damage_types": [damage_type],
            }],
            "damage_resolution": "authoritative",
            "attribution": "matched_recent_roll",
        },
    }


try:
    payload = json.loads(
        (ROOT / "docs" / "contracts" / "fantasy_grounds_snapshot_v1.example.json").read_text(
            encoding="utf-8"
        )
    )
    payload["source"]["extension_version"] = "1.4.8"
    payload["sequence"] = 5
    payload["combat"].update(
        {
            "session_key": "test-contributor-session",
            "session_name": "Named Damage Contributor Test",
            "session_state": "closed",
            "outcome": "victory",
            "completed_at": "2026-07-25T22:00:05Z",
        }
    )
    payload["events"] = [
        contributor_event(1, "Rogue1", "Shortbow", "Sneak Attack", "piercing", "1d6"),
        contributor_event(2, "Ranger1", "Longbow", "Hunter's Mark", "force", "1d6"),
        contributor_event(3, "Paladin1", "Longsword", "Divine Smite", "radiant", "2d8"),
    ]

    validate_snapshot(payload)
    db = temp_dir / "lectern.db"
    initialize_database(db)
    snapshot = temp_dir / "snapshot.json"
    snapshot.write_text(json.dumps(payload), encoding="utf-8")
    result = FantasyGroundsSyncService(db).import_snapshot(snapshot)
    assert result.applied and result.counts["events"] == 3

    with connect(db) as conn:
        rows = conn.execute(
            """
            SELECT tl.actor,tl.details,ee.raw_json
            FROM external_events ee
            JOIN turn_log tl ON tl.id=ee.turn_log_id
            ORDER BY ee.id
            """
        ).fetchall()
        assert [row["actor"] for row in rows] == ["Rogue1", "Ranger1", "Paladin1"]
        assert "Shortbow with Sneak Attack" in rows[0]["details"]
        assert "Longbow with Hunter's Mark" in rows[1]["details"]
        assert "Longsword with Divine Smite" in rows[2]["details"]
        contributors = [
            json.loads(row["raw_json"])["metadata"]["damage_contributors"][0]["name"]
            for row in rows
        ]
        assert contributors == ["Sneak Attack", "Hunter's Mark", "Divine Smite"]

    print("Fantasy Grounds named damage contributor test passed.")
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)
