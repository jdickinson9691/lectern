import tempfile
import unittest
import zipfile
from pathlib import Path

from app.database.schema import connect, initialize_database
from app.services.story_editor import StoryService
from app.services.player_export import PlayerExportService
from app.services.fantasy_grounds_export import FantasyGroundsModuleExporter


class StoryEditorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.db = Path(self.tmp.name) / 'lectern.db'
        initialize_database(self.db)
        self.stories = StoryService(self.db)
        self.player_export = PlayerExportService(self.db)
        self.fg_export = FantasyGroundsModuleExporter(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_public_edits_require_reapproval_and_gm_notes_stay_private(self):
        story_id = self.stories.create_draft(
            'After Redwater', 'The Company regroups in Greyhaven.',
            'GM_ONLY_CAUSE_4815')
        self.assertEqual(story_id, 'DOC-COMP-0001')
        self.assertEqual(self.player_export.snapshot()['entities'], [])
        self.stories.approve(story_id)
        self.assertEqual(len(self.player_export.snapshot()['entities']), 1)

        self.stories.save_draft(story_id, 'After Redwater',
                                'The banner was lost at Redwater.', 'GM_ONLY_CAUSE_4815')
        self.assertEqual(self.stories.get_story(story_id)['status'], 'draft')
        self.assertEqual(self.player_export.snapshot()['entities'], [])
        self.stories.approve(story_id)
        self.stories.save_draft(story_id, 'After Redwater',
                                'The banner was lost at Redwater.', 'GM_ONLY_REVISED_9271')
        self.assertEqual(self.stories.get_story(story_id)['status'], 'approved')
        second_id = self.stories.create_draft('Second Story', 'Not approved yet.')
        self.assertEqual(second_id, 'DOC-COMP-0002')

        path = Path(self.tmp.name) / 'players.mod'
        self.fg_export.export_mod(path)
        with zipfile.ZipFile(path) as archive:
            client = archive.read('client.xml')
        self.assertIn(b'The banner was lost at Redwater.', client)
        self.assertNotIn(b'GM_ONLY_CAUSE_4815', client)
        self.assertNotIn(b'GM_ONLY_REVISED_9271', client)
        self.assertNotIn(b'Second Story', client)
        with connect(self.db) as conn:
            actions = [row[0] for row in conn.execute(
                "SELECT action FROM entity_audit WHERE entity_id=? ORDER BY id", (story_id,))]
            self.assertEqual(actions, ['create_story', 'approve_story',
                                       'story_public_draft', 'approve_story', 'story_gm_notes'])

    def test_stale_preview_does_not_replace_existing_module(self):
        story_id = self.stories.create_draft('First Title', 'First text.')
        self.stories.approve(story_id)
        preview = self.player_export.snapshot()
        path = Path(self.tmp.name) / 'players.mod'
        self.fg_export.export_mod(path, expected_snapshot=preview)
        original = path.read_bytes()

        self.stories.save_draft(story_id, 'Second Title', 'Second text.')
        self.stories.approve(story_id)
        with self.assertRaisesRegex(ValueError, 'preview the export again'):
            self.fg_export.export_mod(path, expected_snapshot=preview)
        self.assertEqual(path.read_bytes(), original)

    def test_empty_player_text_cannot_be_approved(self):
        story_id = self.stories.create_draft('Untold Story', '', 'GM only')
        with self.assertRaisesRegex(ValueError, 'Player text is required'):
            self.stories.approve(story_id)
        self.assertEqual(self.player_export.snapshot()['entities'], [])


if __name__ == '__main__':
    unittest.main()
