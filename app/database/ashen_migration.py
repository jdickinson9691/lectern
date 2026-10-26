"""Schema v5: canonical campaign identity layered over Lectern's existing tables."""
from __future__ import annotations

import sqlite3
import os


DDL = (
    """CREATE TABLE campaign_entities (
        entity_id TEXT PRIMARY KEY,
        kind TEXT NOT NULL CHECK(kind IN ('CAM','DOC','RULE','CLS','SPL','MAG','NPC','PC','FAC','LOC','MIS','ENC','CRE','ITM')),
        name TEXT NOT NULL,
        campaign_id TEXT REFERENCES campaign_entities(entity_id) ON DELETE RESTRICT,
        visibility TEXT NOT NULL DEFAULT 'gm' CHECK(visibility IN ('internal','gm','player')),
        status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','approved','archived')),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CHECK(entity_id GLOB '[A-Z]*-[A-Z0-9-]*')
    )""",
    """CREATE TABLE entity_relationships (
        source_id TEXT NOT NULL REFERENCES campaign_entities(entity_id) ON DELETE CASCADE,
        target_id TEXT NOT NULL REFERENCES campaign_entities(entity_id) ON DELETE CASCADE,
        relation TEXT NOT NULL,
        visibility TEXT NOT NULL DEFAULT 'gm' CHECK(visibility IN ('internal','gm','player')),
        PRIMARY KEY(source_id,target_id,relation),
        CHECK(source_id <> target_id)
    )""",
    """CREATE TABLE entity_knowledge (
        entity_id TEXT NOT NULL REFERENCES campaign_entities(entity_id) ON DELETE CASCADE,
        audience TEXT NOT NULL CHECK(audience IN ('internal','gm','player')),
        field_key TEXT NOT NULL,
        content TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','approved')),
        PRIMARY KEY(entity_id,audience,field_key)
    )""",
    """CREATE TABLE entity_sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id TEXT NOT NULL REFERENCES campaign_entities(entity_id) ON DELETE CASCADE,
        source_type TEXT NOT NULL,
        source_ref TEXT NOT NULL,
        citation TEXT NOT NULL DEFAULT '',
        import_history_id INTEGER REFERENCES import_history(id) ON DELETE SET NULL,
        UNIQUE(entity_id,source_type,source_ref)
    )""",
    """CREATE TABLE entity_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id TEXT NOT NULL REFERENCES campaign_entities(entity_id) ON DELETE RESTRICT,
        action TEXT NOT NULL,
        actor TEXT NOT NULL,
        detail TEXT NOT NULL DEFAULT '',
        occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE entity_legacy_links (
        entity_id TEXT NOT NULL UNIQUE REFERENCES campaign_entities(entity_id) ON DELETE CASCADE,
        lectern_table TEXT NOT NULL CHECK(lectern_table IN ('players','monsters','encounters','weapons','armor','equipment','magic_items','spells','rules_reference')),
        lectern_id INTEGER NOT NULL,
        PRIMARY KEY(lectern_table,lectern_id)
    )""",
    """CREATE TRIGGER campaign_entity_id_immutable
        BEFORE UPDATE OF entity_id ON campaign_entities
        BEGIN SELECT RAISE(ABORT, 'entity_id is permanent'); END""",
    """CREATE TRIGGER campaign_entity_kind_matches_id
        BEFORE INSERT ON campaign_entities
        WHEN substr(NEW.entity_id,1,instr(NEW.entity_id,'-')-1) <> NEW.kind
        BEGIN SELECT RAISE(ABORT, 'entity_id prefix must match kind'); END""",
    """CREATE INDEX idx_campaign_entities_campaign ON campaign_entities(campaign_id)""",
    """CREATE INDEX idx_entity_sources_import ON entity_sources(import_history_id)""",
)


def migrate_v5(conn: sqlite3.Connection) -> None:
    version = conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
    if version and version[0] in ('5', '6', '7', '8'):
        return
    if not version or version[0] != '4':
        raise ValueError('Ashen migration requires schema v4')

    # The caller has finished v4 DDL. A savepoint keeps all v5 changes atomic.
    conn.execute('SAVEPOINT ashen_v5')
    try:
        for statement in DDL:
            conn.execute(statement)
        if os.environ.get('LECTERN_ASHEN_COMPANY') == '1':
            conn.execute("""INSERT INTO campaign_entities(entity_id,kind,name,visibility,status)
                            VALUES('CAM-ASHEN-0001','CAM','Ashen Company','gm','approved')""")
            conn.execute("""INSERT INTO entity_audit(entity_id,action,actor,detail)
                            VALUES('CAM-ASHEN-0001','create','migration:ashen','Core campaign record')""")
        conn.execute("UPDATE metadata SET value='5' WHERE key='schema_version'")
        conn.execute('RELEASE SAVEPOINT ashen_v5')
    except BaseException:
        conn.execute('ROLLBACK TO SAVEPOINT ashen_v5')
        conn.execute('RELEASE SAVEPOINT ashen_v5')
        raise
