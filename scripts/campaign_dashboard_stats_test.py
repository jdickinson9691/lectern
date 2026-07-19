from __future__ import annotations

import os
import shutil
import sqlite3
import sys
from pathlib import Path
from tempfile import mkdtemp

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
temp_dir = Path(mkdtemp(prefix="lectern_campaign_stats_"))
os.environ["LECTERN_DATA_DIR"] = str(temp_dir / "user-data")

from PySide6.QtWidgets import QApplication

from app.database.repositories import Repository
from app.database.schema import connect, initialize_database
from app.ui.main_window import CampaignDashboardPage


try:
    legacy_db = temp_dir / "legacy.db"
    with sqlite3.connect(legacy_db) as legacy:
        legacy.execute(
            "CREATE TABLE turn_log(id INTEGER PRIMARY KEY AUTOINCREMENT,encounter_id INTEGER,round INTEGER,actor TEXT,action_type TEXT,details TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
        )
        legacy.execute("INSERT INTO turn_log(encounter_id,round,actor,action_type,details) VALUES(1,1,'Legacy Hero','Attack','Legacy row')")
    initialize_database(legacy_db)
    with connect(legacy_db) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(turn_log)")}
        assert {"actor_source_key", "actor_side", "amount", "result_code", "natural_roll"} <= columns, "Schema-v8 log columns were not migrated"
        assert conn.execute("SELECT details FROM turn_log").fetchone()[0] == "Legacy row", "Schema migration changed a historical log row"
        assert conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0] == "9"

    db = temp_dir / "lectern.db"
    initialize_database(db)
    repo = Repository(db)
    campaign_id = repo.create_campaign("Statistics Campaign", "Party performance")
    encounter_one = repo.create_encounter("Statistics Encounter One")
    encounter_two = repo.create_encounter("Statistics Encounter Two")
    repo.assign_encounter_to_campaign(encounter_one, campaign_id)
    repo.assign_encounter_to_campaign(encounter_two, campaign_id)

    with connect(db) as conn:
        conn.execute("UPDATE encounters SET round=3,status='completed' WHERE id=?", (encounter_one,))
        conn.execute("UPDATE encounters SET round=2,status='completed' WHERE id=?", (encounter_two,))

    def log(encounter_id, actor, action_type, details, **fields):
        repo.log_turn(encounter_id, actor, action_type, details, **fields)

    log(encounter_one, "Aria", "Damage", "24 | Ogre | Target HP 20/44 | Sword | 24 damage applied", actor_side="party", amount=24)
    log(encounter_one, "Aria", "Healing", "5 | Aria | Target HP 25/44 | Potion | 5 healing applied", actor_side="party", amount=5)
    for _ in range(2):
        log(encounter_one, "Aria", "Attack", "Critical Hit", actor_side="party", result_code="critical_hit", natural_roll=20)
        log(encounter_one, "Rook", "Attack", "Critical Hit", actor_side="party", result_code="critical_hit", natural_roll=20)
    for _ in range(2):
        log(encounter_one, "Mira", "Attack", "Automatic Miss", actor_side="party", result_code="critical_miss", natural_roll=1)
    log(encounter_one, "Mira", "Healing", "10 | Aria | Target HP 35/44 | Cure Wounds | 10 healing applied", actor_side="party", amount=10)
    log(encounter_one, "Ogre", "Damage", "50 | Aria | Target HP 0/44 | Club | 50 damage applied", actor_side="hostile", amount=50)
    log(encounter_one, "Manual / Unattributed", "Damage", "99 | Unknown | Target HP not reported | Damage | 99 damage applied", actor_side="unknown", amount=99)
    log(encounter_two, "Aria", "Damage", "16 | Goblin | Target HP 0/7 | Sword | 16 damage applied", actor_side="party", amount=16)

    summary = repo.campaign_summary(campaign_id)
    assert summary["combat_rounds"] == 5, "Campaign combat rounds were not aggregated per encounter"
    assert summary["party_damage"] == 40 and summary["party_dpr"] == 8.0, "Party DPR is incorrect"
    assert summary["party_healing"] == 15 and summary["party_hpr"] == 3.0, "Party HPR is incorrect"
    assert summary["critical_hit_leaders"] == ["Aria", "Rook"] and summary["critical_hit_count"] == 2, "Critical-hit tie was not retained"
    assert summary["critical_miss_leaders"] == ["Mira"] and summary["critical_miss_count"] == 2, "Critical-miss leader is incorrect"
    assert summary["stat_events"] == 12 and summary["attributed_stat_events"] == 11, "Statistics coverage is incorrect"
    assert summary["damage"] == 189 and summary["healing"] == 15, "Existing all-source totals changed"

    app = QApplication.instance() or QApplication([])
    page = CampaignDashboardPage(repo, lambda: None)
    page.campaigns.setCurrentIndex(page.campaigns.findData(campaign_id))
    page.refresh_dashboard()
    app.processEvents()
    assert "8.0" in page.party_dpr.text() and "3.0" in page.party_hpr.text(), "DPR/HPR cards were not populated"
    assert "Aria, Rook" in page.critical_hits.text() and "Mira" in page.critical_misses.text(), "Critical leader cards were not populated"
    assert "11 of 12" in page.stats_coverage.text(), "Coverage note was not populated"
    page.close()

    print("Campaign Dashboard statistics test passed.")
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)
