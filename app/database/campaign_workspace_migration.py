"""Schema v12: connect ordinary Lectern campaigns to permanent canon roots."""
from __future__ import annotations

import sqlite3

from .campaign_identity import ASHEN_CAMPAIGN_ID


def ensure_campaign_workspace(conn: sqlite3.Connection, campaign_id: int,
                              *, actor: str = 'lectern') -> str:
    """Return one permanent root for a campaign, creating it only if missing."""
    campaign = conn.execute('SELECT id,name FROM campaigns WHERE id=?',
                            (campaign_id,)).fetchone()
    if campaign is None:
        raise KeyError(campaign_id)
    linked = conn.execute('SELECT entity_id FROM campaign_workspace_links WHERE campaign_id=?',
                          (campaign_id,)).fetchone()
    if linked:
        return linked['entity_id']
    ashen_available = (campaign['name'] == 'Ashen Company' and
                       conn.execute('SELECT 1 FROM campaign_entities WHERE entity_id=?',
                                    (ASHEN_CAMPAIGN_ID,)).fetchone() is not None and
                       conn.execute('SELECT 1 FROM campaign_workspace_links WHERE entity_id=?',
                                    (ASHEN_CAMPAIGN_ID,)).fetchone() is None)
    entity_id = ASHEN_CAMPAIGN_ID if ashen_available else f"CAM-LECTERN-{campaign_id:04d}"
    existing = conn.execute('SELECT kind FROM campaign_entities WHERE entity_id=?',
                            (entity_id,)).fetchone()
    if existing is None:
        conn.execute("""INSERT INTO campaign_entities(entity_id,kind,name,visibility,status)
            VALUES(?,'CAM',?,'gm','approved')""", (entity_id, campaign['name']))
        conn.execute("""INSERT INTO entity_audit(entity_id,action,actor,detail)
            VALUES(?,'create',?,?)""", (entity_id, actor, 'Campaign canon root'))
    elif existing['kind'] != 'CAM':
        raise ValueError(f'Campaign root ID collides with {existing["kind"]}: {entity_id}')
    conn.execute('INSERT INTO campaign_workspace_links(campaign_id,entity_id) VALUES(?,?)',
                 (campaign_id, entity_id))
    return entity_id


def migrate_campaign_workspaces_v12(conn: sqlite3.Connection) -> None:
    conn.execute('SAVEPOINT campaign_workspaces_v12')
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS campaign_workspace_links (
            campaign_id INTEGER PRIMARY KEY REFERENCES campaigns(id) ON DELETE CASCADE,
            entity_id TEXT NOT NULL UNIQUE REFERENCES campaign_entities(entity_id) ON DELETE RESTRICT
        )""")
        for row in conn.execute('SELECT id FROM campaigns ORDER BY id').fetchall():
            ensure_campaign_workspace(conn, row['id'], actor='migration:campaign-workflow')
        conn.execute("UPDATE metadata SET value='12' WHERE key='schema_version'")
        conn.execute('RELEASE SAVEPOINT campaign_workspaces_v12')
    except BaseException:
        conn.execute('ROLLBACK TO SAVEPOINT campaign_workspaces_v12')
        conn.execute('RELEASE SAVEPOINT campaign_workspaces_v12')
        raise
