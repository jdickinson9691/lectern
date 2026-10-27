"""Read-only progress and dependency views for the campaign authoring flow."""
from __future__ import annotations

from pathlib import Path

from app.database.campaign_identity import CAMPAIGN_ID
from app.database.schema import connect


STAGES = (
    ("Canon & Lore", None),
    ("Stories", "DOC"),
    ("Campaign Locations", "LOC"),
    ("Campaign Factions", "FAC"),
    ("Campaign NPCs", "NPC"),
    ("Missions", "MIS"),
)


def progress(db_path: Path, campaign_id: str = CAMPAIGN_ID) -> dict:
    with connect(db_path) as conn:
        campaign = conn.execute(
            "SELECT name FROM campaign_entities WHERE entity_id=? AND kind='CAM'",
            (campaign_id,),
        ).fetchone()
        if campaign is None:
            raise KeyError(campaign_id)
        counts = {row['kind']: {'total': row['total'], 'approved': row['approved']}
                  for row in conn.execute("""SELECT kind,COUNT(*) total,
                      SUM(status='approved') approved FROM campaign_entities
                      WHERE campaign_id=? AND status<>'archived' GROUP BY kind""",
                      (campaign_id,))}
        lore = conn.execute("""SELECT COUNT(*) total,
            COALESCE(SUM(status='approved'),0) approved FROM entity_knowledge
            WHERE entity_id=?""", (campaign_id,)).fetchone()
        pending = conn.execute("""SELECT COUNT(*) FROM canon_proposals p
            JOIN campaign_entities e ON e.entity_id=p.entity_id
            WHERE (e.entity_id=? OR e.campaign_id=?) AND p.status='pending'""",
            (campaign_id, campaign_id)).fetchone()[0]
        return {'name': campaign['name'], 'counts': counts,
                'lore': {'total': lore['total'], 'approved': lore['approved']},
                'pending_proposals': pending}


def format_dependencies(db_path: Path, entity_id: str) -> str:
    sources = source_dependencies(db_path, entity_id)
    if not sources:
        return 'Based on: no linked source. Create new content from approved sources when possible.'
    lines = ['Based on:']
    for source in sources:
        label = f"{source['name']} [{source['id']}]"
        if source['warning']:
            label += f" — REVIEW NEEDED: {source['warning']}"
        lines.append(label)
    return '\n'.join(lines)


def source_dependencies(db_path: Path, entity_id: str) -> list[dict]:
    """Return the recorded source links and conservative review warnings."""
    with connect(db_path) as conn:
        target = conn.execute("""SELECT campaign_id,updated_at FROM campaign_entities
            WHERE entity_id=?""", (entity_id,)).fetchone()
        if target is None:
            raise KeyError(entity_id)
        rows = conn.execute("""SELECT s.source_ref,s.citation,e.name,e.kind,e.status,
            e.campaign_id,e.updated_at FROM entity_sources s
            LEFT JOIN campaign_entities e ON e.entity_id=s.source_ref
            WHERE s.entity_id=? AND s.source_type='campaign_entity'
            ORDER BY s.id""", (entity_id,)).fetchall()
        result = []
        for row in rows:
            missing = (row['name'] is None or (row['source_ref'] != target['campaign_id'] and
                   row['campaign_id'] != target['campaign_id']))
            linked_audit = conn.execute("""SELECT MAX(id) FROM entity_audit
                WHERE entity_id=? AND action='source' AND detail=?""",
                (entity_id, row['source_ref'])).fetchone()[0]
            source_audit = conn.execute('SELECT MAX(id) FROM entity_audit WHERE entity_id=?',
                                        (row['source_ref'],)).fetchone()[0]
            changed = (not missing and (
                (linked_audit is not None and source_audit is not None and source_audit > linked_audit)
                or (linked_audit is None and row['updated_at'] > target['updated_at'])))
            warning = ('Missing or different-campaign source' if missing else
                       'Source is no longer approved' if row['status'] != 'approved' else
                       'Source changed after this record' if changed else '')
            result.append({'id': row['source_ref'], 'name': row['name'] or row['source_ref'],
                           'kind': row['kind'], 'status': row['status'],
                           'citation': row['citation'], 'warning': warning})
        return result
