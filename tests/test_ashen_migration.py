import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.database import ashen_upgrade
from app.database.campaign_repository import CampaignRepository
from app.database.schema import connect, initialize_database


class AshenMigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.db = Path(self.tmp.name) / 'lectern.db'

    def tearDown(self):
        self.tmp.cleanup()

    def test_clean_creation_and_idempotence(self):
        initialize_database(self.db)
        initialize_database(self.db)
        with connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0], '12')
            self.assertEqual(conn.execute('SELECT count(*) FROM campaign_entities').fetchone()[0], 1)
            self.assertEqual(conn.execute('PRAGMA foreign_keys').fetchone()[0], 1)

    def test_upgrade_preserves_rows_and_import_history(self):
        initialize_database(self.db)
        with connect(self.db) as conn:
            conn.execute("INSERT INTO players(name,notes) VALUES('Veteran','keep me')")
            conn.execute("INSERT INTO import_history(file_path,rows_imported) VALUES('old.xlsx',7)")
            conn.execute("UPDATE metadata SET value='8' WHERE key='schema_version'")
        initialize_database(self.db)
        with connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT notes FROM players WHERE name='Veteran'").fetchone()[0], 'keep me')
            self.assertEqual(conn.execute('SELECT rows_imported FROM import_history').fetchone()[0], 7)
            self.assertEqual(conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0], '12')

    def test_failure_rolls_back_ashen_layer_and_can_retry(self):
        def broken(conn):
            raise sqlite3.OperationalError('deliberate migration failure')
        with patch.object(ashen_upgrade, 'migrate_v6', broken):
            with self.assertRaises(sqlite3.OperationalError):
                initialize_database(self.db)
        with connect(self.db) as conn:
            version = conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
            self.assertTrue(version is None or version[0] == '10')
            self.assertIsNone(conn.execute("SELECT name FROM sqlite_master WHERE name='campaign_entities'").fetchone())
        initialize_database(self.db)

    def test_ids_links_foreign_keys_and_audit(self):
        initialize_database(self.db)
        repo = CampaignRepository(self.db)
        repo.create_entity('NPC-COMP-0001', 'NPC', 'Lieutenant Mara Venn')
        repo.rename_entity('NPC-COMP-0001', 'Captain Mara Venn')
        with connect(self.db) as conn:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("UPDATE campaign_entities SET entity_id='NPC-COMP-9999' WHERE entity_id='NPC-COMP-0001'")
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO campaign_entities(entity_id,kind,name) VALUES('NPC-COMP-0001','NPC','Duplicate')")
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO campaign_entities(entity_id,kind,name) VALUES('FAC-COMP-0002','NPC','Wrong prefix')")
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO entity_relationships(source_id,target_id,relation) VALUES('NPC-COMP-0001','MISSING','member')")
            self.assertEqual(conn.execute("SELECT name FROM campaign_entities WHERE entity_id='NPC-COMP-0001'").fetchone()[0], 'Captain Mara Venn')
            self.assertEqual(conn.execute("SELECT count(*) FROM entity_audit WHERE entity_id='NPC-COMP-0001'").fetchone()[0], 2)


if __name__ == '__main__':
    unittest.main()
