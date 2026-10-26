"""Schema v6: enforce legacy links and adopt existing campaign rows."""
from __future__ import annotations

import sqlite3
from .campaign_identity import TABLE_KINDS, campaign_monster, ensure_campaign_link


def migrate_v6(conn: sqlite3.Connection) -> None:
    version = conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
    if version and version[0] in ('6', '7', '8'):
        return
    if not version or version[0] != '5':
        raise ValueError('Campaign link migration requires schema v5')

    conn.execute('SAVEPOINT campaign_links_v6')
    try:
        # v5 allowed polymorphic links but could not declare a SQL foreign key to
        # several tables. Reject bad pre-existing links before installing guards.
        for entity_id, table, row_id, kind in conn.execute(
            """SELECT l.entity_id,l.lectern_table,l.lectern_id,e.kind
               FROM entity_legacy_links l LEFT JOIN campaign_entities e USING(entity_id)"""
        ):
            if table not in TABLE_KINDS or kind != TABLE_KINDS[table]:
                raise ValueError(f'Invalid legacy link: {entity_id} -> {table}:{row_id}')
            if conn.execute(f'SELECT 1 FROM {table} WHERE id=?', (row_id,)).fetchone() is None:
                raise ValueError(f'Missing legacy row: {table}:{row_id}')

        for operation in ('INSERT', 'UPDATE'):
            conn.execute(f"""CREATE TRIGGER legacy_link_kind_{operation.lower()}
                BEFORE {operation} ON entity_legacy_links
                WHEN (SELECT kind FROM campaign_entities WHERE entity_id=NEW.entity_id) <>
                     CASE NEW.lectern_table
                         WHEN 'players' THEN 'PC' WHEN 'encounters' THEN 'ENC'
                         WHEN 'monsters' THEN 'CRE' WHEN 'spells' THEN 'SPL'
                         WHEN 'rules_reference' THEN 'RULE' ELSE 'ITM' END
                BEGIN SELECT RAISE(ABORT, 'legacy link kind mismatch'); END""")
            for table in TABLE_KINDS:
                conn.execute(f"""CREATE TRIGGER legacy_link_{table}_{operation.lower()}
                    BEFORE {operation} ON entity_legacy_links
                    WHEN NEW.lectern_table='{table}' AND
                         NOT EXISTS(SELECT 1 FROM {table} WHERE id=NEW.lectern_id)
                    BEGIN SELECT RAISE(ABORT, 'legacy row does not exist'); END""")

        for table in TABLE_KINDS:
            conn.execute(f"""CREATE TRIGGER legacy_{table}_deleted
                AFTER DELETE ON {table}
                BEGIN
                    INSERT INTO entity_audit(entity_id,action,actor,detail)
                    SELECT entity_id,'unlink','lectern', '{table}:' || OLD.id
                    FROM entity_legacy_links
                    WHERE lectern_table='{table}' AND lectern_id=OLD.id;
                    UPDATE campaign_entities SET status='archived',updated_at=CURRENT_TIMESTAMP
                    WHERE entity_id IN (SELECT entity_id FROM entity_legacy_links
                                        WHERE lectern_table='{table}' AND lectern_id=OLD.id);
                    DELETE FROM entity_legacy_links
                    WHERE lectern_table='{table}' AND lectern_id=OLD.id;
                END""")

        if conn.execute("SELECT 1 FROM campaign_entities WHERE entity_id='CAM-ASHEN-0001'").fetchone():
            for row in conn.execute('SELECT id,name FROM players').fetchall():
                ensure_campaign_link(conn, 'players', row['id'], row['name'], actor='migration:ashen')
            for row in conn.execute('SELECT id,name FROM encounters').fetchall():
                ensure_campaign_link(conn, 'encounters', row['id'], row['name'], actor='migration:ashen')
            for row in conn.execute('SELECT id,name,source FROM monsters').fetchall():
                if campaign_monster(conn, row['id'], row['source']):
                    ensure_campaign_link(conn, 'monsters', row['id'], row['name'], actor='migration:ashen')

        conn.execute("UPDATE metadata SET value='6' WHERE key='schema_version'")
        conn.execute('RELEASE SAVEPOINT campaign_links_v6')
    except BaseException:
        conn.execute('ROLLBACK TO SAVEPOINT campaign_links_v6')
        conn.execute('RELEASE SAVEPOINT campaign_links_v6')
        raise
