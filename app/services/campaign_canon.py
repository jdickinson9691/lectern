"""Sourced canon proposals over Lectern's existing campaign records.

The agent may draft facts. Publication remains with the existing approval flow.
"""
from __future__ import annotations

from pathlib import Path

from ..database.campaign_identity import CAMPAIGN_ID
from ..database.schema import connect


class CanonConflict(ValueError):
    """A proposal would replace a different approved fact."""


class CampaignCanonAgent:
    def __init__(self, db_path: Path, campaign_id: str = CAMPAIGN_ID):
        self.db_path = Path(db_path)
        self.campaign_id = campaign_id

    def dossier(self, entity_id: str) -> dict:
        """Return the complete GM-facing record, including review and provenance."""
        with connect(self.db_path) as conn:
            entity = conn.execute("""SELECT entity_id,kind,name,campaign_id,visibility,status
                FROM campaign_entities WHERE entity_id=? AND
                (entity_id=? OR campaign_id=?)""",
                (entity_id, self.campaign_id, self.campaign_id)).fetchone()
            if entity is None:
                raise KeyError(entity_id)
            return {
                'entity': dict(entity),
                'facts': [dict(row) for row in conn.execute("""SELECT audience,field_key,content,status
                    FROM entity_knowledge WHERE entity_id=? ORDER BY audience,field_key""", (entity_id,))],
                'sources': [dict(row) for row in conn.execute("""SELECT source_type,source_ref,citation,import_history_id
                    FROM entity_sources WHERE entity_id=? ORDER BY id""", (entity_id,))],
                'relationships': [dict(row) for row in conn.execute("""SELECT target_id,relation,visibility,status
                    FROM entity_relationships WHERE source_id=? ORDER BY target_id,relation""", (entity_id,))],
                'audit': [dict(row) for row in conn.execute("""SELECT action,actor,detail,occurred_at
                    FROM entity_audit WHERE entity_id=? ORDER BY id""", (entity_id,))],
            }

    def entities(self) -> list[dict]:
        with connect(self.db_path) as conn:
            return [dict(row) for row in conn.execute("""SELECT entity_id,name,kind,status
                FROM campaign_entities WHERE campaign_id=? AND status<>'archived'
                ORDER BY name,entity_id""", (self.campaign_id,))]

    def propose_fact(self, entity_id: str, audience: str, field_key: str, content: str,
                     *, source_type: str, source_ref: str, citation: str = '',
                     actor: str = 'canon-agent') -> None:
        """Draft a sourced fact; never silently replace approved canon."""
        if audience not in {'internal', 'gm', 'player'}:
            raise ValueError('Invalid audience')
        field_key, content = field_key.strip(), content.strip()
        source_type, source_ref = source_type.strip(), source_ref.strip()
        if not all((field_key, content, source_type, source_ref)):
            raise ValueError('Fact and source are required')
        with connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            entity = conn.execute("""SELECT status FROM campaign_entities WHERE entity_id=?
                AND campaign_id=?""", (entity_id, self.campaign_id)).fetchone()
            if entity is None:
                raise KeyError(entity_id)
            if entity['status'] == 'archived':
                raise ValueError('Archived entities cannot receive canon proposals')
            old = conn.execute("""SELECT content,status FROM entity_knowledge
                WHERE entity_id=? AND audience=? AND field_key=?""",
                (entity_id, audience, field_key)).fetchone()
            if old and old['status'] == 'approved' and old['content'] != content:
                raise CanonConflict(f'Approved {audience}:{field_key} differs; review before replacing it')
            unchanged = old is not None and old['content'] == content
            if not unchanged:
                conn.execute("""INSERT INTO entity_knowledge(entity_id,audience,field_key,content,status)
                    VALUES(?,?,?,?,'draft') ON CONFLICT(entity_id,audience,field_key)
                    DO UPDATE SET content=excluded.content,status='draft'""",
                    (entity_id, audience, field_key, content))
            conn.execute("""INSERT INTO entity_sources(entity_id,source_type,source_ref,citation)
                VALUES(?,?,?,?) ON CONFLICT(entity_id,source_type,source_ref)
                DO UPDATE SET citation=excluded.citation""",
                (entity_id, source_type, source_ref, citation))
            conn.execute("""INSERT INTO entity_audit(entity_id,action,actor,detail)
                VALUES(?,?,?,?)""", (entity_id, 'canon_source' if unchanged else 'canon_proposal',
                                       actor, f'{audience}:{field_key} from {source_type}:{source_ref}'))

    def submit_for_review(self, entity_id: str, audience: str, field_key: str, content: str,
                          *, source_type: str, source_ref: str, citation: str = '',
                          actor: str = 'canon-agent') -> int:
        """Queue a proposal without changing established facts or player output."""
        if audience not in {'internal', 'gm', 'player'}:
            raise ValueError('Invalid audience')
        values = [field_key.strip(), content.strip(), source_type.strip(), source_ref.strip()]
        if not all(values):
            raise ValueError('Fact and source are required')
        field_key, content, source_type, source_ref = values
        with connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            entity = conn.execute("""SELECT status FROM campaign_entities WHERE entity_id=?
                AND campaign_id=?""", (entity_id, self.campaign_id)).fetchone()
            if entity is None:
                raise KeyError(entity_id)
            if entity['status'] == 'archived':
                raise ValueError('Archived entities cannot receive canon proposals')
            baseline = conn.execute("""SELECT content,status FROM entity_knowledge
                WHERE entity_id=? AND audience=? AND field_key=?""",
                (entity_id, audience, field_key)).fetchone()
            cursor = conn.execute("""INSERT INTO canon_proposals
                (entity_id,audience,field_key,content,source_type,source_ref,citation,
                 baseline_content,baseline_status,proposed_by)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (entity_id, audience, field_key, content, source_type, source_ref, citation,
                 baseline['content'] if baseline else None,
                 baseline['status'] if baseline else None, actor))
            conn.execute("""INSERT INTO entity_audit(entity_id,action,actor,detail)
                VALUES(?,'canon_review_queued',?,?)""",
                (entity_id, actor, f'#{cursor.lastrowid} {audience}:{field_key}'))
            return cursor.lastrowid

    def review_queue(self, *, include_resolved: bool = False) -> list[dict]:
        with connect(self.db_path) as conn:
            rows = conn.execute("""SELECT p.*, e.name AS entity_name,
                k.content AS current_content,k.status AS current_status
                FROM canon_proposals p JOIN campaign_entities e ON e.entity_id=p.entity_id
                LEFT JOIN entity_knowledge k ON k.entity_id=p.entity_id
                    AND k.audience=p.audience AND k.field_key=p.field_key
                WHERE e.campaign_id=? AND (? OR p.status='pending')
                ORDER BY p.id""", (self.campaign_id, int(include_resolved))).fetchall()
            return [dict(row) for row in rows]

    def resolve(self, proposal_id: int, decision: str, *, reviewer: str = 'gm',
                note: str = '') -> None:
        """Accept into draft or reject; stale comparisons require a fresh review."""
        if decision not in {'accept', 'reject'}:
            raise ValueError('Decision must be accept or reject')
        with connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            proposal = conn.execute("""SELECT p.* FROM canon_proposals p
                JOIN campaign_entities e ON e.entity_id=p.entity_id
                WHERE p.id=? AND e.campaign_id=?""", (proposal_id, self.campaign_id)).fetchone()
            if proposal is None:
                raise KeyError(proposal_id)
            if proposal['status'] != 'pending':
                raise ValueError('Proposal was already reviewed')
            entity = conn.execute('SELECT status FROM campaign_entities WHERE entity_id=?',
                                  (proposal['entity_id'],)).fetchone()
            if entity['status'] == 'archived':
                raise ValueError('Archived entity cannot receive accepted facts')
            current = conn.execute("""SELECT content,status FROM entity_knowledge
                WHERE entity_id=? AND audience=? AND field_key=?""",
                (proposal['entity_id'], proposal['audience'], proposal['field_key'])).fetchone()
            current_content = current['content'] if current else None
            current_status = current['status'] if current else None
            if decision == 'accept' and (current_content != proposal['baseline_content'] or
                                         current_status != proposal['baseline_status']):
                raise CanonConflict('Canon changed since submission; review the current fact again')
            if decision == 'accept':
                conn.execute("""INSERT INTO entity_knowledge(entity_id,audience,field_key,content,status)
                    VALUES(?,?,?,?,'draft') ON CONFLICT(entity_id,audience,field_key)
                    DO UPDATE SET content=excluded.content,status='draft'""",
                    (proposal['entity_id'], proposal['audience'], proposal['field_key'], proposal['content']))
                conn.execute("""INSERT INTO entity_sources(entity_id,source_type,source_ref,citation)
                    VALUES(?,?,?,?) ON CONFLICT(entity_id,source_type,source_ref)
                    DO UPDATE SET citation=excluded.citation""",
                    (proposal['entity_id'], proposal['source_type'], proposal['source_ref'], proposal['citation']))
            conn.execute("""UPDATE canon_proposals SET status=?,reviewed_by=?,review_note=?,
                reviewed_at=CURRENT_TIMESTAMP WHERE id=?""",
                ('accepted' if decision == 'accept' else 'rejected', reviewer, note.strip(), proposal_id))
            conn.execute("""INSERT INTO entity_audit(entity_id,action,actor,detail)
                VALUES(?,?,?,?)""", (proposal['entity_id'], f'canon_{decision}', reviewer,
                                       f'#{proposal_id} {proposal["audience"]}:{proposal["field_key"]} {note.strip()}'))
