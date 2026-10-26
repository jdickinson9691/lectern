"""Schema v8: durable, private Canon review queue."""
from __future__ import annotations

import sqlite3


DDL = (
    """CREATE TABLE canon_proposals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id TEXT NOT NULL REFERENCES campaign_entities(entity_id) ON DELETE RESTRICT,
        audience TEXT NOT NULL CHECK(audience IN ('internal','gm','player')),
        field_key TEXT NOT NULL,
        content TEXT NOT NULL,
        source_type TEXT NOT NULL,
        source_ref TEXT NOT NULL,
        citation TEXT NOT NULL DEFAULT '',
        baseline_content TEXT,
        baseline_status TEXT,
        status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','accepted','rejected')),
        proposed_by TEXT NOT NULL,
        reviewed_by TEXT,
        review_note TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        reviewed_at TEXT
    )""",
    "CREATE INDEX idx_canon_proposals_status ON canon_proposals(status,id)",
)


def migrate_v8(conn: sqlite3.Connection) -> None:
    version = conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
    if version and version[0] == '8':
        return
    if not version or version[0] != '7':
        raise ValueError('Canon review migration requires schema v7')
    conn.execute('SAVEPOINT canon_review_v8')
    try:
        for statement in DDL:
            conn.execute(statement)
        conn.execute("UPDATE metadata SET value='8' WHERE key='schema_version'")
        conn.execute('RELEASE SAVEPOINT canon_review_v8')
    except BaseException:
        conn.execute('ROLLBACK TO SAVEPOINT canon_review_v8')
        conn.execute('RELEASE SAVEPOINT canon_review_v8')
        raise
