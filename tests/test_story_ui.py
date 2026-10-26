import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtWidgets import QApplication, QDialog, QTextEdit
    from app.ui.story_page import StoryPage, ExportPreviewDialog, export_fantasy_grounds_with_preview
except ImportError:
    QApplication = None

from app.database.schema import initialize_database
from app.services.player_export import PlayerExportService


@unittest.skipIf(QApplication is None, 'PySide6 unavailable')
class StoryUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.db = Path(self.tmp.name) / 'lectern.db'
        initialize_database(self.db)
        self.page = StoryPage(self.db)

    def tearDown(self):
        self.page.close()
        self.tmp.cleanup()

    def test_story_page_approval_and_preview_hide_gm_notes(self):
        self.page.new_story()
        self.page.title.setText('After Redwater')
        self.page.player_text.setPlainText('The Company regroups in Greyhaven.')
        self.page.gm_notes.setPlainText('GM_ONLY_UI_NOTE_3994')
        with patch('app.ui.story_page.QMessageBox.critical', side_effect=AssertionError):
            self.page.approve()
        story = self.page.stories.get_story(self.page.current_id)
        self.assertEqual(story['status'], 'approved')
        snapshot = PlayerExportService(self.db).snapshot()
        dialog = ExportPreviewDialog(snapshot, parent=self.page)
        preview = dialog.findChild(QTextEdit).toPlainText()
        self.assertIn('After Redwater', preview)
        self.assertIn('The Company regroups in Greyhaven.', preview)
        self.assertNotIn('GM_ONLY_UI_NOTE_3994', preview)
        dialog.close()

    def test_export_cancel_does_not_replace_existing_module(self):
        self.page.new_story()
        self.page.title.setText('After Redwater')
        self.page.player_text.setPlainText('Player version.')
        with patch('app.ui.story_page.QMessageBox.critical', side_effect=AssertionError):
            self.page.approve()
        path = Path(self.tmp.name) / 'players.mod'
        path.write_bytes(b'previous module')
        with patch('app.ui.story_page.QFileDialog.getSaveFileName', return_value=(str(path), '')):
            with patch.object(ExportPreviewDialog, 'exec', return_value=QDialog.DialogCode.Rejected):
                result = export_fantasy_grounds_with_preview(
                    self.page, self.page.player_export, self.page.fg_export)
        self.assertIsNone(result)
        self.assertEqual(path.read_bytes(), b'previous module')
        with patch('app.ui.story_page.QFileDialog.getSaveFileName', return_value=(str(path), '')):
            with patch.object(ExportPreviewDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
                result = export_fantasy_grounds_with_preview(
                    self.page, self.page.player_export, self.page.fg_export)
        self.assertIsNotNone(result)
        self.assertNotEqual(path.read_bytes(), b'previous module')


if __name__ == '__main__':
    unittest.main()
