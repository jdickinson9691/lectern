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
            "name": "Fantasy Grounds Test Hero",
        },
        "target": {
            "source_key": "5E:ct:id-00001",
            "name": "Test Creature",
        },
        "amount": None,
        "description": description,
        "metadata": {
            "action_name": "Bardic Inspiration Die",
            "effect_name": "Bardic Inspiration Die",
            "effect_key": "combattracker.list.id-00001.effects.id-00001",
            "effect_state": state,
            "lifecycle": lifecycle,
            "duration": 10,
            "apply": "roll",
            "is_active": True,
            "source_name": "Fantasy Grounds Test Hero",
            "source_reference": "combattracker.list.id-00002",
            "source_attribution": "effect_source_reference",
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
    payload["source"]["extension_version"] = "1.4.8"
    payload["sequence"] = 2
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
    assert result.applied and result.counts["events"] == 2

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
        ]
        assert [row["action_type"] for row in rows] == ["Effect", "Effect"]
        raw_added = json.loads(rows[0]["raw_json"])
        raw_removed = json.loads(rows[1]["raw_json"])
        assert raw_added["metadata"]["lifecycle"] == "effect_added"
        assert raw_removed["metadata"]["lifecycle"] == "effect_removed"
        assert raw_added["metadata"]["source_attribution"] == "effect_source_reference"

    print("Fantasy Grounds effect lifecycle test passed.")
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)
