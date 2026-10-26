"""Approved, player-visible campaign projection. Never reads legacy payloads."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from ..database.campaign_identity import CAMPAIGN_ID
from ..database.schema import connect


class PlayerExportService:
    def __init__(self, db_path: Path, campaign_id: str = CAMPAIGN_ID):
        self.db_path = Path(db_path)
        self.campaign_id = campaign_id

    def snapshot(self) -> dict:
        with connect(self.db_path) as conn:
            conn.execute('BEGIN')
            rows = conn.execute("""SELECT entity_id,kind,name FROM campaign_entities
                WHERE (entity_id=? OR campaign_id=?)
                  AND visibility='player' AND status='approved'
                ORDER BY entity_id""", (self.campaign_id, self.campaign_id)).fetchall()
            entities = {
                row['entity_id']: {
                    'id': row['entity_id'], 'kind': row['kind'],
                    'name': row['name'], 'knowledge': {},
                }
                for row in rows
            }
            for row in conn.execute("""SELECT entity_id,field_key,content FROM entity_knowledge
                WHERE audience='player' AND status='approved'
                ORDER BY entity_id,field_key"""):
                if row['entity_id'] in entities:
                    entities[row['entity_id']]['knowledge'][row['field_key']] = row['content']
            relationships = [
                {'source_id': row['source_id'], 'target_id': row['target_id'], 'relation': row['relation']}
                for row in conn.execute("""SELECT source_id,target_id,relation FROM entity_relationships
                    WHERE visibility='player' AND status='approved'
                    ORDER BY source_id,target_id,relation""")
                if row['source_id'] in entities and row['target_id'] in entities
            ]
        return {
            'format': 'lectern-player-campaign-v1',
            'entities': list(entities.values()),
            'relationships': relationships,
        }

    def export_json(self, destination: Path) -> dict:
        """Write one consistent snapshot atomically and return it for the UI."""
        destination = Path(destination)
        snapshot = self.snapshot()
        destination.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(prefix=f'.{destination.name}.', suffix='.tmp', dir=destination.parent)
        try:
            with os.fdopen(handle, 'w', encoding='utf-8', newline='\n') as output:
                json.dump(snapshot, output, ensure_ascii=False, indent=2)
                output.write('\n')
            os.replace(temporary, destination)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return snapshot
