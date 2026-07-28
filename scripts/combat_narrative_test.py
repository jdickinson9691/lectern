"""Offscreen regression checks for round-based Combat Narrative prose."""

from __future__ import annotations

import json
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
from app.services.combat_narrative import (
    CombatNarrativeBuilder,
    NarrativeLibrary,
    NarrativeLibraryError,
    parse_combat_event,
)
from app.ui.main_window import CombatNarrativePage, MainWindow


temp_dir = Path(mkdtemp(prefix="lectern_combat_narrative_"))
app = QApplication.instance() or QApplication([])
page = None
window = None


def contains_sentence(text: str, *terms: str) -> bool:
    """Return whether one rendered sentence preserves every required fact."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return any(
        all(term.casefold() in sentence.casefold() for term in terms)
        for sentence in sentences
    )


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
    builder = CombatNarrativeBuilder()
    narrative = builder.build(log_rows, "Lectern Broken Gate")
    assert narrative == builder.build(log_rows, "Lectern Broken Gate"), "Narrative library selection is not deterministic"
    assert builder.library.schema_version == 1, "Unexpected narrative library schema"
    assert builder.library.content_version, "Narrative library content version is missing"
    assert builder.library.default_style == "heroic_military", "Offline narrative style default is incorrect"
    assert builder.library.available_styles == ("heroic_military",), "Unexpected narrative style registry"
    phrase_count = sum(
        len(phrases)
        for entries in builder.library.sections.values()
        for phrases in entries.values()
    )
    assert phrase_count >= 70, f"Narrative library is unexpectedly small: {phrase_count}"
    all_templates = " ".join(
        phrase
        for entries in builder.library.sections.values()
        for phrases in entries.values()
        for phrase in phrases
    )
    assert not re.search(r"\bdrives?\s+(?:at|into|against)\b", all_templates, re.IGNORECASE), (
        "The repetitive 'drives at' construction remains in the phrase library"
    )
    assert len(builder.library.sections["beat"]["attack_damage"]) >= 8, (
        "Attack-and-damage beat language is not varied enough"
    )
    assert len(builder.library.sections["attack"]["miss"]) >= 6, (
        "Miss language is not varied enough"
    )
    try:
        NarrativeLibrary(style="not-a-style")
    except NarrativeLibraryError:
        pass
    else:
        raise AssertionError("Unknown narrative styles were not rejected")
    unsafe_library = json.loads(builder.library.path.read_text(encoding="utf-8"))
    unsafe_library["styles"]["heroic_military"]["sections"]["attack"]["hit"][0] = (
        "Fantasy Grounds reports {actor} hitting {target}."
    )
    unsafe_path = temp_dir / "unsafe_narrative_library.json"
    unsafe_path.write_text(json.dumps(unsafe_library), encoding="utf-8")
    try:
        NarrativeLibrary(unsafe_path)
    except NarrativeLibraryError:
        pass
    else:
        raise AssertionError("Forbidden literal language was not rejected")
    assert narrative.index("## Round 1") < narrative.index("## Round 2"), "Narrative rounds are not chronological"
    hit_sentence = next(
        sentence
        for sentence in re.split(r"(?<=[.!?])\s+", narrative)
        if all(term in sentence for term in ("Fighter1", "Goblin", "Longsword"))
        and any(
            result in sentence
            for result in ("lands a hit", "finds its mark", "solid hit", "attack connects")
        )
    )
    assert hit_sentence, "Hit actor, target, action, or result was lost"
    assert contains_sentence(narrative, "Fighter1", "Goblin", "Longsword", "slashing damage"), "Damage actor, action, result, or target was lost"
    assert "Hit (" not in narrative, "Attack mechanics leaked from a source row"
    fighter_attack_sentences = [
        sentence
        for sentence in re.split(r"(?<=[.!?])\s+", narrative)
        if all(term in sentence for term in ("Fighter1", "Goblin", "Longsword"))
    ]
    assert len(fighter_attack_sentences) == 1, "Linked attack and damage were not coalesced into one beat sentence"
    assert (
        contains_sentence(narrative, "damage", "blunted")
        or contains_sentence(narrative, "damage", "turned aside")
    ), "Damage reduction evidence was lost"
    assert (
        contains_sentence(narrative, "Goblin", "barely able")
        or contains_sentence(narrative, "Goblin", "nearly exhausts")
    ), "Damage severity was not derived from the target's remaining endurance"
    miss_sentence = next(
        sentence
        for sentence in re.split(r"(?<=[.!?])\s+", narrative)
        if all(term in sentence for term in ("Goblin", "Fighter1", "Scimitar"))
        and any(
            result in sentence
            for result in (
                "misses",
                "fails to find",
                "does not connect",
                "cannot land",
                "goes wide",
                "finds none",
            )
        )
    )
    assert miss_sentence, "Miss actor, target, action, or result was lost"
    assert contains_sentence(narrative, "Fighter1", "damage", "unidentified"), "Unattributed damage was not represented safely"
    assert (
        contains_sentence(narrative, "Fighter1", "limited harm")
        or contains_sentence(narrative, "Fighter1", "light enough")
    ), "Minor damage consequence was not narrated"
    assert contains_sentence(narrative, "Pallor", "Healing Word", "Fighter1", "fighting form"), "Healing actor, action, result, or target was lost"
    assert contains_sentence(narrative, "Fighter1", "temporary vitality"), "Temporary vitality was not narrated with a grounded combat consequence"
    dagger_sentence = next(
        sentence
        for sentence in re.split(r"(?<=[.!?])\s+", narrative)
        if all(term in sentence for term in ("Goblin", "Dagger", "Fighter1", "piercing damage"))
    )
    absorbed_sentence = next(
        sentence
        for sentence in re.split(r"(?<=[.!?])\s+", narrative)
        if "fighter1" in sentence.casefold()
        and "temporary vitality" in sentence.casefold()
        and "impact" in sentence.casefold()
    )
    assert narrative.index(dagger_sentence) < narrative.index(absorbed_sentence), "Temporary-hit-point loss appeared before the damage that caused it"
    assert contains_sentence(narrative, "victory"), "Encounter outcome was not narrated"
    assert "promise of 10" not in narrative, "Resolved damage roll was repeated"
    assert "Goblin Minion 2 gathered Fire Bolt" not in narrative, "A provisional roll was attributed as a completed action"
    assert contains_sentence(narrative, "Goblin Minion 1", "fire damage", "unidentified"), "Unattributed damage lost its target"
    assert (
        contains_sentence(narrative, "Goblin Minion 1", "recovers", "fighting form")
        or contains_sentence(narrative, "Goblin Minion 1", "rallies", "fighting form")
    ), "System healing implied an unsupported actor or action"
    assert contains_sentence(narrative, "Wizard1", "Burning Hands", "Goblin Minion 4", "fire damage"), "A confirmed spell was not carried to its secondary target"
    assert not contains_sentence(narrative, "Goblin Minion 4", "fire damage", "unidentified"), "Confirmed secondary spell damage remained unattributed"
    assert "brought Healing Word to bear" not in narrative, "Resolved healing action was repeated"
    assert not re.search(
        r"\b(?:ward|spite|nameless)\b|from the dark|murderous precision",
        narrative,
        re.IGNORECASE,
    ), f"Unsupported literary language leaked into the D&D narrative:\n{narrative}"
    round_openings = [
        builder.round_opening(round_number, round_number == 1)
        for round_number in range(1, 9)
    ]
    assert len(set(round_openings)) >= 4, "Round-to-round narrative transitions were not varied"
    assert "Result not reported" not in narrative, f"Missing source details leaked into the story:\n{narrative}"
    assert "Lectern" not in narrative and "Fantasy Grounds" not in narrative, "Tool names leaked into the story"
    assert "Turn started" not in narrative, "System turn marker leaked into the story"
    assert not re.search(r"\bdrives?\s+(?:at|into|against)\b", narrative, re.IGNORECASE), (
        f"Repetitive drive phrasing remained in the narrative:\n{narrative}"
    )
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
    assert contains_sentence(capped_vulnerability, "Wizard1", "Fire Bolt", "Goblin", "vulnerability"), "Vulnerability was not connected to its actor and action"
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
    assert contains_sentence(resisted_damage, "Goblin", "resistance", "Wizard1", "Fire Bolt"), "Confirmed resistance was not connected to its actor and action"
    assert not re.search(r"\d", resisted_damage.replace("Wizard1", "")), "Resistance narration exposed mechanical quantities"

    linked_save_beat = [
        parse_combat_event({
            "id": 110,
            "round": 4,
            "actor": "Wizard1",
            "action_type": "Save",
            "details": "11 | Goblin | Against DC 14 | Burning Hands | Failure (11 vs DC 14)",
            "result_code": "save_failure",
        }),
        parse_combat_event({
            "id": 111,
            "round": 4,
            "actor": "Wizard1",
            "action_type": "Damage",
            "details": "6 | Goblin | Target HP 1/7 | Burning Hands | 6 damage applied",
            "damage_types": "fire",
            "amount": 6,
        }),
        parse_combat_event({
            "id": 112,
            "round": 4,
            "actor": "Wizard1",
            "action_type": "Effect",
            "details": " | Goblin | Effect state | Burning Hands | Effect added to Goblin: Burning Hands",
        }),
    ]
    linked_save_beats = builder.coalesce_events(linked_save_beat)
    assert len(linked_save_beats) == 1, "Related save, damage, and effect rows did not form one beat"
    linked_save_text = builder.beat_sentence(linked_save_beats[0])
    assert contains_sentence(
        linked_save_text,
        "Wizard1",
        "Burning Hands",
        "Goblin",
        "fire damage",
    ), "Coalesced save beat lost actor, action, target, or damage type"
    assert any(
        term in linked_save_text.casefold()
        for term in ("fails to withstand", "overcomes", "cannot resist", "fails to resist")
    ), "Coalesced save beat lost the authoritative failed-save outcome"
    assert "DC 14" not in linked_save_text and "11" not in linked_save_text, (
        "Save mechanics leaked into coalesced prose"
    )

    linked_healing_beat = [
        parse_combat_event({
            "id": 120,
            "round": 4,
            "actor": "Paladin1",
            "action_type": "Action",
            "details": " | Fighter1 |  | Lay on Hands | Result not reported",
        }),
        parse_combat_event({
            "id": 121,
            "round": 4,
            "actor": "Paladin1",
            "action_type": "Healing",
            "details": "5 | Fighter1 | Target HP 8/10 | Lay on Hands | 5 healing applied",
            "amount": 5,
        }),
    ]
    linked_healing_beats = builder.coalesce_events(linked_healing_beat)
    assert len(linked_healing_beats) == 1, "Related action and healing rows did not form one beat"
    linked_healing_text = builder.beat_sentence(linked_healing_beats[0])
    assert contains_sentence(
        linked_healing_text,
        "Paladin1",
        "Lay on Hands",
        "Fighter1",
    ), "Coalesced healing beat lost actor, action, or target"
    assert linked_healing_text.count("Lay on Hands") == 1, "Healing action was repeated"

    contributed_attack = [
        parse_combat_event({
            "id": 130,
            "round": 4,
            "actor": "Ranger1",
            "action_type": "Attack",
            "details": "21 | Kobold | Against AC 14 | Longbow | Hit (21 vs AC 14)",
            "result_code": "hit",
        }),
        parse_combat_event({
            "id": 131,
            "round": 4,
            "actor": "Ranger1",
            "action_type": "Damage",
            "details": (
                "12 | Kobold | Target HP 0/7 | Longbow with Hunter's Mark | "
                "7 damage applied"
            ),
            "damage_types": "piercing, force",
            "amount": 7,
        }),
    ]
    contributed_beats = builder.coalesce_events(contributed_attack)
    assert len(contributed_beats) == 1, (
        "A named damage contributor separated the resolution from its attack"
    )
    contributed_text = builder.beat_sentence(contributed_beats[0])
    assert contains_sentence(
        contributed_text,
        "Ranger1",
        "Longbow",
        "Hunter's Mark",
        "Kobold",
        "piercing and force damage",
    ), "Coalesced attack lost its named damage contributor or damage types"
    assert "with Longbow with" not in contributed_text, (
        "Named damage contributor produced a repetitive action construction"
    )

    attributed_temporary_hp = CombatNarrativeBuilder().event_sentence(parse_combat_event({
        "id": 101,
        "round": 4,
        "actor": "Pallor",
        "action_type": "Effect",
        "details": " | Fighter1 | Effect state | Inspiring Leader | Temporary HP changed from 0 to 5",
        "damage_types": "",
        "amount": None,
    }))
    assert contains_sentence(
        attributed_temporary_hp,
        "Pallor",
        "Inspiring Leader",
        "Fighter1",
        "temporary vitality",
    ), "A confirmed temporary-HP source was not carried into the narrative"

    test5_rows = [
        {
            "id": 301,
            "round": 1,
            "actor": "Warlock1",
            "action_type": "Effect",
            "details": (
                " | Warlock1 | Effect added | Armor of Shadows | "
                "Effect added to Warlock1: AC: 3; [D: 8 hours]"
            ),
        },
        {
            "id": 302,
            "round": 1,
            "actor": "Rogue1",
            "action_type": "Effect",
            "details": (
                " | Rogue1 | Effect added | Effect | "
                "Effect added to Rogue1: Sneak Attack; DMG: 1d6"
            ),
        },
        {
            "id": 303,
            "round": 1,
            "actor": "Rogue1",
            "action_type": "Effect",
            "details": (
                " | Rogue1 | Effect ended | Effect | "
                "Effect ended on Rogue1: Sneak Attack; DMG: 1d6"
            ),
        },
        {
            "id": 304,
            "round": 1,
            "actor": "Sorcerer1",
            "action_type": "Effect",
            "details": (
                " | Sorcerer1 | Effect added | Effect | "
                "Effect added to Sorcerer1: Innate Sorcery; SAVEDC: 1; ADVATK"
            ),
        },
        {
            "id": 305,
            "round": 1,
            "actor": "Sorcerer1",
            "action_type": "Attack",
            "details": (
                "19 | Berserker | Against AC 13 | Ray of Sickness | "
                "Hit (19 vs AC 13)"
            ),
            "result_code": "hit",
        },
        {
            "id": 306,
            "round": 1,
            "actor": "Sorcerer1",
            "action_type": "Damage",
            "details": (
                "11 | Berserker | Target HP 56/67 | Ray of Sickness | "
                "11 damage applied"
            ),
            "damage_types": "poison",
            "amount": 11,
        },
        {
            "id": 307,
            "round": 1,
            "actor": "Sorcerer1",
            "action_type": "Effect",
            "details": (
                " | Berserker | Effect added | Effect | "
                "Effect added to Berserker: Poisoned"
            ),
        },
        {
            "id": 308,
            "round": 1,
            "actor": "Bard1",
            "action_type": "Effect",
            "details": (
                " | Warlock1 | Effect added | Effect | "
                "Effect added to Warlock1: Bardic Inspiration Die "
                "(Attack, Save, Check rolls); [D: 1 hour]"
            ),
        },
        {
            "id": 309,
            "round": 1,
            "actor": "Ranger1",
            "action_type": "Effect",
            "details": (
                " | Berserker | Effect added | Effect | "
                "Effect added to Berserker: Hunter's Mark; (C); [D: 1 hour]"
            ),
        },
        {
            "id": 310,
            "round": 1,
            "actor": "Ranger1",
            "action_type": "Effect",
            "details": (
                " | Ranger1 | Effect added | Effect | "
                "Effect added to Ranger1: IFT: CUSTOM(Hunter's Mark); "
                "DMG: 1d6 force; (C); [D: 1 hour]"
            ),
        },
        {
            "id": 311,
            "round": 1,
            "actor": "Ranger1",
            "action_type": "Damage",
            "details": (
                "9 | Berserker | Target HP 47/67 | Longbow | "
                "9 damage applied from 9 rolled"
            ),
            "damage_types": "piercing",
            "amount": 9,
        },
        {
            "id": 312,
            "round": 1,
            "actor": "Ranger1",
            "action_type": "Attack",
            "details": (
                "16 | Ranger1 | Against AC 16 | Longbow | "
                "Hit (16 vs AC 16)"
            ),
            "result_code": "hit",
        },
        {
            "id": 313,
            "round": 1,
            "actor": "Ranger1",
            "action_type": "Damage",
            "details": (
                "9 | Ranger1 | Target HP 3/12 | Longbow | "
                "9 damage applied from 9 rolled"
            ),
            "damage_types": "piercing",
            "amount": 9,
        },
        {
            "id": 314,
            "round": 1,
            "actor": "Ranger1",
            "action_type": "Concentration Check",
            "details": (
                "22 (dice 20; modifiers +2) | Ranger1 | "
                "Concentration DC not reported | Concentration | Outcome not reported"
            ),
        },
    ]
    test5_narrative = builder.build(test5_rows, "Test5", "unresolved")
    assert contains_sentence(
        test5_narrative,
        "Warlock1",
        "Armor of Shadows",
        "defenses",
    ), "Armor of Shadows was reduced to raw AC syntax"
    assert contains_sentence(
        test5_narrative,
        "Rogue1",
        "Sneak Attack",
        "readies",
    ) or contains_sentence(
        test5_narrative,
        "Rogue1",
        "Sneak Attack",
        "prepares",
    ), "Sneak Attack activation was not narrated as a readied ability"
    assert contains_sentence(
        test5_narrative,
        "Sorcerer1",
        "Innate Sorcery",
    ), "Innate Sorcery lost its authoritative name"
    assert (
        "Sorcerer1 invokes Innate Sorcery, bolstering Sorcerer1"
        in test5_narrative
        or "Sorcerer1 calls on Innate Sorcery, sharpening Sorcerer1's"
        in test5_narrative
    ), "Innate Sorcery was not rendered as a complete grammatical sentence"
    assert contains_sentence(
        test5_narrative,
        "Ray of Sickness",
        "Berserker",
        "poisoned",
    ), "Ray of Sickness was not coalesced with its Poisoned condition"
    assert contains_sentence(
        test5_narrative,
        "Bard1",
        "Bardic Inspiration",
        "Warlock1",
    ), "Bardic Inspiration source or target was lost"
    assert test5_narrative.count("Hunter's Mark") == 1, (
        "Hunter's Mark's helper effect was narrated as a second event"
    )
    assert contains_sentence(
        test5_narrative,
        "Ranger1",
        "Longbow",
        "Ranger1",
        "piercing damage",
    ), "The authoritative Test5 self-targeted damage was concealed"
    assert "Ranger1 meets Ranger1" not in test5_narrative, (
        "A self-targeted attack used ordinary opponent-facing language"
    )
    assert (
        "Ranger1's Longbow strikes Ranger1"
        in test5_narrative
        or "Ranger1 is struck by Ranger1's own Longbow"
        in test5_narrative
    ), "The self-targeted Longbow damage was not narrated neutrally"
    assert contains_sentence(
        test5_narrative,
        "Ranger1",
        "concentration",
    ), "The Test5 concentration check disappeared from the narrative"
    assert not re.search(
        r"\b(?:SAVEDC|ADVATK|DMG|IFT|AC)\s*:|Effect (?:added|ended)",
        test5_narrative,
        re.IGNORECASE,
    ), f"Raw effect mechanics leaked into the Test5 narrative:\n{test5_narrative}"
    test5_numeric_prose = re.sub(r"## Round \d+", "## Round", test5_narrative)
    test5_numeric_prose = re.sub(
        r"\b(?:Warlock|Rogue|Sorcerer|Bard|Ranger)\d+\b",
        "Combatant",
        test5_numeric_prose,
    )
    assert not re.search(r"\d", test5_numeric_prose), (
        f"Mechanical numbers leaked into the Test5 narrative:\n{test5_narrative}"
    )

    severity_cases = (
        (20, 80, ("limited harm", "light enough")),
        (30, 60, ("telling force", "weakens")),
        (40, 40, ("hits hard", "badly weakened")),
        (30, 10, ("devastating", "nearly exhausts")),
        (10, 0, ("overwhelms", "exhausts")),
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
        assert any(phrase in severity for phrase in expected), f"Damage severity boundary failed: {severity}"
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
