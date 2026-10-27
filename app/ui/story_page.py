"""Story drafting, approval, and reviewed Fantasy Grounds publication UI."""
from __future__ import annotations

from pathlib import Path

from ..services.campaign_workflow import format_dependencies

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QTextEdit, QFormLayout, QMessageBox, QFileDialog, QDialog,
    QDialogButtonBox,
)

from ..services.story_editor import StoryService
from ..services.player_export import PlayerExportService
from ..services.fantasy_grounds_export import FantasyGroundsModuleExporter


def format_player_preview(snapshot: dict) -> str:
    lines = []
    for entity in snapshot['entities']:
        lines.append(f"{entity['name']} [{entity['id']}] ({entity['kind']})")
        for key, content in sorted(entity['knowledge'].items()):
            lines.append(f'  {key}: {content}')
        for relation in snapshot['relationships']:
            if relation['source_id'] == entity['id']:
                lines.append(f"  {relation['relation']}: {relation['target_id']}")
        lines.append('')
    return '\n'.join(lines).strip() or 'No approved player-visible records.'


class ExportPreviewDialog(QDialog):
    def __init__(self, snapshot: dict, destination: Path | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Review Player Export')
        self.resize(720, 520)
        layout = QVBoxLayout(self)
        count = len(snapshot['entities'])
        layout.addWidget(QLabel(f'{count} approved player-visible record(s) will be included.'))
        if destination is not None:
            action = 'replace' if destination.exists() else 'create'
            path_label = QLabel(f'This will {action}: {destination}')
            path_label.setWordWrap(True)
            layout.addWidget(path_label)
        detail = QTextEdit()
        detail.setReadOnly(True)
        detail.setPlainText(format_player_preview(snapshot))
        layout.addWidget(detail)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
            if destination is not None else QDialogButtonBox.StandardButton.Close
        )
        if destination is not None:
            buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
                'Replace Module' if destination.exists() else 'Export Module')
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
        else:
            buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


def export_fantasy_grounds_with_preview(parent: QWidget, player_export: PlayerExportService,
                                        fg_export: FantasyGroundsModuleExporter) -> tuple[Path, dict] | None:
    snapshot = player_export.snapshot()
    if not snapshot['entities']:
        QMessageBox.information(parent, 'Nothing to Export',
                                'Approve a player-visible Story before exporting.')
        return None
    path, _ = QFileDialog.getSaveFileName(
        parent, 'Export Fantasy Grounds Module', 'ashen_company_players.mod',
        'Fantasy Grounds Modules (*.mod)',
        options=QFileDialog.Option.DontConfirmOverwrite,
    )
    if not path:
        return None
    destination = Path(path)
    if destination.suffix.lower() != '.mod':
        destination = destination.with_suffix('.mod')
    if ExportPreviewDialog(snapshot, destination, parent).exec() != QDialog.DialogCode.Accepted:
        return None
    exported = fg_export.export_mod(destination, expected_snapshot=snapshot)
    return destination, exported


class StoryPage(QWidget):
    def __init__(self, db_path: Path):
        super().__init__()
        self.stories = StoryService(db_path)
        self.player_export = PlayerExportService(db_path)
        self.fg_export = FantasyGroundsModuleExporter(db_path)
        self.current_id: str | None = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('<h2>Ashen Company Stories</h2>'))
        help_text = QLabel('Write the player version separately from GM notes. Publishing requires approval; '
                           'changes to the title or player text return the Story to draft.')
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        selection = QHBoxLayout()
        self.story_select = QComboBox()
        self.story_select.currentIndexChanged.connect(self.load_selected)
        selection.addWidget(self.story_select, 1)
        new_button = QPushButton('New Story')
        new_button.clicked.connect(self.new_story)
        selection.addWidget(new_button)
        layout.addLayout(selection)
        form = QFormLayout()
        self.title = QLineEdit()
        self.title.setPlaceholderText('Story title')
        form.addRow('Title', self.title)
        self.player_text = QTextEdit()
        self.player_text.setPlaceholderText('Text that approved players may read')
        form.addRow('Player text', self.player_text)
        self.gm_notes = QTextEdit()
        self.gm_notes.setPlaceholderText('Private GM notes; never included in player exports')
        form.addRow('GM notes', self.gm_notes)
        layout.addLayout(form)
        self.based_on = QLabel()
        self.based_on.setWordWrap(True)
        layout.addWidget(self.based_on)
        actions = QHBoxLayout()
        for label, callback in [
            ('Save Draft', self.save), ('Approve Player Story', self.approve),
            ('Return to Draft', self.return_to_draft),
            ('Preview Approved Export', self.preview_approved),
            ('Export Fantasy Grounds Module...', self.export_module),
        ]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            actions.addWidget(button)
        layout.addLayout(actions)
        self.status = QLabel('Ready.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.refresh()

    def refresh(self):
        selected = self.current_id
        self.story_select.blockSignals(True)
        self.story_select.clear()
        for row in self.stories.list_stories():
            label = f"{row['name']} [{row['entity_id']}] — {row['status']}"
            self.story_select.addItem(label, row['entity_id'])
        index = self.story_select.findData(selected) if selected else 0
        self.story_select.setCurrentIndex(index if index >= 0 else 0)
        self.story_select.blockSignals(False)
        self.load_selected()

    def load_selected(self):
        entity_id = self.story_select.currentData()
        self.current_id = entity_id
        if not entity_id:
            return
        story = self.stories.get_story(entity_id)
        self.title.setText(story['name'])
        self.player_text.setPlainText(story['player_text'])
        self.gm_notes.setPlainText(story['gm_notes'])
        self.status.setText(f"{entity_id}: {story['status']}; player text: {story['player_text_status']}.")
        self.based_on.setText(format_dependencies(self.stories.db_path, entity_id))

    def new_story(self):
        self.story_select.setCurrentIndex(-1)
        self.current_id = None
        self.title.clear()
        self.player_text.clear()
        self.gm_notes.clear()
        self.status.setText('New Story draft. Enter a title and player text, then save.')
        self.based_on.setText('Create a sourced Story in Story Drafts to retain canon links.')
        self.title.setFocus()

    def _save(self) -> str:
        title = self.title.text()
        player_text = self.player_text.toPlainText()
        gm_notes = self.gm_notes.toPlainText()
        if self.current_id:
            self.stories.save_draft(self.current_id, title, player_text, gm_notes)
            entity_id = self.current_id
        else:
            entity_id = self.stories.create_draft(title, player_text, gm_notes)
        self.current_id = entity_id
        self.refresh()
        return entity_id

    def save(self):
        try:
            entity_id = self._save()
            self.status.setText(f'Saved {entity_id}. Review and approve the player Story to publish it.')
        except Exception as exc:
            QMessageBox.critical(self, 'Story Save Failed', str(exc))

    def approve(self):
        try:
            entity_id = self._save()
            self.stories.approve(entity_id)
            self.refresh()
            self.status.setText(f'Approved {entity_id} for player export.')
        except Exception as exc:
            QMessageBox.critical(self, 'Story Approval Failed', str(exc))

    def return_to_draft(self):
        if not self.current_id:
            return
        try:
            self.stories.return_to_draft(self.current_id)
            self.refresh()
            self.status.setText(f'Returned {self.current_id} to draft.')
        except Exception as exc:
            QMessageBox.critical(self, 'Story Update Failed', str(exc))

    def preview_approved(self):
        snapshot = self.player_export.snapshot()
        ExportPreviewDialog(snapshot, parent=self).exec()

    def export_module(self):
        try:
            result = export_fantasy_grounds_with_preview(
                self, self.player_export, self.fg_export)
            if result is not None:
                destination, snapshot = result
                self.status.setText(f"Exported {len(snapshot['entities'])} approved records to {destination}")
                QMessageBox.information(self, 'Fantasy Grounds Export Complete',
                                        f"Exported {len(snapshot['entities'])} approved records.")
        except Exception as exc:
            QMessageBox.critical(self, 'Fantasy Grounds Export Failed', str(exc))
