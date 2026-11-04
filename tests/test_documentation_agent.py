from __future__ import annotations

from zipfile import ZipFile

from app.database.campaign_repository import CampaignRepository
from app.database.schema import connect, initialize_database
from app.services.documentation_agent import DocumentationAgent


def _xml(path):
    with ZipFile(path) as archive:
        return archive.read('word/document.xml').decode('utf-8')


def test_print_books_are_two_column_and_player_safe(tmp_path):
    db = tmp_path / 'campaign.db'
    initialize_database(db)
    repo = CampaignRepository(db)
    repo.create_entity('CAM-ASHEN-0001', 'CAM', 'Ashen Company', visibility='player')
    repo.set_knowledge('CAM-ASHEN-0001', 'player', 'history', 'PUBLIC HISTORY')
    repo.approve_player_knowledge('CAM-ASHEN-0001', 'history')
    repo.set_knowledge('CAM-ASHEN-0001', 'gm', 'secret', 'GM SECRET')
    with connect(db) as conn:
        conn.execute("UPDATE entity_knowledge SET status='approved' WHERE audience='gm'")
    repo.approve_entity('CAM-ASHEN-0001')
    repo.create_entity('NPC-TEST-0001', 'NPC', 'HIDDEN NPC')
    with connect(db) as conn:
        conn.execute("UPDATE campaign_entities SET status='approved' WHERE entity_id='NPC-TEST-0001'")
    repo.create_entity('MIS-TEST-0001', 'MIS', 'Banner Mission', visibility='player')
    repo.set_knowledge('MIS-TEST-0001', 'player', 'briefing', 'PUBLIC BRIEFING')
    repo.approve_player_knowledge('MIS-TEST-0001', 'briefing')
    repo.approve_entity('MIS-TEST-0001')
    with connect(db) as conn:
        conn.execute("""INSERT INTO mission_plans(mission_id,max_total_levels,difficulty,lore,loot)
            VALUES('MIS-TEST-0001',12,'risky','PRIVATE MISSION LORE','PRIVATE LOOT')""")
    agent = DocumentationAgent(db)
    player = tmp_path / 'player.docx'
    gm = tmp_path / 'gm.docx'
    agent.export('player', player)
    agent.export('gm', gm)
    player_xml, gm_xml = _xml(player), _xml(gm)
    assert 'w:num="2"' in player_xml and 'w:num="2"' in gm_xml
    assert 'PUBLIC HISTORY' in player_xml and 'PUBLIC HISTORY' in gm_xml
    assert 'GM SECRET' not in player_xml and 'HIDDEN NPC' not in player_xml
    assert 'GM SECRET' in gm_xml and 'HIDDEN NPC' in gm_xml
    assert 'PUBLIC BRIEFING' in player_xml and 'PRIVATE MISSION LORE' not in player_xml
    assert 'PRIVATE LOOT' not in player_xml and 'PRIVATE LOOT' in gm_xml
    assert 'Mission System' in player_xml and 'Running the Campaign' in gm_xml
    assert 'Cleric: Unavailable to new characters' in player_xml


def test_documentation_agent_rejects_unknown_audience(tmp_path):
    agent = DocumentationAgent(tmp_path / 'unused.db')
    try:
        agent.export('all', tmp_path / 'unsafe.docx')
    except ValueError:
        pass
    else:
        assert False, 'Unknown audience must be rejected'
    assert not (tmp_path / 'unsafe.docx').exists()
