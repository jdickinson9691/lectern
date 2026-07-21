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
from app.integrations.fantasy_grounds import (
    FantasyGroundsSyncError,
    FantasyGroundsSyncService,
    format_event_log,
    load_snapshot,
    validate_snapshot,
)


try:
    extension_source = (
        ROOT / "integrations" / "fantasy_grounds" / "extension" / "LecternSync" / "scripts" / "lectern_sync.lua"
    ).read_text(encoding="utf-8")
    extension_manifest = (
        ROOT / "integrations" / "fantasy_grounds" / "extension" / "LecternSync" / "extension.xml"
    ).read_text(encoding="utf-8")
    assert 'local EXTENSION_VERSION = "1.4.2"' in extension_source and "<version>1.4.2</version>" in extension_manifest, "Extension version metadata is inconsistent"
    assert 'if vValue == JSON_EMPTY_OBJECT then return "{}" end' in extension_source, "Empty event metadata is not encoded as a JSON object"
    assert 'Comm.registerSlashHandler("lectern-start", startEncounter' in extension_source, "Explicit encounter start command is missing"
    assert 'Comm.registerSlashHandler("lectern-end", endEncounter' in extension_source, "Explicit encounter end command is missing"
    assert 'Comm.registerSlashHandler("lectern-reset", resetEncounterJournal' in extension_source, "Safe encounter reset command is missing"
    assert 'sPersistedEventsJSON = ""' in extension_source and '"confirm"' in extension_source, "Encounter reset does not clear the journal safely"
    assert 'session-state.txt' in extension_source and 'loadSessionState()' in extension_source, "Durable session reload support is missing"
    assert 'extractArrayContents(sSnapshot or "", "events")' in extension_source and 'sMergedEvents = sPersistedEventsJSON' in extension_source, "Accumulated events are not retained across reloads"
    assert 'archiveCurrentJournal()' in extension_source and 'for nIndex = 1, #aEventJournal do' in extension_source, "Mutable current-session events or prior sessions are not retained safely"
    assert 'lifecycle = "encounter_start"' in extension_source and 'lifecycle = "encounter_end"' in extension_source, "Encounter lifecycle events are missing"
    assert 'nodeNumber(node, "defenses.ac.total"' in extension_source, "2024 Fantasy Grounds character AC path is missing"
    assert 'if sCharacterName == "" then return nil end' in extension_source, "Unnamed Fantasy Grounds characters are not filtered"
    assert 'not moduleName(node)' in extension_source, "Module reference battles are not filtered from campaign encounters"
    assert 'DB.addHandler("combattracker.list.*.wounds", "onUpdate"' in extension_source, "Combat Tracker wound changes are not observed"
    assert 'targetsForCombatant(tActorCombatant, tCombat)' in extension_source, "Selected Combat Tracker targets are not captured"
    assert 'tRollContextsByTarget[tTarget.source_key] = tCopy' in extension_source, "Multi-target roll context is not retained per target"
    assert 'combatantForNode(node, tCombat) or combatantByKey' in extension_source, "Roll actors do not use source or active Combat Tracker context"
    assert 'actor = tActor, target = tTarget, action_name = sActionName' in extension_source, "Roll context is not retained for applied results"
    assert 's:gsub("[\\r\\n]+", " ")' in extension_source, "Roll cleanup must preserve the letter r"
    assert 'diceValue(draginfo, "getNumberData", 0)' in extension_source, "Fantasy Grounds entity and effect modifiers are not captured"
    assert 'nRawRoll + nModifier' in extension_source, "Net roll does not include Fantasy Grounds modifiers"
    assert 'GameManager.addEventFunction("onAttackPostResolve", authoritativeAttackResolved)' in extension_source, "Authoritative 5E attack outcomes are not captured"
    assert 'GameManager.addEventFunction("onDamagePostResolve", authoritativeDamageResolved)' in extension_source, "Authoritative 5E damage resolution is not captured"
    assert 'rRoll.tResults' in extension_source and 'damage_components = tComponents' in extension_source, "Component-aware damage types are not exported"
    assert 'natural_roll = nRawRoll' in extension_source and 'authoritative_result = true' in extension_source, "Natural attack roll and authoritative result metadata are missing"
    assert 'contextForAppliedChange(tTarget, "damage")' in extension_source, "Applied damage attribution is not target matched and time bounded"
    assert 'tEvent.actor = tActor' in extension_source and 'tMetadata.action_name = sActionName' in extension_source, "Authoritative enrichment does not repair attribution"

    immune = format_event_log({
        "type": "damage", "round": 1, "actor": None, "target": {"name": "Immune Target"},
        "amount": 0, "description": "Damage resolved", "metadata": {
            "roll_total": 0, "damage_types": ["fire"], "damage_components": [
                {"types": ["fire"], "rolled": 2, "applied": 0, "resisted": 2, "vulnerable": 0}
            ],
        },
    })
    assert "0 damage applied from 2 rolled (negated)" in immune.details, "Negated damage displayed as zero rolled"
    temporary_hp = format_event_log({
        "type": "damage", "round": 1, "actor": None, "target": {"name": "Ward Target"},
        "amount": 3, "description": "Damage resolved", "metadata": {
            "roll_total": 0, "damage_types": ["force"], "damage_components": [
                {"types": ["force"], "rolled": 3, "applied": 3, "resisted": 0, "vulnerable": 0}
            ],
        },
    })
    assert "3 damage applied from 3 rolled" in temporary_hp.details, "Temporary-HP damage displayed as zero rolled"
    overkill = format_event_log({
        "type": "damage", "round": 1, "actor": None, "target": {"name": "Low HP Target"},
        "amount": 7, "description": "Damage resolved", "metadata": {
            "roll_total": 6, "damage_types": ["fire", "slashing"], "damage_components": [
                {"types": ["fire"], "rolled": 3, "applied": 6, "resisted": 0, "vulnerable": 3},
                {"types": ["slashing"], "rolled": 3, "applied": 6, "resisted": 0, "vulnerable": 3},
            ],
        },
    })
    assert sum(component["applied"] for component in json.loads(overkill.damage_components_json)) == 7, "Overkill component totals exceed actual HP loss"

    db = temp_dir / "lectern.db"
    initialize_database(db)
    repo = Repository(db)
    repo.upsert_player({"name": "Fantasy Grounds Test Hero", "class_name": "Local Class", "level": 1, "max_hp": 5})
    fixture_path = ROOT / "docs" / "contracts" / "fantasy_grounds_snapshot_v1.example.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    complete_damage_event = copy.deepcopy(payload["events"][1])
    payload["events"][1]["actor"] = None
    payload["events"][1]["metadata"].pop("action_name")
    payload["events"][1]["metadata"].update({
        "roll_total": 0, "attribution": "manual_or_unattributed", "damage_types": [], "damage_components": [],
    })
    validate_snapshot(payload)
    legacy_payload = copy.deepcopy(payload)
    legacy_payload.pop("events")
    for field in ("session_key", "outcome", "completed_at"):
        legacy_payload["combat"].pop(field)
    validate_snapshot(legacy_payload)

    empty_metadata_payload = copy.deepcopy(payload)
    empty_metadata_payload["events"][0]["metadata"] = []
    empty_metadata_path = temp_dir / "snapshot-empty-metadata.json"
    empty_metadata_path.write_text(json.dumps(empty_metadata_payload), encoding="utf-8")
    normalized_payload = load_snapshot(empty_metadata_path)
    assert normalized_payload["events"][0]["metadata"] == {}, "Lectern Sync 1.4.0 empty metadata was not recovered"

    handoff = temp_dir / "campaign" / "lectern-sync"
    handoff.mkdir(parents=True)
    snapshot = handoff / "snapshot.json"
    snapshot.write_text(json.dumps(payload), encoding="utf-8-sig")

    service = FantasyGroundsSyncService(db)
    ambiguous_encounter = copy.deepcopy(payload["encounters"][0])
    ambiguous_encounter.update({"source_key": "5E:battle:ambiguous", "name": "Another Encounter"})
    assert service._match_prepared_encounter(
        [payload["encounters"][0], ambiguous_encounter], payload["combat"]
    ) is None, "Equally matching prepared encounters should not be guessed"
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
    assert player["level"] == 5 and player["armor_class"] == 17 and player["current_hp"] == 37 and player["str_total"] == 16, "Character statistics mapping failed"
    assert "Test Fighter" in repo.list_rule_names_like("class") and "Test Champion" not in repo.list_rule_names_like("class"), "Class/subclass references were mixed"
    assert "Test Champion" in repo.list_rule_names_like("subclass"), "Subclass reference lookup failed"

    encounters = repo.list_encounters()
    assert len(encounters) == 2, "Prepared and live Fantasy Grounds encounters were not created"
    prepared = next(row for row in encounters if row["name"] == "Test Encounter")
    prepared_combatants = repo.list_combatants(prepared["id"])
    assert [row["name"] for row in prepared_combatants] == ["Test Creature #1", "Test Creature #2"], "Prepared encounter participants were mapped incorrectly"
    assert all(row["armor_class"] == 13 and row["max_hp"] == 12 and row["current_hp"] == 12 and row["initiative_mod"] == 2 for row in prepared_combatants), "Prepared participant statistics were discarded"
    live = next(row for row in encounters if "Live Combat" in row["name"])
    assert result.preferred_encounter_id == live["id"], "Import did not identify the updated live encounter for UI selection"
    assert repo.is_external_encounter(live["id"]), "Live encounter was not marked as externally owned"
    prepared_context = repo.encounter_sync_context(prepared["id"])
    live_context = repo.encounter_sync_context(live["id"])
    assert prepared_context == {
        "kind": "prepared", "counterpart_id": live["id"], "counterpart_name": live["name"],
    }, "Prepared encounter was not linked to its live session"
    assert live_context == {
        "kind": "live", "counterpart_id": prepared["id"], "counterpart_name": prepared["name"],
    }, "Live session was not linked back to its prepared encounter"
    assert "Prepared" in repo.encounter_display_name(prepared) and "Live combat" in repo.encounter_display_name(live), "Encounter roles are not visible in display names"
    combatants = repo.list_combatants(live["id"])
    assert len(combatants) == 1 and combatants[0]["current_hp"] == 9, "Live combatant HP mapping failed"
    with connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM active_conditions").fetchone()[0] == 1, "Combat effects were not imported"
        assert conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0] == "9", "Schema version was not migrated"
        columns = {row[1] for row in conn.execute("PRAGMA table_info(turn_log)")}
        assert {"damage_types", "damage_components_json"} <= columns, "Damage-type schema columns are missing"
        assert conn.execute("SELECT COUNT(*) FROM rules_reference WHERE category LIKE 'Fantasy Grounds %'").fetchone()[0] == 5, "Catalog references were not normalized"
        source = conn.execute("SELECT * FROM external_sources").fetchone()
        assert source["last_sequence"] == 1 and not source["last_error"], "Sync source state is incorrect"
        assert conn.execute("SELECT COUNT(*) FROM external_records WHERE is_stale=0").fetchone()[0] >= 8, "External provenance records are missing"
        assert conn.execute("SELECT COUNT(*) FROM external_events").fetchone()[0] == 2, "Combat events were not imported"
        logs = conn.execute("SELECT actor,action_type,details FROM turn_log ORDER BY id").fetchall()
        assert [row["action_type"] for row in logs] == ["Attack", "Damage"], "Combat event types were not mapped"
        assert logs[0]["actor"] == "Fantasy Grounds Test Hero", "Combat actor was not imported"
        assert logs[0]["details"] == "18 (dice 13; modifiers +5) | Test Creature | Against AC 13 | Longsword | Hit (18 vs AC 13)", "Attack resolution format is incorrect"
        assert logs[1]["actor"] == "Manual / Unattributed" and logs[1]["details"].endswith("3 damage applied from 0 rolled"), "Early incomplete damage event was not represented safely"

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
    updated["events"][1] = complete_damage_event
    updated["combat"]["combatants"][0]["hit_points"]["current"] = 6
    updated["encounters"][0]["participants"][0].update({"armor_class": 14, "hit_points": 20, "initiative_mod": 3})
    updated["events"].append({
        "event_id": "test-session-001:3", "sequence": 3, "timestamp": "2026-07-17T20:00:05Z",
        "round": 1, "encounter_source_key": "test-session-001", "type": "healing",
        "actor": {"source_key": "5E:character:test-hero", "name": "Fantasy Grounds Test Hero"},
        "target": {"source_key": "5E:ct:id-00001", "name": "Test Creature"}, "amount": 2,
        "description": "Wounds decreased from 3 to 1", "metadata": {"previous_wounds": 3, "current_wounds": 1},
    })
    with connect(db) as conn:
        conn.execute("UPDATE encounters SET status='active',round=5,outcome='Old local value' WHERE id=?", (prepared["id"],))
    snapshot.write_text(json.dumps(updated), encoding="utf-8")
    update_result = service.import_configured_snapshot()
    assert update_result.applied and update_result.sequence == 2, "New sequence was not applied"
    live = next(row for row in repo.list_encounters() if "Live Combat" in row["name"])
    assert update_result.preferred_encounter_id == live["id"], "Updated live session was not selected after import"
    assert repo.list_combatants(live["id"])[0]["current_hp"] == 6, "Combat update was not applied"
    assert len(repo.list_players()) == 2 and len(repo.list_encounters()) == 2, "Update created duplicate entities"
    refreshed_prepared = repo.get_encounter(prepared["id"])
    assert refreshed_prepared["status"] == "draft" and refreshed_prepared["round"] == 1 and not refreshed_prepared["outcome"], "Fantasy Grounds prepared encounter state was not refreshed"
    refreshed_participants = repo.list_combatants(prepared["id"])
    assert all(row["armor_class"] == 14 and row["max_hp"] == 20 and row["initiative_mod"] == 3 for row in refreshed_participants), "Prepared participant updates were not applied"
    with connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM turn_log").fetchone()[0] == 3, "Only the new event should be appended"
        assert conn.execute("SELECT details FROM turn_log WHERE action_type='Healing'").fetchone()[0].startswith("2 | Test Creature |"), "Healing was not mapped"
        enriched = conn.execute("SELECT actor,details FROM turn_log WHERE action_type='Damage'").fetchone()
        assert enriched["actor"] == "Fantasy Grounds Test Hero" and "Longsword | 3 damage applied from 3 rolled" in enriched["details"], "Later authoritative event enrichment did not repair the existing row"
        raw_event = json.loads(conn.execute("SELECT raw_json FROM external_events WHERE event_key='test-session-001:2'").fetchone()[0])
        assert raw_event["metadata"]["damage_resolution"] == "authoritative" and raw_event["actor"]["name"] == "Fantasy Grounds Test Hero", "Enriched source evidence was not retained"

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
    new_session["combat"].update({
        "active": True, "session_key": "test-session-002", "session_name": "Explicit Test Combat",
        "session_state": "open", "started_at": "2026-07-17T21:00:00Z", "outcome": None, "completed_at": None,
    })
    new_session["events"].append({
        "event_id": "test-session-002:5", "sequence": 5, "timestamp": "2026-07-17T21:00:00Z",
        "round": 1, "encounter_source_key": "test-session-002", "type": "action",
        "actor": {"source_key": "5E:character:test-hero", "name": "Fantasy Grounds Test Hero"},
        "target": {"source_key": "5E:ct:id-00001", "name": "Test Creature"},
        "amount": None, "description": "[DAMAGE (M)] Greataxe [TYPE: slashing (6)] [TYPE: fire (3)]",
        "metadata": {"action_name": "Greataxe", "roll_type": "damage", "raw_roll": 6, "modifier": 3, "roll_total": 9, "target_ac": 13,
            "damage_types": ["slashing", "fire"], "damage_components": [
                {"types": ["slashing"], "rolled": 6, "applied": 3, "resisted": 3, "vulnerable": 0},
                {"types": ["fire"], "rolled": 3, "applied": 1, "resisted": 2, "vulnerable": 0},
            ]},
    })
    new_session["events"].extend([
        {
            "event_id": "test-session-002:6", "sequence": 6, "timestamp": "2026-07-17T21:00:01Z",
            "round": 1, "encounter_source_key": "test-session-002", "type": "attack",
            "actor": {"source_key": "5E:character:test-hero", "name": "Fantasy Grounds Test Hero"},
            "target": {"source_key": "5E:ct:id-00001", "name": "Test Creature"}, "amount": None,
            "description": "[ATTACK (M)] Longsword", "metadata": {"action_name": "Longsword", "raw_roll": 20,
                "modifier": 5, "roll_total": 25, "target_ac": 30, "natural_roll": 20,
                "result": "Critical Hit", "authoritative_result": True},
        },
        {
            "event_id": "test-session-002:7", "sequence": 7, "timestamp": "2026-07-17T21:00:02Z",
            "round": 1, "encounter_source_key": "test-session-002", "type": "attack",
            "actor": {"source_key": "5E:character:test-hero", "name": "Fantasy Grounds Test Hero"},
            "target": {"source_key": "5E:ct:id-00001", "name": "Test Creature"}, "amount": None,
            "description": "[ATTACK (M)] Longsword", "metadata": {"action_name": "Longsword", "raw_roll": 1,
                "modifier": 14, "roll_total": 15, "target_ac": 10, "natural_roll": 1,
                "result": "Automatic Miss", "authoritative_result": True},
        },
        {
            "event_id": "test-session-002:8", "sequence": 8, "timestamp": "2026-07-17T21:00:03Z",
            "round": 1, "encounter_source_key": "test-session-002", "type": "damage",
            "actor": {"source_key": "5E:character:test-hero", "name": "Fantasy Grounds Test Hero"},
            "target": {"source_key": "5E:ct:id-00001", "name": "Test Creature"}, "amount": 4,
            "description": "Wounds increased", "metadata": {"action_name": "Greataxe", "roll_total": 9,
                "adjustment": -5, "attribution": "matched_recent_roll", "current_hp": 5, "maximum_hp": 12,
                "damage_types": ["slashing", "fire"], "damage_components": [
                    {"types": ["slashing"], "rolled": 6, "applied": 3, "resisted": 3, "vulnerable": 0},
                    {"types": ["fire"], "rolled": 3, "applied": 1, "resisted": 2, "vulnerable": 0},
                ]},
        },
        {
            "event_id": "test-session-002:9", "sequence": 9, "timestamp": "2026-07-17T21:00:04Z",
            "round": 1, "encounter_source_key": "test-session-002", "type": "damage",
            "actor": None, "target": {"source_key": "5E:ct:id-00001", "name": "Test Creature"}, "amount": 2,
            "description": "Manual wounds change", "metadata": {"attribution": "manual_or_unattributed",
                "current_hp": 3, "maximum_hp": 12},
        },
    ])
    snapshot.write_text(json.dumps(new_session), encoding="utf-8")
    new_session_result = service.import_configured_snapshot()
    with connect(db) as conn:
        encounter_ids = {row[0] for row in conn.execute("SELECT DISTINCT encounter_id FROM external_events").fetchall()}
        assert len(encounter_ids) == 2, "Separate Fantasy Grounds combat sessions were merged"
        damage_roll = conn.execute("SELECT action_type,details,damage_types,damage_components_json FROM turn_log WHERE action_type='Damage Roll'").fetchone()
        assert damage_roll and damage_roll["details"] == "9 (dice 6; modifiers +3) | Test Creature | Against AC 13 | Greataxe | 9 damage rolled", "Damage roll value was not displayed"
        assert damage_roll["damage_types"] == "slashing, fire", "Mixed damage types were not normalized"
        assert json.loads(damage_roll["damage_components_json"])[0] == {"types": ["slashing"], "rolled": 6, "applied": 3, "resisted": 3, "vulnerable": 0}, "Damage component details were not preserved"
        assert conn.execute("SELECT COUNT(*) FROM turn_log WHERE details LIKE '%Critical Hit (25 vs AC 30)%'").fetchone()[0] == 1, "Authoritative critical hit was not preserved"
        assert conn.execute("SELECT COUNT(*) FROM turn_log WHERE details LIKE '%Automatic Miss (15 vs AC 10)%'").fetchone()[0] == 1, "Authoritative natural-one miss was not preserved"
        assert conn.execute("SELECT COUNT(*) FROM turn_log WHERE details LIKE '%4 damage applied from 9 rolled (reduced by 5)%'").fetchone()[0] == 1, "Adjusted damage was not explained"
        assert conn.execute("SELECT COUNT(*) FROM turn_log WHERE actor='Manual / Unattributed'").fetchone()[0] == 1, "Manual damage inherited a stale actor"
        assert conn.execute("SELECT damage_types FROM turn_log WHERE actor='Manual / Unattributed'").fetchone()[0] == "unknown", "Manual damage type was guessed"
        explicit_encounter = conn.execute("SELECT id,status FROM encounters WHERE name='Explicit Test Combat'").fetchone()
        assert explicit_encounter and explicit_encounter["status"] == "active", "Explicit session name or open state was not imported"
        assert new_session_result.preferred_encounter_id == explicit_encounter["id"], "New live session was not preferred after import"
        assert repo.encounter_sync_context(explicit_encounter["id"])["counterpart_id"] == prepared["id"], "New live session was not associated with its prepared encounter"

    closed_session = copy.deepcopy(new_session)
    closed_session["sequence"] = 5
    closed_session["combat"].update({
        "active": False, "combatants": [], "active_source_key": None, "session_state": "closed",
        "outcome": "victory", "completed_at": "2026-07-17T21:05:00Z",
    })
    closed_session["events"].append({
        "event_id": "test-session-002:10", "sequence": 10, "timestamp": "2026-07-17T21:05:00Z",
        "round": 2, "encounter_source_key": "test-session-002", "type": "outcome",
        "actor": None, "target": None, "amount": None, "description": "Encounter ended: victory",
        "metadata": {"lifecycle": "encounter_end", "outcome": "victory", "completed_at": "2026-07-17T21:05:00Z"},
    })
    snapshot.write_text(json.dumps(closed_session), encoding="utf-8")
    service.import_configured_snapshot()
    with connect(db) as conn:
        explicit_encounter = conn.execute("SELECT id,status,outcome FROM encounters WHERE name='Explicit Test Combat'").fetchone()
        assert tuple(explicit_encounter)[1:] == ("completed", "victory"), "Explicit end state was not imported"
        assert conn.execute("SELECT COUNT(*) FROM combatants WHERE encounter_id=?", (explicit_encounter["id"],)).fetchone()[0] == 1, "Final roster was discarded after Combat Tracker clearing"
        assert conn.execute("SELECT COUNT(*) FROM turn_log WHERE encounter_id=? AND action_type='Encounter End'", (explicit_encounter["id"],)).fetchone()[0] == 1, "Encounter-end event was not formatted"

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

    with connect(db) as conn:
        source_id = int(conn.execute("SELECT id FROM external_sources WHERE provider='fantasy_grounds'").fetchone()[0])
        imported_campaign_id = int(conn.execute(
            "SELECT entity_id FROM external_entity_links WHERE source_id=? AND entity_type='campaign'", (source_id,)
        ).fetchone()[0])
        local_encounter_id = int(conn.execute(
            "INSERT INTO encounters(name,status,campaign_id) VALUES('Local Encounter To Preserve','draft',?) RETURNING id",
            (imported_campaign_id,),
        ).fetchone()[0])
        conn.execute(
            "INSERT INTO turn_log(encounter_id,round,actor,action_type,details) VALUES(?,1,'Local Hero','Action','Local row')",
            (local_encounter_id,),
        )
    preview = service.preview_clear_imported_data(source_id)
    assert preview.campaigns == 1 and preview.encounters >= 2 and preview.combat_log_rows >= 1, "Clear preview omitted imported data"
    assert preview.local_encounters_detached == 1, "Clear preview did not identify the local encounter to preserve"
    clear_result = service.clear_imported_data(source_id)
    assert clear_result.backup_path.exists(), "Clear operation did not create a safety backup"
    assert not service.automatic_import_enabled(), "Automatic import was not persistently paused after clearing"
    with connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM external_sources WHERE provider='fantasy_grounds'").fetchone()[0] == 0, "Sync metadata was not cleared"
        assert conn.execute("SELECT COUNT(*) FROM campaigns WHERE id=?", (imported_campaign_id,)).fetchone()[0] == 0, "Imported campaign was not cleared"
        local_encounter = conn.execute("SELECT campaign_id FROM encounters WHERE id=?", (local_encounter_id,)).fetchone()
        assert local_encounter and local_encounter["campaign_id"] is None, "Local encounter was not preserved and detached"
        assert conn.execute("SELECT COUNT(*) FROM turn_log WHERE encounter_id=?", (local_encounter_id,)).fetchone()[0] == 1, "Local combat log row was removed"
        assert conn.execute("SELECT COUNT(*) FROM players WHERE name='Fantasy Grounds Test Hero'").fetchone()[0] == 1, "Original local player was removed"

    print("Fantasy Grounds sync test passed.")
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)
