"""GM Mission editing, approval, and player-export preview."""
from __future__ import annotations

from pathlib import Path

from ..services.campaign_workflow import format_dependencies

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QLineEdit, QTextEdit, QPushButton, QFormLayout, QMessageBox,
    QSpinBox, QListWidget, QListWidgetItem, QTabWidget)

from ..services.story_mission_agent import StoryMissionAgent
from ..services.mission_planning import DIFFICULTIES
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
        hint = QLabel('Set a combined character-level limit and GM difficulty, then plan monsters, '
                      'lore, loot, and future hooks. Players choose their own party within the level '
                      'limit. Roster or public limit changes return an approved Mission to draft.')
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
        tabs = QTabWidget()
        briefing_tab = QWidget()
        form = QFormLayout(briefing_tab)
        self.title = QLineEdit()
        self.player_briefing = QTextEdit()
        self.gm_notes = QTextEdit()
        form.addRow('Title', self.title)
        form.addRow('Player briefing', self.player_briefing)
        form.addRow('Private GM notes', self.gm_notes)
        tabs.addTab(briefing_tab, 'Briefing & Approval')
        plan_tab = QWidget()
        plan_layout = QVBoxLayout(plan_tab)
        plan_form = QFormLayout()
        self.level_budget = QSpinBox()
        self.level_budget.setRange(0, 100)
        self.level_budget.setSpecialValueText('Not set')
        self.level_budget.valueChanged.connect(self.update_selected_levels)
        self.difficulty = QComboBox()
        self.difficulty.addItem('Choose difficulty', None)
        for value in DIFFICULTIES:
            self.difficulty.addItem(value.title(), value)
        self.lore = QTextEdit()
        self.lore.setPlaceholderText('GM background, stakes, and continuity with campaign lore')
        self.lore.setMinimumHeight(90)
        self.approved_fiction = QTextEdit()
        self.approved_fiction.setReadOnly(True)
        self.approved_fiction.setMaximumHeight(85)
        self.loot = QTextEdit()
        self.loot.setPlaceholderText('List treasure and rewards, or enter None')
        self.loot.setMinimumHeight(70)
        plan_form.addRow('Max combined character levels', self.level_budget)
        plan_form.addRow('GM mission difficulty', self.difficulty)
        plan_form.addRow('Mission lore (GM)', self.lore)
        plan_form.addRow('Approved fiction context', self.approved_fiction)
        plan_form.addRow('Loot (GM)', self.loot)
        plan_layout.addLayout(plan_form)
        plan_layout.addWidget(QLabel('Chosen characters (sum of levels must stay within the cap)'))
        self.participants = QListWidget()
        self.participants.setMinimumHeight(70)
        self.participants.itemChanged.connect(self.update_selected_levels)
        plan_layout.addWidget(self.participants)
        self.selected_levels = QLabel()
        plan_layout.addWidget(self.selected_levels)
        roster_controls = QHBoxLayout()
        self.monster_choice = QComboBox()
        self.monster_choice.setEditable(True)
        self.monster_choice.setInsertPolicy(QComboBox.NoInsert)
        self.monster_quantity = QSpinBox()
        self.monster_quantity.setRange(1, 99)
        add_monster = QPushButton('Add Monster')
        add_monster.clicked.connect(self.add_monster)
        remove_monster = QPushButton('Remove Selected')
        remove_monster.clicked.connect(self.remove_monster)
        for widget in (QLabel('Monster'), self.monster_choice, QLabel('Count'),
                       self.monster_quantity, add_monster, remove_monster):
            roster_controls.addWidget(widget)
        plan_layout.addWidget(QLabel('Monsters in this mission (catalog CR shown; empty means none planned)'))
        plan_layout.addLayout(roster_controls)
        self.monster_roster = QListWidget()
        self.monster_roster.setMinimumHeight(70)
        plan_layout.addWidget(self.monster_roster)
        hook_controls = QHBoxLayout()
        self.future_choice = QComboBox()
        self.hook_text = QLineEdit()
        self.hook_text.setPlaceholderText('Lore clue or consequence to carry forward')
        add_hook = QPushButton('Add Hook')
        add_hook.clicked.connect(self.add_hook)
        remove_hook = QPushButton('Remove Selected')
        remove_hook.clicked.connect(self.remove_hook)
        for widget in (self.future_choice, self.hook_text, add_hook, remove_hook):
            hook_controls.addWidget(widget)
        plan_layout.addWidget(QLabel('Future lore hooks (GM; link a future mission when known)'))
        plan_layout.addLayout(hook_controls)
        self.hooks = QListWidget()
        self.hooks.setMinimumHeight(70)
        plan_layout.addWidget(self.hooks)
        self.plan_status = QLabel('Difficulty is a GM assessment of the whole mission; '
                                  'the level sum and monster CRs do not calculate 5E encounter balance.')
        self.plan_status.setWordWrap(True)
        plan_layout.addWidget(self.plan_status)
        tabs.addTab(plan_tab, 'Mission Plan (GM)')
        layout.addWidget(tabs, 1)
        self.based_on = QLabel()
        self.based_on.setWordWrap(True)
        layout.addWidget(self.based_on)
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
        monster_id = self.monster_choice.currentData()
        self.monster_choice.clear()
        for monster in self.missions.planning.monster_catalog():
            cr = monster['challenge_rating'] or '?'
            self.monster_choice.addItem(f"{monster['name']} (CR {cr})", monster['id'])
        if monster_id is not None:
            index = self.monster_choice.findData(monster_id)
            if index >= 0:
                self.monster_choice.setCurrentIndex(index)
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
            self.lore.clear()
            self.approved_fiction.clear()
            self.loot.clear()
            self.monster_roster.clear()
            self.hooks.clear()
            self.participants.clear()
            self.selected_levels.clear()
            self.level_budget.setValue(0)
            self.difficulty.setCurrentIndex(0)
            self.status.setText('No Missions yet. Create one in Mission Drafts.')
            self.based_on.clear()
            return
        mission = self.missions.get_mission(self.current_id)
        self.title.setText(mission['name'])
        self.player_briefing.setPlainText(mission['player_briefing'] or '')
        self.gm_notes.setPlainText(mission['gm_notes'] or '')
        plan = self.missions.planning.get(self.current_id)
        self.level_budget.setValue(plan['max_total_levels'] or 0)
        difficulty_index = self.difficulty.findData(plan['difficulty'])
        self.difficulty.setCurrentIndex(max(0, difficulty_index))
        self.lore.setPlainText(plan['lore'])
        self.approved_fiction.setPlainText('\n\n'.join(
            f"{fact['audience']} {fact['field_key']}: {fact['content']}"
            for fact in plan['approved_fiction']) or '(No approved Fiction Agent facts yet)')
        self.loot.setPlainText(plan['loot'])
        self.monster_roster.clear()
        for monster in plan['monsters']:
            self._append_monster(monster['monster_id'], monster['quantity'])
        self.future_choice.clear()
        self.future_choice.addItem('Unlinked future lore', None)
        for future in self.missions.planning.future_missions(self.current_id):
            self.future_choice.addItem(f"{future['name']} [{future['entity_id']}]",
                                       future['entity_id'])
        self.hooks.clear()
        for hook in plan['hooks']:
            self._append_hook(hook['future_mission_id'], hook['lore_hook'])
        selected_ids = {row['player_id'] for row in plan['participants']}
        self.participants.blockSignals(True)
        self.participants.clear()
        for player in self.missions.planning.available_players():
            item = QListWidgetItem(f"{player['name']} — level {player['level'] or 0}")
            item.setData(Qt.ItemDataRole.UserRole, (player['id'], player['level'] or 0))
            item.setCheckState(Qt.CheckState.Checked if player['id'] in selected_ids
                               else Qt.CheckState.Unchecked)
            self.participants.addItem(item)
        self.participants.blockSignals(False)
        self.update_selected_levels()
        self.plan_status.setText(
            f"{len(plan['monsters'])} monster types; catalog XP total "
            f"{plan['catalog_xp_total']} (catalog XP may be missing). "
            'Difficulty is a GM assessment; the roster and level sum alone do not calculate 5E balance.'
            + (' Selected characters now exceed the cap; revise the roster.'
               if plan['max_total_levels'] and
               plan['selected_level_total'] > plan['max_total_levels'] else ''))
        self.status.setText(f"{self.current_id}: {mission['status']}; "
                            f"player briefing: {mission['briefing_status'] or 'missing'}.")
        self.based_on.setText(format_dependencies(self.missions.db_path, self.current_id))

    def _save(self):
        if not self.current_id:
            raise ValueError('Select a Mission')
        if not self.title.text().strip():
            raise ValueError('Mission title is required')
        self.missions.planning.save(
            self.current_id,
            max_total_levels=self.level_budget.value() or None,
            difficulty=self.difficulty.currentData(),
            lore=self.lore.toPlainText(), loot=self.loot.toPlainText(),
            monsters=[self.monster_roster.item(i).data(Qt.ItemDataRole.UserRole)
                      for i in range(self.monster_roster.count())],
            hooks=[self.hooks.item(i).data(Qt.ItemDataRole.UserRole)
                   for i in range(self.hooks.count())],
            participants=[self.participants.item(i).data(Qt.ItemDataRole.UserRole)[0]
                          for i in range(self.participants.count())
                          if self.participants.item(i).checkState() == Qt.CheckState.Checked],
        )
        self.missions.save_mission(self.current_id, self.title.text(),
            self.player_briefing.toPlainText(), self.gm_notes.toPlainText())

    def _append_monster(self, monster_id: int, quantity: int):
        catalog = next((row for row in self.missions.planning.monster_catalog()
                        if row['id'] == monster_id), None)
        if catalog is None:
            raise ValueError(f'Monster {monster_id} is missing from the catalog')
        item = QListWidgetItem(f"{quantity} × {catalog['name']} — CR {catalog['challenge_rating'] or '?'}")
        item.setData(Qt.ItemDataRole.UserRole, (monster_id, quantity))
        self.monster_roster.addItem(item)

    def add_monster(self):
        monster_id = self.monster_choice.currentData()
        if monster_id is None:
            return
        for i in range(self.monster_roster.count()):
            if self.monster_roster.item(i).data(Qt.ItemDataRole.UserRole)[0] == monster_id:
                QMessageBox.information(self, 'Monster Already Listed',
                                        'Select the existing row to remove it before changing its count.')
                return
        self._append_monster(monster_id, self.monster_quantity.value())

    def remove_monster(self):
        row = self.monster_roster.currentRow()
        if row >= 0:
            self.monster_roster.takeItem(row)

    def _append_hook(self, future_id: str | None, hook_text: str):
        target = next((self.future_choice.itemText(i) for i in range(self.future_choice.count())
                       if self.future_choice.itemData(i) == future_id), 'Unlinked future lore')
        item = QListWidgetItem(f'{target}: {hook_text}')
        item.setData(Qt.ItemDataRole.UserRole, (future_id, hook_text))
        self.hooks.addItem(item)

    def add_hook(self):
        hook_text = self.hook_text.text().strip()
        if not hook_text:
            QMessageBox.information(self, 'Lore Hook Required', 'Write the future lore hook first.')
            return
        self._append_hook(self.future_choice.currentData(), hook_text)
        self.hook_text.clear()

    def remove_hook(self):
        row = self.hooks.currentRow()
        if row >= 0:
            self.hooks.takeItem(row)

    def update_selected_levels(self):
        total = sum(self.participants.item(i).data(Qt.ItemDataRole.UserRole)[1]
                    for i in range(self.participants.count())
                    if self.participants.item(i).checkState() == Qt.CheckState.Checked)
        cap = self.level_budget.value()
        self.selected_levels.setText(f'Selected levels: {total} / {cap or "cap not set"}')

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
