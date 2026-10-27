"""Player-safe Ashen publication controls, separate from full-data CSV export."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QVBoxLayout, QWidget,
)

from ..database.campaign_repository import CampaignRepository
from ..database.campaign_identity import CAMPAIGN_ID
from ..services.fantasy_grounds_export import FantasyGroundsModuleExporter
from ..services.player_export import PlayerExportService
from ..services.story_editor import StoryService
from .story_page import export_fantasy_grounds_with_preview


class AshenPlayerExportPage(QWidget):
    def __init__(self, db_path: Path):
        super().__init__()
        self.campaign_repo = CampaignRepository(db_path)
        self.story_service = StoryService(db_path)
        self.player_export = PlayerExportService(db_path)
        self.fg_export = FantasyGroundsModuleExporter(db_path)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('<h2>Ashen Company Player Export</h2>'))
        note = QLabel('Only approved, player-visible campaign records are published. Full CSV exports contain GM data.')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.entity = QComboBox()
        layout.addWidget(self.entity)
        row = QHBoxLayout()
        self.visibility = QComboBox()
        for name, value in [('GM only', 'gm'), ('Internal', 'internal'), ('Player visible', 'player')]:
            self.visibility.addItem(name, value)
        row.addWidget(self.visibility)
        for caption, action in [
            ('Set Visibility', self.set_visibility),
            ('Approve', self.approve),
            ('Return to Draft', self.revoke),
        ]:
            button = QPushButton(caption)
            button.clicked.connect(action)
            row.addWidget(button)
        layout.addLayout(row)
        row = QHBoxLayout()
        for caption, action in [
            ('Export Player JSON...', self.export_json),
            ('Export Fantasy Grounds Module...', self.export_mod),
        ]:
            button = QPushButton(caption)
            button.clicked.connect(action)
            row.addWidget(button)
        layout.addLayout(row)
        self.status = QLabel('Ready.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addStretch()
        self.refresh()

    def refresh(self):
        selected = self.entity.currentData()
        self.entity.clear()
        for row in self.campaign_repo.list_entities(CAMPAIGN_ID):
            self.entity.addItem(
                f"{row['entity_id']} — {row['name']} ({row['visibility']}, {row['status']})",
                row['entity_id'],
            )
            if row['entity_id'] == selected:
                self.entity.setCurrentIndex(self.entity.count() - 1)

    def _run(self, action, success):
        entity_id = self.entity.currentData()
        if not entity_id:
            return
        try:
            action(entity_id)
            self.refresh()
            self.status.setText(success.format(entity_id=entity_id))
        except Exception as exc:
            QMessageBox.critical(self, 'Ashen Publication Failed', str(exc))

    def set_visibility(self):
        self._run(lambda eid: self.campaign_repo.set_visibility(eid, self.visibility.currentData()),
                  'Updated visibility for {entity_id}.')

    def approve(self):
        def action(eid):
            if eid.startswith('DOC-'):
                self.story_service.approve(eid)
            else:
                self.campaign_repo.approve_entity(eid)
        self._run(action, 'Approved {entity_id}.')

    def revoke(self):
        def action(eid):
            if eid.startswith('DOC-'):
                self.story_service.return_to_draft(eid)
            else:
                self.campaign_repo.revoke_entity(eid)
        self._run(action, 'Returned {entity_id} to draft.')

    def export_json(self):
        name, _ = QFileDialog.getSaveFileName(self, 'Export Approved Player Data',
                                              'ashen_company_players.json', 'JSON Files (*.json)')
        if name:
            try:
                snapshot = self.player_export.export_json(Path(name))
                self.status.setText(f"Exported {len(snapshot['entities'])} player records.")
            except Exception as exc:
                QMessageBox.critical(self, 'Player Export Failed', str(exc))

    def export_mod(self):
        try:
            result = export_fantasy_grounds_with_preview(self, self.player_export, self.fg_export)
            if result is not None:
                _, snapshot = result
                self.status.setText(f"Exported {len(snapshot['entities'])} approved Story records.")
        except Exception as exc:
            QMessageBox.critical(self, 'Fantasy Grounds Export Failed', str(exc))
