"""Sourced NPC and Location drafting with explicit player approval."""
from __future__ import annotations

from pathlib import Path

from ..database.campaign_identity import CAMPAIGN_ID
from ..database.schema import connect
from .campaign_canon import CampaignCanonAgent
from .story_mission_agent import StoryMissionAgent


class CampaignWorldAgent:
    KIND = ''
    PREFIX = ''
    PLAYER_KEY = ''
    LABEL = ''

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.canon = CampaignCanonAgent(db_path)
        self.context = StoryMissionAgent(db_path)

    def available_sources(self) -> list[dict]:
        return self.context.available_sources()

    def approved_context(self, entity_ids: list[str]) -> list[dict]:
        return self.context.approved_context(entity_ids)

    def list_records(self) -> list[dict]:
        with connect(self.db_path) as conn:
            return [dict(row) for row in conn.execute("""SELECT entity_id,name,status,visibility
                FROM campaign_entities WHERE kind=? AND campaign_id=?
                ORDER BY entity_id""", (self.KIND, CAMPAIGN_ID))]

    def get_record(self, entity_id: str) -> dict:
        with connect(self.db_path) as conn:
            row = conn.execute("""SELECT e.entity_id,e.name,e.status,e.visibility,
                p.content AS player_text,p.status AS player_text_status,
                n.content AS gm_notes
                FROM campaign_entities e
                LEFT JOIN entity_knowledge p ON p.entity_id=e.entity_id
                    AND p.audience='player' AND p.field_key=?
                LEFT JOIN entity_knowledge n ON n.entity_id=e.entity_id
                    AND n.audience='gm' AND n.field_key='notes'
                WHERE e.entity_id=? AND e.kind=? AND e.campaign_id=?""",
                (self.PLAYER_KEY, entity_id, self.KIND, CAMPAIGN_ID)).fetchone()
            if row is None:
                raise KeyError(entity_id)
            result = dict(row)
            result['sources'] = [source[0] for source in conn.execute("""SELECT source_ref FROM entity_sources
                WHERE entity_id=? AND source_type='campaign_entity' ORDER BY id""", (entity_id,))]
            return result

    def draft(self, name: str, player_text: str, gm_notes: str = '', *,
              source_entity_ids: list[str], actor: str | None = None) -> str:
        name, player_text, gm_notes = name.strip(), player_text.strip(), gm_notes.strip()
        if not name or not player_text:
            raise ValueError(f'{self.LABEL} name and player text are required')
        if not source_entity_ids:
            raise ValueError('At least one approved canon source is required')
        actor = actor or f'{self.KIND.lower()}-agent'
        with connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            sources = StoryMissionAgent._approved_context(conn, source_entity_ids)
            numbers = [int(row[0][len(self.PREFIX):])
                       for row in conn.execute("SELECT entity_id FROM campaign_entities WHERE kind=?", (self.KIND,))
                       if row[0].startswith(self.PREFIX) and row[0][len(self.PREFIX):].isdigit()]
            entity_id = f'{self.PREFIX}{max(numbers, default=0) + 1:04d}'
            conn.execute("""INSERT INTO campaign_entities
                (entity_id,kind,name,campaign_id,visibility,status)
                VALUES(?,?,?,?,'player','draft')""", (entity_id, self.KIND, name, CAMPAIGN_ID))
            conn.execute("""INSERT INTO entity_knowledge(entity_id,audience,field_key,content)
                VALUES(?,'player',?,?)""", (entity_id, self.PLAYER_KEY, player_text))
            if gm_notes:
                conn.execute("""INSERT INTO entity_knowledge(entity_id,audience,field_key,content)
                    VALUES(?,'gm','notes',?)""", (entity_id, gm_notes))
            self._audit(conn, entity_id, 'create', actor, f'{self.LABEL}: {name}')
            StoryMissionAgent._attach_sources(conn, entity_id, sources, actor)
            return entity_id

    def save(self, entity_id: str, name: str, player_text: str, gm_notes: str = '', *,
             actor: str = 'gm') -> None:
        name, player_text, gm_notes = name.strip(), player_text.strip(), gm_notes.strip()
        if not name:
            raise ValueError(f'{self.LABEL} name is required')
        with connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute("""SELECT e.name,e.status,p.content AS player_text,n.content AS gm_notes
                FROM campaign_entities e
                LEFT JOIN entity_knowledge p ON p.entity_id=e.entity_id
                    AND p.audience='player' AND p.field_key=?
                LEFT JOIN entity_knowledge n ON n.entity_id=e.entity_id
                    AND n.audience='gm' AND n.field_key='notes'
                WHERE e.entity_id=? AND e.kind=? AND e.campaign_id=?""",
                (self.PLAYER_KEY, entity_id, self.KIND, CAMPAIGN_ID)).fetchone()
            if row is None:
                raise KeyError(entity_id)
            if row['status'] == 'archived':
                raise ValueError(f'Archived {self.LABEL} records cannot be edited')
            public_changed = row['name'] != name or (row['player_text'] or '') != player_text
            gm_changed = (row['gm_notes'] or '') != gm_notes
            if public_changed:
                conn.execute("""UPDATE campaign_entities SET name=?,status='draft',
                    updated_at=CURRENT_TIMESTAMP WHERE entity_id=?""", (name, entity_id))
                if player_text:
                    conn.execute("""INSERT INTO entity_knowledge(entity_id,audience,field_key,content,status)
                        VALUES(?,'player',?,?,'draft') ON CONFLICT(entity_id,audience,field_key)
                        DO UPDATE SET content=excluded.content,status='draft'""",
                        (entity_id, self.PLAYER_KEY, player_text))
                else:
                    conn.execute("""DELETE FROM entity_knowledge WHERE entity_id=?
                        AND audience='player' AND field_key=?""", (entity_id, self.PLAYER_KEY))
                self._audit(conn, entity_id, 'public_draft', actor,
                            f'{self.LABEL} name or player text changed')
            if gm_changed:
                if gm_notes:
                    conn.execute("""INSERT INTO entity_knowledge(entity_id,audience,field_key,content,status)
                        VALUES(?,'gm','notes',?,'draft') ON CONFLICT(entity_id,audience,field_key)
                        DO UPDATE SET content=excluded.content,status='draft'""",
                        (entity_id, gm_notes))
                else:
                    conn.execute("""DELETE FROM entity_knowledge WHERE entity_id=?
                        AND audience='gm' AND field_key='notes'""", (entity_id,))
                self._audit(conn, entity_id, 'gm_notes', actor, f'{self.LABEL} GM notes changed')

    def approve(self, entity_id: str, *, actor: str = 'gm') -> None:
        with connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute("""SELECT e.status,e.visibility,p.content,p.status AS player_status
                FROM campaign_entities e LEFT JOIN entity_knowledge p
                    ON p.entity_id=e.entity_id AND p.audience='player' AND p.field_key=?
                WHERE e.entity_id=? AND e.kind=? AND e.campaign_id=?""",
                (self.PLAYER_KEY, entity_id, self.KIND, CAMPAIGN_ID)).fetchone()
            if row is None:
                raise KeyError(entity_id)
            if row['status'] == 'archived' or row['visibility'] != 'player':
                raise ValueError('Only active player-visible records can be approved')
            if not (row['content'] or '').strip():
                raise ValueError('Player text is required before approval')
            if row['status'] == 'approved' and row['player_status'] == 'approved':
                return
            conn.execute("""UPDATE entity_knowledge SET status='approved'
                WHERE entity_id=? AND audience='player' AND field_key=?""",
                (entity_id, self.PLAYER_KEY))
            conn.execute("""UPDATE campaign_entities SET status='approved',
                updated_at=CURRENT_TIMESTAMP WHERE entity_id=?""", (entity_id,))
            self._audit(conn, entity_id, 'approve', actor, f'{self.LABEL} player text approved')

    def return_to_draft(self, entity_id: str, *, actor: str = 'gm') -> None:
        with connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute("""SELECT status FROM campaign_entities WHERE entity_id=?
                AND kind=? AND campaign_id=?""", (entity_id, self.KIND, CAMPAIGN_ID)).fetchone()
            if row is None:
                raise KeyError(entity_id)
            if row['status'] == 'approved':
                conn.execute("""UPDATE campaign_entities SET status='draft',
                    updated_at=CURRENT_TIMESTAMP WHERE entity_id=?""", (entity_id,))
                self._audit(conn, entity_id, 'revoke', actor, f'{self.LABEL} returned to draft')

    def submit_canon_fact(self, entity_id: str, audience: str, field_key: str,
                          content: str, *, source_type: str, source_ref: str,
                          citation: str = '') -> int:
        return self.canon.submit_for_review(entity_id, audience, field_key, content,
            source_type=source_type, source_ref=source_ref, citation=citation,
            actor=f'{self.KIND.lower()}-agent')

    @staticmethod
    def _audit(conn, entity_id: str, action: str, actor: str, detail: str) -> None:
        conn.execute("""INSERT INTO entity_audit(entity_id,action,actor,detail)
            VALUES(?,?,?,?)""", (entity_id, action, actor, detail))


class NPCAgent(CampaignWorldAgent):
    KIND = 'NPC'
    PREFIX = 'NPC-COMP-'
    PLAYER_KEY = 'profile'
    LABEL = 'NPC'


class LocationAgent(CampaignWorldAgent):
    KIND = 'LOC'
    PREFIX = 'LOC-COMP-'
    PLAYER_KEY = 'description'
    LABEL = 'Location'


class FactionAgent(CampaignWorldAgent):
    KIND = 'FAC'
    PREFIX = 'FAC-COMP-'
    PLAYER_KEY = 'overview'
    LABEL = 'Faction'
    RELATIONS = {'NPC': 'has_member', 'LOC': 'active_in', 'MIS': 'involved_in'}

    def available_targets(self) -> list[dict]:
        with connect(self.db_path) as conn:
            return [dict(row) for row in conn.execute("""SELECT entity_id,name,kind,status,visibility
                FROM campaign_entities WHERE campaign_id=? AND kind IN ('NPC','LOC','MIS')
                AND status<>'archived' ORDER BY kind,name,entity_id""", (CAMPAIGN_ID,))]

    def relationships(self, faction_id: str) -> list[dict]:
        with connect(self.db_path) as conn:
            self._require_faction(conn, faction_id)
            return [dict(row) for row in conn.execute("""SELECT r.target_id,t.name AS target_name,
                t.kind,r.relation,r.visibility,r.status FROM entity_relationships r
                JOIN campaign_entities t ON t.entity_id=r.target_id
                WHERE r.source_id=? ORDER BY r.relation,t.name""", (faction_id,))]

    def link(self, faction_id: str, target_id: str, *, visibility: str = 'gm',
             actor: str = 'gm') -> str:
        if visibility not in {'gm', 'player'}:
            raise ValueError('Relationship visibility must be gm or player')
        with connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            self._require_faction(conn, faction_id)
            target = conn.execute("""SELECT kind,status FROM campaign_entities
                WHERE entity_id=? AND campaign_id=?""", (target_id, CAMPAIGN_ID)).fetchone()
            if target is None or target['kind'] not in self.RELATIONS or target['status'] == 'archived':
                raise ValueError('Active campaign NPC, Location, or Mission required')
            relation = self.RELATIONS[target['kind']]
            conn.execute("""INSERT INTO entity_relationships
                (source_id,target_id,relation,visibility,status)
                VALUES(?,?,?,?,'draft')""", (faction_id, target_id, relation, visibility))
            self._audit(conn, faction_id, 'relationship_draft', actor,
                        f'{relation}:{target_id} ({visibility})')
            return relation

    def approve_relationship(self, faction_id: str, target_id: str, *,
                             actor: str = 'gm') -> None:
        with connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            self._require_faction(conn, faction_id)
            row = conn.execute("""SELECT r.relation,r.visibility,r.status,t.kind
                FROM entity_relationships r JOIN campaign_entities t ON t.entity_id=r.target_id
                WHERE r.source_id=? AND r.target_id=?""", (faction_id, target_id)).fetchone()
            if row is None or row['relation'] != self.RELATIONS.get(row['kind']):
                raise KeyError((faction_id, target_id))
            endpoints = conn.execute("""SELECT COUNT(*) FROM campaign_entities
                WHERE entity_id IN (?,?) AND campaign_id=?
                AND visibility='player' AND status='approved'""",
                (faction_id, target_id, CAMPAIGN_ID)).fetchone()[0]
            if row['visibility'] != 'player' or endpoints != 2:
                raise ValueError('Player relationship and both endpoints must be approved')
            if row['status'] != 'approved':
                conn.execute("""UPDATE entity_relationships SET status='approved'
                    WHERE source_id=? AND target_id=? AND relation=?""",
                    (faction_id, target_id, row['relation']))
                self._audit(conn, faction_id, 'approve_relationship', actor,
                            f'{row["relation"]}:{target_id}')

    def return_relationship_to_draft(self, faction_id: str, target_id: str, *,
                                     actor: str = 'gm') -> None:
        with connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            self._require_faction(conn, faction_id)
            row = conn.execute("""SELECT relation,status FROM entity_relationships
                WHERE source_id=? AND target_id=?""", (faction_id, target_id)).fetchone()
            if row is None:
                raise KeyError((faction_id, target_id))
            if row['status'] == 'approved':
                conn.execute("""UPDATE entity_relationships SET status='draft'
                    WHERE source_id=? AND target_id=? AND relation=?""",
                    (faction_id, target_id, row['relation']))
                self._audit(conn, faction_id, 'revoke_relationship', actor,
                            f'{row["relation"]}:{target_id}')

    @staticmethod
    def _require_faction(conn, faction_id: str) -> None:
        row = conn.execute("""SELECT status FROM campaign_entities WHERE entity_id=?
            AND kind='FAC' AND campaign_id=?""", (faction_id, CAMPAIGN_ID)).fetchone()
        if row is None:
            raise KeyError(faction_id)
        if row['status'] == 'archived':
            raise ValueError('Archived Faction cannot be linked')
