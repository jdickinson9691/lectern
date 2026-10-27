"""Draft and approval workflow for Ashen Company Story records."""
from __future__ import annotations

from pathlib import Path

from ..database.schema import connect
from ..database.campaign_identity import CAMPAIGN_ID


class StoryService:
    PREFIX = 'DOC-COMP-'

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    def list_stories(self) -> list[dict]:
        with connect(self.db_path) as conn:
            rows = conn.execute("""SELECT entity_id, name, visibility, status
                FROM campaign_entities
                WHERE kind='DOC' AND campaign_id=?
                ORDER BY entity_id""", (CAMPAIGN_ID,)).fetchall()
            return [dict(row) for row in rows]

    def get_story(self, entity_id: str) -> dict:
        with connect(self.db_path) as conn:
            row = conn.execute("""SELECT entity_id, name, visibility, status
                FROM campaign_entities WHERE entity_id=? AND kind='DOC'
                AND campaign_id=?""", (entity_id, CAMPAIGN_ID)).fetchone()
            if row is None:
                raise KeyError(entity_id)
            story = dict(row)
            story['player_text'] = ''
            story['gm_notes'] = ''
            story['player_text_status'] = 'draft'
            for note in conn.execute("""SELECT audience, field_key, content, status
                FROM entity_knowledge WHERE entity_id=?""", (entity_id,)):
                if note['audience'] == 'player' and note['field_key'] == 'story':
                    story['player_text'] = note['content']
                    story['player_text_status'] = note['status']
                elif note['audience'] == 'gm' and note['field_key'] == 'notes':
                    story['gm_notes'] = note['content']
            return story

    def create_draft(self, title: str, player_text: str, gm_notes: str = '', *,
                     actor: str = 'user') -> str:
        title = title.strip()
        player_text = player_text.strip()
        gm_notes = gm_notes.strip()
        if not title:
            raise ValueError('Story title is required')
        with connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            return self.create_draft_in_transaction(conn, title, player_text, gm_notes, actor=actor)

    @classmethod
    def create_draft_in_transaction(cls, conn, title: str, player_text: str,
                                    gm_notes: str = '', *, actor: str = 'user') -> str:
        """Let other campaign workflows compose Story creation atomically."""
        title, player_text, gm_notes = title.strip(), player_text.strip(), gm_notes.strip()
        if not title:
            raise ValueError('Story title is required')
        numbers = [int(row[0][len(cls.PREFIX):])
                       for row in conn.execute("""SELECT entity_id FROM campaign_entities
                           WHERE entity_id GLOB 'DOC-COMP-[0-9]*'""")
                       if row[0][len(cls.PREFIX):].isdigit()]
        entity_id = f'{cls.PREFIX}{max(numbers, default=0) + 1:04d}'
        conn.execute("""INSERT INTO campaign_entities
                (entity_id, kind, name, campaign_id, visibility, status)
                VALUES(?, 'DOC', ?, ?, 'player', 'draft')""",
                (entity_id, title, CAMPAIGN_ID))
        if player_text:
            cls._set_note(conn, entity_id, 'player', 'story', player_text)
        if gm_notes:
            cls._set_note(conn, entity_id, 'gm', 'notes', gm_notes)
        cls._audit(conn, entity_id, 'create_story', actor, title)
        return entity_id

    def save_draft(self, entity_id: str, title: str, player_text: str,
                   gm_notes: str = '', *, actor: str = 'user') -> None:
        title = title.strip()
        player_text = player_text.strip()
        gm_notes = gm_notes.strip()
        if not title:
            raise ValueError('Story title is required')
        with connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute("""SELECT name, status FROM campaign_entities
                WHERE entity_id=? AND kind='DOC' AND campaign_id=?""",
                (entity_id, CAMPAIGN_ID)).fetchone()
            if row is None:
                raise KeyError(entity_id)
            if row['status'] == 'archived':
                raise ValueError('Archived Stories cannot be edited')
            notes = {(note['audience'], note['field_key']): note['content']
                     for note in conn.execute("""SELECT audience, field_key, content
                         FROM entity_knowledge WHERE entity_id=?""", (entity_id,))}
            public_changed = (row['name'] != title or
                              notes.get(('player', 'story'), '') != player_text)
            gm_changed = notes.get(('gm', 'notes'), '') != gm_notes
            if not public_changed and not gm_changed:
                return
            if public_changed:
                conn.execute("""UPDATE campaign_entities SET name=?, status='draft',
                    updated_at=CURRENT_TIMESTAMP WHERE entity_id=?""", (title, entity_id))
                if player_text:
                    self._set_note(conn, entity_id, 'player', 'story', player_text)
                else:
                    conn.execute("""DELETE FROM entity_knowledge
                        WHERE entity_id=? AND audience='player' AND field_key='story'""", (entity_id,))
                self._audit(conn, entity_id, 'story_public_draft', actor, 'Public text or title changed')
            if gm_changed:
                if gm_notes:
                    self._set_note(conn, entity_id, 'gm', 'notes', gm_notes)
                else:
                    conn.execute("""DELETE FROM entity_knowledge
                        WHERE entity_id=? AND audience='gm' AND field_key='notes'""", (entity_id,))
                self._audit(conn, entity_id, 'story_gm_notes', actor, 'GM notes changed')

    def approve(self, entity_id: str, *, actor: str = 'user') -> None:
        with connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute("""SELECT status, visibility FROM campaign_entities
                WHERE entity_id=? AND kind='DOC' AND campaign_id=?""",
                (entity_id, CAMPAIGN_ID)).fetchone()
            if row is None:
                raise KeyError(entity_id)
            if row['status'] == 'archived' or row['visibility'] != 'player':
                raise ValueError('Only player-visible, active Stories can be approved')
            note = conn.execute("""SELECT content, status FROM entity_knowledge
                WHERE entity_id=? AND audience='player' AND field_key='story'""",
                (entity_id,)).fetchone()
            if note is None or not note['content'].strip():
                raise ValueError('Player text is required before approval')
            if row['status'] == 'approved' and note['status'] == 'approved':
                return
            conn.execute("""UPDATE entity_knowledge SET status='approved'
                WHERE entity_id=? AND audience='player' AND field_key='story'""", (entity_id,))
            conn.execute("""UPDATE campaign_entities SET status='approved',
                updated_at=CURRENT_TIMESTAMP WHERE entity_id=?""", (entity_id,))
            self._audit(conn, entity_id, 'approve_story', actor, 'Player Story approved')

    def return_to_draft(self, entity_id: str, *, actor: str = 'user') -> None:
        with connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute("""SELECT status FROM campaign_entities WHERE entity_id=?
                AND kind='DOC' AND campaign_id=?""", (entity_id, CAMPAIGN_ID)).fetchone()
            if row is None:
                raise KeyError(entity_id)
            if row['status'] == 'approved':
                conn.execute("""UPDATE campaign_entities SET status='draft',
                    updated_at=CURRENT_TIMESTAMP WHERE entity_id=?""", (entity_id,))
                self._audit(conn, entity_id, 'revoke_story', actor, 'Story returned to draft')

    @staticmethod
    def _set_note(conn, entity_id: str, audience: str, key: str, content: str) -> None:
        conn.execute("""INSERT INTO entity_knowledge(entity_id,audience,field_key,content,status)
            VALUES(?,?,?,?,'draft') ON CONFLICT(entity_id,audience,field_key)
            DO UPDATE SET content=excluded.content,status='draft'""",
            (entity_id, audience, key, content))

    @staticmethod
    def _audit(conn, entity_id: str, action: str, actor: str, detail: str) -> None:
        conn.execute("""INSERT INTO entity_audit(entity_id,action,actor,detail)
            VALUES(?,?,?,?)""", (entity_id, action, actor, detail))
