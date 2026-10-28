"""Coordinate sourced fiction proposals without changing approved canon."""
from __future__ import annotations

from pathlib import Path

from ..database.campaign_identity import CAMPAIGN_ID
from ..database.schema import connect
from .campaign_canon import CampaignCanonAgent


SECTIONS = {
    'Canon & Lore': (('CAM', 'FAC', 'LOC', 'DOC'), None),
    'NPC Background': (('NPC',), 'background'),
    'Mission Background': (('MIS',), 'background'),
    'Mission Details': (('MIS',), 'details'),
}


class FictionAgent:
    """Build a continuity-aware intake for the existing canon review queue."""

    def __init__(self, db_path: Path, campaign_id: str = CAMPAIGN_ID):
        self.db_path = Path(db_path)
        self.campaign_id = campaign_id
        self.canon = CampaignCanonAgent(db_path, campaign_id)

    def targets(self, section: str) -> list[dict]:
        kinds, _ = self._section(section)
        with connect(self.db_path) as conn:
            rows = conn.execute("""SELECT entity_id,kind,name,status FROM campaign_entities
                WHERE (entity_id=? OR campaign_id=?) AND status<>'archived'
                ORDER BY kind,name,entity_id""", (self.campaign_id, self.campaign_id))
            return [dict(row) for row in rows if row['kind'] in kinds]

    def approved_sources(self, audience: str) -> list[dict]:
        self._audience(audience)
        allowed = ('player',) if audience == 'player' else ('player', 'gm', 'internal')
        placeholders = ','.join('?' for _ in allowed)
        with connect(self.db_path) as conn:
            return [dict(row) for row in conn.execute(f"""SELECT e.entity_id,e.name,
                k.audience,k.field_key,k.content FROM entity_knowledge k
                JOIN campaign_entities e ON e.entity_id=k.entity_id
                WHERE (e.entity_id=? OR e.campaign_id=?) AND e.status='approved'
                AND k.status='approved' AND k.audience IN ({placeholders})
                ORDER BY e.name,k.audience,k.field_key""",
                (self.campaign_id, self.campaign_id, *allowed))]

    def current_fact(self, entity_id: str, audience: str, field_key: str) -> dict | None:
        with connect(self.db_path) as conn:
            row = conn.execute("""SELECT k.content,k.status FROM entity_knowledge k
                JOIN campaign_entities e ON e.entity_id=k.entity_id
                WHERE k.entity_id=? AND k.audience=? AND k.field_key=?
                AND (e.entity_id=? OR e.campaign_id=?)""",
                (entity_id, audience, field_key, self.campaign_id, self.campaign_id)).fetchone()
            return dict(row) if row else None

    def propose(self, section: str, entity_id: str, audience: str,
                content: str, *, source_entity_id: str, source_audience: str,
                source_field_key: str, field_key: str = '') -> int:
        kinds, fixed_key = self._section(section)
        self._audience(audience)
        key = fixed_key or field_key.strip()
        if not key or not content.strip():
            raise ValueError('Fact key and proposed text are required')
        with connect(self.db_path) as conn:
            target = conn.execute("""SELECT kind,status FROM campaign_entities
                WHERE entity_id=? AND (entity_id=? OR campaign_id=?)""",
                (entity_id, self.campaign_id, self.campaign_id)).fetchone()
            if target is None or target['kind'] not in kinds or target['status'] == 'archived':
                raise ValueError(f'{section} requires a matching active campaign record')
        anchor = next((row for row in self.approved_sources(audience)
                       if row['entity_id'] == source_entity_id
                       and row['audience'] == source_audience
                       and row['field_key'] == source_field_key), None)
        if anchor is None:
            raise ValueError('An approved source fact from this campaign is required')
        source_ref = f'{source_entity_id}:{source_audience}:{source_field_key}'
        with connect(self.db_path) as conn:
            prior = conn.execute("""SELECT id FROM canon_proposals WHERE entity_id=?
                AND audience=? AND field_key=? AND content=? AND status='pending'""",
                (entity_id, audience, key, content.strip())).fetchone()
            if prior:
                return prior['id']
        return self.canon.submit_for_review(
            entity_id, audience, key, content,
            source_type='campaign_fact', source_ref=source_ref,
            citation=f"Continuity anchor: {anchor['name']} ({source_ref}). New fiction requires GM review.",
            actor='fiction-agent')

    def pending(self) -> list[dict]:
        return self.canon.review_queue()

    @staticmethod
    def _section(section: str) -> tuple[tuple[str, ...], str | None]:
        if section not in SECTIONS:
            raise ValueError(f'Unknown fiction section: {section}')
        return SECTIONS[section]

    @staticmethod
    def _audience(audience: str) -> None:
        if audience not in {'player', 'gm', 'internal'}:
            raise ValueError('Invalid audience')
