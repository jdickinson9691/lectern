import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.database import campaign_link_migration, player_release_migration, canon_review_migration
from app.database.campaign_repository import CampaignRepository
from app.database.repositories import Repository
from app.database.schema import connect, initialize_database
from app.importers.csv_transfer import CsvTransferService


class CampaignIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.db = Path(self.tmp.name) / 'lectern.db'
        initialize_database(self.db)
        self.repo = Repository(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_campaign_writes_get_stable_ids_generic_rules_do_not(self):
        player_id = self.repo.upsert_player({'name': 'Mara'})
        self.repo.upsert_player({'name': 'Mara', 'notes': 'updated'})
        encounter_id = self.repo.create_encounter('Redwater')
        self.repo.create_encounter('Redwater')
        manual_id = self.repo.upsert_monster(self._monster('Ash Hound', 'manual'))
        generic_id = self.repo.upsert_monster(self._monster('Wolf', 'SRD'))
        duplicate_id = self.repo.duplicate_player(player_id)
        with connect(self.db) as conn:
            links = {(r['lectern_table'], r['lectern_id']): r['entity_id'] for r in conn.execute('SELECT * FROM entity_legacy_links')}
            self.assertEqual(links[('players', player_id)], 'PC-COMP-0001')
            duplicate_entity_id = links[('players', duplicate_id)]
            self.assertTrue(duplicate_entity_id.startswith('PC-COMP-'))
            self.assertNotEqual(duplicate_entity_id, 'PC-COMP-0001')
            self.assertEqual(links[('encounters', encounter_id)], 'ENC-COMP-0001')
            self.assertEqual(links[('monsters', manual_id)], 'CRE-COMP-0001')
            self.assertNotIn(('monsters', generic_id), links)
        self.repo.delete_player(duplicate_id)
        with connect(self.db) as conn:
            self.assertIsNone(conn.execute('SELECT 1 FROM entity_legacy_links WHERE entity_id=?', (duplicate_entity_id,)).fetchone())
            self.assertEqual(conn.execute('SELECT status FROM campaign_entities WHERE entity_id=?', (duplicate_entity_id,)).fetchone()[0], 'archived')

    def test_csv_rename_keeps_id_and_records_import(self):
        player_id = self.repo.upsert_player({'name': 'Mara'})
        service = CsvTransferService(self.db)
        path = Path(self.tmp.name) / 'players.csv'
        service.export_table('players', path)
        with path.open(newline='', encoding='utf-8-sig') as handle:
            reader = csv.DictReader(handle)
            columns, rows = reader.fieldnames, list(reader)
        self.assertEqual(rows[0]['entity_id'], 'PC-COMP-0001')
        rows[0]['name'] = 'Captain Mara'
        with path.open('w', newline='', encoding='utf-8-sig') as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
        self.assertEqual(service.preview_table('players', path)[0]['status'], 'Modified')
        self.assertEqual(service.import_table('players', path), 1)
        with connect(self.db) as conn:
            self.assertEqual(conn.execute('SELECT name FROM players WHERE id=?', (player_id,)).fetchone()[0], 'Captain Mara')
            self.assertEqual(conn.execute("SELECT name FROM campaign_entities WHERE entity_id='PC-COMP-0001'").fetchone()[0], 'Captain Mara')
            self.assertEqual(conn.execute("SELECT count(*) FROM entity_sources WHERE entity_id='PC-COMP-0001' AND source_type='csv'").fetchone()[0], 1)
            self.assertEqual(conn.execute('SELECT count(*) FROM players').fetchone()[0], 1)

    def test_csv_without_id_creates_id_and_unknown_id_rolls_back(self):
        service = CsvTransferService(self.db)
        path = Path(self.tmp.name) / 'new.csv'
        path.write_text('name,notes\nNew Recruit,imported\n', encoding='utf-8')
        self.assertEqual(service.import_table('players', path), 1)
        with connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM entity_legacy_links WHERE lectern_table='players'").fetchone()[0], 1)
        path.write_text('name,entity_id\nImpostor,PC-COMP-9999\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Unknown players entity ID'):
            service.import_table('players', path)
        with connect(self.db) as conn:
            self.assertIsNone(conn.execute("SELECT id FROM players WHERE name='Impostor'").fetchone())

    def test_invalid_links_rejected_even_by_direct_sql(self):
        player_id = self.repo.upsert_player({'name': 'Mara'})
        campaign = CampaignRepository(self.db)
        campaign.create_entity('CRE-COMP-0042', 'CRE', 'Unused creature')
        with self.assertRaises(ValueError):
            campaign.link_legacy_row('CRE-COMP-0042', 'players', player_id)
        with self.assertRaises(ValueError):
            campaign.link_legacy_row('CRE-COMP-0042', 'monsters', 9999)
        with connect(self.db) as conn:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO entity_legacy_links VALUES('CRE-COMP-0042','players',?)", (player_id,))
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO entity_legacy_links VALUES('CRE-COMP-0042','monsters',9999)")

    @staticmethod
    def _monster(name, source):
        return dict(name=name, size='', type='', alignment='', armor_class=10,
                    hit_points=3, speed='', challenge_rating='', xp=0,
                    str_score=0, dex_score=0, con_score=0, int_score=0,
                    wis_score=0, cha_score=0, source=source, notes='')


if __name__ == '__main__':
    unittest.main()
