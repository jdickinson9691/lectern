"""Draft sourced Ashen Company Stories and review Missions for publication."""
from __future__ import annotations

from pathlib import Path

from ..database.campaign_identity import CAMPAIGN_ID
from ..database.schema import connect
from .campaign_canon import CampaignCanonAgent
from .story_editor import StoryService


class StoryMissionAgent:
    MISSION_PREFIX = 'MIS-COMP-'

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.stories = StoryService(db_path)
        self.canon = CampaignCanonAgent(db_path)

    def approved_context(self, entity_ids: list[str]) -> list[dict]:
        """Return only approved player-facing facts suitable for a player draft."""
        with connect(self.db_path) as conn:
            return self._approved_context(conn, entity_ids)

    def available_sources(self) -> list[dict]:
        with connect(self.db_path) as conn:
            return [dict(row) for row in conn.execute("""SELECT entity_id,name,kind
                FROM campaign_entities WHERE campaign_id=? AND visibility='player'
                AND status='approved' ORDER BY name,entity_id""", (CAMPAIGN_ID,))]

    @staticmethod
    def _approved_context(conn, entity_ids: list[str]) -> list[dict]:
        context = []
        for entity_id in dict.fromkeys(entity_ids):
            row = conn.execute("""SELECT entity_id,name,kind FROM campaign_entities
                WHERE entity_id=? AND campaign_id=? AND visibility='player'
                AND status='approved'""", (entity_id, CAMPAIGN_ID)).fetchone()
            if row is None:
                raise ValueError(f'Approved player-visible source required: {entity_id}')
            facts = {fact['field_key']: fact['content'] for fact in conn.execute("""SELECT field_key,content
                FROM entity_knowledge WHERE entity_id=? AND audience='player'
                AND status='approved' ORDER BY field_key""", (entity_id,))}
            context.append({'id': row['entity_id'], 'name': row['name'],
                            'kind': row['kind'], 'facts': facts})
        return context

    def draft_story(self, title: str, player_text: str, gm_notes: str = '', *,
                    source_entity_ids: list[str], actor: str = 'story-mission-agent') -> str:
        if not title.strip() or not player_text.strip():
            raise ValueError('Story title and player text are required')
        if not source_entity_ids:
            raise ValueError('At least one approved canon source is required')
        with connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            sources = self._approved_context(conn, source_entity_ids)
            entity_id = StoryService.create_draft_in_transaction(
                conn, title, player_text, gm_notes, actor=actor)
            self._attach_sources(conn, entity_id, sources, actor)
            return entity_id

    def draft_mission(self, title: str, player_briefing: str, gm_notes: str = '', *,
                      source_entity_ids: list[str], story_id: str | None = None,
                      actor: str = 'story-mission-agent') -> str:
        title, player_briefing, gm_notes = title.strip(), player_briefing.strip(), gm_notes.strip()
        if not title or not player_briefing:
            raise ValueError('Mission title and player briefing are required')
        if not source_entity_ids:
            raise ValueError('At least one approved canon source is required')
        with connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            sources = self._approved_context(conn, source_entity_ids)
            if story_id is not None:
                story = conn.execute("""SELECT 1 FROM campaign_entities WHERE entity_id=?
                    AND kind='DOC' AND campaign_id=? AND status<>'archived'""",
                    (story_id, CAMPAIGN_ID)).fetchone()
                if story is None:
                    raise ValueError(f'Existing Ashen Company Story required: {story_id}')
            numbers = [int(row[0][len(self.MISSION_PREFIX):])
                       for row in conn.execute("SELECT entity_id FROM campaign_entities WHERE kind='MIS'")
                       if row[0].startswith(self.MISSION_PREFIX) and
                       row[0][len(self.MISSION_PREFIX):].isdigit()]
            entity_id = f'{self.MISSION_PREFIX}{max(numbers, default=0) + 1:04d}'
            conn.execute("""INSERT INTO campaign_entities
                (entity_id,kind,name,campaign_id,visibility,status)
                VALUES(?,'MIS',?,?,'player','draft')""", (entity_id, title, CAMPAIGN_ID))
            conn.execute("""INSERT INTO entity_knowledge(entity_id,audience,field_key,content)
                VALUES(?,'player','briefing',?)""", (entity_id, player_briefing))
            if gm_notes:
                conn.execute("""INSERT INTO entity_knowledge(entity_id,audience,field_key,content)
                    VALUES(?,'gm','notes',?)""", (entity_id, gm_notes))
            if story_id is not None:
                conn.execute("""INSERT INTO entity_relationships
                    (source_id,target_id,relation,visibility,status)
                    VALUES(?,?,'has_story','gm','draft')""", (entity_id, story_id))
            conn.execute("""INSERT INTO entity_audit(entity_id,action,actor,detail)
                VALUES(?,'create_mission',?,?)""", (entity_id, actor, title))
            self._attach_sources(conn, entity_id, sources, actor)
            return entity_id

    def list_missions(self) -> list[dict]:
        with connect(self.db_path) as conn:
            return [dict(row) for row in conn.execute("""SELECT e.entity_id,e.name,e.status,
                e.visibility,b.content AS player_briefing,b.status AS briefing_status,
                n.content AS gm_notes
                FROM campaign_entities e
                LEFT JOIN entity_knowledge b ON b.entity_id=e.entity_id
                    AND b.audience='player' AND b.field_key='briefing'
                LEFT JOIN entity_knowledge n ON n.entity_id=e.entity_id
                    AND n.audience='gm' AND n.field_key='notes'
                WHERE e.kind='MIS' AND e.campaign_id=? ORDER BY e.entity_id""",
                (CAMPAIGN_ID,))]

    def get_mission(self, entity_id: str) -> dict:
        with connect(self.db_path) as conn:
            row = conn.execute("""SELECT e.entity_id,e.name,e.status,e.visibility,
                b.content AS player_briefing,b.status AS briefing_status,
                n.content AS gm_notes
                FROM campaign_entities e
                LEFT JOIN entity_knowledge b ON b.entity_id=e.entity_id
                    AND b.audience='player' AND b.field_key='briefing'
                LEFT JOIN entity_knowledge n ON n.entity_id=e.entity_id
                    AND n.audience='gm' AND n.field_key='notes'
                WHERE e.entity_id=? AND e.kind='MIS' AND e.campaign_id=?""",
                (entity_id, CAMPAIGN_ID)).fetchone()
            if row is None:
                raise KeyError(entity_id)
            return dict(row)

    def save_mission(self, entity_id: str, title: str, player_briefing: str,
                     gm_notes: str = '', *, actor: str = 'gm') -> None:
        title, player_briefing, gm_notes = title.strip(), player_briefing.strip(), gm_notes.strip()
        if not title:
            raise ValueError('Mission title is required')
        with connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute("""SELECT e.name,e.status,b.content AS player_briefing,
                n.content AS gm_notes FROM campaign_entities e
                LEFT JOIN entity_knowledge b ON b.entity_id=e.entity_id
                    AND b.audience='player' AND b.field_key='briefing'
                LEFT JOIN entity_knowledge n ON n.entity_id=e.entity_id
                    AND n.audience='gm' AND n.field_key='notes'
                WHERE e.entity_id=? AND e.kind='MIS' AND e.campaign_id=?""",
                (entity_id, CAMPAIGN_ID)).fetchone()
            if row is None:
                raise KeyError(entity_id)
            if row['status'] == 'archived':
                raise ValueError('Archived Missions cannot be edited')
            public_changed = row['name'] != title or (row['player_briefing'] or '') != player_briefing
            gm_changed = (row['gm_notes'] or '') != gm_notes
            if not public_changed and not gm_changed:
                return
            if public_changed:
                conn.execute("""UPDATE campaign_entities SET name=?,status='draft',
                    updated_at=CURRENT_TIMESTAMP WHERE entity_id=?""", (title, entity_id))
                if player_briefing:
                    conn.execute("""INSERT INTO entity_knowledge(entity_id,audience,field_key,content,status)
                        VALUES(?,'player','briefing',?,'draft')
                        ON CONFLICT(entity_id,audience,field_key)
                        DO UPDATE SET content=excluded.content,status='draft'""",
                        (entity_id, player_briefing))
                else:
                    conn.execute("""DELETE FROM entity_knowledge WHERE entity_id=?
                        AND audience='player' AND field_key='briefing'""", (entity_id,))
                self._audit(conn, entity_id, 'mission_public_draft', actor,
                            'Title or player briefing changed')
            if gm_changed:
                if gm_notes:
                    conn.execute("""INSERT INTO entity_knowledge(entity_id,audience,field_key,content,status)
                        VALUES(?,'gm','notes',?,'draft')
                        ON CONFLICT(entity_id,audience,field_key)
                        DO UPDATE SET content=excluded.content,status='draft'""",
                        (entity_id, gm_notes))
                else:
                    conn.execute("""DELETE FROM entity_knowledge WHERE entity_id=?
                        AND audience='gm' AND field_key='notes'""", (entity_id,))
                self._audit(conn, entity_id, 'mission_gm_notes', actor, 'GM notes changed')

    def approve_mission(self, entity_id: str, *, actor: str = 'gm') -> None:
        with connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute("""SELECT e.status,e.visibility,b.content,b.status AS briefing_status
                FROM campaign_entities e LEFT JOIN entity_knowledge b
                ON b.entity_id=e.entity_id AND b.audience='player' AND b.field_key='briefing'
                WHERE e.entity_id=? AND e.kind='MIS' AND e.campaign_id=?""",
                (entity_id, CAMPAIGN_ID)).fetchone()
            if row is None:
                raise KeyError(entity_id)
            if row['status'] == 'archived' or row['visibility'] != 'player':
                raise ValueError('Only active player-visible Missions can be approved')
            if not (row['content'] or '').strip():
                raise ValueError('Player briefing is required before approval')
            if row['status'] == 'approved' and row['briefing_status'] == 'approved':
                return
            conn.execute("""UPDATE entity_knowledge SET status='approved'
                WHERE entity_id=? AND audience='player' AND field_key='briefing'""", (entity_id,))
            conn.execute("""UPDATE campaign_entities SET status='approved',
                updated_at=CURRENT_TIMESTAMP WHERE entity_id=?""", (entity_id,))
            self._audit(conn, entity_id, 'approve_mission', actor, 'Player Mission approved')

    def return_mission_to_draft(self, entity_id: str, *, actor: str = 'gm') -> None:
        with connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute("""SELECT status FROM campaign_entities
                WHERE entity_id=? AND kind='MIS' AND campaign_id=?""",
                (entity_id, CAMPAIGN_ID)).fetchone()
            if row is None:
                raise KeyError(entity_id)
            if row['status'] == 'approved':
                conn.execute("""UPDATE campaign_entities SET status='draft',
                    updated_at=CURRENT_TIMESTAMP WHERE entity_id=?""", (entity_id,))
                self._audit(conn, entity_id, 'revoke_mission', actor, 'Mission returned to draft')

    def submit_canon_fact(self, entity_id: str, audience: str, field_key: str,
                          content: str, *, source_type: str, source_ref: str,
                          citation: str = '') -> int:
        return self.canon.submit_for_review(
            entity_id, audience, field_key, content, source_type=source_type,
            source_ref=source_ref, citation=citation, actor='story-mission-agent')

    @staticmethod
    def _attach_sources(conn, entity_id: str, sources: list[dict], actor: str) -> None:
        for source in sources:
            conn.execute("""INSERT INTO entity_sources
                (entity_id,source_type,source_ref,citation)
                VALUES(?,'campaign_entity',?,?)""",
                (entity_id, source['id'], source['name']))
            conn.execute("""INSERT INTO entity_audit(entity_id,action,actor,detail)
                VALUES(?,'source',?,?)""", (entity_id, actor, source['id']))

    @staticmethod
    def _audit(conn, entity_id: str, action: str, actor: str, detail: str) -> None:
        conn.execute("""INSERT INTO entity_audit(entity_id,action,actor,detail)
            VALUES(?,?,?,?)""", (entity_id, action, actor, detail))
