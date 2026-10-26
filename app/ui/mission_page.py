"""GM Mission editing, approval, and player-export preview."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QLineEdit, QTextEdit, QPushButton, QFormLayout, QMessageBox)

from ..services.story_mission_agent import StoryMissionAgent
from ..services.player_export import PlayerExportService
from ..services.fantasy_grounds_export import FantasyGroundsModuleExporter
from .story_page import ExportPreviewDialog, export_fantasy_grounds_with_preview


class MissionPage(QWidget):
    def __init__(self, db_path: Path):
        super().__init__()
        self.missions = StoryMissionAgent(db_path)
        self.player_export = PlayerExportService(db_path)
        self.fg_export = FantasyGroundsModuleExporter(db_path)
        self.current_id: str | None = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('<h2>Ashen Company Missions (GM)</h2>'))
        hint = QLabel('Review player briefing and private GM notes separately. Editing the title or '
                      'briefing returns the Mission to draft. Only approved player text is exported.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        selection = QHBoxLayout()
        self.mission_select = QComboBox()
        self.mission_select.currentIndexChanged.connect(self.load_selected)
        selection.addWidget(self.mission_select, 1)
        refresh = QPushButton('Refresh')
        refresh.clicked.connect(self.refresh)
        selection.addWidget(refresh)
        layout.addLayout(selection)
        form = QFormLayout()
        self.title = QLineEdit()
        self.player_briefing = QTextEdit()
        self.gm_notes = QTextEdit()
        form.addRow('Title', self.title)
        form.addRow('Player briefing', self.player_briefing)
        form.addRow('Private GM notes', self.gm_notes)
        layout.addLayout(form)
        actions = QHBoxLayout()
        for label, method in [('Save Draft', self.save), ('Approve Player Mission', self.approve),
                              ('Return to Draft', self.return_to_draft),
                              ('Preview Approved Export', self.preview),
                              ('Export Fantasy Grounds Module...', self.export_module)]:
            button = QPushButton(label)
            button.clicked.connect(method)
            actions.addWidget(button)
        layout.addLayout(actions)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.refresh()

    def refresh(self):
        selected = self.current_id
        self.mission_select.blockSignals(True)
        self.mission_select.clear()
        for mission in self.missions.list_missions():
            self.mission_select.addItem(
                f"{mission['name']} [{mission['entity_id']}] — {mission['status']}",
                mission['entity_id'])
        index = self.mission_select.findData(selected) if selected else 0
        self.mission_select.setCurrentIndex(index if index >= 0 else 0)
        self.mission_select.blockSignals(False)
        self.load_selected()

    def load_selected(self):
        self.current_id = self.mission_select.currentData()
        if not self.current_id:
            self.title.clear()
            self.player_briefing.clear()
            self.gm_notes.clear()
            self.status.setText('No Missions yet. Create one in Story & Mission Drafts.')
            return
        mission = self.missions.get_mission(self.current_id)
        self.title.setText(mission['name'])
        self.player_briefing.setPlainText(mission['player_briefing'] or '')
        self.gm_notes.setPlainText(mission['gm_notes'] or '')
        self.status.setText(f"{self.current_id}: {mission['status']}; "
                            f"player briefing: {mission['briefing_status'] or 'missing'}.")

    def _save(self):
        if not self.current_id:
            raise ValueError('Select a Mission')
        self.missions.save_mission(self.current_id, self.title.text(),
            self.player_briefing.toPlainText(), self.gm_notes.toPlainText())

    def save(self):
        try:
            self._save()
            self.refresh()
            self.status.setText(f'Saved {self.current_id}. Review and approve before player export.')
        except Exception as exc:
            QMessageBox.critical(self, 'Mission Save Failed', str(exc))

    def approve(self):
        try:
            self._save()
            self.missions.approve_mission(self.current_id)
            self.refresh()
            self.status.setText(f'Approved {self.current_id} for player export.')
        except Exception as exc:
            QMessageBox.critical(self, 'Mission Approval Failed', str(exc))

    def return_to_draft(self):
        if not self.current_id:
            return
        try:
            self.missions.return_mission_to_draft(self.current_id)
            self.refresh()
            self.status.setText(f'Returned {self.current_id} to draft.')
        except Exception as exc:
            QMessageBox.critical(self, 'Mission Update Failed', str(exc))

    def preview(self):
        ExportPreviewDialog(self.player_export.snapshot(), parent=self).exec()

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
