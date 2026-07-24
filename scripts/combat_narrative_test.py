"""Offscreen regression checks for round-based Combat Narrative prose."""

from __future__ import annotations

import os
import re
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
from app.services.combat_narrative import CombatNarrativeBuilder, parse_combat_event
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
            (encounter_id, 2, "Fantasy Grounds", "Effect", " | Fighter1 | Effect state | Effect | Temporary HP changed from 5 to 2", "", None),
            (encounter_id, 2, "Goblin", "Damage", "3 | Fighter1 | Target HP 20/20 | Dagger | 3 damage applied", "piercing", 3),
            (encounter_id, 3, "Goblin Minion 2", "Damage Roll", "10 | Fighter1 | Against AC 16 | Fire Bolt | 10 damage rolled", "fire", None),
            (encounter_id, 3, "Manual / Unattributed", "Damage", "5 | Goblin Minion 1 | Target HP 2/7 | Damage | 5 damage applied", "fire", 5),
            (encounter_id, 3, "Fantasy Grounds", "Healing", "5 | Goblin Minion 1 | Target HP 7/7 | Healing | 5 healing applied", "", 5),
            (encounter_id, 4, "Wizard1", "Damage Roll", "15 | Goblin Minion 3 | Against AC 12 | Burning Hands | 15 damage rolled", "fire", None),
            (encounter_id, 4, "Wizard1", "Damage", "28 | Goblin Minion 3 | Target HP 0/30 | Burning Hands | 28 damage applied from 15 rolled (increased by 13)", "fire", 28),
            (encounter_id, 4, "Manual / Unattributed", "Damage", "15 | Goblin Minion 4 | Target HP 0/30 | Damage | 15 damage applied", "fire", 15),
            (encounter_id, 4, "Fantasy Grounds", "Encounter End", "Encounter ended: victory", "", None),
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
    assert "Fighter1 attacks Goblin with Longsword and lands a hit" in narrative, "Hit actor, target, action, or result was lost"
    assert "Fighter1's Longsword deals slashing damage to Goblin" in narrative, "Damage actor, action, result, or target was lost"
    assert "The effect is blunted, limiting its impact" in narrative, "Damage reduction evidence was lost"
    assert "The effect is devastating, leaving Goblin barely able to continue" in narrative, "Damage severity was not derived from the target's remaining endurance"
    assert "Goblin attacks Fighter1 with Scimitar, but the attack misses" in narrative, "Miss actor, target, action, or result was lost"
    assert "Fighter1 takes damage from an unidentified source" in narrative, "Unattributed damage was not represented safely"
    assert "The effect causes limited harm, and Fighter1 remains firmly in the fight" in narrative, "Minor damage consequence was not narrated"
    assert "Pallor's Healing Word restores Fighter1 to fighting form" in narrative, "Healing actor, action, result, or target was lost"
    assert "Fighter1 is bolstered by temporary vitality, providing an additional buffer against harm" in narrative, "Temporary vitality was not narrated with a grounded combat consequence"
    dagger_damage = "Goblin's Dagger deals piercing damage to Fighter1"
    absorbed_damage = "Fighter1's temporary vitality absorbs the impact and is weakened"
    assert dagger_damage in narrative and absorbed_damage in narrative, "Temporary-hit-point damage was not connected to its action"
    assert narrative.index(dagger_damage) < narrative.index(absorbed_damage), "Temporary-hit-point loss appeared before the damage that caused it"
    assert "The encounter ends in victory" in narrative, "Encounter outcome was not narrated"
    assert "promise of 10" not in narrative, "Resolved damage roll was repeated"
    assert "Goblin Minion 2 gathered Fire Bolt" not in narrative, "A provisional roll was attributed as a completed action"
    assert "Goblin Minion 1 takes fire damage from an unidentified source" in narrative, "Unattributed damage lost its target"
    assert "Goblin Minion 1 recovers and returns to fighting form" in narrative, "System healing implied an unsupported actor or action"
    assert "Wizard1's Burning Hands deals fire damage to Goblin Minion 4" in narrative, "A confirmed spell was not carried to its secondary target"
    assert "Goblin Minion 4 takes fire damage from an unidentified source" not in narrative, "Confirmed secondary spell damage remained unattributed"
    assert "brought Healing Word to bear" not in narrative, "Resolved healing action was repeated"
    assert not any(
        phrase in narrative.casefold()
        for phrase in ("ward", "spite", "from the dark", "nameless", "murderous precision")
    ), f"Unsupported literary language leaked into the D&D narrative:\n{narrative}"
    assert "Result not reported" not in narrative, f"Missing source details leaked into the story:\n{narrative}"
    assert "Lectern" not in narrative and "Fantasy Grounds" not in narrative, "Tool names leaked into the story"
    assert "Turn started" not in narrative, "System turn marker leaked into the story"
    numeric_prose = re.sub(r"## Round \d+", "## Round", narrative)
    numeric_prose = re.sub(r"\b(?:Fighter|Wizard|Cleric)\d+\b", "Combatant", numeric_prose)
    numeric_prose = re.sub(r"\bGoblin Minion \d+\b", "Goblin Minion", numeric_prose)
    assert not re.search(r"\d", numeric_prose), f"Mechanical numbers leaked into the narrative:\n{narrative}"

    capped_vulnerability = CombatNarrativeBuilder().event_sentence(parse_combat_event({
        "id": 99,
        "round": 4,
        "actor": "Wizard1",
        "action_type": "Damage",
        "details": "7 | Goblin | Target HP 0/7 | Fire Bolt | 7 damage applied from 6 rolled (increased by 1)",
        "damage_types": "fire",
        "damage_components_json": '[{"rolled":6,"applied":7,"resisted":0,"vulnerable":6}]',
        "amount": 7,
    }))
    assert "Wizard1's Fire Bolt exploits Goblin's vulnerability, greatly magnifying the effect" in capped_vulnerability, "Vulnerability was not connected to its actor and action"
    assert not re.search(r"\d", capped_vulnerability.replace("Wizard1", "")), "Vulnerability narration exposed mechanical quantities"

    resisted_damage = CombatNarrativeBuilder().event_sentence(parse_combat_event({
        "id": 100,
        "round": 4,
        "actor": "Wizard1",
        "action_type": "Damage",
        "details": "5 | Goblin | Target HP 2/7 | Fire Bolt | 5 damage applied from 10 rolled (reduced by 5)",
        "damage_types": "fire",
        "damage_components_json": '[{"rolled":10,"applied":5,"resisted":5,"vulnerable":0}]',
        "amount": 5,
    }))
    assert "Goblin's resistance blunts Wizard1's Fire Bolt, limiting its effect" in resisted_damage, "Confirmed resistance was not connected to its actor and action"
    assert not re.search(r"\d", resisted_damage.replace("Wizard1", "")), "Resistance narration exposed mechanical quantities"

    attributed_temporary_hp = CombatNarrativeBuilder().event_sentence(parse_combat_event({
        "id": 101,
        "round": 4,
        "actor": "Pallor",
        "action_type": "Effect",
        "details": " | Fighter1 | Effect state | Inspiring Leader | Temporary HP changed from 0 to 5",
        "damage_types": "",
        "amount": None,
    }))
    assert attributed_temporary_hp == (
        "Pallor's Inspiring Leader bolsters Fighter1 with temporary vitality, "
        "providing an additional buffer against harm."
    ), "A confirmed temporary-HP source was not carried into the narrative"

    severity_cases = (
        (20, 80, "causes limited harm"),
        (30, 60, "lands with telling force"),
        (40, 40, "hits hard"),
        (30, 10, "is devastating"),
        (10, 0, "overwhelms Goblin's remaining endurance"),
    )
    for case_id, (applied, remaining, expected) in enumerate(severity_cases, start=1):
        severity = CombatNarrativeBuilder().event_sentence(parse_combat_event({
            "id": 200 + case_id,
            "round": 5,
            "actor": "Fighter",
            "action_type": "Damage",
            "details": (
                f"{applied} | Goblin | Target HP {remaining}/100 | Longsword | "
                f"{applied} damage applied"
            ),
            "damage_types": "slashing",
            "amount": applied,
        }))
        assert expected in severity, f"Damage severity boundary failed: {severity}"
        assert not re.search(r"\d", severity), f"Damage severity exposed quantities: {severity}"

    page = CombatNarrativePage(repo)
    page.resize(1100, 700)
    page.show()
    app.processEvents()
    assert page.current_encounter_id == encounter_id, "Narrative page did not select the encounter"
    assert page.campaign_filter.findData(campaign_id) >= 0, "Narrative page is missing campaign selection"
    assert page.encounters.findData(encounter_id) >= 0, "Narrative page is missing encounter selection"
    assert page.event_count.text() == "19 source events", "Narrative source-event count is incorrect"
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
