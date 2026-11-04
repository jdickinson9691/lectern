from __future__ import annotations

import sqlite3

import pytest

from app.database.campaign_repository import CampaignRepository
from app.database.mission_experience_migration import migrate_mission_experience_v14
from app.database.schema import connect, initialize_database
from app.services.mission_experience import MissionExperienceService, level_for_xp
from app.services.player_export import PlayerExportService
from app.services.story_mission_agent import StoryMissionAgent


def _mission(tmp_path):
    db = tmp_path / 'xp.db'
    initialize_database(db)
    repo = CampaignRepository(db)
    repo.create_entity('CAM-ASHEN-0001', 'CAM', 'Ashen Company')
    repo.create_entity('LOC-TEST-0001', 'LOC', 'Camp', visibility='player')
    repo.set_knowledge('LOC-TEST-0001', 'player', 'description', 'A camp')
    repo.approve_player_knowledge('LOC-TEST-0001', 'description')
    repo.approve_entity('LOC-TEST-0001')
    agent = StoryMissionAgent(db)
    mission = agent.draft_mission('First patrol', 'Patrol the road.',
                                  source_entity_ids=['LOC-TEST-0001'])
    with connect(db) as conn:
        conn.execute("INSERT INTO players(name,level) VALUES('Ari',1),('Bex',1),('Cai',1)")
        ids = [row[0] for row in conn.execute('SELECT id FROM players ORDER BY id')]
    agent.planning.save(mission, max_total_levels=3, difficulty='normal',
                        lore='Check the old road', loot='None', monsters=[], hooks=[],
                        participants=ids)
    agent.approve_mission(mission)
    return db, mission, ids


def test_clean_database_has_xp_ledger_and_2024_thresholds(tmp_path):
    db = tmp_path / 'clean.db'
    initialize_database(db)
    with connect(db) as conn:
        assert conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0] == '14'
        assert conn.execute('SELECT count(*) FROM mission_xp_awards').fetchone()[0] == 0
    assert level_for_xp(299) == 1
    assert level_for_xp(300) == 2
    assert level_for_xp(900) == 3
    assert level_for_xp(355000) == 20


def test_mission_award_is_equal_audited_and_not_a_milestone(tmp_path):
    db, mission, ids = _mission(tmp_path)
    xp = MissionExperienceService(db)
    awards = xp.award(mission, 901, 'Patrol, negotiation, and threat neutralized')
    assert [row['xp'] for row in awards] == [301, 300, 300]
    assert [xp.character(player_id)['earned_level'] for player_id in ids] == [2, 2, 2]
    with connect(db) as conn:
        assert [row[0] for row in conn.execute('SELECT level FROM players ORDER BY id')] == [1, 1, 1]
        assert conn.execute("SELECT count(*) FROM entity_audit WHERE entity_id=? AND action='mission_xp_award'", (mission,)).fetchone()[0] == 1
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
    with pytest.raises(ValueError, match='already awarded'):
        xp.award(mission, 901, 'Duplicate')
    with pytest.raises(ValueError, match='roster and level cap are locked'):
        StoryMissionAgent(db).planning.save(
            mission, max_total_levels=3, difficulty='normal', lore='Changed', loot='None',
            monsters=[], hooks=[], participants=ids[:2])
    assert 'Patrol, negotiation' not in str(PlayerExportService(db).snapshot())


def test_bad_award_rolls_back_and_preserves_existing_player_data(tmp_path):
    db, mission, ids = _mission(tmp_path)
    xp = MissionExperienceService(db)
    with pytest.raises(ValueError, match='at least 1 XP'):
        xp.award(mission, 2, 'Too little')
    with pytest.raises(ValueError, match='Describe'):
        xp.award(mission, 300, ' ')
    assert xp.mission_awards(mission) == []
    with connect(db) as conn:
        assert conn.execute('SELECT count(*) FROM character_xp_baselines').fetchone()[0] == 0
        assert conn.execute('SELECT count(*) FROM players').fetchone()[0] == 3
    xp.award(mission, 900, 'Road secured')
    assert xp.character(ids[0])['total_xp'] == 300
    initialize_database(db)
    assert xp.character(ids[0])['total_xp'] == 300


def test_upgrade_from_v13_and_migration_failure(tmp_path):
    db, mission, _ = _mission(tmp_path)
    with connect(db) as conn:
        conn.execute('DROP TABLE mission_xp_awards')
        conn.execute('DROP TABLE character_xp_baselines')
        conn.execute("UPDATE metadata SET value='13' WHERE key='schema_version'")
    initialize_database(db)
    with connect(db) as conn:
        assert conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0] == '14'
        assert conn.execute('SELECT name FROM campaign_entities WHERE entity_id=?', (mission,)).fetchone()[0] == 'First patrol'
        conn.execute('DROP TABLE mission_xp_awards')
        conn.execute('DROP TABLE character_xp_baselines')
        conn.execute('CREATE TABLE mission_xp_awards(mission_id TEXT PRIMARY KEY)')
        conn.execute("UPDATE metadata SET value='13' WHERE key='schema_version'")
    with connect(db) as conn:
        with pytest.raises(sqlite3.OperationalError):
            migrate_mission_experience_v14(conn)
        assert conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0] == '13'
        assert conn.execute("SELECT name FROM sqlite_master WHERE name='character_xp_baselines'").fetchone() is None
