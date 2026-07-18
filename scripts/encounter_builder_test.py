from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from tempfile import mkdtemp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

temp_dir = Path(mkdtemp(prefix="lectern_encounter_builder_"))
os.environ["LECTERN_DATA_DIR"] = str(temp_dir / "user-data")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.database.repositories import Repository
from app.database.schema import connect, initialize_database
from app.ui.main_window import EncounterBuilderPage


def monster(name: str, armor_class: int, hit_points: int) -> dict:
    return {
        "name": name, "size": "Medium", "type": "Humanoid", "alignment": "",
        "armor_class": armor_class, "hit_points": hit_points, "speed": "",
        "challenge_rating": "1/8", "xp": 0,
        "str_score": 10, "dex_score": 10, "con_score": 10,
        "int_score": 10, "wis_score": 10, "cha_score": 10,
        "source": "test", "notes": "",
    }


try:
    db = temp_dir / "lectern.db"
    initialize_database(db)
    repo = Repository(db)
    repo.upsert_monster(monster("A-mi-kuk", 14, 115))
    repo.upsert_monster(monster("Bandit", 12, 11))
    repo.upsert_monster(monster("Wolf", 13, 11))
    encounter_id = repo.create_encounter("Bandit Regression")

    app = QApplication.instance() or QApplication([])
    page = None

    def refresh_all():
        page.refresh()

    page = EncounterBuilderPage(repo, refresh_all)
    page.setStyleSheet(
        "QSpinBox { background-color: rgba(32,33,36,220); "
        "border: 1px solid #3c4043; border-radius: 4px; }"
    )
    page.resize(1200, 700)
    page.show()
    app.processEvents()
    page.current_encounter_id = encounter_id
    page.refresh()
    assert page.monster_search.currentIndex() == -1, "Monster picker silently selected its first row"
    search_gap = page.monster_search.geometry().top() - page.monster_search_label.geometry().bottom()
    quantity_gap = page.monster_quantity_label.geometry().top() - page.monster_search.geometry().bottom()
    controls_gap = page.monster_qty.geometry().top() - page.monster_quantity_label.geometry().bottom()
    assert 0 <= search_gap <= 16, "Monster search label and field are spaced too far apart"
    assert 0 <= quantity_gap <= 30, "Monster search and quantity sections are spaced too far apart"
    assert 0 <= controls_gap <= 16, "Monster quantity label and controls are spaced too far apart"

    page.monster_qty.setValue(1)
    QTest.mouseClick(page.monster_qty_up, Qt.LeftButton)
    assert page.monster_qty.value() == 2, "Quantity up arrow did not increment"
    QTest.mouseClick(page.monster_qty_down, Qt.LeftButton)
    assert page.monster_qty.value() == 1, "Quantity down arrow did not decrement"

    page.monster_search.setEditText("Bandit")
    page.monster_qty.setValue(2)
    page.add_monsters()
    rows = repo.list_combatants(encounter_id)
    assert [row["name"] for row in rows] == ["Bandit #1", "Bandit #2"], "Bandit selection mapped to the wrong monster"
    assert all(row["source_id"] == repo.get_monster_by_id(row["source_id"])["id"] for row in rows), "Stored monster IDs are invalid"
    bandit_id = next(row["id"] for row in repo.list_monsters() if row["name"] == "Bandit")
    assert all(row["source_id"] == bandit_id for row in rows), "Bandit combatants did not retain the Bandit database ID"
    assert page.monster_search.currentText() == "Bandit", "Refresh changed Bandit selection to A-mi-kuk"

    page.monster_qty.setValue(1)
    page.add_monsters()
    rows = repo.list_combatants(encounter_id)
    assert [row["name"] for row in rows] == ["Bandit #1", "Bandit #2", "Bandit #3"], "Repeated add used a reset picker value"

    page.monster_search.setEditText("wolf")
    page.add_monsters()
    rows = repo.list_combatants(encounter_id)
    assert [row["name"] for row in rows] == ["Bandit #1", "Bandit #2", "Bandit #3", "Wolf #1"], "Case-insensitive monster selection or ordering failed"
    assert [row["sort_order"] for row in rows] == [0, 1, 2, 3], "Combatant insertion order is inconsistent"

    external_id = repo.create_encounter("Fantasy Grounds Prepared Encounter")
    with connect(db) as conn:
        source_id = int(conn.execute(
            "INSERT INTO external_sources(provider,campaign_key,campaign_name,ruleset) VALUES('fantasy_grounds','test','Test','5E')"
        ).lastrowid)
        conn.execute(
            "INSERT INTO external_entity_links(source_id,source_key,entity_type,entity_id) VALUES(?,?,'encounter',?)",
            (source_id, "5E:battle:test", external_id),
        )
    page.current_encounter_id = external_id
    page.refresh()
    assert not page.external_notice.isHidden(), "Fantasy Grounds ownership notice is missing"
    assert not page.add_monster_button.isEnabled() and not page.remove_button.isEnabled(), "Fantasy Grounds encounter can be edited locally"
    assert not page.monster_qty_up.isEnabled() and not page.monster_qty_down.isEnabled(), "Fantasy Grounds quantity controls remain editable"

    page.close()
    print("Encounter Builder regression test passed.")
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)
