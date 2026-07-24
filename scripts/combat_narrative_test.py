"""Offscreen regression checks for round-based Combat Narrative prose."""

from __future__ import annotations

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
from app.services.combat_narrative import CombatNarrativeBuilder
from app.ui.main_window import CombatNarrativePage, MainWindow


temp_dir = Path(mkdtemp(prefix="lectern_combat_narrative_"))
app = QApplication.instance() or QApplication([])
page = None
window = None
try:
    database = temp_dir / "lectern.db"
    initialize_database(database)
    repo = Repository(database)
    campaign_id = repo.create_campaign("Narrative Campaign")
    encounter_id = repo.create_encounter("The Broken Gate", campaign_id)
    with connect(database) as connection:
        rows = [
            (encounter_id, 1, "Fantasy Grounds", "Encounter Start", "Encounter started: Lectern Trial", "", None),
            (encounter_id, 1, "Fantasy Grounds", "Healing", "10 | Fighter1 | Target HP 10/10 | Healing | 10 healing applied", "", 10),
            (encounter_id, 1, "Fighter1", "Turn Start", "Turn started", "", None),
            (encounter_id, 1, "Fighter1", "Attack", "18 | Goblin | Against AC 14 | Longsword | Hit (18 vs AC 14)", "", None),
            (encounter_id, 1, "Fighter1", "Damage Roll", "10 | Goblin | Against AC 14 | Longsword | 10 damage rolled", "slashing", None),
            (encounter_id, 1, "Fighter1", "Damage", "7 | Goblin | Target HP 3/10 | Longsword | 7 damage applied from 10 rolled (reduced by 3)", "slashing", 7),
            (encounter_id, 2, "Goblin", "Attack", "9 | Fighter1 | Against AC 16 | Scimitar | Miss (9 vs AC 16)", "", None),
            (encounter_id, 2, "Manual / Unattributed", "Damage", "2 | Fighter1 | Target HP 18/20 | Damage | 2 damage applied", "unknown", 2),
            (encounter_id, 2, "Pallor", "Action", " | Fighter1 |  | Healing Word | Result not reported", "", None),
            (encounter_id, 2, "Pallor", "Healing", "5 | Fighter1 | Target HP 20/20 | Healing Word | 5 healing applied", "", 5),
            (encounter_id, 2, "Fantasy Grounds", "Effect", "0 | Fighter1 | Target HP 18/20 | Effect | Temporary HP changed from 0 to 5", "", None),
            (encounter_id, 2, "Fantasy Grounds", "Encounter End", "Encounter ended: victory", "", None),
        ]
        connection.executemany(
            """
            INSERT INTO turn_log(
                encounter_id,round,actor,action_type,details,damage_types,amount
            ) VALUES(?,?,?,?,?,?,?)
            """,
            rows,
        )

    log_rows = repo.list_turn_log(encounter_id)
    narrative = CombatNarrativeBuilder().build(log_rows, "Lectern Broken Gate")
    assert narrative.index("## Round 1") < narrative.index("## Round 2"), "Narrative rounds are not chronological"
    assert "Fighter1 came on with Longsword and caught Goblin clean" in narrative, "Hit was not narrated heroically"
    assert "Fighter1's Longsword struck Goblin for 7 points of slashing damage" in narrative, "Damage was not narrated"
    assert "Defenses robbed 3 points from the blow" in narrative, "Damage reduction evidence was lost"
    assert "Goblin stayed upright by spite alone, with 3 of 10 hit points" in narrative, "Target HP evidence was lost"
    assert "Goblin struck at Fighter1 with Scimitar, but the blow went wide" in narrative, "Miss was not narrated"
    assert "struck Fighter1 for 2 points of damage" in narrative, "Manual damage was not narrated safely"
    assert "Pallor reached Fighter1 through Healing Word, dragging back 5 hit points from the dark" in narrative, "Healing was not narrated"
    assert "A ward hardened around Fighter1" in narrative, "Temporary HP was not narrated"
    assert "Victory belonged to those still standing" in narrative, "Encounter outcome was not narrated"
    assert "promise of 10" not in narrative, "Resolved damage roll was repeated"
    assert "brought Healing Word to bear" not in narrative, "Resolved healing action was repeated"
    assert "Result not reported" not in narrative, f"Missing source details leaked into the story:\n{narrative}"
    assert "Lectern" not in narrative and "Fantasy Grounds" not in narrative, "Tool names leaked into the story"
    assert "Turn started" not in narrative, "System turn marker leaked into the story"

    page = CombatNarrativePage(repo)
    page.resize(1100, 700)
    page.show()
    app.processEvents()
    assert page.current_encounter_id == encounter_id, "Narrative page did not select the encounter"
    assert page.campaign_filter.findData(campaign_id) >= 0, "Narrative page is missing campaign selection"
    assert page.encounters.findData(encounter_id) >= 0, "Narrative page is missing encounter selection"
    assert page.event_count.text() == "11 source events", "Narrative source-event count is incorrect"
    assert "Round 1" in page.narrative_view.toPlainText(), "Narrative page did not render the story"

    window = MainWindow(database)
    names = [window.nav.item(index).text() for index in range(window.nav.count())]
    dashboard_index = names.index("Combat Dashboard")
    assert names[dashboard_index + 1] == "Combat Narrative", "Combat Narrative is not directly below Combat Dashboard"

    print("Combat Narrative test passed.")
finally:
    if page is not None:
        page.close()
    if window is not None:
        window.close()
    app.processEvents()
    shutil.rmtree(temp_dir, ignore_errors=True)
