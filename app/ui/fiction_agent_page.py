"""GM workspace for connected fiction proposals."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QComboBox,
    QLineEdit, QTextEdit, QPushButton, QMessageBox, QGroupBox,
)

from ..services.fiction_agent import FictionAgent, SECTIONS


class FictionAgentPage(QWidget):
    def __init__(self, db_path: Path, open_review: Callable[[], None]):
        super().__init__()
        self.agent = FictionAgent(db_path)
        self.open_review = open_review
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('<h2>Fiction Agent (GM)</h2>'))
        intro = QLabel('Develop canon, lore, NPC backgrounds, and mission history or details '
                       'from approved campaign facts. Every submission goes to GM review as a '
                       'proposal; it does not change approved canon or player exports.')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form_group = QGroupBox('New fiction proposal')
        form = QFormLayout(form_group)
        self.section = QComboBox()
        self.section.addItems(SECTIONS)
        self.section.currentIndexChanged.connect(self.refresh_targets)
        self.target = QComboBox()
        self.target.currentIndexChanged.connect(self.refresh_current)
        self.audience = QComboBox()
        self.audience.addItems(['gm', 'player', 'internal'])
        self.audience.currentIndexChanged.connect(self.refresh_sources)
        self.audience.currentIndexChanged.connect(self.refresh_current)
        self.key = QLineEdit()
        self.key.setPlaceholderText('Example: founding_purpose')
        self.key.textChanged.connect(self.refresh_current)
        self.source = QComboBox()
        self.source.currentIndexChanged.connect(self.refresh_source_context)
        self.source_context = QTextEdit()
        self.source_context.setReadOnly(True)
        self.source_context.setMaximumHeight(85)
        self.current = QTextEdit()
        self.current.setReadOnly(True)
        self.current.setMaximumHeight(85)
        self.draft = QTextEdit()
        self.draft.setPlaceholderText('Write or paste the proposed fiction here.')
        self.draft.setMinimumHeight(115)
        for label, widget in (
            ('Area', self.section), ('Target record', self.target),
            ('Audience', self.audience), ('Fact key', self.key),
            ('Approved continuity source', self.source),
            ('Source fact', self.source_context), ('Current fact', self.current),
            ('Proposed fiction', self.draft),
        ):
            form.addRow(label, widget)
        self.queue_button = QPushButton('Send Proposal to GM Review')
        self.queue_button.clicked.connect(self.submit)
        form.addRow(self.queue_button)
        layout.addWidget(form_group)
        actions = QHBoxLayout()
        self.pending = QLabel()
        actions.addWidget(self.pending, 1)
        refresh = QPushButton('Refresh')
        refresh.clicked.connect(self.refresh)
        actions.addWidget(refresh)
        review = QPushButton('Open Canon Review')
        review.clicked.connect(open_review)
        actions.addWidget(review)
        layout.addLayout(actions)
        layout.addStretch()
        self.refresh()

    def refresh(self):
        self.refresh_targets()
        self.refresh_sources()
        self.pending.setText(f'{len(self.agent.pending())} fiction proposals awaiting GM review.')

    def refresh_targets(self):
        previous = self.target.currentData()
        self.target.blockSignals(True)
        self.target.clear()
        section = self.section.currentText()
        for row in self.agent.targets(section):
            self.target.addItem(f"{row['name']} [{row['entity_id']}]", row['entity_id'])
        index = self.target.findData(previous)
        self.target.setCurrentIndex(index if index >= 0 else 0)
        self.target.blockSignals(False)
        fixed = SECTIONS[section][1]
        self.key.setText(fixed or '')
        self.key.setReadOnly(bool(fixed))
        self.refresh_current()

    def refresh_sources(self):
        previous = self.source.currentData()
        self.source.blockSignals(True)
        self.source.clear()
        for row in self.agent.approved_sources(self.audience.currentText()):
            label = f"{row['name']} — {row['audience']}:{row['field_key']}"
            self.source.addItem(label, (row['entity_id'], row['audience'], row['field_key']))
        index = self.source.findData(previous)
        self.source.setCurrentIndex(index if index >= 0 else 0)
        self.source.blockSignals(False)
        self.refresh_source_context()
        self.queue_button.setEnabled(self.source.count() > 0 and self.target.count() > 0)

    def refresh_source_context(self):
        selected = self.source.currentData()
        if selected is None:
            self.source_context.setPlainText('Approve a campaign fact before using it as a continuity source.')
            return
        row = next((item for item in self.agent.approved_sources(self.audience.currentText())
                    if (item['entity_id'], item['audience'], item['field_key']) == selected), None)
        self.source_context.setPlainText(row['content'] if row else '')

    def refresh_current(self):
        entity_id = self.target.currentData()
        key = self.key.text().strip()
        fact = self.agent.current_fact(entity_id, self.audience.currentText(), key) if entity_id and key else None
        self.current.setPlainText(f"{fact['content']}\nStatus: {fact['status']}" if fact else '(No current fact)')

    def submit(self):
        source = self.source.currentData()
        if source is None:
            QMessageBox.information(self, 'Approved Source Required',
                                    'Choose an approved campaign fact first.')
            return
        try:
            proposal_id = self.agent.propose(
                self.section.currentText(), self.target.currentData(),
                self.audience.currentText(), self.draft.toPlainText(),
                source_entity_id=source[0], source_audience=source[1],
                source_field_key=source[2], field_key=self.key.text())
        except (ValueError, KeyError) as exc:
            QMessageBox.warning(self, 'Fiction Proposal', str(exc))
            return
        self.pending.setText(f'Proposal #{proposal_id} is awaiting GM review.')
        self.draft.clear()
