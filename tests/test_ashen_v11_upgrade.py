from pathlib import Path
import sqlite3

import pytest

from app.database.schema import connect, initialize_database


def test_clean_database_adds_optional_ashen_schema_without_seeding(tmp_path: Path, monkeypatch):
    monkeypatch.delenv('LECTERN_ASHEN_COMPANY', raising=False)
    db = tmp_path / 'clean.db'
    initialize_database(db)
    with connect(db) as conn:
        assert conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0] == '11'
        assert conn.execute('SELECT COUNT(*) FROM campaign_entities').fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM campaigns').fetchone()[0] == 0


def test_ashen_launcher_adds_canon_root_and_dashboard_campaign(tmp_path: Path, monkeypatch):
    monkeypatch.setenv('LECTERN_ASHEN_COMPANY', '1')
    db = tmp_path / 'ashen.db'
    initialize_database(db)
    with connect(db) as conn:
        rows = conn.execute('SELECT entity_id,name FROM campaign_entities').fetchall()
        assert [(r[0], r[1]) for r in rows] == [('CAM-ASHEN-0001', 'Ashen Company')]
        assert [(r['name'], r['source_type']) for r in conn.execute('SELECT name,source_type FROM campaigns')] == [('Ashen Company', 'local')]


def test_ashen_launcher_can_opt_in_existing_empty_database(tmp_path: Path, monkeypatch):
    monkeypatch.delenv('LECTERN_ASHEN_COMPANY', raising=False)
    db = tmp_path / 'generic.db'
    initialize_database(db)
    with connect(db) as conn:
        conn.execute("INSERT INTO players(name) VALUES('New Ashen Recruit')")
    monkeypatch.setenv('LECTERN_ASHEN_COMPANY', '1')
    initialize_database(db)
    with connect(db) as conn:
        assert conn.execute("SELECT name FROM campaign_entities WHERE entity_id='CAM-ASHEN-0001'").fetchone()[0] == 'Ashen Company'
        assert conn.execute("SELECT COUNT(*) FROM entity_legacy_links WHERE lectern_table='players'").fetchone()[0] == 1


def test_existing_lectern_rows_remain_unclaimed(tmp_path: Path, monkeypatch):
    monkeypatch.delenv('LECTERN_ASHEN_COMPANY', raising=False)
    db = tmp_path / 'lectern.db'
    initialize_database(db)
    with connect(db) as conn:
        conn.execute("INSERT INTO players(name,notes) VALUES('Existing Hero','keep')")
        conn.execute("INSERT INTO encounters(name) VALUES('Existing Battle')")
        conn.execute("INSERT INTO import_history(file_path,rows_imported) VALUES('old.csv',1)")
        conn.execute("UPDATE metadata SET value='10' WHERE key='schema_version'")
    initialize_database(db)
    with connect(db) as conn:
        assert conn.execute("SELECT notes FROM players WHERE name='Existing Hero'").fetchone()[0] == 'keep'
        assert conn.execute("SELECT name FROM encounters WHERE name='Existing Battle'").fetchone()[0] == 'Existing Battle'
        assert conn.execute('SELECT rows_imported FROM import_history').fetchone()[0] == 1
        assert conn.execute('SELECT COUNT(*) FROM entity_legacy_links').fetchone()[0] == 0


def test_upgrade_preserves_existing_ashen_data(tmp_path: Path, monkeypatch):
    monkeypatch.setenv('LECTERN_ASHEN_COMPANY', '1')
    db = tmp_path / 'existing.db'
    initialize_database(db)
    with connect(db) as conn:
        conn.execute("INSERT INTO campaign_entities(entity_id,kind,name,campaign_id) VALUES('LOC-COMP-0001','LOC','Test Site','CAM-ASHEN-0001')")
        conn.execute("UPDATE metadata SET value='8' WHERE key='schema_version'")
    initialize_database(db)
    with connect(db) as conn:
        assert conn.execute("SELECT name FROM campaign_entities WHERE entity_id='LOC-COMP-0001'").fetchone()[0] == 'Test Site'
        assert conn.execute("SELECT COUNT(*) FROM campaigns WHERE name='Ashen Company'").fetchone()[0] == 1
        assert conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0] == '11'


def test_existing_ashen_canon_regains_missing_dashboard_row_without_reseed(tmp_path: Path, monkeypatch):
    monkeypatch.setenv('LECTERN_ASHEN_COMPANY', '1')
    db = tmp_path / 'old-ashen.db'
    initialize_database(db)
    with connect(db) as conn:
        conn.execute("DELETE FROM campaigns WHERE name='Ashen Company'")
        conn.execute("INSERT INTO campaign_entities(entity_id,kind,name,campaign_id,visibility,status) "
                     "VALUES('NPC-COMP-0001','NPC','Mara Venn','CAM-ASHEN-0001','player','approved')")
        conn.execute("INSERT INTO entity_knowledge(entity_id,audience,field_key,content,status) "
                     "VALUES('NPC-COMP-0001','player','summary','A Company veteran.','approved')")
    initialize_database(db)
    initialize_database(db)
    with connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM campaigns WHERE name='Ashen Company'").fetchone()[0] == 1
        assert conn.execute("SELECT content FROM entity_knowledge WHERE entity_id='NPC-COMP-0001'").fetchone()[0] == 'A Company veteran.'
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
