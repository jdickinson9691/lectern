from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from tempfile import mkdtemp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

temp_dir = Path(mkdtemp(prefix="lectern_fg_effects_"))
os.environ["LECTERN_DATA_DIR"] = str(temp_dir / "user-data")

from app.database.schema import connect, initialize_database
from app.integrations.fantasy_grounds import (
    FantasyGroundsSyncService,
    format_event_log,
    validate_snapshot,
)


def effect_event(
    sequence: int,
    lifecycle: str,
    state: str,
    description: str,
    *,
    actor_name: str = "Fantasy Grounds Test Hero",
    target_name: str = "Test Creature",
    action_name: str = "Bardic Inspiration Die",
    effect_name: str = "Bardic Inspiration Die",
    effect_key: str = "combattracker.list.id-00001.effects.id-00001",
    duration: int = 10,
    source_attribution: str = "effect_source_reference",
) -> dict:
    return {
        "event_id": f"test-effect-session:{sequence}",
        "sequence": sequence,
        "timestamp": f"2026-07-24T20:00:0{sequence}Z",
        "round": 1,
        "encounter_source_key": "test-effect-session",
        "type": "effect",
        "actor": {
            "source_key": "5E:character:test-hero",
            "name": actor_name,
        },
        "target": {
            "source_key": "5E:ct:id-00001",
            "name": target_name,
        },
        "amount": None,
        "description": description,
        "metadata": {
            "action_name": action_name,
            "originating_action": action_name,
            "effect_name": effect_name,
            "effect_key": effect_key,
            "effect_state": state,
            "lifecycle": lifecycle,
            "duration": duration,
            "apply": "roll",
            "is_active": True,
            "source_name": actor_name,
            "source_reference": "combattracker.list.id-00002",
            "source_attribution": source_attribution,
        },
    }


try:
    payload = json.loads(
        (
            ROOT
            / "docs"
            / "contracts"
            / "fantasy_grounds_snapshot_v1.example.json"
        ).read_text(encoding="utf-8")
    )
    payload["source"]["extension_version"] = "1.4.9"
    payload["sequence"] = 4
    payload["combat"].update(
        {
            "session_key": "test-effect-session",
            "session_name": "Effect Lifecycle Test",
            "session_state": "closed",
            "outcome": "unresolved",
            "completed_at": "2026-07-24T20:00:03Z",
        }
    )
    payload["events"] = [
        effect_event(
            1,
            "effect_added",
            "added",
            "Effect added to Test Creature: Bardic Inspiration Die",
        ),
        effect_event(
            2,
            "effect_removed",
            "removed",
            "Effect ended on Test Creature: Bardic Inspiration Die",
        ),
        effect_event(
            3,
            "effect_added",
            "added",
            "Effect added to Warlock1: AC: 3; [D: 8 hours]",
            actor_name="Warlock1",
            target_name="Warlock1",
            action_name="Armor of Shadows",
            effect_name="AC: 3",
            effect_key="combattracker.list.warlock.effects.armor",
            duration=8,
            source_attribution="originating_effect_action",
        ),
        effect_event(
            4,
            "effect_added",
            "added",
            "Effect added to Unknown Mage: AC: 3; [D: 8 hours]",
            actor_name="Unknown Mage",
            target_name="Unknown Mage",
            action_name="Effect",
            effect_name="AC: 3",
            effect_key="combattracker.list.unknown.effects.armor",
            duration=8,
            source_attribution="active_self",
        ),
    ]

    validate_snapshot(payload)
    added = format_event_log(payload["events"][0])
    removed = format_event_log(payload["events"][1])
    assert added.actor == "Fantasy Grounds Test Hero"
    assert added.action_type == "Effect"
    assert (
        added.details
        == " | Test Creature | Effect added | Bardic Inspiration Die | "
        "Effect added to Test Creature: Bardic Inspiration Die"
    )
    assert not added.incomplete
    assert "Effect ended" in removed.details and not removed.incomplete

    db = temp_dir / "lectern.db"
    initialize_database(db)
    snapshot = temp_dir / "snapshot.json"
    snapshot.write_text(json.dumps(payload), encoding="utf-8")
    result = FantasyGroundsSyncService(db).import_snapshot(snapshot)
    assert result.applied and result.counts["events"] == 4

    with connect(db) as conn:
        rows = conn.execute(
            """
            SELECT tl.actor,tl.action_type,tl.details,ee.raw_json
            FROM external_events ee
            JOIN turn_log tl ON tl.id=ee.turn_log_id
            ORDER BY ee.id
            """
        ).fetchall()
        assert [row["actor"] for row in rows] == [
            "Fantasy Grounds Test Hero",
            "Fantasy Grounds Test Hero",
            "Warlock1",
            "Unknown Mage",
        ]
        assert [row["action_type"] for row in rows] == [
            "Effect",
            "Effect",
            "Effect",
            "Effect",
        ]
        raw_added = json.loads(rows[0]["raw_json"])
        raw_removed = json.loads(rows[1]["raw_json"])
        assert raw_added["metadata"]["lifecycle"] == "effect_added"
        assert raw_removed["metadata"]["lifecycle"] == "effect_removed"
        assert raw_added["metadata"]["source_attribution"] == "effect_source_reference"
        armor_row = rows[2]
        generic_row = rows[3]
        assert armor_row["actor"] == "Warlock1"
        assert " | Warlock1 | Effect added | Armor of Shadows | " in armor_row["details"]
        assert (
            json.loads(armor_row["raw_json"])["metadata"]["originating_action"]
            == "Armor of Shadows"
        )
        assert "Armor of Shadows" not in generic_row["details"]
        assert " | Unknown Mage | Effect added | Effect | " in generic_row["details"]

    print("Fantasy Grounds effect lifecycle test passed.")
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)
