from __future__ import annotations

import os
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch
import sqlite3

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication

from app.database.schema import connect, initialize_database
from app.database.repositories import Repository
from app.database.campaign_workspace_migration import migrate_campaign_workspaces_v12
from app.services.campaign_canon import CampaignCanonAgent
from app.services.campaign_workflow import progress, source_dependencies
from app.services.player_export import PlayerExportService
from app.services.story_editor import StoryService
from app.services.story_mission_agent import StoryMissionAgent
from app.services.world_agents import NPCAgent
from app.ui.campaign_workflow_page import CanonLorePage
from app.ui.main_window import MainWindow
from app.ui.main_window import CampaignDashboardPage


def ashen_database(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setenv('LECTERN_ASHEN_COMPANY', '1')
    db = tmp_path / 'campaign.db'
    initialize_database(db)
    return db


def test_campaign_root_lore_moves_from_proposal_to_approved_private_canon(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    db = ashen_database(tmp_path, monkeypatch)
    agent = CampaignCanonAgent(db)
    proposal = agent.submit_for_review(
        'CAM-ASHEN-0001', 'gm', 'origin', 'The Company survived Redwater.',
        source_type='document', source_ref='campaign-notes:1')
    assert progress(db)['pending_proposals'] == 1
    agent.resolve(proposal, 'accept', reviewer='gm')
    page = CanonLorePage(db, lambda: None)
    assert page.entities.currentData() == 'CAM-ASHEN-0001'
    assert page.facts.item(0, 2).text() == 'draft'
    page.facts.selectRow(0)
    page.approve_selected()
    with connect(db) as conn:
        row = conn.execute("""SELECT status FROM entity_knowledge WHERE
            entity_id='CAM-ASHEN-0001' AND audience='gm' AND field_key='origin'""").fetchone()
        assert row['status'] == 'approved'
    assert progress(db)['lore']['approved'] == 1
    assert PlayerExportService(db).snapshot()['entities'] == []
    page.close()


def test_sourced_record_warns_when_approved_source_returns_to_draft(tmp_path, monkeypatch):
    db = ashen_database(tmp_path, monkeypatch)
    stories = StoryService(db)
    source = stories.create_draft('Company Charter', 'We endure.')
    stories.approve(source)
    npc = NPCAgent(db).draft('Mara Venn', 'Company lieutenant.',
                             source_entity_ids=[source])
    assert source_dependencies(db, npc)[0]['warning'] == ''
    stories.save_draft(source, 'Company Charter', 'We endure together.')
    assert source_dependencies(db, npc)[0]['warning'] == 'Source is no longer approved'
    stories.approve(source)
    assert source_dependencies(db, npc)[0]['warning'] == 'Source changed after this record'


def test_approved_player_lore_can_source_story_without_gm_secret(tmp_path, monkeypatch):
    db = ashen_database(tmp_path, monkeypatch)
    agent = CampaignCanonAgent(db)
    for audience, key, content in (
        ('player', 'history', 'The Company survived Redwater.'),
        ('gm', 'secret', 'GM ONLY: the standard is cursed.'),
    ):
        proposal = agent.submit_for_review('CAM-ASHEN-0001', audience, key, content,
                                            source_type='document', source_ref=f'notes:{key}')
        agent.resolve(proposal, 'accept')
        from app.database.campaign_repository import CampaignRepository
        CampaignRepository(db).approve_knowledge('CAM-ASHEN-0001', audience, key)
    writer = StoryMissionAgent(db)
    assert 'CAM-ASHEN-0001' in [row['entity_id'] for row in writer.available_sources()]
    context = writer.approved_context(['CAM-ASHEN-0001'])
    assert context[0]['facts'] == {'history': 'The Company survived Redwater.'}
    assert 'GM ONLY' not in str(context)
    story = writer.draft_story('After Redwater', 'We march on.',
                               source_entity_ids=['CAM-ASHEN-0001'])
    assert source_dependencies(db, story)[0]['warning'] == ''
    StoryService(db).approve(story)
    assert 'GM ONLY' not in str(PlayerExportService(db).snapshot())


def test_campaign_navigation_follows_authoring_order(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    db = ashen_database(tmp_path, monkeypatch)
    window = MainWindow(db)
    names = [window.nav.item(index).text() for index in range(window.nav.count())]
    expected = ['Campaigns', 'Campaign Plan', 'Canon & Lore', 'Fiction Agent', 'Canon Review (GM)',
                'Stories', 'Story Drafts', 'Campaign Locations', 'Campaign Factions',
                'Campaign NPCs', 'Mission Drafts', 'Missions', 'Review & Publish']
    assert names[:len(expected)] == expected
    window.navigate_to('Campaign Plan')
    assert window.nav.currentItem().text() == 'Campaign Plan'
    window.close()


def test_new_campaigns_get_distinct_permanent_roots_and_content_launcher(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.delenv('LECTERN_ASHEN_COMPANY', raising=False)
    db = tmp_path / 'data' / 'campaign_manager.db'
    initialize_database(db)
    repo = Repository(db)
    first = repo.create_campaign('North March')
    second = repo.create_campaign('South March')
    with connect(db) as conn:
        roots = {row['campaign_id']: row['entity_id'] for row in conn.execute(
            'SELECT campaign_id,entity_id FROM campaign_workspace_links')}
    assert roots == {first: f'CAM-LECTERN-{first:04d}',
                     second: f'CAM-LECTERN-{second:04d}'}
    page = CampaignDashboardPage(repo, lambda: None)
    page.campaigns.setCurrentIndex(page.campaigns.findData(second))
    with patch('app.ui.main_window.subprocess.Popen') as launch:
        page.open_campaign_content()
    assert launch.call_args.kwargs['env']['LECTERN_CANON_CAMPAIGN_ID'] == roots[second]
    assert launch.call_args.kwargs['env']['LECTERN_DATA_DIR'] == str(db.parent.parent)
    page.close()


def test_two_campaign_content_processes_do_not_mix_records_or_exports(tmp_path, monkeypatch):
    monkeypatch.delenv('LECTERN_ASHEN_COMPANY', raising=False)
    db = tmp_path / 'multi.db'
    initialize_database(db)
    repo = Repository(db)
    alpha = repo.create_campaign('Alpha')
    beta = repo.create_campaign('Beta')
    roots = [f'CAM-LECTERN-{number:04d}' for number in (alpha, beta)]
    code = '''import json,sys
from pathlib import Path
from app.services.story_editor import StoryService
from app.services.player_export import PlayerExportService
from app.services.fantasy_grounds_export import FantasyGroundsModuleExporter
db=Path(sys.argv[1]); title=sys.argv[2]
stories=StoryService(db)
assert stories.list_stories() == []
entity_id=stories.create_draft(title,title+' public','GM SECRET '+title)
stories.approve(entity_id)
snapshot=PlayerExportService(db).snapshot()
print(json.dumps({'titles':[e['name'] for e in snapshot['entities']],
                  'module':FantasyGroundsModuleExporter(db).module_name,
                  'gm_leak':'GM SECRET' in str(snapshot)}))'''
    for root, name in zip(roots, ('Alpha Story', 'Beta Story')):
        env = os.environ.copy()
        env['LECTERN_CANON_CAMPAIGN_ID'] = root
        completed = subprocess.run([sys.executable, '-c', code, str(db), name],
                                   cwd=Path(__file__).resolve().parents[1], env=env,
                                   text=True, capture_output=True, check=True)
        result = json.loads(completed.stdout)
        assert result['titles'] == [name]
        assert result['module'] == f'Lectern {name.split()[0]} Players'
        assert not result['gm_leak']


def test_upgrade_backfills_campaign_roots_without_changing_existing_rows(tmp_path, monkeypatch):
    monkeypatch.delenv('LECTERN_ASHEN_COMPANY', raising=False)
    db = tmp_path / 'old.db'
    initialize_database(db)
    with connect(db) as conn:
        conn.execute("INSERT INTO campaigns(name,source_type) VALUES('Legacy','local')")
        campaign_id = conn.execute("SELECT id FROM campaigns WHERE name='Legacy'").fetchone()[0]
        conn.execute("INSERT INTO players(name,notes) VALUES('Veteran','preserve me')")
        conn.execute("UPDATE metadata SET value='11' WHERE key='schema_version'")
    initialize_database(db)
    initialize_database(db)
    with connect(db) as conn:
        assert conn.execute('SELECT entity_id FROM campaign_workspace_links WHERE campaign_id=?',
                            (campaign_id,)).fetchone()[0] == f'CAM-LECTERN-{campaign_id:04d}'
        assert conn.execute("SELECT notes FROM players WHERE name='Veteran'").fetchone()[0] == 'preserve me'
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []


def test_campaign_root_migration_rolls_back_partial_backfill(tmp_path, monkeypatch):
    monkeypatch.delenv('LECTERN_ASHEN_COMPANY', raising=False)
    db = tmp_path / 'rollback.db'
    initialize_database(db)
    with connect(db) as conn:
        for name in ('First', 'Second', 'Third'):
            conn.execute('INSERT INTO campaigns(name) VALUES(?)', (name,))
        conn.execute("""INSERT INTO campaign_entities(entity_id,kind,name,status)
            VALUES('CAM-LECTERN-0002','CAM','Reserved','approved')""")
        conn.execute("""INSERT INTO campaign_workspace_links(campaign_id,entity_id)
            VALUES(3,'CAM-LECTERN-0002')""")
    with connect(db) as conn:
        with pytest.raises(sqlite3.IntegrityError):
            migrate_campaign_workspaces_v12(conn)
        assert conn.execute("SELECT 1 FROM campaign_entities WHERE entity_id='CAM-LECTERN-0001'").fetchone() is None
        assert conn.execute('SELECT 1 FROM campaign_workspace_links WHERE campaign_id=1').fetchone() is None
