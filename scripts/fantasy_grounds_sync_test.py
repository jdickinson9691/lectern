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
        assert conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0] == "6", "Schema version was not migrated"
        assert conn.execute("SELECT COUNT(*) FROM rules_reference WHERE category LIKE 'Fantasy Grounds %'").fetchone()[0] == 5, "Catalog references were not normalized"
        source = conn.execute("SELECT * FROM external_sources").fetchone()
        assert source["last_sequence"] == 1 and not source["last_error"], "Sync source state is incorrect"
        assert conn.execute("SELECT COUNT(*) FROM external_records WHERE is_stale=0").fetchone()[0] >= 8, "External provenance records are missing"

    repeat = service.import_snapshot(snapshot)
    assert not repeat.applied and repeat.sequence == 1, "Repeated sequence should be ignored"

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
    snapshot.write_text(json.dumps(updated), encoding="utf-8")
    update_result = service.import_configured_snapshot()
    assert update_result.applied and update_result.sequence == 2, "New sequence was not applied"
    live = next(row for row in repo.list_encounters() if "Live Combat" in row["name"])
    assert repo.list_combatants(live["id"])[0]["current_hp"] == 6, "Combat update was not applied"
    assert len(repo.list_players()) == 2 and len(repo.list_encounters()) == 2, "Update created duplicate entities"

    stale = copy.deepcopy(updated)
    stale["sequence"] = 3
    stale["catalog"]["feats"] = []
    snapshot.write_text(json.dumps(stale), encoding="utf-8")
    service.import_configured_snapshot()
    with connect(db) as conn:
        feat = conn.execute("SELECT is_stale FROM external_records WHERE record_type='feat'").fetchone()
        assert feat and feat[0] == 1, "Missing source record was not marked stale"
        assert conn.execute("SELECT COUNT(*) FROM rules_reference WHERE name='Test Alert'").fetchone()[0] == 1, "Stale reference was deleted"

    print("Fantasy Grounds sync test passed.")
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)
