"""Sourced Story and Mission drafting surface."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QListWidget, QListWidgetItem, QTextEdit, QLineEdit, QPushButton, QFormLayout,
    QMessageBox, QGroupBox, QAbstractItemView)
from PySide6.QtCore import Qt

from ..services.story_mission_agent import StoryMissionAgent


class StoryMissionPage(QWidget):
    def __init__(self, db_path: Path):
        super().__init__()
        self.agent = StoryMissionAgent(db_path)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('<h2>Story & Mission Drafts</h2>'))
        hint = QLabel('Select approved player-facing canon as source material. Drafts and GM notes '
                      'stay private until the existing approval flow publishes player text.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.sources = QListWidget()
        self.sources.setSelectionMode(QAbstractItemView.MultiSelection)
        self.sources.setMaximumHeight(100)
        self.sources.itemSelectionChanged.connect(self.show_context)
        layout.addWidget(QLabel('Approved source records'))
        layout.addWidget(self.sources)
        self.context = QTextEdit()
        self.context.setReadOnly(True)
        self.context.setMaximumHeight(115)
        layout.addWidget(self.context)
        form = QFormLayout()
        self.kind = QComboBox()
        self.kind.addItems(['Story', 'Mission'])
        self.kind.currentTextChanged.connect(self.update_kind)
        self.title = QLineEdit()
        self.player_text = QTextEdit()
        self.player_text.setMaximumHeight(105)
        self.gm_notes = QTextEdit()
        self.gm_notes.setMaximumHeight(85)
        self.story_link = QComboBox()
        form.addRow('Draft type', self.kind)
        form.addRow('Title', self.title)
        form.addRow('Player text / briefing', self.player_text)
        form.addRow('Private GM notes', self.gm_notes)
        form.addRow('Related Story (Mission)', self.story_link)
        layout.addLayout(form)
        actions = QHBoxLayout()
        save = QPushButton('Create Draft')
        save.clicked.connect(self.create_draft)
        actions.addWidget(save)
        refresh = QPushButton('Refresh Sources')
        refresh.clicked.connect(self.refresh)
        actions.addWidget(refresh)
        actions.addStretch()
        layout.addLayout(actions)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.refresh()

    def refresh(self):
        selected = set(self.selected_sources())
        self.sources.clear()
        for source in self.agent.available_sources():
            item = QListWidgetItem(f"{source['name']} [{source['entity_id']}] ({source['kind']})")
            item.setData(Qt.UserRole, source['entity_id'])
            self.sources.addItem(item)
            if source['entity_id'] in selected:
                item.setSelected(True)
        old_story = self.story_link.currentData()
        self.story_link.clear()
        self.story_link.addItem('(None)', None)
        for story in self.agent.stories.list_stories():
            if story['status'] != 'archived':
                self.story_link.addItem(f"{story['name']} [{story['entity_id']}]", story['entity_id'])
        if old_story:
            index = self.story_link.findData(old_story)
            if index >= 0:
                self.story_link.setCurrentIndex(index)
        self.show_context()
        self.update_kind()

    def selected_sources(self) -> list[str]:
        return [item.data(Qt.UserRole) for item in self.sources.selectedItems()]

    def show_context(self):
        ids = self.selected_sources()
        if not ids:
            self.context.setPlainText('Select one or more approved records to see their player-facing facts.')
            return
        context = self.agent.approved_context(ids)
        lines = []
        for source in context:
            lines.append(f"{source['name']} [{source['id']}]")
            lines.extend(f"  {key}: {value}" for key, value in source['facts'].items())
        self.context.setPlainText('\n'.join(lines))

    def update_kind(self):
        self.story_link.setEnabled(self.kind.currentText() == 'Mission')

    def create_draft(self):
        try:
            kwargs = dict(source_entity_ids=self.selected_sources())
            if self.kind.currentText() == 'Story':
                entity_id = self.agent.draft_story(
                    self.title.text(), self.player_text.toPlainText(),
                    self.gm_notes.toPlainText(), **kwargs)
            else:
                entity_id = self.agent.draft_mission(
                    self.title.text(), self.player_text.toPlainText(),
                    self.gm_notes.toPlainText(), story_id=self.story_link.currentData(), **kwargs)
            self.title.clear()
            self.player_text.clear()
            self.gm_notes.clear()
            self.refresh()
            self.status.setText(f'Created {entity_id} as a draft. Review canon changes in Canon Review (GM).')
        except Exception as exc:
            QMessageBox.warning(self, 'Draft Not Created', str(exc))
