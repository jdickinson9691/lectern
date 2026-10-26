"""Write boundary for campaign entities, approval, and their audit trail."""
from __future__ import annotations

from pathlib import Path
from .schema import connect
from .campaign_identity import link_legacy_row


class CampaignRepository:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    def create_entity(self, entity_id: str, kind: str, name: str, *,
                      campaign_id: str | None = 'CAM-ASHEN-0001',
                      visibility: str = 'gm', actor: str = 'user') -> None:
        if kind == 'CAM':
            campaign_id = None
        with connect(self.db_path) as conn:
            conn.execute("""INSERT INTO campaign_entities
                (entity_id,kind,name,campaign_id,visibility)
                VALUES(?,?,?,?,?)""", (entity_id, kind, name, campaign_id, visibility))
            conn.execute("""INSERT INTO entity_audit(entity_id,action,actor,detail)
                VALUES(?,'create',?,?)""", (entity_id, actor, name))

    def rename_entity(self, entity_id: str, name: str, *, actor: str = 'user') -> None:
        with connect(self.db_path) as conn:
            old = conn.execute('SELECT name FROM campaign_entities WHERE entity_id=?', (entity_id,)).fetchone()
            if old is None:
                raise KeyError(entity_id)
            conn.execute('UPDATE campaign_entities SET name=?,updated_at=CURRENT_TIMESTAMP WHERE entity_id=?',
                         (name, entity_id))
            conn.execute("""INSERT INTO entity_audit(entity_id,action,actor,detail)
                VALUES(?,'rename',?,?)""", (entity_id, actor, f'{old[0]} -> {name}'))

    def link_legacy_row(self, entity_id: str, table: str, row_id: int,
                        *, actor: str = 'user') -> None:
        with connect(self.db_path) as conn:
            link_legacy_row(conn, entity_id, table, row_id)
            conn.execute("""INSERT INTO entity_audit(entity_id,action,actor,detail)
                VALUES(?,'link',?,?)""", (entity_id, actor, f'{table}:{row_id}'))

    def list_entities(self):
        with connect(self.db_path) as conn:
            return conn.execute(
                'SELECT entity_id,kind,name,visibility,status FROM campaign_entities ORDER BY name,entity_id'
            ).fetchall()

    def set_visibility(self, entity_id: str, visibility: str, *, actor: str = 'user') -> None:
        if visibility not in {'internal', 'gm', 'player'}:
            raise ValueError('Visibility must be internal, gm, or player')
        with connect(self.db_path) as conn:
            row = conn.execute('SELECT visibility,status FROM campaign_entities WHERE entity_id=?', (entity_id,)).fetchone()
            if row is None:
                raise KeyError(entity_id)
            if row['status'] == 'archived':
                raise ValueError('Archived entities cannot be published')
            if row['visibility'] == visibility:
                return
            conn.execute('UPDATE campaign_entities SET visibility=?,updated_at=CURRENT_TIMESTAMP WHERE entity_id=?',
                         (visibility, entity_id))
            self._audit(conn, entity_id, 'visibility', actor, f'{row["visibility"]} -> {visibility}')

    def approve_entity(self, entity_id: str, *, actor: str = 'user') -> None:
        with connect(self.db_path) as conn:
            row = conn.execute('SELECT visibility,status FROM campaign_entities WHERE entity_id=?', (entity_id,)).fetchone()
            if row is None:
                raise KeyError(entity_id)
            if row['visibility'] != 'player' or row['status'] == 'archived':
                raise ValueError('Only active player-visible entities can be approved')
            if row['status'] != 'approved':
                conn.execute("UPDATE campaign_entities SET status='approved',updated_at=CURRENT_TIMESTAMP WHERE entity_id=?", (entity_id,))
                self._audit(conn, entity_id, 'approve', actor, 'player entity')

    def revoke_entity(self, entity_id: str, *, actor: str = 'user') -> None:
        with connect(self.db_path) as conn:
            row = conn.execute('SELECT status FROM campaign_entities WHERE entity_id=?', (entity_id,)).fetchone()
            if row is None:
                raise KeyError(entity_id)
            if row['status'] == 'approved':
                conn.execute("UPDATE campaign_entities SET status='draft',updated_at=CURRENT_TIMESTAMP WHERE entity_id=?", (entity_id,))
                self._audit(conn, entity_id, 'revoke', actor, 'player entity')

    def set_knowledge(self, entity_id: str, audience: str, field_key: str, content: str,
                      *, actor: str = 'user') -> None:
        if audience not in {'internal', 'gm', 'player'} or not field_key.strip():
            raise ValueError('Audience and field key are required')
        with connect(self.db_path) as conn:
            conn.execute("""INSERT INTO entity_knowledge(entity_id,audience,field_key,content,status)
                VALUES(?,?,?,?,'draft') ON CONFLICT(entity_id,audience,field_key)
                DO UPDATE SET content=excluded.content,status='draft'""",
                (entity_id, audience, field_key, content))
            self._audit(conn, entity_id, 'knowledge_draft', actor, f'{audience}:{field_key}')

    def approve_player_knowledge(self, entity_id: str, field_key: str, *, actor: str = 'user') -> None:
        with connect(self.db_path) as conn:
            row = conn.execute("""SELECT status FROM entity_knowledge
                WHERE entity_id=? AND audience='player' AND field_key=?""", (entity_id, field_key)).fetchone()
            if row is None:
                raise KeyError((entity_id, field_key))
            if row['status'] != 'approved':
                conn.execute("""UPDATE entity_knowledge SET status='approved'
                    WHERE entity_id=? AND audience='player' AND field_key=?""", (entity_id, field_key))
                self._audit(conn, entity_id, 'approve_knowledge', actor, field_key)

    def revoke_player_knowledge(self, entity_id: str, field_key: str, *, actor: str = 'user') -> None:
        with connect(self.db_path) as conn:
            cursor = conn.execute("""UPDATE entity_knowledge SET status='draft'
                WHERE entity_id=? AND audience='player' AND field_key=? AND status='approved'""",
                (entity_id, field_key))
            if cursor.rowcount:
                self._audit(conn, entity_id, 'revoke_knowledge', actor, field_key)

    def add_relationship(self, source_id: str, target_id: str, relation: str, *,
                         visibility: str = 'gm', actor: str = 'user') -> None:
        if visibility not in {'internal', 'gm', 'player'} or not relation.strip():
            raise ValueError('Visibility and relation are required')
        with connect(self.db_path) as conn:
            conn.execute("""INSERT INTO entity_relationships(source_id,target_id,relation,visibility)
                VALUES(?,?,?,?)""", (source_id, target_id, relation, visibility))
            self._audit(conn, source_id, 'relationship_draft', actor, f'{relation}:{target_id}')

    def approve_player_relationship(self, source_id: str, target_id: str, relation: str,
                                    *, actor: str = 'user') -> None:
        with connect(self.db_path) as conn:
            row = conn.execute("""SELECT visibility,status FROM entity_relationships
                WHERE source_id=? AND target_id=? AND relation=?""", (source_id, target_id, relation)).fetchone()
            if row is None:
                raise KeyError((source_id, target_id, relation))
            endpoints = conn.execute("""SELECT count(*) FROM campaign_entities
                WHERE entity_id IN (?,?) AND visibility='player' AND status='approved'""",
                (source_id, target_id)).fetchone()[0]
            if row['visibility'] != 'player' or endpoints != 2:
                raise ValueError('Relationship and both endpoints must be player-visible and approved')
            if row['status'] != 'approved':
                conn.execute("""UPDATE entity_relationships SET status='approved'
                    WHERE source_id=? AND target_id=? AND relation=?""", (source_id, target_id, relation))
                self._audit(conn, source_id, 'approve_relationship', actor, f'{relation}:{target_id}')

    def revoke_player_relationship(self, source_id: str, target_id: str, relation: str,
                                   *, actor: str = 'user') -> None:
        with connect(self.db_path) as conn:
            cursor = conn.execute("""UPDATE entity_relationships SET status='draft'
                WHERE source_id=? AND target_id=? AND relation=? AND status='approved'""",
                (source_id, target_id, relation))
            if cursor.rowcount:
                self._audit(conn, source_id, 'revoke_relationship', actor, f'{relation}:{target_id}')

    @staticmethod
    def _audit(conn, entity_id: str, action: str, actor: str, detail: str) -> None:
        conn.execute("""INSERT INTO entity_audit(entity_id,action,actor,detail)
            VALUES(?,?,?,?)""", (entity_id, action, actor, detail))
