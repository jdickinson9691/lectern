"""Read-only 5E Fantasy Grounds player module from the approved projection."""
from __future__ import annotations

import hashlib
import os
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from pathlib import Path

from .player_export import PlayerExportService


MODULE_NAME = 'Lectern Ashen Company Players'
_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def _node_id(entity_id: str) -> str:
    # Numeric FG record names stay stable when other records are added.
    number = int.from_bytes(hashlib.sha256(entity_id.encode('utf-8')).digest()[:8], 'big')
    return f'id-{number:020d}'


def _xml_bytes(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding='utf-8', xml_declaration=True, short_empty_elements=True)


def _string(parent: ET.Element, tag: str, value: str) -> ET.Element:
    child = ET.SubElement(parent, tag, {'type': 'string'})
    child.text = value
    return child


class FantasyGroundsModuleExporter:
    """Build a client module without ever reading raw GM or legacy tables."""

    def __init__(self, db_path: Path):
        self.player_export = PlayerExportService(db_path)

    def export_mod(self, destination: Path, *, expected_snapshot: dict | None = None) -> dict:
        destination = Path(destination)
        if destination.suffix.lower() != '.mod':
            raise ValueError('Fantasy Grounds output must end in .mod')
        snapshot = self.player_export.snapshot()
        if expected_snapshot is not None and snapshot != expected_snapshot:
            raise ValueError('Approved player content changed; preview the export again')
        if not snapshot['entities']:
            raise ValueError('No approved, player-visible records to export')
        definition, client = self._build_xml(snapshot)
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f'.{destination.name}.', suffix='.tmp', dir=destination.parent)
        os.close(descriptor)
        try:
            with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                for name, payload in [('definition.xml', definition), ('client.xml', client)]:
                    entry = zipfile.ZipInfo(name, _ZIP_TIME)
                    entry.compress_type = zipfile.ZIP_DEFLATED
                    archive.writestr(entry, payload)
            with zipfile.ZipFile(temporary) as archive:
                if archive.testzip() is not None:
                    raise ValueError('Fantasy Grounds module failed archive validation')
            os.replace(temporary, destination)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return snapshot

    @staticmethod
    def _build_xml(snapshot: dict) -> tuple[bytes, bytes]:
        if snapshot.get('format') != 'lectern-player-campaign-v1':
            raise ValueError('Unsupported player export format')
        definition = ET.Element('root', {'version': '4.8'})
        for tag, value in [('name', MODULE_NAME), ('displayname', MODULE_NAME),
                           ('category', 'Campaign'), ('author', 'Lectern'), ('ruleset', '5E')]:
            ET.SubElement(definition, tag).text = value

        client = ET.Element('root', {'version': '5.1'})
        # CoreRPG maps Story records to reference.encounters for read-only modules.
        reference = ET.SubElement(client, 'reference')
        story = ET.SubElement(reference, 'encounters')
        category = ET.SubElement(story, 'category', {'name': 'Ashen Company'})
        entities = sorted(snapshot['entities'], key=lambda item: item['id'])
        by_id = {entity['id']: entity for entity in entities}
        if len(by_id) != len(entities):
            raise ValueError('Duplicate canonical entity ID in player snapshot')
        ids = {_node_id(entity_id) for entity_id in by_id}
        if len(ids) != len(by_id):
            raise ValueError('Fantasy Grounds record ID collision')
        relations = defaultdict(list)
        for relation in snapshot['relationships']:
            if relation['source_id'] in by_id and relation['target_id'] in by_id:
                relations[relation['source_id']].append(relation)
        for entity in entities:
            record = ET.SubElement(category, _node_id(entity['id']))
            _string(record, 'name', entity['name'])
            _string(record, 'lecternid', entity['id'])
            body = ET.SubElement(record, 'text', {'type': 'formattedtext'})
            for key, content in sorted(entity['knowledge'].items()):
                for line in content.splitlines() or ['']:
                    paragraph = ET.SubElement(body, 'p')
                    if (entity['kind'], key) in {('DOC', 'story'), ('NPC', 'profile'), ('LOC', 'description'), ('FAC', 'overview'), ('MIS', 'briefing')}:
                        paragraph.text = line
                    else:
                        ET.SubElement(paragraph, 'b').text = f'{key}: '
                        ET.SubElement(paragraph, 'i').text = line
            for relation in sorted(relations[entity['id']], key=lambda row: (row['relation'], row['target_id'])):
                paragraph = ET.SubElement(body, 'p')
                ET.SubElement(paragraph, 'b').text = f"{relation['relation']}: "
                target = by_id[relation['target_id']]
                ET.SubElement(paragraph, 'i').text = target['name']

        library = ET.SubElement(client, 'library')
        book = ET.SubElement(library, 'lecternashencompany', {'static': 'true'})
        _string(book, 'name', MODULE_NAME)
        _string(book, 'categoryname', 'Campaign')
        entries = ET.SubElement(book, 'entries')
        story_entry = ET.SubElement(entries, 'story')
        link = ET.SubElement(story_entry, 'librarylink', {'type': 'windowreference'})
        ET.SubElement(link, 'class').text = 'reference_list'
        ET.SubElement(link, 'recordname').text = '..'
        _string(story_entry, 'name', 'Story')
        _string(story_entry, 'recordtype', 'story')
        return _xml_bytes(definition), _xml_bytes(client)
