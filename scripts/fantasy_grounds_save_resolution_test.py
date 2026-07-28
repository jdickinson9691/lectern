from __future__ import annotations

import json
import os
import shutil
import sys
import copy
from pathlib import Path
from tempfile import mkdtemp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

temp_dir = Path(mkdtemp(prefix="lectern_fg_saves_"))
os.environ["LECTERN_DATA_DIR"] = str(temp_dir / "user-data")

from app.database.schema import connect, initialize_database
from app.integrations.fantasy_grounds import (
    FantasyGroundsSyncError,
    FantasyGroundsSyncService,
    validate_snapshot,
)


def save_event(sequence: int, target_key: str, target_name: str, total: int, result: str) -> dict:
    raw_roll = total + 1
    return {
        "event_id": f"test-save-session:{sequence}",
        "sequence": sequence,
        "timestamp": f"2026-07-25T20:00:0{sequence}Z",
        "round": 2,
        "encounter_source_key": "test-save-session",
        "type": "save",
        "actor": {"source_key": "5E:character:bard1", "name": "Bard1"},
        "target": {"source_key": target_key, "name": target_name},
        "amount": None,
        "description": "[SAVE VS] Bane [CHA DC 10] [MAGIC]",
        "metadata": {
            "action_name": "Bane",
            "originating_action": "Bane",
            "roll_type": "save",
            "save_ability": "charisma",
            "save_dc": 10,
            "save_total": total,
            "raw_roll": raw_roll,
            "modifier": -1,
            "roll_total": total,
            "natural_roll": raw_roll,
            "result": result,
            "save_resolution": result.casefold(),
            "authoritative_result": True,
        },
    }


def concentration_event(
    sequence: int, total: int, result: str | None, dc: int | None
) -> dict:
    metadata = {
        "action_name": "Concentration",
        "originating_action": "Concentration",
        "roll_type": "concentration",
        "raw_roll": total,
        "modifier": 0,
        "roll_total": total,
        "actor_attribution": "recent_damage_target",
    }
    if dc is not None:
        metadata["concentration_dc"] = dc
    if result is not None:
        metadata["result"] = result
        metadata["concentration_resolution"] = result.casefold()
    return {
        "event_id": f"test-save-session:{sequence}",
        "sequence": sequence,
        "timestamp": f"2026-07-25T20:00:0{sequence}Z",
        "round": 2,
        "encounter_source_key": "test-save-session",
        "type": "action",
        "actor": {"source_key": "5E:character:ranger1", "name": "Ranger1"},
        "target": {"source_key": "5E:character:ranger1", "name": "Ranger1"},
        "amount": None,
        "description": "[CONCENTRATION]",
        "metadata": metadata,
    }


try:
    payload = json.loads(
        (ROOT / "docs" / "contracts" / "fantasy_grounds_snapshot_v1.example.json").read_text(
            encoding="utf-8"
        )
    )
    payload["source"]["extension_version"] = "1.4.9"
    payload["sequence"] = 5
    payload["combat"].update(
        {
            "session_key": "test-save-session",
            "session_name": "Authoritative Save Test",
            "session_state": "closed",
            "outcome": "unresolved",
            "completed_at": "2026-07-25T20:00:05Z",
        }
    )
    payload["events"] = [
        save_event(1, "5E:ct:kobold-1", "Kobold Warrior 1", 8, "Failure"),
        save_event(2, "5E:ct:kobold-2", "Kobold Warrior 2", 13, "Success"),
        {
            "event_id": "test-save-session:3",
            "sequence": 3,
            "timestamp": "2026-07-25T20:00:03Z",
            "round": 2,
            "encounter_source_key": "test-save-session",
            "type": "damage",
            "actor": {"source_key": "5E:ct:bandit", "name": "Bandit"},
            "target": {"source_key": "5E:character:ranger1", "name": "Ranger1"},
            "amount": 3,
            "description": "Damage resolved by Fantasy Grounds",
            "metadata": {
                "action_name": "Scimitar",
                "roll_total": 3,
                "damage_types": ["slashing"],
                "current_hp": 9,
                "maximum_hp": 12,
            },
        },
        concentration_event(4, 13, "Success", 10),
        concentration_event(5, 8, None, None),
    ]

    validate_snapshot(payload)
    invalid = copy.deepcopy(payload)
    invalid["events"][0]["metadata"]["save_dc"] = None
    try:
        validate_snapshot(invalid)
        raise AssertionError("An authoritative save without its actual DC was accepted")
    except FantasyGroundsSyncError as exc:
        assert "save_dc must be a number" in str(exc)
    db = temp_dir / "lectern.db"
    initialize_database(db)
    snapshot = temp_dir / "snapshot.json"
    snapshot.write_text(json.dumps(payload), encoding="utf-8")
    result = FantasyGroundsSyncService(db).import_snapshot(snapshot)
    assert result.applied and result.counts["events"] == 5

    with connect(db) as conn:
        rows = conn.execute(
            """
            SELECT tl.actor,tl.details,tl.result_code,ee.raw_json
            FROM external_events ee
            JOIN turn_log tl ON tl.id=ee.turn_log_id
            ORDER BY ee.id
            """
        ).fetchall()
        assert [row["actor"] for row in rows[:2]] == ["Bard1", "Bard1"]
        assert [row["result_code"] for row in rows[:2]] == ["save_failure", "save_success"]
        assert "Kobold Warrior 1 | Against DC 10 | Bane | Charisma save: Failure" in rows[0]["details"]
        assert "Kobold Warrior 2 | Against DC 10 | Bane | Charisma save: Success" in rows[1]["details"]
        concentration_rows = [row for row in rows if "Concentration" in row["details"]]
        assert len(concentration_rows) == 2
        assert [row["actor"] for row in concentration_rows] == ["Ranger1", "Ranger1"]
        assert concentration_rows[0]["result_code"] == "concentration_success"
        assert "Ranger1 | Against DC 10 | Concentration | Success" in concentration_rows[0]["details"]
        assert not concentration_rows[1]["result_code"]
        assert "Ranger1 | Concentration DC not reported | Concentration | Outcome not reported" in concentration_rows[1]["details"]
        raw_events = [json.loads(row["raw_json"]) for row in rows[:2]]
        assert [event["target"]["name"] for event in raw_events] == [
            "Kobold Warrior 1",
            "Kobold Warrior 2",
        ]
        assert all(event["metadata"]["originating_action"] == "Bane" for event in raw_events)
        assert all(event["metadata"]["save_dc"] == 10 for event in raw_events)
        assert [event["metadata"]["save_total"] for event in raw_events] == [8, 13]

    print("Fantasy Grounds authoritative save test passed.")
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)
