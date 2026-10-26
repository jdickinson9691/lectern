import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from app.database.campaign_repository import CampaignRepository
from app.database.repositories import Repository
from app.database.schema import connect, initialize_database
from app.services.fantasy_grounds_export import FantasyGroundsModuleExporter, _node_id


class FantasyGroundsExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.db = Path(self.tmp.name) / 'lectern.db'
        initialize_database(self.db)
        self.campaign = CampaignRepository(self.db)
        self.exporter = FantasyGroundsModuleExporter(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_module_contains_only_approved_player_projection(self):
        Repository(self.db).upsert_player({'name': 'Mara', 'notes': 'LEGACY GM SECRET'})
        self.campaign.create_entity('NPC-COMP-0001', 'NPC', 'Visible Ally', visibility='player')
        self.campaign.create_entity('NPC-COMP-0002', 'NPC', 'Hidden Traitor')
        self.campaign.approve_entity('NPC-COMP-0001')
        self.campaign.set_knowledge('NPC-COMP-0001', 'player', 'bio', 'Known <ally> & friend')
        self.campaign.approve_player_knowledge('NPC-COMP-0001', 'bio')
        self.campaign.set_knowledge('NPC-COMP-0001', 'gm', 'secret', 'GM KNOWLEDGE SECRET')
        self.campaign.set_knowledge('NPC-COMP-0001', 'player', 'draft', 'DRAFT KNOWLEDGE SECRET')
        self.campaign.add_relationship('NPC-COMP-0001', 'NPC-COMP-0002', 'SECRET RELATION', visibility='player')
        with connect(self.db) as conn:
            conn.execute("UPDATE campaign_entities SET status='approved' WHERE entity_id='NPC-COMP-0002'")
            conn.execute("UPDATE entity_relationships SET status='approved' WHERE relation='SECRET RELATION'")
            conn.execute("INSERT INTO entity_sources(entity_id,source_type,source_ref,citation) VALUES('NPC-COMP-0001','document','private.docx','SOURCE SECRET')")
            conn.execute("INSERT INTO entity_audit(entity_id,action,actor,detail) VALUES('NPC-COMP-0001','note','gm','AUDIT SECRET')")
        path = Path(self.tmp.name) / 'players.mod'
        snapshot = self.exporter.export_mod(path)
        self.assertEqual([entity['id'] for entity in snapshot['entities']], ['NPC-COMP-0001'])
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(set(archive.namelist()), {'definition.xml', 'client.xml'})
            self.assertIsNone(archive.testzip())
            definition = ET.fromstring(archive.read('definition.xml'))
            client = ET.fromstring(archive.read('client.xml'))
            self.assertEqual(definition.findtext('ruleset'), '5E')
            self.assertEqual(client.findtext('library/lecternashencompany/entries/story/recordtype'), 'story')
            record = client.find(f"reference/encounters/category/{_node_id('NPC-COMP-0001')}")
            self.assertEqual(record.findtext('name'), 'Visible Ally')
            self.assertIn('Known <ally> & friend', ''.join(record.find('text').itertext()))
        raw = path.read_bytes()
        for secret in (b'LEGACY GM SECRET', b'GM KNOWLEDGE SECRET', b'DRAFT KNOWLEDGE SECRET',
                       b'SECRET RELATION', b'Hidden Traitor', b'SOURCE SECRET', b'AUDIT SECRET'):
            self.assertNotIn(secret, raw)
        for member in ('definition.xml', 'client.xml'):
            with zipfile.ZipFile(path) as archive:
                payload = archive.read(member)
            for secret in (b'LEGACY GM SECRET', b'GM KNOWLEDGE SECRET', b'DRAFT KNOWLEDGE SECRET',
                           b'SECRET RELATION', b'Hidden Traitor', b'SOURCE SECRET', b'AUDIT SECRET'):
                self.assertNotIn(secret, payload)

    def test_end_to_end_story_path_excludes_gm_text(self):
        story_id = 'DOC-COMP-0001'
        self.campaign.create_entity(story_id, 'DOC', 'After Redwater', visibility='player')
        self.campaign.set_knowledge(story_id, 'player', 'story',
                                    'The Company regroups in Greyhaven.')
        self.campaign.approve_player_knowledge(story_id, 'story')
        self.campaign.set_knowledge(story_id, 'gm', 'secret',
                                    'GM_ONLY_BURIED_CAUSE_9137')
        self.campaign.create_entity('DOC-COMP-0002', 'DOC',
                                    'GM_ONLY_HIDDEN_STORY_2846', visibility='gm')
        self.campaign.approve_entity(story_id)

        path = Path(self.tmp.name) / 'ashens_story.mod'
        snapshot = self.exporter.export_mod(path)
        self.assertEqual([entity['id'] for entity in snapshot['entities']], [story_id])

        with zipfile.ZipFile(path) as archive:
            self.assertEqual(set(archive.namelist()), {'definition.xml', 'client.xml'})
            self.assertIsNone(archive.testzip())
            payloads = {name: archive.read(name) for name in archive.namelist()}
        client = ET.fromstring(payloads['client.xml'])
        category = client.find('reference/encounters/category')
        self.assertIsNotNone(category)
        self.assertEqual(category.get('name'), 'Ashen Company')
        self.assertEqual([record.tag for record in category], [_node_id(story_id)])
        self.assertIsNone(client.find('story'))
        record = category[0]
        self.assertEqual(record.findtext('name'), 'After Redwater')
        self.assertEqual(record.findtext('lecternid'), story_id)
        self.assertEqual(record.find('text').findtext('p'),
                         'The Company regroups in Greyhaven.')
        visible_text = ''.join(record.find('text').itertext())
        self.assertNotIn('Lectern ID:', visible_text)
        self.assertNotIn('Type:', visible_text)
        self.assertNotIn('story:', visible_text)

        for payload in payloads.values():
            self.assertNotIn(b'GM_ONLY_BURIED_CAUSE_9137', payload)
            self.assertNotIn(b'GM_ONLY_HIDDEN_STORY_2846', payload)

    def test_relationships_and_stable_record_names(self):
        for entity_id, name in [('NPC-COMP-0001', 'Ally'), ('LOC-COMP-0001', 'Watch')]:
            self.campaign.create_entity(entity_id, entity_id.split('-')[0], name, visibility='player')
            self.campaign.approve_entity(entity_id)
        self.campaign.add_relationship('NPC-COMP-0001', 'LOC-COMP-0001', 'guards', visibility='player')
        self.campaign.approve_player_relationship('NPC-COMP-0001', 'LOC-COMP-0001', 'guards')
        first = Path(self.tmp.name) / 'first.mod'
        self.exporter.export_mod(first)
        with zipfile.ZipFile(first) as archive:
            client = ET.fromstring(archive.read('client.xml'))
        text = ''.join(client.find(f"reference/encounters/category/{_node_id('NPC-COMP-0001')}/text").itertext())
        self.assertIn('guards: Watch', text)
        self.assertNotIn('LOC-COMP-0001', text)
        self.campaign.create_entity('FAC-COMP-0001', 'FAC', 'Guild', visibility='player')
        self.campaign.approve_entity('FAC-COMP-0001')
        second = Path(self.tmp.name) / 'second.mod'
        self.exporter.export_mod(second)
        with zipfile.ZipFile(second) as archive:
            client = ET.fromstring(archive.read('client.xml'))
        self.assertIsNotNone(client.find(f"reference/encounters/category/{_node_id('NPC-COMP-0001')}"))
        third = Path(self.tmp.name) / 'third.mod'
        self.exporter.export_mod(third)
        self.assertEqual(second.read_bytes(), third.read_bytes())

    def test_empty_export_and_bad_suffix_do_not_write(self):
        path = Path(self.tmp.name) / 'empty.mod'
        with self.assertRaises(ValueError):
            self.exporter.export_mod(path)
        self.assertFalse(path.exists())
        with self.assertRaises(ValueError):
            self.exporter.export_mod(Path(self.tmp.name) / 'bad.zip')


if __name__ == '__main__':
    unittest.main()
