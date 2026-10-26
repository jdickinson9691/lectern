import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtWidgets import QApplication
    from app.ui.canon_review_page import CanonReviewPage
except ImportError:
    QApplication = None

from app.database import canon_review_migration
from app.database.campaign_repository import CampaignRepository
from app.database.schema import connect, initialize_database
from app.services.campaign_canon import CampaignCanonAgent, CanonConflict
from app.services.player_export import PlayerExportService


class CanonReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.db = Path(self.temp.name) / 'review.db'
        initialize_database(self.db)
        self.repo = CampaignRepository(self.db)
        self.repo.create_entity('LOC-COMP-0001', 'LOC', 'Redwater', visibility='player')
        self.repo.set_knowledge('LOC-COMP-0001', 'player', 'description', 'Unsafe crossing')
        self.repo.approve_player_knowledge('LOC-COMP-0001', 'description')
        self.repo.approve_entity('LOC-COMP-0001')
        self.agent = CampaignCanonAgent(self.db)

    def tearDown(self):
        self.temp.cleanup()

    def submit(self, content='Safe crossing'):
        return self.agent.submit_for_review('LOC-COMP-0001', 'player', 'description', content,
            source_type='document', source_ref='field-notes:1', citation='page 2')

    def test_conflict_compares_without_changing_export_then_accepts_as_draft(self):
        proposal = self.submit()
        queued = self.agent.review_queue()[0]
        self.assertEqual(queued['current_content'], 'Unsafe crossing')
        self.assertEqual(queued['content'], 'Safe crossing')
        self.assertEqual(queued['baseline_status'], 'approved')
        self.assertEqual(PlayerExportService(self.db).snapshot()['entities'][0]['knowledge']['description'],
                         'Unsafe crossing')
        self.agent.resolve(proposal, 'accept', reviewer='gm', note='Confirmed on page 2')
        self.assertEqual(self.agent.review_queue(), [])
        with connect(self.db) as conn:
            fact = conn.execute("SELECT content,status FROM entity_knowledge WHERE entity_id='LOC-COMP-0001'").fetchone()
            self.assertEqual(tuple(fact), ('Safe crossing', 'draft'))
            self.assertEqual(conn.execute('SELECT review_note FROM canon_proposals WHERE id=?',
                                          (proposal,)).fetchone()[0], 'Confirmed on page 2')
        self.assertNotIn('Safe crossing', str(PlayerExportService(self.db).snapshot()))

    def test_reject_preserves_approved_fact_and_source(self):
        proposal = self.submit()
        self.agent.resolve(proposal, 'reject')
        self.assertEqual(self.agent.review_queue(include_resolved=True)[0]['status'], 'rejected')
        with connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT content FROM entity_knowledge WHERE entity_id='LOC-COMP-0001'").fetchone()[0], 'Unsafe crossing')
            self.assertEqual(conn.execute('SELECT count(*) FROM entity_sources').fetchone()[0], 0)

    def test_stale_accept_and_repeat_decision_fail(self):
        proposal = self.submit()
        self.repo.set_knowledge('LOC-COMP-0001', 'player', 'description', 'Different edit')
        with self.assertRaises(CanonConflict):
            self.agent.resolve(proposal, 'accept')
        self.agent.resolve(proposal, 'reject')
        with self.assertRaises(ValueError):
            self.agent.resolve(proposal, 'reject')

@unittest.skipIf(QApplication is None, 'PySide6 unavailable')
class CanonReviewUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.db = Path(self.temp.name) / 'review-ui.db'
        initialize_database(self.db)
        repo = CampaignRepository(self.db)
        repo.create_entity('LOC-COMP-0001', 'LOC', 'Redwater', visibility='player')
        repo.set_knowledge('LOC-COMP-0001', 'player', 'description', 'Unsafe crossing')
        repo.approve_player_knowledge('LOC-COMP-0001', 'description')
        repo.approve_entity('LOC-COMP-0001')

    def tearDown(self):
        self.temp.cleanup()

    def test_screen_compares_and_resolves(self):
        page = CanonReviewPage(self.db)
        page.audience_select.setCurrentText('player')
        page.field_key.setText('description')
        page.fact_text.setPlainText('Safe crossing')
        page.source_ref.setText('field-notes:1')
        page.submit()
        self.assertEqual(page.proposals.count(), 1)
        self.assertIn('Unsafe crossing', page.current_text.toPlainText())
        self.assertIn('Safe crossing', page.proposed_text.toPlainText())
        self.assertIn('field-notes:1', page.source.text())
        page.note.setText('Reviewed source')
        page.resolve('accept')
        self.assertEqual(page.proposals.count(), 0)
        self.assertIn('accepted as draft', page.status.text())
        page.close()


if __name__ == '__main__':
    unittest.main()
