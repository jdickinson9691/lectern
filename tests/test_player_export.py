import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.database import player_release_migration, canon_review_migration
from app.database.campaign_repository import CampaignRepository
from app.database.repositories import Repository
from app.database.schema import connect, initialize_database
from app.services.player_export import PlayerExportService


class PlayerExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.db = Path(self.tmp.name) / 'lectern.db'
        initialize_database(self.db)
        self.campaign = CampaignRepository(self.db)
        self.exporter = PlayerExportService(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_export_is_strictly_approved_and_player_visible(self):
        repo = Repository(self.db)
        repo.upsert_player({'name': 'Mara', 'notes': 'GM SECRET: hidden heir'})
        self.campaign.create_entity('NPC-COMP-0001', 'NPC', 'Visible Ally', visibility='player')
        self.campaign.create_entity('NPC-COMP-0002', 'NPC', 'Hidden Traitor')
        self.campaign.create_entity('NPC-COMP-0003', 'NPC', 'Draft Contact', visibility='player')
        self.campaign.create_entity('NPC-COMP-0004', 'NPC', 'Internal Agent', visibility='internal')
        self.campaign.set_visibility('PC-COMP-0001', 'player')
        self.campaign.approve_entity('PC-COMP-0001')
        self.campaign.approve_entity('NPC-COMP-0001')
        self.campaign.set_knowledge('PC-COMP-0001', 'gm', 'secret', 'GM SECRET: Redwater culprit')
        self.campaign.set_knowledge('PC-COMP-0001', 'internal', 'memo', 'INTERNAL SECRET: staff note')
        self.campaign.set_knowledge('PC-COMP-0001', 'player', 'bio', 'Known mercenary')
        self.campaign.set_knowledge('PC-COMP-0001', 'player', 'unreviewed', 'DRAFT SECRET: do not publish')
        self.campaign.approve_player_knowledge('PC-COMP-0001', 'bio')
        self.campaign.add_relationship('PC-COMP-0001', 'NPC-COMP-0001', 'ally', visibility='player')
        self.campaign.approve_player_relationship('PC-COMP-0001', 'NPC-COMP-0001', 'ally')
        self.campaign.add_relationship('PC-COMP-0001', 'NPC-COMP-0002', 'secret-parent', visibility='player')
        self.campaign.add_relationship('NPC-COMP-0001', 'PC-COMP-0001', 'secret-debt', visibility='gm')
        with connect(self.db) as conn:
            conn.execute("UPDATE campaign_entities SET status='approved' WHERE entity_id IN ('NPC-COMP-0002','NPC-COMP-0004')")
            conn.execute("UPDATE entity_knowledge SET status='approved' WHERE audience IN ('gm','internal')")
            conn.execute("INSERT INTO entity_sources(entity_id,source_type,source_ref,citation) VALUES('PC-COMP-0001','document','private.docx','SOURCE SECRET')")
            conn.execute("INSERT INTO entity_audit(entity_id,action,actor,detail) VALUES('PC-COMP-0001','note','gm','AUDIT SECRET')")
            # Even a mistakenly approved relationship to a hidden endpoint cannot leak.
            conn.execute("UPDATE entity_relationships SET status='approved' WHERE relation IN ('secret-parent','secret-debt')")

        path = Path(self.tmp.name) / 'players.json'
        snapshot = self.exporter.export_json(path)
        data = json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(data, snapshot)
        self.assertEqual([row['id'] for row in data['entities']], ['NPC-COMP-0001', 'PC-COMP-0001'])
        self.assertEqual(data['relationships'], [
            {'source_id': 'PC-COMP-0001', 'target_id': 'NPC-COMP-0001', 'relation': 'ally'}
        ])
        pc = next(row for row in data['entities'] if row['id'] == 'PC-COMP-0001')
        self.assertEqual(pc['knowledge'], {'bio': 'Known mercenary'})
        raw = path.read_text(encoding='utf-8')
        for secret in ['GM SECRET', 'INTERNAL SECRET', 'DRAFT SECRET', 'Hidden Traitor', 'Internal Agent',
                       'Draft Contact', 'secret-parent', 'secret-debt', 'SOURCE SECRET', 'AUDIT SECRET']:
            self.assertNotIn(secret, raw)
        self.assertNotIn('notes', raw)
        self.assertNotIn('lectern_id', raw)

    def test_edits_and_revocation_withhold_previous_approval(self):
        self.campaign.create_entity('LOC-COMP-0001', 'LOC', 'Old Watchtower', visibility='player')
        self.campaign.create_entity('NPC-COMP-0001', 'NPC', 'Scout', visibility='player')
        self.campaign.approve_entity('LOC-COMP-0001')
        self.campaign.approve_entity('NPC-COMP-0001')
        self.campaign.set_knowledge('LOC-COMP-0001', 'player', 'rumor', 'Open to visitors')
        self.campaign.approve_player_knowledge('LOC-COMP-0001', 'rumor')
        self.campaign.add_relationship('NPC-COMP-0001', 'LOC-COMP-0001', 'guards', visibility='player')
        self.campaign.approve_player_relationship('NPC-COMP-0001', 'LOC-COMP-0001', 'guards')
        self.campaign.rename_entity('LOC-COMP-0001', 'Ruined Watchtower')
        self.assertNotIn('LOC-COMP-0001', [row['id'] for row in self.exporter.snapshot()['entities']])
        with connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT status FROM entity_relationships WHERE relation='guards'").fetchone()[0], 'draft')
        self.campaign.approve_entity('LOC-COMP-0001')
        with connect(self.db) as conn:
            conn.execute("UPDATE entity_knowledge SET content='Closed to visitors' WHERE field_key='rumor'")
        loc = next(row for row in self.exporter.snapshot()['entities'] if row['id'] == 'LOC-COMP-0001')
        self.assertEqual(loc['knowledge'], {})
        self.campaign.approve_player_knowledge('LOC-COMP-0001', 'rumor')
        self.campaign.approve_player_relationship('NPC-COMP-0001', 'LOC-COMP-0001', 'guards')
        self.assertEqual(len(self.exporter.snapshot()['relationships']), 1)
        self.campaign.revoke_entity('NPC-COMP-0001')
        self.assertEqual(self.exporter.snapshot()['relationships'], [])
        with connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT status FROM entity_relationships WHERE relation='guards'").fetchone()[0], 'draft')

    def test_other_campaign_excluded_and_approval_requires_player_visibility(self):
        self.campaign.create_entity('CAM-OTHER-0001', 'CAM', 'Other Campaign', visibility='player')
        self.campaign.create_entity('LOC-OTHER-0001', 'LOC', 'Other Place', campaign_id='CAM-OTHER-0001', visibility='player')
        self.campaign.approve_entity('CAM-OTHER-0001')
        self.campaign.approve_entity('LOC-OTHER-0001')
        self.campaign.create_entity('LOC-COMP-0001', 'LOC', 'GM Place')
        with self.assertRaises(ValueError):
            self.campaign.approve_entity('LOC-COMP-0001')
        self.assertEqual(self.exporter.snapshot()['entities'], [])
        with connect(self.db) as conn:
            conn.execute("UPDATE campaign_entities SET status='archived' WHERE entity_id='LOC-COMP-0001'")
        self.campaign.rename_entity('LOC-COMP-0001', 'Renamed Archived Place')
        with connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT status FROM campaign_entities WHERE entity_id='LOC-COMP-0001'").fetchone()[0], 'archived')

if __name__ == '__main__':
    unittest.main()
