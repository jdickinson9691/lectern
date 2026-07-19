from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from tempfile import mkdtemp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

temp_dir = Path(mkdtemp(prefix="lectern_fg_reprocess_"))
os.environ["LECTERN_DATA_DIR"] = str(temp_dir / "user-data")

from app.database.schema import connect, initialize_database
from app.integrations.fantasy_grounds import FantasyGroundsSyncError, FantasyGroundsSyncService


def event(event_id: str, event_type: str, **changes):
    value = {
        "event_id": event_id,
        "sequence": int(event_id.rsplit(":", 1)[-1]),
        "timestamp": f"2026-07-18T20:00:0{int(event_id.rsplit(':', 1)[-1])}Z",
        "round": 3,
        "encounter_source_key": "history-001",
        "type": event_type,
        "actor": {"source_key": "5E:character:hero", "name": "Historical Hero"},
        "target": {"source_key": "goblin", "name": "Historical Goblin"},
        "amount": None,
        "description": "",
        "metadata": {},
    }
    value.update(changes)
    return value


try:
    db = temp_dir / "lectern.db"
    initialize_database(db)
    events = [
        event(
            "history:1", "attack", description="Longsword attack",
            metadata={"action_name": "Longsword", "raw_roll": 14, "modifier": 5,
                      "roll_total": 19, "target_ac": 16, "result": "Hit"},
        ),
        event(
            "history:2", "damage", amount=4, description="Wounds increased",
            metadata={"action_name": "Longsword", "roll_total": 9, "adjustment": -5,
                      "current_hp": 3, "maximum_hp": 7, "attribution": "matched_recent_roll"},
        ),
        event(
            "history:3", "healing", amount=2, description="Wounds decreased",
            metadata={"action_name": "Cure Wounds", "current_hp": 5, "maximum_hp": 7},
        ),
        event(
            "history:4", "attack", description="Critical attack",
            metadata={"action_name": "Longsword", "raw_roll": 20, "modifier": 5,
                      "roll_total": 25, "target_ac": 30, "natural_roll": 20,
                      "result": "Critical Hit", "authoritative_result": True},
        ),
        event(
            "history:5", "attack", description="Automatic miss",
            metadata={"action_name": "Longsword", "raw_roll": 1, "modifier": 14,
                      "roll_total": 15, "target_ac": 10, "natural_roll": 1,
                      "result": "Automatic Miss", "authoritative_result": True},
        ),
        event(
            "history:6", "damage", actor=None, amount=1, description="Manual wounds change",
            metadata={"attribution": "manual_or_unattributed", "current_hp": 4, "maximum_hp": 7},
        ),
        event(
            "history:7", "attack", actor=None, target=None, description="", metadata={},
        ),
        event(
            "history:8", "action", actor=None, target=None, description="",
            metadata={"action_name": "", "raw_roll": 14, "modifier": 0, "roll_total": 14, "roll_type": "dice"},
        ),
    ]
    with connect(db) as conn:
        campaign_id = conn.execute("INSERT INTO campaigns(name) VALUES('History')").lastrowid
        encounter_id = conn.execute(
            "INSERT INTO encounters(name,campaign_id,status,round) VALUES('Old FG Combat',?,'completed',3)",
            (campaign_id,),
        ).lastrowid
        source_id = conn.execute(
            "INSERT INTO external_sources(provider,campaign_key,campaign_name,ruleset) VALUES('fantasy_grounds','history','History','5E')"
        ).lastrowid
        other_source_id = conn.execute(
            "INSERT INTO external_sources(provider,campaign_key,campaign_name,ruleset) VALUES('other_vtt','history','Other VTT','5E')"
        ).lastrowid
        local_id = conn.execute(
            "INSERT INTO turn_log(encounter_id,round,actor,action_type,details,created_at) VALUES(?,2,'Local Hero','Action','Local bytes','2026-01-01')",
            (encounter_id,),
        ).lastrowid
        unlinked_id = conn.execute(
            "INSERT INTO turn_log(encounter_id,round,actor,action_type,details,created_at) VALUES(?,2,'Unlinked Hero','Action','Unlinked bytes','2026-01-02')",
            (encounter_id,),
        ).lastrowid
        for item in events:
            log_id = conn.execute(
                "INSERT INTO turn_log(encounter_id,round,actor,action_type,details,created_at) VALUES(?,3,'Legacy','Action','Legacy details',?)",
                (encounter_id, item["timestamp"]),
            ).lastrowid
            conn.execute(
                "INSERT INTO external_events(source_id,event_key,encounter_id,turn_log_id,event_type,occurred_at,raw_json,imported_sequence) VALUES(?,?,?,?,?,?,?,1)",
                (source_id, item["event_id"], encounter_id, log_id, item["type"], item["timestamp"], json.dumps(item)),
            )
        invalid_log_id = conn.execute(
            "INSERT INTO turn_log(encounter_id,round,actor,action_type,details) VALUES(?,3,'Invalid legacy','Action','Invalid legacy bytes')",
            (encounter_id,),
        ).lastrowid
        conn.execute(
            "INSERT INTO external_events(source_id,event_key,encounter_id,turn_log_id,event_type,occurred_at,raw_json,imported_sequence) VALUES(?,?,?,?,?,?,?,1)",
            (source_id, "history:invalid", encounter_id, invalid_log_id, "attack", "2026-07-18T20:00:08Z", "{invalid"),
        )
        other_log_id = conn.execute(
            "INSERT INTO turn_log(encounter_id,round,actor,action_type,details) VALUES(?,3,'Other VTT','Action','Other VTT bytes')",
            (encounter_id,),
        ).lastrowid
        conn.execute(
            "INSERT INTO external_events(source_id,event_key,encounter_id,turn_log_id,event_type,occurred_at,raw_json,imported_sequence) VALUES(?,?,?,?,?,?,?,1)",
            (other_source_id, "other:1", encounter_id, other_log_id, "attack", "2026-07-18T20:00:09Z", json.dumps(events[0])),
        )
        raw_before = [row[0] for row in conn.execute("SELECT raw_json FROM external_events WHERE source_id=? ORDER BY id", (source_id,))]
        untouched_before = {
            row["id"]: bytes(str(tuple(row)).encode())
            for row in conn.execute("SELECT * FROM turn_log WHERE id IN (?,?,?) ORDER BY id", (local_id, unlinked_id, other_log_id))
        }

    service = FantasyGroundsSyncService(db)
    preview = service.preview_log_reprocessing()
    assert tuple(preview.__dict__.values()) == (1, 9, 8, 3), "Reprocessing preview counts are incorrect"
    result = service.reprocess_imported_logs()
    assert result.updated == 6 and result.unchanged == 0 and result.incomplete == 2 and result.failed == 1
    assert result.backup_path.exists(), "A safety backup was not created"
    with connect(db) as conn:
        rows = conn.execute(
            "SELECT ee.event_key,tl.* FROM external_events ee JOIN turn_log tl ON tl.id=ee.turn_log_id "
            "WHERE ee.source_id=? AND json_valid(ee.raw_json) ORDER BY ee.id",
            (source_id,),
        ).fetchall()
        assert len(rows) == 8 and conn.execute("SELECT COUNT(*) FROM external_events WHERE source_id=?", (source_id,)).fetchone()[0] == 9
        assert "19 (dice 14; modifiers +5)" in rows[0]["details"] and "Against AC 16" in rows[0]["details"]
        assert "4 damage applied from 9 rolled (reduced by 5)" in rows[1]["details"]
        assert rows[2]["details"] == "2 | Historical Goblin | Target HP 5/7 | Cure Wounds | 2 healing applied"
        assert "Critical Hit (25 vs AC 30)" in rows[3]["details"]
        assert "Automatic Miss (15 vs AC 10)" in rows[4]["details"]
        assert rows[0]["actor_side"] == "party" and rows[0]["actor_source_key"] == "5E:character:hero", "Party attribution was not restored"
        assert rows[1]["amount"] == 4 and rows[2]["amount"] == 2, "Applied damage or healing was not normalized"
        assert rows[3]["result_code"] == "critical_hit" and rows[4]["result_code"] == "critical_miss", "Critical results were not normalized"
        assert rows[5]["actor"] == "Manual / Unattributed"
        assert "not reported" in rows[6]["details"].lower()
        assert rows[7]["details"] == "14 (dice 14; modifiers +0) | Target not reported | Defense not reported | Action not reported | Result not reported", "Incomplete raw dice roll was hidden"
        assert all(row["round"] == 3 and row["created_at"] == events[index]["timestamp"] for index, row in enumerate(rows))
        untouched_after = {
            row["id"]: bytes(str(tuple(row)).encode())
            for row in conn.execute("SELECT * FROM turn_log WHERE id IN (?,?,?) ORDER BY id", (local_id, unlinked_id, other_log_id))
        }
        assert untouched_after == untouched_before, "Local or non-Fantasy-Grounds logs were changed"
        assert [row[0] for row in conn.execute("SELECT raw_json FROM external_events WHERE source_id=? ORDER BY id", (source_id,))] == raw_before, "Raw event evidence was modified"

    repeat = service.reprocess_imported_logs()
    assert repeat.updated == 0 and repeat.unchanged == 6 and repeat.incomplete == 2 and repeat.failed == 1
    with connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM turn_log").fetchone()[0] == 12, "Reprocessing created duplicate log rows"

        rollback_first = event("rollback:8", "effect", description="First transactional update")
        rollback_second = event("rollback:9", "effect", description="Trigger rollback")
        first_log = conn.execute(
            "INSERT INTO turn_log(encounter_id,round,actor,action_type,details) VALUES(?,1,'Legacy','Action','First legacy')",
            (encounter_id,),
        ).lastrowid
        second_log = conn.execute(
            "INSERT INTO turn_log(encounter_id,round,actor,action_type,details) VALUES(?,1,'Legacy','Action','Second legacy')",
            (encounter_id,),
        ).lastrowid
        for item, log_id in ((rollback_first, first_log), (rollback_second, second_log)):
            conn.execute(
                "INSERT INTO external_events(source_id,event_key,encounter_id,turn_log_id,event_type,occurred_at,raw_json,imported_sequence) VALUES(?,?,?,?,?,?,?,1)",
                (source_id, item["event_id"], encounter_id, log_id, item["type"], item["timestamp"], json.dumps(item)),
            )
        conn.execute(
            f"CREATE TRIGGER force_reprocess_failure BEFORE UPDATE ON turn_log "
            f"WHEN OLD.id={int(second_log)} BEGIN SELECT RAISE(ABORT, 'forced failure'); END"
        )
    try:
        service.reprocess_imported_logs()
        raise AssertionError("A processing failure was not reported")
    except FantasyGroundsSyncError:
        pass
    with connect(db) as conn:
        assert conn.execute("SELECT details FROM turn_log WHERE id=?", (first_log,)).fetchone()[0] == "First legacy", "Failure did not roll back earlier updates"
        assert conn.execute("SELECT details FROM turn_log WHERE id=?", (second_log,)).fetchone()[0] == "Second legacy", "Failed row was modified"

    print("Fantasy Grounds historical reprocessing test passed.")
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)
