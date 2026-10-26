"""Schema v7: explicit relationship approval and fail-closed edit rules."""
from __future__ import annotations

import sqlite3


DDL = (
    """ALTER TABLE entity_relationships ADD COLUMN status TEXT NOT NULL DEFAULT 'draft'
       CHECK(status IN ('draft','approved'))""",
    """CREATE TRIGGER player_entity_edit_invalidates_approval
       AFTER UPDATE OF name,kind,campaign_id,visibility ON campaign_entities
       WHEN NEW.status='approved' AND
            (OLD.name IS NOT NEW.name OR OLD.kind IS NOT NEW.kind OR
             OLD.campaign_id IS NOT NEW.campaign_id OR OLD.visibility IS NOT NEW.visibility)
       BEGIN
           UPDATE campaign_entities SET status='draft' WHERE entity_id=NEW.entity_id;
       END""",
    """CREATE TRIGGER player_knowledge_edit_invalidates_approval
       AFTER UPDATE OF audience,field_key,content ON entity_knowledge
       WHEN NEW.status='approved' AND
            (OLD.audience IS NOT NEW.audience OR OLD.field_key IS NOT NEW.field_key OR
             OLD.content IS NOT NEW.content)
       BEGIN
           UPDATE entity_knowledge SET status='draft'
           WHERE entity_id=NEW.entity_id AND audience=NEW.audience AND field_key=NEW.field_key;
       END""",
    """CREATE TRIGGER player_relationship_edit_invalidates_approval
       AFTER UPDATE OF source_id,target_id,relation,visibility ON entity_relationships
       WHEN NEW.status='approved' AND
            (OLD.source_id IS NOT NEW.source_id OR OLD.target_id IS NOT NEW.target_id OR
             OLD.relation IS NOT NEW.relation OR OLD.visibility IS NOT NEW.visibility)
       BEGIN
           UPDATE entity_relationships SET status='draft'
           WHERE source_id=NEW.source_id AND target_id=NEW.target_id AND relation=NEW.relation;
       END""",
    """CREATE TRIGGER player_endpoint_change_invalidates_relationships
       AFTER UPDATE OF status,visibility ON campaign_entities
       WHEN NEW.status <> 'approved' OR NEW.visibility <> 'player'
       BEGIN
           UPDATE entity_relationships SET status='draft'
           WHERE source_id=NEW.entity_id OR target_id=NEW.entity_id;
       END""",
)


def migrate_v7(conn: sqlite3.Connection) -> None:
    version = conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
    if version and version[0] in ('7', '8'):
        return
    if not version or version[0] != '6':
        raise ValueError('Player release migration requires schema v6')
    conn.execute('SAVEPOINT player_release_v7')
    try:
        for statement in DDL:
            conn.execute(statement)
        conn.execute("UPDATE metadata SET value='7' WHERE key='schema_version'")
        conn.execute('RELEASE SAVEPOINT player_release_v7')
    except BaseException:
        conn.execute('ROLLBACK TO SAVEPOINT player_release_v7')
        conn.execute('RELEASE SAVEPOINT player_release_v7')
        raise
