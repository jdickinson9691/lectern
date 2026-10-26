"""GM-only comparison and decision screen for sourced canon proposals."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QTextEdit, QPushButton, QGroupBox, QMessageBox, QLineEdit, QFormLayout)
from PySide6.QtCore import Qt

from ..services.campaign_canon import CampaignCanonAgent


class CanonReviewPage(QWidget):
    def __init__(self, db_path: Path):
        super().__init__()
        self.agent = CampaignCanonAgent(db_path)
        self.current: dict | None = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('<h2>Campaign Canon Review (GM)</h2>'))
        hint = QLabel('Compare each sourced proposal with the current fact. Accepting saves a draft; '
                      'player-facing facts still need approval before export.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        intake = QGroupBox('Submit a sourced proposal')
        form = QFormLayout(intake)
        self.entity_select = QComboBox()
        self.audience_select = QComboBox()
        self.audience_select.addItems(['gm', 'internal', 'player'])
        self.field_key = QLineEdit()
        self.field_key.setPlaceholderText('Example: description')
        self.fact_text = QTextEdit()
        self.fact_text.setMaximumHeight(75)
        self.source_type = QLineEdit('document')
        self.source_ref = QLineEdit()
        self.source_ref.setPlaceholderText('File, page, or other stable reference')
        self.citation = QLineEdit()
        for label, widget in [('Entity', self.entity_select), ('Audience', self.audience_select),
                              ('Fact key', self.field_key), ('Proposed text', self.fact_text),
                              ('Source type', self.source_type), ('Source reference', self.source_ref),
                              ('Citation', self.citation)]:
            form.addRow(label, widget)
        submit = QPushButton('Submit for Review')
        submit.clicked.connect(self.submit)
        form.addRow(submit)
        layout.addWidget(intake)
        selection = QHBoxLayout()
        self.proposals = QComboBox()
        self.proposals.currentIndexChanged.connect(self.load_selected)
        selection.addWidget(self.proposals, 1)
        refresh = QPushButton('Refresh')
        refresh.clicked.connect(self.refresh)
        selection.addWidget(refresh)
        layout.addLayout(selection)
        self.context = QLabel()
        self.context.setTextFormat(Qt.PlainText)
        self.context.setWordWrap(True)
        layout.addWidget(self.context)
        comparison = QHBoxLayout()
        for title, attribute in [('Current canon', 'current_text'), ('Proposed fact', 'proposed_text')]:
            group = QGroupBox(title)
            group_layout = QVBoxLayout(group)
            editor = QTextEdit()
            editor.setReadOnly(True)
            setattr(self, attribute, editor)
            group_layout.addWidget(editor)
            comparison.addWidget(group, 1)
        layout.addLayout(comparison, 1)
        self.source = QLabel()
        self.source.setTextFormat(Qt.PlainText)
        self.source.setWordWrap(True)
        layout.addWidget(self.source)
        self.note = QLineEdit()
        self.note.setPlaceholderText('Optional reason for the audit trail')
        layout.addWidget(self.note)
        actions = QHBoxLayout()
        self.accept_button = QPushButton('Accept as Draft')
        self.accept_button.clicked.connect(lambda: self.resolve('accept'))
        actions.addWidget(self.accept_button)
        self.reject_button = QPushButton('Reject Proposal')
        self.reject_button.clicked.connect(lambda: self.resolve('reject'))
        actions.addWidget(self.reject_button)
        actions.addStretch()
        layout.addLayout(actions)
        self.status = QLabel()
        layout.addWidget(self.status)
        self.refresh()

    def refresh(self):
        entity_id = self.entity_select.currentData()
        self.entity_select.clear()
        for entity in self.agent.entities():
            self.entity_select.addItem(f"{entity['name']} [{entity['entity_id']}]", entity['entity_id'])
        if entity_id:
            index = self.entity_select.findData(entity_id)
            if index >= 0:
                self.entity_select.setCurrentIndex(index)
        selected = self.proposals.currentData()
        self.proposals.blockSignals(True)
        self.proposals.clear()
        for row in self.agent.review_queue():
            self.proposals.addItem(
                f"#{row['id']} {row['entity_name']} [{row['entity_id']}] — {row['audience']}:{row['field_key']}",
                row['id'])
        index = self.proposals.findData(selected) if selected is not None else 0
        self.proposals.setCurrentIndex(index if index >= 0 else 0)
        self.proposals.blockSignals(False)
        self.load_selected()

    def submit(self):
        try:
            proposal_id = self.agent.submit_for_review(
                self.entity_select.currentData(), self.audience_select.currentText(),
                self.field_key.text(), self.fact_text.toPlainText(),
                source_type=self.source_type.text(), source_ref=self.source_ref.text(),
                citation=self.citation.text(), actor='gm')
            self.fact_text.clear()
            self.source_ref.clear()
            self.citation.clear()
            self.refresh()
            self.proposals.setCurrentIndex(self.proposals.findData(proposal_id))
            self.status.setText(f'Proposal #{proposal_id} is ready for GM review.')
        except Exception as exc:
            QMessageBox.warning(self, 'Canon Proposal', str(exc))

    def load_selected(self):
        proposal_id = self.proposals.currentData()
        self.current = next((row for row in self.agent.review_queue()
                             if row['id'] == proposal_id), None)
        row = self.current
        self.accept_button.setEnabled(row is not None)
        self.reject_button.setEnabled(row is not None)
        if row is None:
            self.context.setText('No proposals awaiting review.')
            self.current_text.clear()
            self.proposed_text.clear()
            self.source.clear()
            return
        changed = (row['current_content'] != row['baseline_content'] or
                   row['current_status'] != row['baseline_status'])
        self.context.setText(f"{row['entity_name']} • {row['audience']}:{row['field_key']} • "
                             f"Current status: {row['current_status'] or 'none'}" +
                             (' • Canon changed since submission' if changed else ''))
        self.current_text.setPlainText(row['current_content'] or '(No current fact)')
        self.proposed_text.setPlainText(row['content'])
        self.source.setText(f"Source: {row['source_type']} — {row['source_ref']}\n"
                            f"Citation: {row['citation'] or '(none)'}\n"
                            f"Proposed by: {row['proposed_by']}")

    def resolve(self, decision: str):
        if self.current is None:
            return
        proposal_id = self.current['id']
        try:
            self.agent.resolve(proposal_id, decision, reviewer='gm', note=self.note.text())
            self.note.clear()
            self.refresh()
            self.status.setText(f'Proposal #{proposal_id} {"accepted as draft" if decision == "accept" else "rejected"}.')
        except Exception as exc:
            QMessageBox.warning(self, 'Canon Review', str(exc))
            self.refresh()
