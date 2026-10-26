import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtWidgets import QApplication
    from app.ui.story_mission_page import StoryMissionPage
    from app.ui.mission_page import MissionPage
except ImportError:
    QApplication = None

from app.database.campaign_repository import CampaignRepository
from app.database.schema import connect, initialize_database
from app.services.player_export import PlayerExportService
from app.services.fantasy_grounds_export import FantasyGroundsModuleExporter
from app.services.story_mission_agent import StoryMissionAgent


class StoryMissionAgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.db = Path(self.temp.name) / 'campaign.db'
        initialize_database(self.db)
        self.repo = CampaignRepository(self.db)
        self.repo.create_entity('LOC-COMP-0001', 'LOC', 'Greyhaven', visibility='player')
        self.repo.set_knowledge('LOC-COMP-0001', 'player', 'description', 'A refuge on the coast')
        self.repo.approve_player_knowledge('LOC-COMP-0001', 'description')
        self.repo.set_knowledge('LOC-COMP-0001', 'gm', 'secret', 'GM ONLY: the refuge is watched')
        self.repo.approve_entity('LOC-COMP-0001')
        self.agent = StoryMissionAgent(self.db)

    def tearDown(self):
        self.temp.cleanup()

    def test_approved_context_contains_no_gm_or_draft_facts(self):
        self.repo.set_knowledge('LOC-COMP-0001', 'player', 'rumor', 'Unapproved rumor')
        context = self.agent.approved_context(['LOC-COMP-0001'])
        self.assertEqual(context[0]['facts'], {'description': 'A refuge on the coast'})
        self.assertNotIn('GM ONLY', str(context))
        self.assertNotIn('Unapproved rumor', str(context))

    def test_story_mission_ids_sources_links_and_private_notes(self):
        story = self.agent.draft_story('The Shore Road', 'The road leads to Greyhaven.',
            'GM ONLY: ambush at dawn', source_entity_ids=['LOC-COMP-0001'])
        mission = self.agent.draft_mission('Reach Greyhaven', 'Reach the coastal refuge.',
            'GM ONLY: rival patrol', source_entity_ids=['LOC-COMP-0001'], story_id=story)
        self.assertEqual(story, 'DOC-COMP-0001')
        self.assertEqual(mission, 'MIS-COMP-0001')
        self.assertEqual(self.agent.list_missions()[0]['player_briefing'], 'Reach the coastal refuge.')
        with connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT status FROM campaign_entities WHERE entity_id=?", (mission,)).fetchone()[0], 'draft')
            self.assertEqual(conn.execute("SELECT target_id FROM entity_relationships WHERE source_id=?", (mission,)).fetchone()[0], story)
            self.assertEqual(conn.execute("SELECT source_ref FROM entity_sources WHERE entity_id=?", (mission,)).fetchone()[0], 'LOC-COMP-0001')
        snapshot = PlayerExportService(self.db).snapshot()
        self.assertNotIn(story, [row['id'] for row in snapshot['entities']])
        self.assertNotIn(mission, [row['id'] for row in snapshot['entities']])
        self.assertNotIn('GM ONLY', str(snapshot))

    def test_invalid_source_and_story_leave_no_partial_draft(self):
        with self.assertRaises(ValueError):
            self.agent.draft_story('Bad', 'Text', source_entity_ids=['LOC-COMP-9999'])
        with self.assertRaises(ValueError):
            self.agent.draft_mission('Bad', 'Text', source_entity_ids=['LOC-COMP-0001'],
                                     story_id='DOC-COMP-9999')
        with connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM campaign_entities WHERE kind IN ('DOC','MIS')").fetchone()[0], 0)

    def test_canon_suggestion_uses_review_queue(self):
        proposal = self.agent.submit_canon_fact('LOC-COMP-0001', 'player', 'description',
            'An inland refuge', source_type='document', source_ref='new-map:2')
        self.assertGreater(proposal, 0)
        self.assertEqual(self.agent.canon.review_queue()[0]['content'], 'An inland refuge')
        self.assertEqual(PlayerExportService(self.db).snapshot()['entities'][0]['knowledge']['description'],
                         'A refuge on the coast')

    def test_mission_approval_edit_and_revocation_gate_player_export(self):
        mission = self.agent.draft_mission('Reach Greyhaven', 'Find the coastal refuge.',
            'GM ONLY: patrol', source_entity_ids=['LOC-COMP-0001'])
        self.agent.approve_mission(mission)
        exported = next(row for row in PlayerExportService(self.db).snapshot()['entities']
                        if row['id'] == mission)
        self.assertEqual(exported['knowledge'], {'briefing': 'Find the coastal refuge.'})
        self.assertNotIn('GM ONLY', str(exported))
        module = Path(self.temp.name) / 'approved.mod'
        FantasyGroundsModuleExporter(self.db).export_mod(module)
        with zipfile.ZipFile(module) as archive:
            client_xml = archive.read('client.xml').decode('utf-8')
        self.assertIn('Find the coastal refuge.', client_xml)
        self.assertNotIn('GM ONLY', client_xml)
        self.agent.save_mission(mission, 'Reach Greyhaven', 'Find the coastal refuge.',
                                'GM ONLY: different patrol')
        self.assertEqual(self.agent.get_mission(mission)['status'], 'approved')
        self.agent.save_mission(mission, 'Reach Greyhaven', 'Find a new refuge.',
                                'GM ONLY: different patrol')
        self.assertEqual(self.agent.get_mission(mission)['status'], 'draft')
        self.assertNotIn(mission, [row['id'] for row in PlayerExportService(self.db).snapshot()['entities']])
        self.agent.approve_mission(mission)
        self.assertEqual(self.agent.get_mission(mission)['briefing_status'], 'approved')
        self.agent.return_mission_to_draft(mission)
        self.assertNotIn(mission, [row['id'] for row in PlayerExportService(self.db).snapshot()['entities']])

    def test_empty_briefing_cannot_be_approved_and_wrong_kind_rejected(self):
        mission = self.agent.draft_mission('Reach Greyhaven', 'Find the refuge.',
            source_entity_ids=['LOC-COMP-0001'])
        self.agent.save_mission(mission, 'Reach Greyhaven', '')
        with self.assertRaisesRegex(ValueError, 'briefing is required'):
            self.agent.approve_mission(mission)
        with self.assertRaises(KeyError):
            self.agent.approve_mission('LOC-COMP-0001')
        self.assertEqual(self.agent.get_mission(mission)['status'], 'draft')


@unittest.skipIf(QApplication is None, 'PySide6 unavailable')
class StoryMissionPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.db = Path(self.temp.name) / 'campaign-ui.db'
        initialize_database(self.db)
        repo = CampaignRepository(self.db)
        repo.create_entity('LOC-COMP-0001', 'LOC', 'Greyhaven', visibility='player')
        repo.set_knowledge('LOC-COMP-0001', 'player', 'description', 'A refuge on the coast')
        repo.approve_player_knowledge('LOC-COMP-0001', 'description')
        repo.set_knowledge('LOC-COMP-0001', 'gm', 'secret', 'GM ONLY: the refuge is watched')
        repo.approve_entity('LOC-COMP-0001')

    def tearDown(self):
        self.temp.cleanup()

    def test_screen_creates_sourced_story_and_mission(self):
        page = StoryMissionPage(self.db)
        page.sources.item(0).setSelected(True)
        self.assertIn('A refuge on the coast', page.context.toPlainText())
        self.assertNotIn('GM ONLY', page.context.toPlainText())
        page.title.setText('The Shore Road')
        page.player_text.setPlainText('Greyhaven is ahead.')
        page.gm_notes.setPlainText('GM ONLY: ambush')
        with patch('app.ui.story_mission_page.QMessageBox.warning', side_effect=AssertionError):
            page.create_draft()
        self.assertIn('DOC-COMP-0001', page.status.text())
        page.kind.setCurrentText('Mission')
        page.sources.item(0).setSelected(True)
        page.story_link.setCurrentIndex(page.story_link.findData('DOC-COMP-0001'))
        page.title.setText('Reach Greyhaven')
        page.player_text.setPlainText('Cross the shore road.')
        with patch('app.ui.story_mission_page.QMessageBox.warning', side_effect=AssertionError):
            page.create_draft()
        self.assertIn('MIS-COMP-0001', page.status.text())
        page.close()

    def test_mission_screen_review_and_approval(self):
        agent = StoryMissionAgent(self.db)
        mission = agent.draft_mission('Reach Greyhaven', 'Find the refuge.',
            'GM ONLY: patrol', source_entity_ids=['LOC-COMP-0001'])
        page = MissionPage(self.db)
        self.assertEqual(page.current_id, mission)
        self.assertEqual(page.player_briefing.toPlainText(), 'Find the refuge.')
        with patch('app.ui.mission_page.QMessageBox.critical', side_effect=AssertionError):
            page.approve()
        self.assertIn('Approved', page.status.text())
        page.gm_notes.setPlainText('GM ONLY: revised patrol')
        with patch('app.ui.mission_page.QMessageBox.critical', side_effect=AssertionError):
            page.save()
        self.assertEqual(agent.get_mission(mission)['status'], 'approved')
        page.player_briefing.setPlainText('Find another refuge.')
        with patch('app.ui.mission_page.QMessageBox.critical', side_effect=AssertionError):
            page.save()
        self.assertEqual(agent.get_mission(mission)['status'], 'draft')
        page.close()


if __name__ == '__main__':
    unittest.main()
