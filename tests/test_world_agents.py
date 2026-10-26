import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtWidgets import QApplication
    from app.ui.world_page import WorldPage
except ImportError:
    QApplication = None

from app.database.schema import connect, initialize_database
from app.services.story_editor import StoryService
from app.services.player_export import PlayerExportService
from app.services.fantasy_grounds_export import FantasyGroundsModuleExporter
from app.services.world_agents import NPCAgent, LocationAgent, FactionAgent


class WorldAgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.db = Path(self.temp.name) / 'world.db'
        initialize_database(self.db)
        stories = StoryService(self.db)
        self.source = stories.create_draft('After Redwater', 'The Company reaches Greyhaven.',
                                          'GM ONLY: hidden pursuer')
        stories.approve(self.source)

    def tearDown(self):
        self.temp.cleanup()

    def test_npc_and_location_ids_sources_and_export_privacy(self):
        npc = NPCAgent(self.db)
        location = LocationAgent(self.db)
        npc_id = npc.draft('Mara Venn', 'A Company veteran.', 'GM ONLY: secret allegiance',
                           source_entity_ids=[self.source])
        location_id = location.draft('Greyhaven', 'A coastal refuge.', 'GM ONLY: hidden tunnel',
                                     source_entity_ids=[self.source])
        self.assertEqual(npc_id, 'NPC-COMP-0001')
        self.assertEqual(location_id, 'LOC-COMP-0001')
        self.assertEqual(npc.get_record(npc_id)['sources'], [self.source])
        self.assertEqual(location.get_record(location_id)['sources'], [self.source])
        before = PlayerExportService(self.db).snapshot()
        self.assertNotIn(npc_id, [row['id'] for row in before['entities']])
        self.assertNotIn(location_id, [row['id'] for row in before['entities']])
        npc.approve(npc_id)
        location.approve(location_id)
        snapshot = PlayerExportService(self.db).snapshot()
        by_id = {row['id']: row for row in snapshot['entities']}
        self.assertEqual(by_id[npc_id]['knowledge'], {'profile': 'A Company veteran.'})
        self.assertEqual(by_id[location_id]['knowledge'], {'description': 'A coastal refuge.'})
        self.assertNotIn('GM ONLY', str(snapshot))
        module = Path(self.temp.name) / 'world.mod'
        FantasyGroundsModuleExporter(self.db).export_mod(module)
        with zipfile.ZipFile(module) as archive:
            client = archive.read('client.xml').decode('utf-8')
        self.assertIn('A Company veteran.', client)
        self.assertIn('A coastal refuge.', client)
        self.assertNotIn('GM ONLY', client)

    def test_gm_edit_preserves_approval_public_edit_revokes_it(self):
        agent = NPCAgent(self.db)
        entity_id = agent.draft('Mara Venn', 'A Company veteran.', 'GM ONLY: first',
                                source_entity_ids=[self.source])
        agent.approve(entity_id)
        agent.save(entity_id, 'Mara Venn', 'A Company veteran.', 'GM ONLY: revised')
        self.assertEqual(agent.get_record(entity_id)['status'], 'approved')
        agent.save(entity_id, 'Captain Mara Venn', 'New public text.', 'GM ONLY: revised')
        self.assertEqual(agent.get_record(entity_id)['status'], 'draft')
        self.assertNotIn(entity_id, [row['id'] for row in PlayerExportService(self.db).snapshot()['entities']])
        agent.approve(entity_id)
        agent.return_to_draft(entity_id)
        self.assertNotIn(entity_id, [row['id'] for row in PlayerExportService(self.db).snapshot()['entities']])

    def test_invalid_source_and_empty_player_text_do_not_publish(self):
        agent = LocationAgent(self.db)
        with self.assertRaises(ValueError):
            agent.draft('Greyhaven', 'Description', source_entity_ids=['DOC-COMP-9999'])
        with connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM campaign_entities WHERE kind='LOC'").fetchone()[0], 0)
        entity_id = agent.draft('Greyhaven', 'A refuge.', source_entity_ids=[self.source])
        agent.save(entity_id, 'Greyhaven', '')
        with self.assertRaisesRegex(ValueError, 'Player text is required'):
            agent.approve(entity_id)

    def test_canon_suggestion_uses_review_queue(self):
        agent = NPCAgent(self.db)
        entity_id = agent.draft('Mara Venn', 'A veteran.', source_entity_ids=[self.source])
        proposal_id = agent.submit_canon_fact(entity_id, 'gm', 'allegiance', 'Secret order',
            source_type='document', source_ref='gm-notes:3')
        self.assertGreater(proposal_id, 0)
        self.assertEqual(agent.canon.review_queue()[0]['content'], 'Secret order')
        self.assertNotIn('Secret order', str(PlayerExportService(self.db).snapshot()))

    def test_faction_links_require_approved_endpoints_for_player_export(self):
        npc_agent, location_agent, faction_agent = NPCAgent(self.db), LocationAgent(self.db), FactionAgent(self.db)
        npc_id = npc_agent.draft('Company Survivor', 'A remaining member.',
                                 source_entity_ids=[self.source])
        location_id = location_agent.draft('Greyhaven', 'Temporary Company quarters.',
                                           source_entity_ids=[self.source])
        faction_id = faction_agent.draft('Ashen Company', 'The Company survived Redwater.',
                                         'GM ONLY: private plan', source_entity_ids=[self.source])
        self.assertEqual(faction_id, 'FAC-COMP-0001')
        self.assertEqual(faction_agent.link(faction_id, npc_id, visibility='player'), 'has_member')
        self.assertEqual(faction_agent.link(faction_id, location_id, visibility='player'), 'active_in')
        with self.assertRaises(ValueError):
            faction_agent.approve_relationship(faction_id, npc_id)
        npc_agent.approve(npc_id)
        location_agent.approve(location_id)
        faction_agent.approve(faction_id)
        faction_agent.approve_relationship(faction_id, npc_id)
        faction_agent.approve_relationship(faction_id, location_id)
        snapshot = PlayerExportService(self.db).snapshot()
        relations = {(r['relation'], r['target_id']) for r in snapshot['relationships']}
        self.assertEqual(relations, {('has_member', npc_id), ('active_in', location_id)})
        self.assertNotIn('GM ONLY', str(snapshot))
        faction_agent.return_relationship_to_draft(faction_id, npc_id)
        self.assertNotIn(('has_member', npc_id),
                         {(r['relation'], r['target_id']) for r in PlayerExportService(self.db).snapshot()['relationships']})

    def test_faction_link_rejects_non_campaign_target_and_gm_link_is_private(self):
        agent = FactionAgent(self.db)
        faction_id = agent.draft('Ashen Company', 'Survived Redwater.',
                                 source_entity_ids=[self.source])
        with self.assertRaises(ValueError):
            agent.link(faction_id, self.source)
        npc_id = NPCAgent(self.db).draft('Survivor', 'Company member.',
                                          source_entity_ids=[self.source])
        agent.link(faction_id, npc_id)
        with self.assertRaises(ValueError):
            agent.approve_relationship(faction_id, npc_id)
        agent.approve(faction_id)
        NPCAgent(self.db).approve(npc_id)
        self.assertEqual(PlayerExportService(self.db).snapshot()['relationships'], [])


@unittest.skipIf(QApplication is None, 'PySide6 unavailable')
class WorldPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.db = Path(self.temp.name) / 'world-ui.db'
        initialize_database(self.db)
        stories = StoryService(self.db)
        self.source = stories.create_draft('After Redwater', 'The Company reaches Greyhaven.')
        stories.approve(self.source)

    def tearDown(self):
        self.temp.cleanup()

    def test_npc_and_location_screens_create_and_approve(self):
        for agent_type, name, text in [(NPCAgent, 'Mara Venn', 'A veteran.'),
                                       (LocationAgent, 'Greyhaven', 'A refuge.')]:
            page = WorldPage(self.db, agent_type)
            page.sources.item(0).setSelected(True)
            page.name.setText(name)
            page.player_text.setPlainText(text)
            page.gm_notes.setPlainText('GM ONLY: private')
            with patch('app.ui.world_page.QMessageBox.critical', side_effect=AssertionError):
                page.approve()
            self.assertIn('Approved', page.status.text())
            self.assertEqual(agent_type(self.db).get_record(page.current_id)['status'], 'approved')
            page.player_text.setPlainText('Revised public text.')
            with patch('app.ui.world_page.QMessageBox.critical', side_effect=AssertionError):
                page.save()
            self.assertEqual(agent_type(self.db).get_record(page.current_id)['status'], 'draft')
            page.close()

    def test_faction_screen_links_approved_npc(self):
        npc_agent = NPCAgent(self.db)
        npc_id = npc_agent.draft('Survivor', 'A remaining Company member.',
                                 source_entity_ids=[self.source])
        npc_agent.approve(npc_id)
        page = WorldPage(self.db, FactionAgent)
        page.sources.item(0).setSelected(True)
        page.name.setText('Ashen Company')
        page.player_text.setPlainText('The Company survived Redwater.')
        with patch('app.ui.world_page.QMessageBox.critical', side_effect=AssertionError):
            page.approve()
        page.faction_target.setCurrentIndex(page.faction_target.findData(npc_id))
        page.faction_visibility.setCurrentText('player')
        with patch('app.ui.world_page.QMessageBox.warning', side_effect=AssertionError):
            page.add_faction_link()
            page.approve_faction_link()
        self.assertIn('approved', page.faction_links.currentText())
        page.close()


if __name__ == '__main__':
    unittest.main()
