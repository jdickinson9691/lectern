"""Campaign-first authoring guide and GM canon library."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QTextEdit, QHeaderView, QMessageBox,
)

from app.database.campaign_identity import CAMPAIGN_ID
from app.database.campaign_repository import CampaignRepository
from app.services.campaign_canon import CampaignCanonAgent
from app.services.campaign_workflow import STAGES, progress


class CampaignWorkflowPage(QWidget):
    """A navigable sequence; editors remain available out of order."""

    def __init__(self, db_path: Path, navigate: Callable[[str], None],
                 campaign_id: str = CAMPAIGN_ID):
        super().__init__()
        self.db_path = Path(db_path)
        self.campaign_id = campaign_id
        self.navigate = navigate
        layout = QVBoxLayout(self)
        self.heading = QLabel()
        layout.addWidget(self.heading)
        intro = QLabel('Build the campaign in this order. You can return to any step when the world changes.')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.rows: list[tuple[str, QLabel]] = []
        for number, (label, _) in enumerate((('Campaigns', None), *STAGES), 1):
            row = QHBoxLayout()
            button = QPushButton(f'{number}. {label}')
            button.setMinimumWidth(225)
            button.clicked.connect(lambda checked=False, name=label: self.navigate(name))
            detail = QLabel()
            detail.setWordWrap(True)
            row.addWidget(button)
            row.addWidget(detail, 1)
            layout.addLayout(row)
            self.rows.append((label, detail))
        finish = QHBoxLayout()
        for label in ('Canon Review (GM)', 'Review & Publish'):
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, name=label: self.navigate(name))
            finish.addWidget(button)
        finish.addStretch()
        layout.addLayout(finish)
        layout.addStretch()
        self.refresh()

    def refresh(self):
        state = progress(self.db_path, self.campaign_id)
        self.heading.setText(f"<h2>{state['name']} — Campaign Plan</h2>")
        for label, detail in self.rows:
            if label == 'Campaigns':
                detail.setText('Select or create the campaign before editing its content.')
            elif label == 'Canon & Lore':
                lore = state['lore']
                detail.setText(f"{lore['approved']} approved of {lore['total']} lore facts; "
                               f"{state['pending_proposals']} proposals awaiting review.")
            else:
                kind = dict(STAGES)[label]
                count = state['counts'].get(kind, {'total': 0, 'approved': 0})
                detail.setText(f"{count['approved']} approved of {count['total']} records.")


class CanonLorePage(QWidget):
    """GM view of approved and draft canon, sources, and downstream use."""

    def __init__(self, db_path: Path, open_review: Callable[[], None],
                 campaign_id: str = CAMPAIGN_ID):
        super().__init__()
        self.db_path = Path(db_path)
        self.campaign_id = campaign_id
        self.agent = CampaignCanonAgent(db_path, campaign_id)
        self.repository = CampaignRepository(db_path)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('<h2>Canon & Lore (GM)</h2>'))
        note = QLabel('Approved facts are the campaign reference. Accepting a proposal creates a draft; '
                      'approve the fact here after review. Player publication has a separate approval step.')
        note.setWordWrap(True)
        layout.addWidget(note)
        choose = QHBoxLayout()
        self.entities = QComboBox()
        self.entities.currentIndexChanged.connect(self.load_selected)
        choose.addWidget(self.entities, 1)
        review = QPushButton('Propose or Review Canon…')
        review.clicked.connect(open_review)
        choose.addWidget(review)
        layout.addLayout(choose)
        self.facts = QTableWidget(0, 4)
        self.facts.setHorizontalHeaderLabels(['Audience', 'Fact', 'Status', 'Content'])
        self.facts.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.facts.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.facts.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.facts, 2)
        approve = QPushButton('Approve Selected Canon Fact')
        approve.clicked.connect(self.approve_selected)
        layout.addWidget(approve)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        layout.addWidget(self.detail, 1)
        self.refresh()

    def refresh(self):
        selected = self.entities.currentData()
        self.entities.blockSignals(True)
        self.entities.clear()
        for entity in self.agent.entities():
            self.entities.addItem(f"{entity['name']} [{entity['entity_id']}] ({entity['kind']})",
                                  entity['entity_id'])
        index = self.entities.findData(selected or self.campaign_id)
        self.entities.setCurrentIndex(index if index >= 0 else 0)
        self.entities.blockSignals(False)
        self.load_selected()

    def load_selected(self):
        entity_id = self.entities.currentData()
        self.facts.setRowCount(0)
        self.detail.clear()
        if not entity_id:
            return
        dossier = self.agent.dossier(entity_id)
        for row, fact in enumerate(dossier['facts']):
            self.facts.insertRow(row)
            for column, value in enumerate((fact['audience'], fact['field_key'],
                                            fact['status'], fact['content'])):
                self.facts.setItem(row, column, QTableWidgetItem(value))
        sources = [f"{s['source_type']}: {s['source_ref']} {s['citation']}".strip()
                   for s in dossier['sources']]
        links = [f"{r['relation']} → {r['target_id']} ({r['status']})"
                 for r in dossier['relationships']]
        history = [f"{a['occurred_at']} — {a['action']}: {a['detail']}"
                   for a in dossier['audit'][-8:]]
        self.detail.setPlainText('Sources:\n' + ('\n'.join(sources) or '(None)') +
                                 '\n\nRelationships:\n' + ('\n'.join(links) or '(None)') +
                                 '\n\nRecent changes:\n' + ('\n'.join(history) or '(None)'))

    def approve_selected(self):
        entity_id = self.entities.currentData()
        row = self.facts.currentRow()
        if not entity_id or row < 0:
            QMessageBox.information(self, 'Select a Fact', 'Select a draft fact to approve.')
            return
        audience = self.facts.item(row, 0).text()
        key = self.facts.item(row, 1).text()
        try:
            self.repository.approve_knowledge(entity_id, audience, key, actor='gm')
            self.refresh()
        except Exception as exc:
            QMessageBox.warning(self, 'Canon Approval Failed', str(exc))
