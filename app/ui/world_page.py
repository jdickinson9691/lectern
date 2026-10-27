"""Shared GM editor for sourced NPC and Location records."""
from __future__ import annotations

from pathlib import Path

from ..services.campaign_workflow import format_dependencies

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QListWidget, QListWidgetItem, QTextEdit, QLineEdit, QPushButton, QFormLayout,
    QMessageBox, QAbstractItemView, QGroupBox)

from ..services.world_agents import CampaignWorldAgent, FactionAgent
from ..services.player_export import PlayerExportService
from ..services.fantasy_grounds_export import FantasyGroundsModuleExporter
from .story_page import ExportPreviewDialog, export_fantasy_grounds_with_preview


class WorldPage(QWidget):
    def __init__(self, db_path: Path, agent_type: type[CampaignWorldAgent]):
        super().__init__()
        self.agent = agent_type(db_path)
        self.player_export = PlayerExportService(db_path)
        self.fg_export = FantasyGroundsModuleExporter(db_path)
        self.current_id: str | None = None
        label = self.agent.LABEL
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f'<h2>Ashen Company {label} Records (GM)</h2>'))
        hint = QLabel('New records require approved player-facing sources. Public edits return an '
                      'approved record to draft; private GM notes stay outside player exports.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        selection = QHBoxLayout()
        self.record_select = QComboBox()
        self.record_select.currentIndexChanged.connect(self.load_selected)
        selection.addWidget(self.record_select, 1)
        refresh = QPushButton('Refresh')
        refresh.clicked.connect(self.refresh)
        selection.addWidget(refresh)
        layout.addLayout(selection)
        layout.addWidget(QLabel('Approved source records for a new draft'))
        self.sources = QListWidget()
        self.sources.setSelectionMode(QAbstractItemView.MultiSelection)
        self.sources.setMaximumHeight(90)
        self.sources.itemSelectionChanged.connect(self.show_context)
        layout.addWidget(self.sources)
        self.context = QTextEdit()
        self.context.setReadOnly(True)
        self.context.setMaximumHeight(90)
        layout.addWidget(self.context)
        form = QFormLayout()
        self.name = QLineEdit()
        self.player_text = QTextEdit()
        self.player_text.setMaximumHeight(105)
        self.gm_notes = QTextEdit()
        self.gm_notes.setMaximumHeight(85)
        form.addRow('Name', self.name)
        form.addRow('Player profile' if label == 'NPC' else 'Player description', self.player_text)
        form.addRow('Private GM notes', self.gm_notes)
        layout.addLayout(form)
        self.based_on = QLabel()
        self.based_on.setWordWrap(True)
        layout.addWidget(self.based_on)
        actions = QHBoxLayout()
        for text, method in [('Save Draft', self.save), ('Approve Player Text', self.approve),
                             ('Return to Draft', self.return_to_draft),
                             ('Preview Approved Export', self.preview),
                             ('Export Fantasy Grounds Module...', self.export_module)]:
            button = QPushButton(text)
            button.clicked.connect(method)
            actions.addWidget(button)
        layout.addLayout(actions)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        if isinstance(self.agent, FactionAgent):
            links = QGroupBox('Faction links to NPCs, Locations, and Missions')
            link_layout = QVBoxLayout(links)
            add_row = QHBoxLayout()
            self.faction_target = QComboBox()
            self.faction_visibility = QComboBox()
            self.faction_visibility.addItems(['gm', 'player'])
            add_row.addWidget(self.faction_target, 1)
            add_row.addWidget(self.faction_visibility)
            add = QPushButton('Add Link as Draft')
            add.clicked.connect(self.add_faction_link)
            add_row.addWidget(add)
            link_layout.addLayout(add_row)
            review_row = QHBoxLayout()
            self.faction_links = QComboBox()
            review_row.addWidget(self.faction_links, 1)
            approve_link = QPushButton('Approve Player Link')
            approve_link.clicked.connect(self.approve_faction_link)
            review_row.addWidget(approve_link)
            revoke_link = QPushButton('Return Link to Draft')
            revoke_link.clicked.connect(self.revoke_faction_link)
            review_row.addWidget(revoke_link)
            link_layout.addLayout(review_row)
            layout.addWidget(links)
        self.refresh()

    def selected_sources(self) -> list[str]:
        return [item.data(Qt.UserRole) for item in self.sources.selectedItems()]

    def refresh(self):
        selected_sources = set(self.selected_sources())
        self.sources.clear()
        for source in self.agent.available_sources():
            item = QListWidgetItem(f"{source['name']} [{source['entity_id']}] ({source['kind']})")
            item.setData(Qt.UserRole, source['entity_id'])
            self.sources.addItem(item)
            if source['entity_id'] in selected_sources:
                item.setSelected(True)
        selected_record = self.current_id
        self.record_select.blockSignals(True)
        self.record_select.clear()
        self.record_select.addItem(f'(New {self.agent.LABEL})', None)
        for row in self.agent.list_records():
            self.record_select.addItem(
                f"{row['name']} [{row['entity_id']}] — {row['status']}", row['entity_id'])
        index = self.record_select.findData(selected_record) if selected_record else 0
        self.record_select.setCurrentIndex(index if index >= 0 else 0)
        self.record_select.blockSignals(False)
        self.load_selected()
        self.show_context()
        if isinstance(self.agent, FactionAgent):
            self.refresh_faction_links()

    def load_selected(self):
        self.current_id = self.record_select.currentData()
        if self.current_id is None:
            self.name.clear()
            self.player_text.clear()
            self.gm_notes.clear()
            self.status.setText(f'New {self.agent.LABEL} draft. Select a source and enter player text.')
            self.based_on.clear()
            if isinstance(self.agent, FactionAgent):
                self.refresh_faction_links()
            return
        row = self.agent.get_record(self.current_id)
        self.name.setText(row['name'])
        self.player_text.setPlainText(row['player_text'] or '')
        self.gm_notes.setPlainText(row['gm_notes'] or '')
        self.status.setText(f"{self.current_id}: {row['status']}; "
                            f"player text: {row['player_text_status'] or 'missing'}.")
        self.based_on.setText(format_dependencies(self.agent.db_path, self.current_id))
        if isinstance(self.agent, FactionAgent):
            self.refresh_faction_links()

    def show_context(self):
        ids = self.selected_sources()
        if not ids:
            self.context.setPlainText('Select approved source records to see player-facing facts.')
            return
        context = self.agent.approved_context(ids)
        lines = []
        for source in context:
            lines.append(f"{source['name']} [{source['id']}]")
            lines.extend(f'  {key}: {value}' for key, value in source['facts'].items())
        self.context.setPlainText('\n'.join(lines))

    def _save(self) -> str:
        if self.current_id is None:
            entity_id = self.agent.draft(
                self.name.text(), self.player_text.toPlainText(), self.gm_notes.toPlainText(),
                source_entity_ids=self.selected_sources())
            self.current_id = entity_id
        else:
            entity_id = self.current_id
            self.agent.save(entity_id, self.name.text(), self.player_text.toPlainText(),
                            self.gm_notes.toPlainText())
        return entity_id

    def save(self):
        try:
            entity_id = self._save()
            self.refresh()
            self.status.setText(f'Saved {entity_id}. Review before approving player text.')
        except Exception as exc:
            QMessageBox.critical(self, f'{self.agent.LABEL} Save Failed', str(exc))

    def approve(self):
        try:
            entity_id = self._save()
            self.agent.approve(entity_id)
            self.refresh()
            self.status.setText(f'Approved {entity_id} for player export.')
        except Exception as exc:
            QMessageBox.critical(self, f'{self.agent.LABEL} Approval Failed', str(exc))

    def return_to_draft(self):
        if self.current_id is None:
            return
        try:
            self.agent.return_to_draft(self.current_id)
            self.refresh()
            self.status.setText(f'Returned {self.current_id} to draft.')
        except Exception as exc:
            QMessageBox.critical(self, f'{self.agent.LABEL} Update Failed', str(exc))

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

    def refresh_faction_links(self):
        self.faction_target.clear()
        for target in self.agent.available_targets():
            self.faction_target.addItem(
                f"{target['kind']}: {target['name']} [{target['entity_id']}]",
                target['entity_id'])
        self.faction_links.clear()
        if self.current_id is not None:
            for row in self.agent.relationships(self.current_id):
                self.faction_links.addItem(
                    f"{row['relation']}: {row['target_name']} [{row['target_id']}] "
                    f"— {row['visibility']}/{row['status']}", row['target_id'])

    def add_faction_link(self):
        if self.current_id is None or self.faction_target.currentData() is None:
            return
        try:
            relation = self.agent.link(self.current_id, self.faction_target.currentData(),
                                       visibility=self.faction_visibility.currentText())
            self.refresh_faction_links()
            self.status.setText(f'Added {relation} link as a draft.')
        except Exception as exc:
            QMessageBox.warning(self, 'Faction Link', str(exc))

    def approve_faction_link(self):
        if self.current_id is None or self.faction_links.currentData() is None:
            return
        try:
            target_id = self.faction_links.currentData()
            self.agent.approve_relationship(self.current_id, target_id)
            self.refresh_faction_links()
            self.status.setText(f'Approved player link to {target_id}.')
        except Exception as exc:
            QMessageBox.warning(self, 'Faction Link Approval', str(exc))

    def revoke_faction_link(self):
        if self.current_id is None or self.faction_links.currentData() is None:
            return
        try:
            target_id = self.faction_links.currentData()
            self.agent.return_relationship_to_draft(self.current_id, target_id)
            self.refresh_faction_links()
            self.status.setText(f'Returned link to {target_id} to draft.')
        except Exception as exc:
            QMessageBox.warning(self, 'Faction Link Update', str(exc))
