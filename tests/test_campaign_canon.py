import tempfile
import unittest
from pathlib import Path

from app.database.campaign_repository import CampaignRepository
from app.database.schema import connect, initialize_database
from app.services.campaign_canon import CampaignCanonAgent, CanonConflict
from app.services.player_export import PlayerExportService


class CampaignCanonAgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.db = Path(self.temp.name) / 'lectern.db'
        initialize_database(self.db)
        self.repo = CampaignRepository(self.db)
        self.repo.create_entity('LOC-COMP-0001', 'LOC', 'Redwater', visibility='player')
        self.agent = CampaignCanonAgent(self.db)

    def tearDown(self):
        self.temp.cleanup()

    def test_sourced_proposal_is_private_until_explicit_approval(self):
        self.agent.propose_fact('LOC-COMP-0001', 'player', 'description', 'A ruined crossing',
                                source_type='document', source_ref='campaign-notes:1')
        dossier = self.agent.dossier('LOC-COMP-0001')
        self.assertEqual(dossier['facts'][0]['status'], 'draft')
        self.assertEqual(dossier['sources'][0]['source_ref'], 'campaign-notes:1')
        self.assertEqual(dossier['audit'][-1]['action'], 'canon_proposal')
        self.assertEqual(PlayerExportService(self.db).snapshot()['entities'], [])
        self.repo.approve_player_knowledge('LOC-COMP-0001', 'description')
        self.repo.approve_entity('LOC-COMP-0001')
        self.assertEqual(PlayerExportService(self.db).snapshot()['entities'][0]['knowledge']['description'],
                         'A ruined crossing')

    def test_conflicting_approved_fact_rolls_back_source_and_audit(self):
        self.agent.propose_fact('LOC-COMP-0001', 'player', 'description', 'A ruined crossing',
                                source_type='document', source_ref='campaign-notes:1')
        self.repo.approve_player_knowledge('LOC-COMP-0001', 'description')
        with self.assertRaises(CanonConflict):
            self.agent.propose_fact('LOC-COMP-0001', 'player', 'description', 'A safe crossing',
                                    source_type='document', source_ref='unreviewed:2')
        with connect(self.db) as conn:
            self.assertIsNone(conn.execute("SELECT 1 FROM entity_sources WHERE source_ref='unreviewed:2'").fetchone())
            row = conn.execute("SELECT content,status FROM entity_knowledge WHERE entity_id='LOC-COMP-0001'").fetchone()
            self.assertEqual(tuple(row), ('A ruined crossing', 'approved'))

    def test_second_source_preserves_approved_fact(self):
        self.agent.propose_fact('LOC-COMP-0001', 'player', 'description', 'A ruined crossing',
                                source_type='document', source_ref='campaign-notes:1')
        self.repo.approve_player_knowledge('LOC-COMP-0001', 'description')
        self.agent.propose_fact('LOC-COMP-0001', 'player', 'description', 'A ruined crossing',
                                source_type='document', source_ref='map-label:2')
        dossier = self.agent.dossier('LOC-COMP-0001')
        self.assertEqual(dossier['facts'][0]['status'], 'approved')
        self.assertEqual(len(dossier['sources']), 2)
        self.assertEqual(dossier['audit'][-1]['action'], 'canon_source')

    def test_missing_source_and_unknown_entity_do_not_write(self):
        with self.assertRaises(ValueError):
            self.agent.propose_fact('LOC-COMP-0001', 'gm', 'secret', 'Hidden door',
                                    source_type='document', source_ref='')
        with self.assertRaises(KeyError):
            self.agent.propose_fact('LOC-COMP-9999', 'gm', 'secret', 'Hidden door',
                                    source_type='document', source_ref='notes:1')
        with connect(self.db) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM entity_knowledge').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
