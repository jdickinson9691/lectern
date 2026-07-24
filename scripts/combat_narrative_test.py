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
            (encounter_id, 1, "Fighter1", "Turn Start", "Turn started", "", None),
            (encounter_id, 1, "Fighter1", "Attack", "18 | Goblin | Against AC 14 | Longsword | Hit (18 vs AC 14)", "", None),
            (encounter_id, 1, "Fighter1", "Damage", "7 | Goblin | Target HP 3/10 | Longsword | 7 damage applied from 10 rolled (reduced by 3)", "slashing", 7),
            (encounter_id, 2, "Goblin", "Attack", "9 | Fighter1 | Against AC 16 | Scimitar | Miss (9 vs AC 16)", "", None),
            (encounter_id, 2, "Manual / Unattributed", "Damage", "2 | Fighter1 | Target HP 18/20 | Damage | 2 damage applied", "unknown", 2),
            (encounter_id, 2, "Pallor", "Healing", "5 | Fighter1 | Target HP 20/20 | Healing Word | 5 healing applied", "", 5),
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
    narrative = CombatNarrativeBuilder().build(log_rows, "The Broken Gate")
    assert narrative.index("## Round 1") < narrative.index("## Round 2"), "Narrative rounds are not chronological"
    assert "Fighter1 attacked Goblin with Longsword and found an opening" in narrative, "Hit was not narrated"
    assert "Fighter1's Longsword dealt 7 slashing damage to Goblin" in narrative, "Damage was not narrated"
    assert "after defenses reduced the impact by 3" in narrative, "Damage reduction evidence was lost"
    assert "leaving the target at 3 of 10 hit points" in narrative, "Target HP evidence was lost"
    assert "Goblin attacked Fighter1 with Scimitar, but the strike failed to connect" in narrative, "Miss was not narrated"
    assert "An unattributed effect dealt 2 damage to Fighter1" in narrative, "Manual damage was not narrated safely"
    assert "Pallor restored 5 hit points to Fighter1" in narrative, "Healing was not narrated"
    assert "Turn started" not in narrative, "System turn marker leaked into the story"

    page = CombatNarrativePage(repo)
    page.resize(1100, 700)
    page.show()
    app.processEvents()
    assert page.current_encounter_id == encounter_id, "Narrative page did not select the encounter"
    assert page.campaign_filter.findData(campaign_id) >= 0, "Narrative page is missing campaign selection"
    assert page.encounters.findData(encounter_id) >= 0, "Narrative page is missing encounter selection"
    assert page.event_count.text() == "5 narrative events", "Narrative event count includes turn markers"
    assert "The Broken Gate" in page.narrative_view.toPlainText(), "Narrative page did not render the story"

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
