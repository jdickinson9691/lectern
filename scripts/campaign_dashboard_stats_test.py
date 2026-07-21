from __future__ import annotations

import json
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
from app.ui.main_window import CampaignDashboardPage, MainWindow


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
        campaign_columns = {row[1] for row in conn.execute("PRAGMA table_info(campaigns)")}
        assert {"source_type", "is_archived"} <= campaign_columns, "Schema-v10 campaign columns were not migrated"
        assert conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0] == "10"

    db = temp_dir / "lectern.db"
    initialize_database(db)
    repo = Repository(db)
    campaign_id = repo.create_campaign("Statistics Campaign", "Party performance")
    repo.upsert_player({"name": "Aria", "class_name": "Fighter", "max_hp": 44})
    repo.upsert_player({"name": "Mira", "class_name": "Cleric", "max_hp": 32})
    party_ids=[row['id'] for row in repo.list_players()]
    repo.set_campaign_party(campaign_id,party_ids)
    assert [row['name'] for row in repo.list_campaign_party(campaign_id)] == ["Aria", "Mira"], "Persistent campaign party was not saved"
    encounter_one = repo.create_encounter("Statistics Encounter One",campaign_id)
    encounter_two = repo.create_encounter("Statistics Encounter Two",campaign_id)
    assert all(row['campaign_id']==campaign_id for row in repo.list_encounters_for_campaign(campaign_id)), "Campaign-scoped encounters were not created in their campaign"
    archived_id=repo.create_campaign("Archived Campaign")
    repo.set_campaign_archived(archived_id,True)
    assert archived_id not in {row['id'] for row in repo.list_campaigns()} and archived_id in {row['id'] for row in repo.list_campaigns(include_archived=True)}, "Campaign archive visibility is incorrect"
    repo.update_campaign(campaign_id,"Statistics Campaign","Updated party performance")
    assert repo.get_campaign(campaign_id)['source_type']=="local" and repo.get_campaign(campaign_id)['description']=="Updated party performance", "Local campaign edit or ownership failed"

    with connect(db) as conn:
        conn.execute("UPDATE encounters SET round=3,status='completed' WHERE id=?", (encounter_one,))
        conn.execute("UPDATE encounters SET round=2,status='completed' WHERE id=?", (encounter_two,))

    def log(encounter_id, actor, action_type, details, **fields):
        repo.log_turn(encounter_id, actor, action_type, details, **fields)

    log(encounter_one, "Aria", "Damage", "24 | Ogre | Target HP 20/44 | Sword | 24 damage applied", actor_side="party", amount=24,
        damage_types="slashing", damage_components_json=json.dumps([{"types": ["slashing", "magic"], "applied": 24}]))
    log(encounter_one, "Aria", "Healing", "5 | Aria | Target HP 25/44 | Potion | 5 healing applied", actor_side="party", amount=5)
    for _ in range(2):
        log(encounter_one, "Aria", "Attack", "Critical Hit", actor_side="party", result_code="critical_hit", natural_roll=20)
        log(encounter_one, "Rook", "Attack", "Critical Hit", actor_side="party", result_code="critical_hit", natural_roll=20)
    for _ in range(2):
        log(encounter_one, "Mira", "Attack", "Automatic Miss", actor_side="party", result_code="critical_miss", natural_roll=1)
    log(encounter_one, "Mira", "Healing", "10 | Aria | Target HP 35/44 | Cure Wounds | 10 healing applied", actor_side="party", amount=10)
    log(encounter_one, "Ogre", "Damage", "50 | Aria | Target HP 0/44 | Club | 50 damage applied", actor_side="hostile", amount=50)
    log(encounter_one, "Manual / Unattributed", "Damage", "99 | Unknown | Target HP not reported | Damage | 99 damage applied", actor_side="unknown", amount=99)
    log(encounter_two, "Aria", "Damage", "16 | Goblin | Target HP 0/7 | Sword | 16 damage applied", actor_side="party", amount=16,
        damage_types="slashing", damage_components_json=json.dumps([{"types": ["slashing"], "applied": 16}]))
    log(encounter_two, "Rook", "Damage", "6 fire damage applied", actor_side="party", amount=6,
        damage_types="fire, magic", damage_components_json=json.dumps([{"types": ["fire", "magic"], "applied": 6}]))
    log(encounter_two, "Mira", "Damage", "6 fire damage applied", actor_side="party", amount=6,
        damage_types="fire", damage_components_json=json.dumps([{"types": ["fire"], "applied": 6}]))
    log(encounter_two, "Rook", "Damage", "4 poison damage applied", actor_side="party", amount=4,
        damage_types="poison")

    summary = repo.campaign_summary(campaign_id)
    assert summary["combat_rounds"] == 5, "Campaign combat rounds were not aggregated per encounter"
    assert summary["party_damage"] == 56 and summary["party_dpr"] == 11.2, "Party DPR is incorrect"
    assert summary["party_healing"] == 15 and summary["party_hpr"] == 3.0, "Party HPR is incorrect"
    assert summary["critical_hit_leaders"] == ["Aria", "Rook"] and summary["critical_hit_count"] == 2, "Critical-hit tie was not retained"
    assert summary["critical_miss_leaders"] == ["Mira"] and summary["critical_miss_count"] == 2, "Critical-miss leader is incorrect"
    assert summary["stat_events"] == 15 and summary["attributed_stat_events"] == 14, "Statistics coverage is incorrect"
    assert summary["damage"] == 205 and summary["healing"] == 15, "Existing all-source totals changed"
    type_rows = {row["damage_type"]: row for row in summary["damage_type_leaders"]}
    assert len(type_rows) == 13, "All standard 5E damage types were not reported"
    assert type_rows["slashing"] == {"damage_type": "slashing", "leaders": [{"name": "Aria", "damage": 40, "events": 2}], "damage": 40}, "Slashing leader is incorrect"
    assert [leader["name"] for leader in type_rows["fire"]["leaders"]] == ["Mira", "Rook"] and type_rows["fire"]["damage"] == 6, "Fire tie was not retained"
    assert type_rows["poison"]["leaders"] == [{"name": "Rook", "damage": 4, "events": 1}], "Single-type legacy fallback is incorrect"
    assert not type_rows["acid"]["leaders"] and "magic" not in type_rows, "Unknown or non-damage qualifiers were included"

    app = QApplication.instance() or QApplication([])
    page = CampaignDashboardPage(repo, lambda: None)
    page.resize(1200, 800)
    page.show()
    page.campaigns.setCurrentIndex(page.campaigns.findData(campaign_id))
    page.refresh_dashboard()
    app.processEvents()
    assert page.campaign_source.text()=="LOCAL" and page.manage_party_button.isEnabled(), "Local campaign ownership controls are incorrect"
    assert "Aria" in page.party_summary.text() and "Mira" in page.party_summary.text(), "Persistent party summary was not rendered"
    assert page.campaign_encounter.count()==2 and page.encounter.count()==0, "Campaign and unassigned encounter selectors are not scoped"
    assert "11.2" in page.party_dpr.text() and "3.0" in page.party_hpr.text(), "DPR/HPR cards were not populated"
    assert "Aria, Rook" in page.critical_hits.text() and "Mira" in page.critical_misses.text(), "Critical leader cards were not populated"
    stat_cards = {page.party_dpr_card, page.party_hpr_card, page.critical_hits_card, page.critical_misses_card}
    assert len(stat_cards) == 4 and all(card.isVisible() for card in stat_cards), "Party combat statistics do not have four distinct visible cards"
    assert len({card.styleSheet() for card in stat_cards}) == 4, "Party combat statistic cards do not have distinct accent styling"
    assert "14 of 15" in page.stats_coverage.text(), "Coverage note was not populated"
    ui_type_rows = {page.damage_type_leaders.item(row, 0).text(): row for row in range(page.damage_type_leaders.rowCount())}
    assert len(ui_type_rows) == 13, "Damage-type leader table does not show every standard type"
    fire_row = ui_type_rows["Fire"]
    assert page.damage_type_leaders.item(fire_row, 1).text() == "Mira, Rook" and page.damage_type_leaders.item(fire_row, 2).text() == "6" and page.damage_type_leaders.item(fire_row, 3).text() == "1 each", "Damage-type tie was not rendered"
    expected_colors = {"Fire": "#8f2f2a", "Cold": "#245b8a", "Poison": "#83b96b", "Acid": "#1f5a3b"}
    for damage_type, expected_color in expected_colors.items():
        row = ui_type_rows[damage_type]
        assert all(page.damage_type_leaders.item(row, column).background().color().name() == expected_color for column in range(4)), f"{damage_type} row does not use its damage-type color"
    assert len({page.damage_type_leaders.item(row, 0).background().color().name() for row in range(page.damage_type_leaders.rowCount())}) == 13, "Damage types do not have distinct row colors"
    assert page.damage_type_leaders.item(ui_type_rows["Acid"], 1).text() == "No recorded party damage", "Empty damage type state was not rendered"
    assert page.damage_types_group.geometry().left() < page.encounters_group.geometry().left(), "Damage-type leaders are not positioned left of campaign encounters"
    assert abs(page.damage_types_group.geometry().top() - page.encounters_group.geometry().top()) <= 1, "Dashboard lower panels are not aligned side by side"
    assert page.damage_type_leaders.minimumHeight() >= 390 and page.damage_type_leaders.maximumHeight() > 10000, "Damage-type table is still vertically capped"
    page.close()

    screenshot_path = os.environ.get("LECTERN_CAMPAIGN_SCREENSHOT", "").strip()
    if screenshot_path:
        window = MainWindow(db)
        window.resize(1400, 900)
        window.nav.setCurrentRow(1)
        campaign_page = next(item for item in window.pages if isinstance(item, CampaignDashboardPage))
        campaign_page.campaigns.setCurrentIndex(campaign_page.campaigns.findData(campaign_id))
        campaign_page.refresh_dashboard()
        window.show()
        app.processEvents()
        last_damage_item = campaign_page.damage_type_leaders.item(campaign_page.damage_type_leaders.rowCount() - 1, 0)
        last_damage_rect = campaign_page.damage_type_leaders.visualItemRect(last_damage_item)
        assert last_damage_rect.isValid() and last_damage_rect.height() > 0 and last_damage_rect.bottom() < campaign_page.damage_type_leaders.viewport().height(), "The complete damage-type list is not visible at the normal launch size"
        assert window.grab().save(screenshot_path), "Campaign Dashboard screenshot could not be saved"
        window.close()

    print("Campaign Dashboard statistics test passed.")
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)
