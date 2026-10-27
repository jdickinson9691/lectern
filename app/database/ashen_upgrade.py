"""Bring the optional Ashen canon layer onto Lectern's schema v10.

The old Ashen checkout numbered its private migrations v5-v8.  Lectern 3.0
used those numbers independently.  This wrapper keeps both histories intact
and publishes the combined schema as v11 without reseeding user data.
"""
from __future__ import annotations

import sqlite3
import os

from .ashen_migration import migrate_v5
from .campaign_link_migration import migrate_v6
from .campaign_identity import campaign_monster, ensure_campaign_link
from .player_release_migration import migrate_v7
from .canon_review_migration import migrate_v8


ASHEN_TABLES = {
    'campaign_entities', 'entity_relationships', 'entity_knowledge',
    'entity_sources', 'entity_audit', 'entity_legacy_links', 'canon_proposals',
}


def _ensure_ashen_root(conn: sqlite3.Connection) -> None:
    if os.environ.get('LECTERN_ASHEN_COMPANY') != '1':
        return
    # The canon root and the ordinary Campaign Dashboard use distinct tables.
    # Keep the dashboard's local campaign row in the dedicated Ashen database,
    # including databases created by earlier releases that had only the root.
    if not conn.execute("SELECT 1 FROM campaigns WHERE name='Ashen Company'").fetchone():
        conn.execute("INSERT INTO campaigns(name,description,source_type) "
                     "VALUES('Ashen Company','The surviving company after Redwater','local')")
    if conn.execute("SELECT 1 FROM campaign_entities WHERE entity_id='CAM-ASHEN-0001'").fetchone():
        return
    conn.execute("""INSERT INTO campaign_entities(entity_id,kind,name,visibility,status)
                    VALUES('CAM-ASHEN-0001','CAM','Ashen Company','gm','approved')""")
    conn.execute("""INSERT INTO entity_audit(entity_id,action,actor,detail)
                    VALUES('CAM-ASHEN-0001','create','migration:ashen','Core campaign record')""")
    # A database first opened without the dedicated launcher can already hold
    # legacy rows when its owner opts into Ashen later.
    for row in conn.execute('SELECT id,name FROM players').fetchall():
        ensure_campaign_link(conn, 'players', row['id'], row['name'], actor='migration:ashen')
    for row in conn.execute('SELECT id,name FROM encounters').fetchall():
        ensure_campaign_link(conn, 'encounters', row['id'], row['name'], actor='migration:ashen')
    for row in conn.execute('SELECT id,name,source FROM monsters').fetchall():
        if campaign_monster(conn, row['id'], row['source']):
            ensure_campaign_link(conn, 'monsters', row['id'], row['name'], actor='migration:ashen')


def migrate_ashen_v11(conn: sqlite3.Connection) -> None:
    existing = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    present = ASHEN_TABLES & existing
    if present and present != ASHEN_TABLES:
        raise ValueError(f'Incomplete Ashen schema: {sorted(ASHEN_TABLES - present)}')
    if present:
        _ensure_ashen_root(conn)
        conn.execute("UPDATE metadata SET value='11' WHERE key='schema_version'")
        return

    conn.execute('SAVEPOINT ashen_v11')
    try:
        # Reuse the tested DDL and guards in their historical order.  The
        # temporary version values are contained by the outer savepoint.
        conn.execute("UPDATE metadata SET value='4' WHERE key='schema_version'")
        migrate_v5(conn)
        migrate_v6(conn)
        migrate_v7(conn)
        migrate_v8(conn)
        _ensure_ashen_root(conn)
        conn.execute("UPDATE metadata SET value='11' WHERE key='schema_version'")
        conn.execute('RELEASE SAVEPOINT ashen_v11')
    except BaseException:
        conn.execute('ROLLBACK TO SAVEPOINT ashen_v11')
        conn.execute('RELEASE SAVEPOINT ashen_v11')
        raise
