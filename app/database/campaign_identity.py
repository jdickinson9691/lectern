"""Permanent IDs and validated links to Lectern's existing records."""
from __future__ import annotations

import sqlite3
import os


ASHEN_CAMPAIGN_ID = 'CAM-ASHEN-0001'
CAMPAIGN_ID = os.environ.get('LECTERN_CANON_CAMPAIGN_ID', ASHEN_CAMPAIGN_ID)
TABLE_KINDS = {
    'players': 'PC',
    'encounters': 'ENC',
    'monsters': 'CRE',
    'weapons': 'ITM',
    'armor': 'ITM',
    'equipment': 'ITM',
    'magic_items': 'ITM',
    'spells': 'SPL',
    'rules_reference': 'RULE',
}


def has_ashen_campaign(conn: sqlite3.Connection) -> bool:
    return conn.execute(
        'SELECT 1 FROM campaign_entities WHERE entity_id=?', (ASHEN_CAMPAIGN_ID,)
    ).fetchone() is not None


def link_legacy_row(conn: sqlite3.Connection, entity_id: str,
                    table: str, row_id: int) -> None:
    """Link an existing row to a compatible entity within the current transaction."""
    if table not in TABLE_KINDS:
        raise ValueError(f'Unsupported Lectern table: {table}')
    entity = conn.execute(
        'SELECT kind FROM campaign_entities WHERE entity_id=?', (entity_id,)
    ).fetchone()
    if entity is None:
        raise ValueError(f'Unknown campaign entity: {entity_id}')
    if entity[0] != TABLE_KINDS[table]:
        raise ValueError(f'{entity_id} is not a {TABLE_KINDS[table]} entity')
    if conn.execute(f'SELECT 1 FROM {table} WHERE id=?', (row_id,)).fetchone() is None:
        raise ValueError(f'Missing Lectern row: {table}:{row_id}')
    conn.execute(
        'INSERT INTO entity_legacy_links(entity_id,lectern_table,lectern_id) VALUES(?,?,?)',
        (entity_id, table, row_id),
    )


def ensure_campaign_link(conn: sqlite3.Connection, table: str, row_id: int,
                         name: str, *, actor: str = 'lectern') -> str:
    """Create one permanent ID per campaign row; safe to repeat after an upsert."""
    if table not in TABLE_KINDS:
        raise ValueError(f'Unsupported Lectern table: {table}')
    existing = conn.execute(
        'SELECT entity_id FROM entity_legacy_links WHERE lectern_table=? AND lectern_id=?',
        (table, row_id),
    ).fetchone()
    if existing:
        old = conn.execute('SELECT name FROM campaign_entities WHERE entity_id=?', (existing[0],)).fetchone()
        if old and old[0] != name:
            conn.execute('UPDATE campaign_entities SET name=?,updated_at=CURRENT_TIMESTAMP WHERE entity_id=?',
                         (name, existing[0]))
            conn.execute(
                """INSERT INTO entity_audit(entity_id,action,actor,detail)
                   VALUES(?,'rename',?,?)""",
                (existing[0], actor, f'{old[0]} -> {name}'),
            )
        return existing[0]
    kind = TABLE_KINDS[table]
    prefix = f'{kind}-COMP-'
    used = {
        int(row[0][len(prefix):])
        for row in conn.execute('SELECT entity_id FROM campaign_entities WHERE entity_id LIKE ?', (prefix + '%',))
        if row[0][len(prefix):].isdigit()
    }
    number = int(row_id)
    while number in used:
        number += 1
    entity_id = f'{prefix}{number:04d}'
    conn.execute(
        """INSERT INTO campaign_entities(entity_id,kind,name,campaign_id)
           VALUES(?,?,?,?)""",
        (entity_id, kind, name, CAMPAIGN_ID),
    )
    link_legacy_row(conn, entity_id, table, row_id)
    conn.execute(
        """INSERT INTO entity_audit(entity_id,action,actor,detail)
           VALUES(?,'create',?,?)""",
        (entity_id, actor, f'{table}:{row_id}'),
    )
    return entity_id


def campaign_monster(conn: sqlite3.Connection, row_id: int, source: str | None) -> bool:
    if (source or '').strip().lower() in {'manual', 'campaign'}:
        return True
    return conn.execute(
        "SELECT 1 FROM entity_legacy_links WHERE lectern_table='monsters' AND lectern_id=?",
        (row_id,),
    ).fetchone() is not None
