"""Offscreen regression checks for the structured Combat Dashboard log."""

import os
import shutil
import sys
from pathlib import Path
from tempfile import mkdtemp

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication

from app.database.repositories import Repository
from app.database.schema import connect, initialize_database
from app.ui.main_window import CombatDashboardPage


temp_dir = Path(mkdtemp(prefix="lectern_combat_log_ui_"))
app = QApplication.instance() or QApplication([])
page = None
try:
    db = temp_dir / "lectern.db"
    initialize_database(db)
    repo = Repository(db)
    encounter_id = repo.create_encounter("Combat Log UI")
    with connect(db) as conn:
        conn.execute("UPDATE encounters SET status='active',round=4 WHERE id=?",(encounter_id,))
        conn.execute("INSERT INTO combatants(encounter_id,source_type,name,armor_class,max_hp,current_hp,is_active) VALUES(?,'player','Fighter1',16,20,10,1)",(encounter_id,))
        rows = [
            (4,"Berserker 2","Attack","16 (dice 11; modifiers +5) | Fighter1 | Against AC 16 | Greataxe | Hit (16 vs AC 16)"),
            (4,"Berserker 2","Damage Roll","9 (dice 6; modifiers +3) | Fighter1 | Against AC 16 | Greataxe | 9 damage rolled"),
            (4,"Berserker 2","Damage","4 | Fighter1 | Target HP 12/20 | Greataxe | 4 damage applied from 9 rolled (reduced by 5)"),
            (4,"Manual / Unattributed","Damage","2 | Fighter1 | Target HP 10/20 | Damage | 2 damage applied"),
            (3,"Fighter1","Attack","25 (dice 20; modifiers +5) | Berserker 2 | Against AC 30 | Longsword | Critical Hit (25 vs AC 30)"),
            (3,"Fighter1","Turn Start","Turn started"),
            (2,"Fighter1","Note","Older local free-text entry"),
        ]
        conn.executemany("INSERT INTO turn_log(encounter_id,round,actor,action_type,details) VALUES(?,?,?,?,?)",[(encounter_id,*row) for row in rows])
        conn.execute("UPDATE turn_log SET damage_types='slashing, fire',damage_components_json='[{\"types\":[\"slashing\"],\"rolled\":6,\"applied\":3}]' WHERE encounter_id=? AND actor='Berserker 2' AND action_type LIKE 'Damage%'",(encounter_id,))
        conn.execute("UPDATE turn_log SET damage_types='unknown' WHERE encounter_id=? AND actor='Manual / Unattributed'",(encounter_id,))
    historical_id=repo.create_encounter("Newer Historical Log")
    with connect(db) as conn:
        conn.execute("UPDATE encounters SET status='completed',round=11 WHERE id=?",(historical_id,))
        conn.execute("INSERT INTO turn_log(encounter_id,round,actor,action_type,details) VALUES(?,11,'Fantasy Grounds','Action','Action')",(historical_id,))
    page = CombatDashboardPage(repo); page.setStyleSheet("QWidget{background:#202124;color:#e8eaed} QTreeWidget,QLineEdit,QComboBox{background:#202124;border:1px solid #3c4043} QTreeWidget{alternate-background-color:#27292d} QTreeWidget::item{color:#e8eaed} QHeaderView::section{background:#2a2c30;color:#e8eaed;padding:6px}"); page.resize(1400,800); page.show(); app.processEvents()
    splitter_sizes=page.workspace_splitter.sizes(); roster_share=splitter_sizes[0]/sum(splitter_sizes)
    assert page.workspace_splitter.count()==2 and 0.22 <= roster_share <= 0.28, f"Combat workspace is not using the requested 25/75 split: {splitter_sizes}"
    assert page.roster_panel.geometry().left() < page.log_panel.geometry().left(), "Campaign entities are not positioned left of the combat session log"
    assert page.roster_panel.isAncestorOf(page.order), "Campaign entity table is not contained in the left panel"
    assert page.log_panel.isAncestorOf(page.log_tree), "Combat session log is not contained in the right panel"
    assert page.encounters.currentData()==encounter_id and page.current_encounter_id==encounter_id, "Dashboard did not prefer the active encounter over a newer historical log"
    page.select_encounter_id(historical_id); page.refresh(); app.processEvents()
    assert page.encounters.currentData()==historical_id and page.current_encounter_id==historical_id, "Dashboard could not select an imported encounter after refresh"
    page.select_encounter_id(encounter_id); page.refresh(); app.processEvents()
    page.current_encounter_id=encounter_id; page.refresh_log(); app.processEvents()
    assert page.log_tree.columnCount()==8, "Combat log does not expose the structured damage-type column"
    assert page.log_tree.topLevelItemCount()==3, "Filtered combat log did not group visible events by round"
    assert page.log_count.text()=="6 events", "Turn-marker toggle did not hide only system rows"
    round_four=page.log_tree.topLevelItem(0); assert round_four.text(0)=="Round 4 - 4 events" and round_four.isExpanded(), f"Round group heading is incorrect: {round_four.text(0)!r}, expanded={round_four.isExpanded()}"
    attack=next(round_four.child(i) for i in range(round_four.childCount()) if round_four.child(i).text(1)=="Attack")
    assert [attack.text(i) for i in range(8)]==["Berserker 2","Attack","16 (dice 11; modifiers +5)","Fighter1","Against AC 16","Greataxe","","Hit (16 vs AC 16)"], "Fantasy Grounds attack was parsed incorrectly"
    damage=next(round_four.child(i) for i in range(round_four.childCount()) if round_four.child(i).text(1)=="Damage" and round_four.child(i).text(0)=="Berserker 2")
    assert damage.text(6)=="slashing, fire" and "Components:" in damage.child(0).text(0), "Damage type or component detail was not displayed"
    assert attack.childCount()==1 and attack.child(0).text(0).startswith("Original:"), "Expandable original details are missing"
    page.log_result_filter.setCurrentIndex(page.log_result_filter.findData("critical")); app.processEvents(); assert page.log_count.text()=="1 event", "Critical-hit filter failed"
    page.log_result_filter.setCurrentIndex(0); page.log_search.setText("greataxe"); app.processEvents(); assert page.log_count.text()=="3 events", "Combat-log search failed"
    page.log_search.clear(); page.log_action_filter.setCurrentIndex(page.log_action_filter.findData("Damage")); app.processEvents(); assert page.log_count.text()=="2 events", "Action-type filter failed"
    page.hide_system_events.setChecked(False); page.log_action_filter.setCurrentIndex(0); app.processEvents(); assert page.log_count.text()=="7 events", "Turn-marker visibility toggle failed"
    if len(sys.argv)>1:
        output=Path(sys.argv[1]); output.parent.mkdir(parents=True,exist_ok=True); assert page.grab().save(str(output)),f"Could not save {output}"
    print("Combat Log UI regression test passed.")
finally:
    if page is not None: page.close()
    app.processEvents()
    shutil.rmtree(temp_dir,ignore_errors=True)
