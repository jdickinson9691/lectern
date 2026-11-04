from __future__ import annotations

import os
import sqlite3
import zipfile

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication

from app.database.schema import connect, initialize_database
from app.database.campaign_repository import CampaignRepository
from app.database.mission_planning_migration import migrate_mission_planning_v13
from app.services.mission_planning import DIFFICULTIES, MissionPlanningService
from app.services.player_export import PlayerExportService
from app.services.fantasy_grounds_export import FantasyGroundsModuleExporter
from app.services.story_mission_agent import StoryMissionAgent
from app.ui.mission_page import MissionPage


def _mission_database(tmp_path):
    db = tmp_path / 'mission.db'
    initialize_database(db)
    repo = CampaignRepository(db)
    repo.create_entity('CAM-ASHEN-0001', 'CAM', 'Ashen Company')
    repo.create_entity('LOC-TEST-0001', 'LOC', 'Greyhaven', visibility='player')
    repo.set_knowledge('LOC-TEST-0001', 'player', 'description', 'A refuge')
    repo.approve_player_knowledge('LOC-TEST-0001', 'description')
    repo.approve_entity('LOC-TEST-0001')
    agent = StoryMissionAgent(db)
    first = agent.draft_mission('Recover the Banner', 'Find the banner.',
                                source_entity_ids=['LOC-TEST-0001'])
    second = agent.draft_mission('Follow the Thread', 'Find the source.',
                                 source_entity_ids=['LOC-TEST-0001'])
    with connect(db) as conn:
        conn.execute("INSERT INTO monsters(name,challenge_rating,xp) VALUES('Bandit','1/8',25)")
        monster_id = conn.execute("SELECT id FROM monsters WHERE name='Bandit'").fetchone()[0]
    return db, agent, first, second, monster_id


def test_complete_mission_plan_exports_only_level_cap_and_difficulty(tmp_path):
    db, agent, first, second, monster_id = _mission_database(tmp_path)
    planning = agent.planning
    planning.save(first, max_total_levels=12, difficulty='risky',
                  lore='GM SECRET: the banner was lost at Redwater.',
                  loot='GM SECRET: a silver signet.', monsters=[(monster_id, 2)],
                  hooks=[(second, 'GM SECRET: the signet points to a later mission.')])
    plan = planning.get(first)
    assert plan['max_total_levels'] == 12
    assert plan['difficulty'] == 'risky'
    assert plan['monsters'][0]['challenge_rating'] == '1/8'
    assert plan['monsters'][0]['quantity'] == 2
    assert plan['catalog_xp_total'] == 50
    assert plan['hooks'][0]['future_mission_id'] == second
    agent.approve_mission(first)
    player = next(row for row in PlayerExportService(db).snapshot()['entities']
                  if row['id'] == first)
    assert player['knowledge'] == {
        'briefing': 'Find the banner.',
        'max_total_levels': '12',
        'difficulty': 'risky',
    }
    assert 'GM SECRET' not in str(PlayerExportService(db).snapshot())
    module = tmp_path / 'mission.mod'
    FantasyGroundsModuleExporter(db).export_mod(module)
    with zipfile.ZipFile(module) as archive:
        client = archive.read('client.xml').decode('utf-8')
    assert 'max_total_levels' in client and '12' in client
    assert 'difficulty' in client and 'risky' in client
    assert 'GM SECRET' not in client
    planning.save(first, max_total_levels=12, difficulty='risky',
                  lore='GM SECRET: revised lore.', loot='GM SECRET: revised loot.',
                  monsters=[(monster_id, 2)], hooks=[])
    assert agent.get_mission(first)['status'] == 'approved'
    planning.save(first, max_total_levels=12, difficulty='difficult',
                  lore='GM SECRET: revised lore.', loot='GM SECRET: revised loot.',
                  monsters=[(monster_id, 3)], hooks=[])
    assert agent.get_mission(first)['status'] == 'draft'
    assert first not in [row['id'] for row in PlayerExportService(db).snapshot()['entities']]


@pytest.mark.parametrize('difficulty', DIFFICULTIES)
def test_all_five_mission_difficulties_are_valid(tmp_path, difficulty):
    db, agent, first, _, _ = _mission_database(tmp_path)
    agent.planning.save(first, max_total_levels=8, difficulty=difficulty,
                        lore='Mission lore', loot='None', monsters=[], hooks=[])
    agent.approve_mission(first)
    assert agent.planning.get(first)['difficulty'] == difficulty


def test_incomplete_plan_cannot_be_approved(tmp_path):
    db, agent, first, _, _ = _mission_database(tmp_path)
    with pytest.raises(ValueError, match='level budget and mission difficulty'):
        agent.approve_mission(first)
    agent.planning.save(first, max_total_levels=8, difficulty='easy',
                        lore='Mission lore', loot='', monsters=[], hooks=[])
    with pytest.raises(ValueError, match='loot'):
        agent.approve_mission(first)
    assert first not in [row['id'] for row in PlayerExportService(db).snapshot()['entities']]


def test_legacy_approved_mission_private_edit_keeps_publication(tmp_path):
    db, agent, first, _, _ = _mission_database(tmp_path)
    with connect(db) as conn:
        conn.execute("UPDATE campaign_entities SET status='approved' WHERE entity_id=?", (first,))
        conn.execute("""UPDATE entity_knowledge SET status='approved' WHERE entity_id=?
            AND audience='player' AND field_key='briefing'""", (first,))
        conn.execute('DELETE FROM mission_plans WHERE mission_id=?', (first,))
    agent.planning.save(first, max_total_levels=None, difficulty=None,
                        lore='Private historical note', loot='None',
                        monsters=[], hooks=[])
    assert agent.get_mission(first)['status'] == 'approved'
    assert agent.planning.get(first)['lore'] == 'Private historical note'


def test_bad_roster_or_cross_campaign_hook_rolls_back_plan(tmp_path):
    db, agent, first, _, monster_id = _mission_database(tmp_path)
    agent.planning.save(first, max_total_levels=10, difficulty='normal',
                        lore='Original lore', loot='None',
                        monsters=[(monster_id, 1)], hooks=[])
    with pytest.raises(ValueError, match='not in the Lectern catalog'):
        agent.planning.save(first, max_total_levels=20, difficulty='deadly',
                            lore='Changed lore', loot='Gold',
                            monsters=[(999999, 1)], hooks=[])
    with connect(db) as conn:
        conn.execute("""INSERT INTO campaign_entities(entity_id,kind,name,campaign_id)
            VALUES('CAM-OTHER-0001','CAM','Other',NULL)""")
        conn.execute("""INSERT INTO campaign_entities(entity_id,kind,name,campaign_id)
            VALUES('MIS-OTHER-0001','MIS','Other Mission','CAM-OTHER-0001')""")
    with pytest.raises(KeyError):
        agent.planning.save(first, max_total_levels=20, difficulty='deadly',
                            lore='Changed lore', loot='Gold',
                            monsters=[(monster_id, 1)],
                            hooks=[('MIS-OTHER-0001', 'Cross campaign')])
    plan = agent.planning.get(first)
    assert plan['max_total_levels'] == 10
    assert plan['difficulty'] == 'normal'
    assert plan['lore'] == 'Original lore'
    assert plan['monsters'][0]['quantity'] == 1


def test_players_choose_any_roster_within_combined_level_cap(tmp_path):
    db, agent, first, _, _ = _mission_database(tmp_path)
    with connect(db) as conn:
        conn.execute("INSERT INTO players(name,level) VALUES('Ari',4),('Bex',5),('Cai',3)")
        ids = [row[0] for row in conn.execute('SELECT id FROM players ORDER BY name')]
    service = agent.planning
    service.save(first, max_total_levels=9, difficulty='normal',
                 lore='A company patrol', loot='None', monsters=[], hooks=[],
                 participants=ids[:2])
    assert service.get(first)['selected_level_total'] == 9
    with pytest.raises(ValueError, match='total 12 levels'):
        service.save(first, max_total_levels=9, difficulty='normal',
                     lore='Changed', loot='Gold', monsters=[], hooks=[],
                     participants=ids)
    assert service.get(first)['selected_level_total'] == 9
    service.save(first, max_total_levels=9, difficulty='normal',
                 lore='A company patrol', loot='None', monsters=[], hooks=[],
                 participants=[ids[1], ids[2]])
    assert service.get(first)['selected_level_total'] == 8
    with connect(db) as conn:
        conn.execute('UPDATE players SET level=7 WHERE id=?', (ids[1],))
    with pytest.raises(ValueError, match='exceed the mission level cap'):
        service.validate_for_approval(first)


def test_v13_upgrade_preserves_existing_mission_and_creates_empty_plan_schema(tmp_path):
    db, agent, first, _, _ = _mission_database(tmp_path)
    with connect(db) as conn:
        conn.execute('DROP TABLE mission_participants')
        conn.execute('DROP TABLE mission_hooks')
        conn.execute('DROP TABLE mission_monsters')
        conn.execute('DROP TABLE mission_plans')
        conn.execute("UPDATE metadata SET value='12' WHERE key='schema_version'")
        briefing = conn.execute("""SELECT content FROM entity_knowledge WHERE entity_id=?
            AND field_key='briefing'""", (first,)).fetchone()[0]
    initialize_database(db)
    with connect(db) as conn:
        assert conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0] == '14'
        assert conn.execute('SELECT COUNT(*) FROM mission_plans').fetchone()[0] == 0
        assert conn.execute("""SELECT content FROM entity_knowledge WHERE entity_id=?
            AND field_key='briefing'""", (first,)).fetchone()[0] == briefing
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []


def test_v13_migration_failure_rolls_back_new_tables(tmp_path):
    db = tmp_path / 'rollback.db'
    initialize_database(db)
    with connect(db) as conn:
        for table in ('mission_participants', 'mission_hooks',
                      'mission_monsters', 'mission_plans'):
            conn.execute(f'DROP TABLE {table}')
        conn.execute('CREATE TABLE mission_hooks(id INTEGER)')
        conn.execute("UPDATE metadata SET value='12' WHERE key='schema_version'")
    with connect(db) as conn:
        with pytest.raises(sqlite3.OperationalError):
            migrate_mission_planning_v13(conn)
        assert conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0] == '12'
        names = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        assert 'mission_plans' not in names
        assert 'mission_monsters' not in names
        assert 'mission_participants' not in names


def test_mission_screen_saves_roster_lore_loot_and_hook(tmp_path):
    app = QApplication.instance() or QApplication([])
    db, agent, first, second, monster_id = _mission_database(tmp_path)
    with connect(db) as conn:
        conn.execute("""INSERT INTO entity_knowledge
            (entity_id,audience,field_key,content,status)
            VALUES(?,'gm','background','Approved Redwater history','approved')""",
            (first,))
    page = MissionPage(db)
    assert page.current_id == first
    assert 'Approved Redwater history' in page.approved_fiction.toPlainText()
    page.level_budget.setValue(12)
    page.difficulty.setCurrentIndex(page.difficulty.findData('normal'))
    page.lore.setPlainText('Redwater retreat')
    page.loot.setPlainText('Recovered banner')
    page.monster_choice.setCurrentIndex(page.monster_choice.findData(monster_id))
    page.monster_quantity.setValue(2)
    page.add_monster()
    page.future_choice.setCurrentIndex(page.future_choice.findData(second))
    page.hook_text.setText('The signet leads onward')
    page.add_hook()
    page._save()
    plan = agent.planning.get(first)
    assert plan['max_total_levels'] == 12
    assert plan['monsters'][0]['quantity'] == 2
    assert plan['hooks'][0]['future_mission_id'] == second
    page.close()
