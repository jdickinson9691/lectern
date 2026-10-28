from __future__ import annotations

import os

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication

from app.database.schema import connect, initialize_database
from app.services.fiction_agent import FictionAgent
from app.services.player_export import PlayerExportService
from app.ui.fiction_agent_page import FictionAgentPage


def _database(tmp_path):
    db = tmp_path / 'fiction.db'
    initialize_database(db)
    with connect(db) as conn:
        conn.execute("""INSERT INTO campaign_entities(entity_id,kind,name,visibility,status)
            VALUES('CAM-ASHEN-0001','CAM','Ashen Company','gm','approved')""")
        conn.execute("""INSERT INTO campaign_entities
            (entity_id,kind,name,campaign_id,visibility,status)
            VALUES('NPC-FICT-0001','NPC','Mara','CAM-ASHEN-0001','player','approved'),
                  ('MIS-FICT-0001','MIS','Redwater','CAM-ASHEN-0001','player','approved')""")
        conn.execute("""INSERT INTO entity_knowledge
            (entity_id,audience,field_key,content,status)
            VALUES('CAM-ASHEN-0001','player','history','The Company survived Redwater.','approved'),
                  ('CAM-ASHEN-0001','gm','secret','GM SECRET','approved')""")
    return db


def test_fiction_agent_queues_all_domains_without_publication(tmp_path):
    db = _database(tmp_path)
    agent = FictionAgent(db)
    before = PlayerExportService(db).snapshot()
    requests = [
        ('Canon & Lore', 'CAM-ASHEN-0001', 'origin'),
        ('NPC Background', 'NPC-FICT-0001', 'background'),
        ('Mission Background', 'MIS-FICT-0001', 'background'),
        ('Mission Details', 'MIS-FICT-0001', 'details'),
    ]
    for section, target, key in requests:
        proposal_id = agent.propose(
            section, target, 'player', f'Proposed {section}',
            source_entity_id='CAM-ASHEN-0001', source_audience='player',
            source_field_key='history', field_key='origin')
        assert proposal_id > 0
    assert len(agent.pending()) == 4
    assert {row['field_key'] for row in agent.pending()} == {'origin', 'background', 'details'}
    assert PlayerExportService(db).snapshot() == before
    assert agent.propose('Mission Details', 'MIS-FICT-0001', 'player',
                         'Proposed Mission Details', source_entity_id='CAM-ASHEN-0001',
                         source_audience='player', source_field_key='history') == agent.pending()[-1]['id']


def test_fiction_agent_rejects_private_source_for_player_and_wrong_target(tmp_path):
    db = _database(tmp_path)
    agent = FictionAgent(db)
    assert all(row['content'] != 'GM SECRET' for row in agent.approved_sources('player'))
    assert any(row['content'] == 'GM SECRET' for row in agent.approved_sources('gm'))
    kwargs = dict(source_entity_id='CAM-ASHEN-0001', source_audience='gm',
                  source_field_key='secret')
    with pytest.raises(ValueError, match='approved source'):
        agent.propose('NPC Background', 'NPC-FICT-0001', 'player', 'Proposed', **kwargs)
    with pytest.raises(ValueError, match='matching active'):
        agent.propose('Mission Details', 'NPC-FICT-0001', 'gm', 'Proposed', **kwargs)
    with connect(db) as conn:
        assert conn.execute('SELECT COUNT(*) FROM canon_proposals').fetchone()[0] == 0


def test_fiction_agent_page_shows_source_and_routes_to_review(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = _database(tmp_path)
    opened = []
    page = FictionAgentPage(db, lambda: opened.append(True))
    assert page.target.count() > 0
    assert page.source.count() == 2
    page.audience.setCurrentText('player')
    assert page.source.count() == 1
    page.section.setCurrentText('NPC Background')
    page.draft.setPlainText('Mara remembers the march.')
    page.submit()
    assert len(FictionAgent(db).pending()) == 1
    page.open_review()
    assert opened == [True]
    page.close()
