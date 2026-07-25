from __future__ import annotations

import copy
import json
import os
import shutil
import sys
from pathlib import Path
from tempfile import mkdtemp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

temp_dir = Path(mkdtemp(prefix="lectern_fg_healing_"))
os.environ["LECTERN_DATA_DIR"] = str(temp_dir / "user-data")

from app.database.schema import connect, initialize_database
from app.integrations.fantasy_grounds import (
    FantasyGroundsSyncError,
    FantasyGroundsSyncService,
    validate_snapshot,
)


def healing_event(
    sequence: int,
    actor_name: str,
    action_name: str,
    amount: int,
    healing_kind: str,
) -> dict:
    return {
        "event_id": f"test-healing-session:{sequence}",
        "sequence": sequence,
        "timestamp": f"2026-07-25T21:00:0{sequence}Z",
        "round": 3,
        "encounter_source_key": "test-healing-session",
        "type": "healing",
        "actor": {"source_key": f"5E:character:{actor_name.casefold()}", "name": actor_name},
        "target": {"source_key": "5E:ct:fighter1", "name": "Fighter1"},
        "amount": amount,
        "description": f"Wounds decreased after {action_name}",
        "metadata": {
            "action_name": action_name,
            "originating_action": action_name,
            "roll_total": amount,
            "healing_kind": healing_kind,
            "healing_resolution": "authoritative",
            "attribution": "authoritative_health_apply",
            "authoritative_result": True,
            "previous_wounds": amount,
            "current_wounds": 0,
            "current_hp": 10,
            "maximum_hp": 10,
        },
    }


try:
    payload = json.loads(
        (ROOT / "docs" / "contracts" / "fantasy_grounds_snapshot_v1.example.json").read_text(
            encoding="utf-8"
        )
    )
    payload["source"]["extension_version"] = "1.4.9"
    payload["sequence"] = 4
    payload["combat"].update(
        {
            "session_key": "test-healing-session",
            "session_name": "Authoritative Healing Test",
            "session_state": "closed",
            "outcome": "unresolved",
            "completed_at": "2026-07-25T21:00:04Z",
        }
    )
    payload["events"] = [
        healing_event(1, "Paladin1", "Lay on Hands", 5, "fixed"),
        healing_event(2, "Cleric1", "Cure Wounds", 8, "dice"),
    ]

    validate_snapshot(payload)
    invalid = copy.deepcopy(payload)
    invalid["events"][0]["actor"] = None
    try:
        validate_snapshot(invalid)
        raise AssertionError("Authoritative healing without its actor was accepted")
    except FantasyGroundsSyncError as exc:
        assert "must identify the healer" in str(exc)

    db = temp_dir / "lectern.db"
    initialize_database(db)
    snapshot = temp_dir / "snapshot.json"
    snapshot.write_text(json.dumps(payload), encoding="utf-8")
    result = FantasyGroundsSyncService(db).import_snapshot(snapshot)
    assert result.applied and result.counts["events"] == 2

    with connect(db) as conn:
        rows = conn.execute(
            """
            SELECT tl.actor,tl.action_type,tl.details,tl.amount,ee.raw_json
            FROM external_events ee
            JOIN turn_log tl ON tl.id=ee.turn_log_id
            ORDER BY ee.id
            """
        ).fetchall()
        assert [row["actor"] for row in rows] == ["Paladin1", "Cleric1"]
        assert [row["action_type"] for row in rows] == ["Healing", "Healing"]
        assert [row["amount"] for row in rows] == [5, 8]
        assert "Fighter1 | Target HP 10/10 | Lay on Hands | 5 healing applied" in rows[0]["details"]
        assert "Fighter1 | Target HP 10/10 | Cure Wounds | 8 healing applied" in rows[1]["details"]
        raw_events = [json.loads(row["raw_json"]) for row in rows]
        assert raw_events[0]["metadata"]["healing_kind"] == "fixed"
        assert raw_events[0]["metadata"]["originating_action"] == "Lay on Hands"
        assert raw_events[1]["metadata"]["healing_kind"] == "dice"
        assert raw_events[1]["metadata"]["originating_action"] == "Cure Wounds"

    print("Fantasy Grounds healing attribution test passed.")
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)
