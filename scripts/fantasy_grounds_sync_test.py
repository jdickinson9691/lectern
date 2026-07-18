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

temp_dir = Path(mkdtemp(prefix="lectern_fg_sync_"))
os.environ["LECTERN_DATA_DIR"] = str(temp_dir / "user-data")

from app.database.repositories import Repository
from app.database.schema import connect, initialize_database
from app.integrations.fantasy_grounds import FantasyGroundsSyncError, FantasyGroundsSyncService, validate_snapshot


try:
    db = temp_dir / "lectern.db"
    initialize_database(db)
    repo = Repository(db)
    repo.upsert_player({"name": "Fantasy Grounds Test Hero", "class_name": "Local Class", "level": 1, "max_hp": 5})
    fixture_path = ROOT / "docs" / "contracts" / "fantasy_grounds_snapshot_v1.example.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    validate_snapshot(payload)
    legacy_payload = copy.deepcopy(payload)
    legacy_payload.pop("events")
    for field in ("session_key", "outcome", "completed_at"):
        legacy_payload["combat"].pop(field)
    validate_snapshot(legacy_payload)

    handoff = temp_dir / "campaign" / "lectern-sync"
    handoff.mkdir(parents=True)
    snapshot = handoff / "snapshot.json"
    snapshot.write_text(json.dumps(payload), encoding="utf-8")

    service = FantasyGroundsSyncService(db)
    configured = service.configure_folder(handoff)
    assert configured == handoff.resolve(), "Existing lectern-sync folder was not retained"
    result = service.import_configured_snapshot()
    assert result.applied and result.sequence == 1, "Initial snapshot was not applied"
    assert result.counts["classes"] == 1 and result.counts["subclasses"] == 1, "Catalog counts are incorrect"

    players = repo.list_players()
    assert len(players) == 2, "Fantasy Grounds character was not imported alongside the local character"
    assert next(row for row in players if row["name"] == "Fantasy Grounds Test Hero")["class_name"] == "Local Class", "Local same-name character was overwritten"
    player = next(row for row in players if row["class_name"] == "Test Fighter")
    assert player["name"] == "Fantasy Grounds Test Hero [Fantasy Grounds]", "Character collision-safe naming failed"
    assert player["level"] == 5 and player["current_hp"] == 37 and player["str_total"] == 16, "Character statistics mapping failed"
    assert "Test Fighter" in repo.list_rule_names_like("class") and "Test Champion" not in repo.list_rule_names_like("class"), "Class/subclass references were mixed"
    assert "Test Champion" in repo.list_rule_names_like("subclass"), "Subclass reference lookup failed"

    encounters = repo.list_encounters()
    assert len(encounters) == 2, "Prepared and live Fantasy Grounds encounters were not created"
    live = next(row for row in encounters if "Live Combat" in row["name"])
    assert repo.is_external_encounter(live["id"]), "Live encounter was not marked as externally owned"
    combatants = repo.list_combatants(live["id"])
    assert len(combatants) == 1 and combatants[0]["current_hp"] == 9, "Live combatant HP mapping failed"
    with connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM active_conditions").fetchone()[0] == 1, "Combat effects were not imported"
        assert conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0] == "7", "Schema version was not migrated"
        assert conn.execute("SELECT COUNT(*) FROM rules_reference WHERE category LIKE 'Fantasy Grounds %'").fetchone()[0] == 5, "Catalog references were not normalized"
        source = conn.execute("SELECT * FROM external_sources").fetchone()
        assert source["last_sequence"] == 1 and not source["last_error"], "Sync source state is incorrect"
        assert conn.execute("SELECT COUNT(*) FROM external_records WHERE is_stale=0").fetchone()[0] >= 8, "External provenance records are missing"
        assert conn.execute("SELECT COUNT(*) FROM external_events").fetchone()[0] == 2, "Combat events were not imported"
        logs = conn.execute("SELECT action_type,details FROM turn_log ORDER BY id").fetchall()
        assert [row["action_type"] for row in logs] == ["Attack", "Damage"], "Combat event types were not mapped"
        assert logs[1]["details"].startswith("Damage: 3;"), "Damage details are not dashboard-compatible"

    repeat = service.import_snapshot(snapshot)
    assert not repeat.applied and repeat.sequence == 1, "Repeated sequence should be ignored"
    with connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM turn_log").fetchone()[0] == 2, "Repeated snapshot duplicated turn log events"

    invalid = copy.deepcopy(payload)
    invalid["sequence"] = 2
    invalid["catalog"]["feats"][0]["source_key"] = invalid["catalog"]["classes"][0]["source_key"]
    invalid_path = handoff / "invalid.json"
    invalid_path.write_text(json.dumps(invalid), encoding="utf-8")
    try:
        service.import_snapshot(invalid_path)
        raise AssertionError("Duplicate source key was accepted")
    except FantasyGroundsSyncError:
        pass
    with connect(db) as conn:
        assert conn.execute("SELECT last_sequence FROM external_sources").fetchone()[0] == 1, "Invalid snapshot changed sync state"

    updated = copy.deepcopy(payload)
    updated["sequence"] = 2
    updated["combat"]["combatants"][0]["hit_points"]["current"] = 6
    updated["events"].append({
        "event_id": "test-session-001:3", "sequence": 3, "timestamp": "2026-07-17T20:00:05Z",
        "round": 1, "encounter_source_key": "test-session-001", "type": "healing",
        "actor": {"source_key": "5E:character:test-hero", "name": "Fantasy Grounds Test Hero"},
        "target": {"source_key": "5E:ct:id-00001", "name": "Test Creature"}, "amount": 2,
        "description": "Wounds decreased from 3 to 1", "metadata": {"previous_wounds": 3, "current_wounds": 1},
    })
    snapshot.write_text(json.dumps(updated), encoding="utf-8")
    update_result = service.import_configured_snapshot()
    assert update_result.applied and update_result.sequence == 2, "New sequence was not applied"
    live = next(row for row in repo.list_encounters() if "Live Combat" in row["name"])
    assert repo.list_combatants(live["id"])[0]["current_hp"] == 6, "Combat update was not applied"
    assert len(repo.list_players()) == 2 and len(repo.list_encounters()) == 2, "Update created duplicate entities"
    with connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM turn_log").fetchone()[0] == 3, "Only the new event should be appended"
        assert conn.execute("SELECT details FROM turn_log WHERE action_type='Healing'").fetchone()[0].startswith("Healing: 2;"), "Healing was not mapped"

    stale = copy.deepcopy(updated)
    stale["sequence"] = 3
    stale["catalog"]["feats"] = []
    stale["combat"].update({"active": False, "outcome": "victory", "completed_at": "2026-07-17T20:01:00Z"})
    stale["events"].append({
        "event_id": "test-session-001:4", "sequence": 4, "timestamp": "2026-07-17T20:01:00Z",
        "round": 1, "encounter_source_key": "test-session-001", "type": "outcome",
        "actor": None, "target": None, "amount": None, "description": "Encounter outcome: victory",
        "metadata": {"outcome": "victory"},
    })
    snapshot.write_text(json.dumps(stale), encoding="utf-8")
    service.import_configured_snapshot()
    with connect(db) as conn:
        feat = conn.execute("SELECT is_stale FROM external_records WHERE record_type='feat'").fetchone()
        assert feat and feat[0] == 1, "Missing source record was not marked stale"
        assert conn.execute("SELECT COUNT(*) FROM rules_reference WHERE name='Test Alert'").fetchone()[0] == 1, "Stale reference was deleted"
        encounter = conn.execute("SELECT status,outcome,completed_at FROM encounters WHERE name LIKE '%Live Combat%'").fetchone()
        assert tuple(encounter) == ("completed", "victory", "2026-07-17T20:01:00Z"), "Encounter outcome was not applied"
        assert conn.execute("SELECT COUNT(*) FROM turn_log WHERE action_type='Outcome'").fetchone()[0] == 1, "Outcome event was not logged"

    new_session = copy.deepcopy(stale)
    new_session["sequence"] = 4
    new_session["combat"].update({"active": True, "session_key": "test-session-002", "outcome": None, "completed_at": None})
    new_session["events"].append({
        "event_id": "test-session-002:5", "sequence": 5, "timestamp": "2026-07-17T21:00:00Z",
        "round": 1, "encounter_source_key": "test-session-002", "type": "action",
        "actor": {"source_key": "5E:character:test-hero", "name": "Fantasy Grounds Test Hero"},
        "target": None, "amount": None, "description": "New combat session action", "metadata": {},
    })
    snapshot.write_text(json.dumps(new_session), encoding="utf-8")
    service.import_configured_snapshot()
    with connect(db) as conn:
        encounter_ids = {row[0] for row in conn.execute("SELECT DISTINCT encounter_id FROM external_events").fetchall()}
        assert len(encounter_ids) == 2, "Separate Fantasy Grounds combat sessions were merged"

    duplicate_event = copy.deepcopy(new_session)
    duplicate_event["sequence"] = 5
    duplicate_event["events"].append(copy.deepcopy(duplicate_event["events"][0]))
    duplicate_path = handoff / "duplicate-event.json"
    duplicate_path.write_text(json.dumps(duplicate_event), encoding="utf-8")
    try:
        service.import_snapshot(duplicate_path)
        raise AssertionError("Duplicate event ID was accepted")
    except FantasyGroundsSyncError:
        pass

    print("Fantasy Grounds sync test passed.")
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)
