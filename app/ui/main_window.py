from __future__ import annotations
import json
import re
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QStackedWidget, QFileDialog, QTableWidget, QTableWidgetItem,
    QLineEdit, QFormLayout, QSpinBox, QMessageBox, QComboBox, QCompleter,
    QGroupBox, QTextEdit, QTextBrowser, QListWidgetItem, QGridLayout, QScrollArea, QSizePolicy, QTabWidget, QCheckBox, QInputDialog,
    QDialog, QDialogButtonBox, QAbstractItemView, QAbstractSpinBox, QToolButton,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QFrame
)
from PySide6.QtCore import Qt, QRect, QSize, QTimer, QUrl
from PySide6.QtGui import QPainter, QPixmap, QIcon, QImage, QColor, QBrush, QFont, QTextCursor, QDesktopServices
from ..database.repositories import Repository
from ..importers.spreadsheet_importer import SpreadsheetImporter
from ..importers.csv_transfer import CsvTransferService, CSV_TABLES
from ..importers.character_pdf import CharacterPdfImporter
from ..services.data_workflow import DataWorkflowService
from ..integrations.fantasy_grounds import FantasyGroundsSyncError, FantasyGroundsSyncService
from ..version import APP_EXPANDED_NAME, APP_NAME, VERSION
from ..paths import icon_path, watermark_path, help_path, user_data_dir


class WatermarkedPage(QWidget):
    """Wrap one application screen with a centered, scale-aware watermark."""

    def __init__(self, content: QWidget, image_path: Path, parent=None):
        super().__init__(parent)
        self._source = QPixmap(str(image_path)) if image_path.exists() else QPixmap()
        if not self._source.isNull():
            # The supplied logo has a black background. Use its luminance as the
            # alpha channel so black becomes transparent instead of dimming the
            # entire page, while the silver/white logo remains visible.
            alpha = self._source.toImage().convertToFormat(QImage.Format_Grayscale8)
            transparent_logo = QImage(self._source.size(), QImage.Format_ARGB32)
            transparent_logo.fill(Qt.white)
            transparent_logo.setAlphaChannel(alpha)
            self._source = QPixmap.fromImage(transparent_logo)
        self._watermark = QLabel(self)
        self._watermark.setAlignment(Qt.AlignCenter)
        self._watermark.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._watermark.setStyleSheet("background: transparent; border: none;")

        content.setObjectName("LecternPageContent")
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._watermark, 0, 0)
        layout.addWidget(content, 0, 0)
        self._content = content
        self._watermark.raise_()
        self._refresh_watermark()

    def _refresh_watermark(self) -> None:
        if self._source.isNull():
            self._watermark.clear()
            return
        max_w = max(1, int(self.width() * 0.58))
        max_h = max(1, int(self.height() * 0.58))
        scaled = self._source.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        faded = QPixmap(scaled.size())
        faded.fill(Qt.transparent)
        painter = QPainter(faded)
        painter.setOpacity(0.14)
        painter.drawPixmap(0, 0, scaled)
        painter.end()
        self._watermark.setPixmap(faded)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_watermark()


ABILITY_LABELS = [('str','Strength'), ('dex','Dexterity'), ('con','Constitution'), ('int','Intelligence'), ('wis','Wisdom'), ('cha','Charisma')]

def ability_modifier(score: int) -> int:
    return (int(score) - 10) // 2


def clamp_editor_width(widget, width: int = 520):
    """Keep editor controls readable on wide monitors while still allowing resize."""
    widget.setMaximumWidth(width)
    widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)


class AdaptivePageLayout(QVBoxLayout):
    """A page layout whose section gaps respond to content and window height.

    Qt already lets expanding widgets (tables, editors, and lists) consume the
    remaining room. This layout complements that behavior by tightening section
    gaps when the page is crowded and gently opening them when room is available.
    """

    def __init__(self, parent=None, minimum_spacing: int = 8, maximum_spacing: int = 18):
        super().__init__(parent)
        self.minimum_spacing = minimum_spacing
        self.maximum_spacing = maximum_spacing
        self.setContentsMargins(16, 12, 16, 16)
        self.setSpacing(minimum_spacing)

    def setGeometry(self, rect: QRect) -> None:
        sections = []
        for index in range(self.count()):
            item = self.itemAt(index)
            if item is None or item.isEmpty() or item.spacerItem() is not None:
                continue
            sections.append(item)

        gap_count = max(0, len(sections) - 1)
        if gap_count:
            margins = self.contentsMargins()
            available = max(0, rect.height() - margins.top() - margins.bottom())
            content_height = sum(item.sizeHint().height() for item in sections)
            spare_per_gap = max(0, available - content_height) / gap_count
            spacing = round(self.minimum_spacing + spare_per_gap * 0.16)
            spacing = max(self.minimum_spacing, min(self.maximum_spacing, spacing))
            if spacing != self.spacing():
                self.setSpacing(spacing)
        super().setGeometry(rect)


def adaptive_page_layout(page: QWidget) -> AdaptivePageLayout:
    """Create the shared content-aware vertical layout used by every screen."""
    return AdaptivePageLayout(page)

def apply_portrait_icon(item: QTableWidgetItem, portrait_path_value) -> None:
    portrait=Path(str(portrait_path_value or ''))
    if portrait.exists(): item.setIcon(QIcon(str(portrait)))

class TablePage(QWidget):
    def __init__(self, title: str, repo: Repository, table: str):
        super().__init__(); self.repo=repo; self.table=table
        layout=adaptive_page_layout(self); layout.addWidget(QLabel(f"<h2>{title}</h2>"))
        self.table_widget=QTableWidget(); layout.addWidget(self.table_widget)
        btn=QPushButton("Refresh"); btn.clicked.connect(self.refresh); layout.addWidget(btn)
        self.refresh()
    def refresh(self):
        rows=self.repo.list_rows(self.table)
        if not rows:
            self.table_widget.setRowCount(0); self.table_widget.setColumnCount(0); return
        cols=list(rows[0].keys()); self.table_widget.setColumnCount(len(cols)); self.table_widget.setHorizontalHeaderLabels(cols); self.table_widget.setRowCount(len(rows))
        for r,row in enumerate(rows):
            for c,col in enumerate(cols): self.table_widget.setItem(r,c,QTableWidgetItem(str(row[col] if row[col] is not None else "")))
        self.table_widget.resizeColumnsToContents()

class ImportPage(QWidget):
    def __init__(self, db_path: Path, refresh_callback):
        super().__init__(); self.db_path=db_path; self.refresh_callback=refresh_callback
        layout=adaptive_page_layout(self); layout.addWidget(QLabel("<h2>Spreadsheet Import</h2>"))
        self.status=QLabel("Import the D&D Combat Tracker workbook to populate Add screens and reference tables."); layout.addWidget(self.status)
        btn=QPushButton("Import Workbook..."); btn.clicked.connect(self.import_workbook); layout.addWidget(btn); layout.addStretch()
    def import_workbook(self):
        path,_=QFileDialog.getOpenFileName(self,"Select Workbook","","Excel Workbooks (*.xlsx)")
        if not path: return
        try:
            rows=SpreadsheetImporter(self.db_path).import_file(Path(path))
            self.status.setText(f"Imported {rows} rows from {path}")
            self.refresh_callback()
            QMessageBox.information(self,"Import Complete",f"Imported {rows} rows.")
        except Exception as exc:
            QMessageBox.critical(self,"Import Failed",str(exc))

class PlayerEditorWidget(QWidget):
    SKILLS = [
        ('Acrobatics','dex'), ('Animal Handling','wis'), ('Arcana','int'), ('Athletics','str'), ('Deception','cha'),
        ('History','int'), ('Insight','wis'), ('Intimidation','cha'), ('Investigation','int'), ('Medicine','wis'),
        ('Nature','int'), ('Perception','wis'), ('Performance','cha'), ('Persuasion','cha'), ('Religion','int'),
        ('Sleight of Hand','dex'), ('Stealth','dex'), ('Survival','wis')
    ]
    SAVES = [('Strength','str'), ('Dexterity','dex'), ('Constitution','con'), ('Intelligence','int'), ('Wisdom','wis'), ('Charisma','cha')]

    def __init__(self, repo: Repository, saved_callback=None):
        super().__init__()
        self.repo = repo
        self.saved_callback = saved_callback
        self.current_player_id = None
        self.ability_widgets = {}
        self.skill_boxes = {}
        self.save_boxes = {}
        self._loading_player = False
        self._feat_bonus_choices = [{}, {}, {}]
        root = QVBoxLayout(self)
        root.addWidget(QLabel("<h3>Player Character Editor</h3>"))
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)
        self._build_general_tab()
        self._build_abilities_tab()
        self._build_equipment_tab()
        self._build_inventory_tab()
        self._build_combat_tab()
        self._build_skills_tab()
        self._build_saves_tab()
        self._build_notes_tab()
        self.species.currentTextChanged.connect(self.apply_species_bonuses)
        for index, combo in enumerate([self.feat_1, self.feat_2, self.feat_3]):
            combo.currentTextChanged.connect(lambda _text, i=index: self.apply_feat_bonuses(i))
        buttons = QHBoxLayout()
        self.save_btn = QPushButton("Save Player")
        self.save_btn.clicked.connect(self.save)
        self.clear_btn = QPushButton("Clear / New")
        self.clear_btn.clicked.connect(self.clear_form)
        buttons.addWidget(self.save_btn); buttons.addWidget(self.clear_btn); buttons.addStretch()
        root.addLayout(buttons)
        self.refresh_reference_lists()
        self.update_ability_totals()

    def _form(self, parent):
        form = QFormLayout(parent)
        form.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return form

    def _build_general_tab(self):
        tab = QWidget(); form = self._form(tab)
        self.name = QLineEdit(); self.player_name = QLineEdit()
        self.species = QComboBox(); self.species.setEditable(True)
        self.class_name = QComboBox(); self.class_name.setEditable(True)
        self.subclass = QComboBox(); self.subclass.setEditable(True)
        self.background = QComboBox(); self.background.setEditable(True)
        self.level = QSpinBox(); self.level.setRange(1, 20); self.level.setValue(1); self.level.valueChanged.connect(self.update_derived_stats)
        self.portrait_path = QLineEdit(); self.portrait_path.setPlaceholderText("Optional image path")
        browse = QPushButton("Browse..."); browse.clicked.connect(self.choose_portrait)
        portrait_row = QHBoxLayout(); portrait_row.addWidget(self.portrait_path); portrait_row.addWidget(browse)
        portrait_widget = QWidget(); portrait_widget.setLayout(portrait_row)
        for w in [self.name, self.player_name, self.species, self.class_name, self.subclass, self.background, self.portrait_path]: clamp_editor_width(w, 520)
        form.addRow("Character Name *", self.name); form.addRow("Player Name", self.player_name); form.addRow("Species", self.species)
        form.addRow("Class", self.class_name); form.addRow("Subclass", self.subclass); form.addRow("Background", self.background)
        form.addRow("Level", self.level); form.addRow("Portrait", portrait_widget)
        self.tabs.addTab(tab, "General")

    def _build_abilities_tab(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        grid = QGridLayout(); headers = ["Ability", "Base", "Species", "Feat", "Total", "Modifier"]
        for c,h in enumerate(headers): grid.addWidget(QLabel(f"<b>{h}</b>"),0,c)
        for r,(key,label) in enumerate(ABILITY_LABELS, start=1):
            grid.addWidget(QLabel(label), r, 0)
            base=QSpinBox(); base.setRange(1,30); base.setValue(10); base.setMaximumWidth(90)
            race=QSpinBox(); race.setRange(-10,10); race.setMaximumWidth(90)
            feat=QSpinBox(); feat.setRange(-10,10); feat.setMaximumWidth(90)
            total=QLabel("10"); mod=QLabel("+0")
            self.ability_widgets[key]={"base":base,"race":race,"feat":feat,"total":total,"mod":mod}
            for w in [base,race,feat]: w.valueChanged.connect(self.update_ability_totals)
            grid.addWidget(base,r,1); grid.addWidget(race,r,2); grid.addWidget(feat,r,3); grid.addWidget(total,r,4); grid.addWidget(mod,r,5)
        layout.addLayout(grid); layout.addStretch(); self.tabs.addTab(tab,"Abilities")

    def _build_equipment_tab(self):
        tab=QWidget(); form=self._form(tab)
        self.feat_1=QComboBox(); self.feat_1.setEditable(True); self.feat_2=QComboBox(); self.feat_2.setEditable(True); self.feat_3=QComboBox(); self.feat_3.setEditable(True)
        self.weapon=QComboBox(); self.weapon.setEditable(True); self.armor=QComboBox(); self.armor.setEditable(True); self.spellcasting_ability=QComboBox(); self.spellcasting_ability.addItems(["", "Intelligence", "Wisdom", "Charisma"])
        self.equipment=QTextEdit(); self.equipment.setMaximumHeight(95)
        for w in [self.feat_1,self.feat_2,self.feat_3,self.weapon,self.armor,self.spellcasting_ability]: clamp_editor_width(w,520)
        self.equipment.setMaximumWidth(520)
        form.addRow("Feat 1",self.feat_1); form.addRow("Feat 2",self.feat_2); form.addRow("Feat 3",self.feat_3)
        form.addRow("Equipped Weapon",self.weapon); form.addRow("Equipped Armor",self.armor); form.addRow("Spellcasting Ability",self.spellcasting_ability); form.addRow("Equipment Notes",self.equipment)
        self.tabs.addTab(tab,"Equipment")

    def _build_inventory_tab(self):
        tab=QWidget(); layout=QVBoxLayout(tab)
        money=QHBoxLayout(); self.currency={}
        for coin in ['cp','sp','ep','gp','pp']:
            box=QSpinBox(); box.setRange(0,999999); box.setMaximumWidth(100); self.currency[coin]=box
            money.addWidget(QLabel(coin.upper())); money.addWidget(box)
        money.addStretch(); layout.addLayout(money)
        self.inventory=QTextEdit(); self.inventory.setPlaceholderText("Inventory with carried/equipped notes. Full item rows and encumbrance come in the next pass.")
        layout.addWidget(self.inventory); self.tabs.addTab(tab,"Inventory")

    def _build_combat_tab(self):
        tab=QWidget(); form=self._form(tab)
        self.ac=QSpinBox(); self.ac.setRange(0,99); self.ac.setValue(10)
        self.max_hp=QSpinBox(); self.max_hp.setRange(1,9999); self.max_hp.setValue(1)
        self.current_hp=QSpinBox(); self.current_hp.setRange(0,9999); self.current_hp.setValue(1)
        self.init_mod=QSpinBox(); self.init_mod.setRange(-20,50)
        self.prof_label=QLabel("+2"); self.passive_perception=QLabel("10"); self.passive_investigation=QLabel("10"); self.passive_insight=QLabel("10")
        self.attack_bonus=QLabel("+2"); self.spell_save_dc=QLabel("10")
        form.addRow("Armor Class", self.ac); form.addRow("Max HP", self.max_hp); form.addRow("Current HP", self.current_hp); form.addRow("Initiative Modifier", self.init_mod)
        form.addRow("Proficiency Bonus", self.prof_label); form.addRow("Passive Perception", self.passive_perception); form.addRow("Passive Investigation", self.passive_investigation); form.addRow("Passive Insight", self.passive_insight)
        form.addRow("Attack Bonus", self.attack_bonus); form.addRow("Spell Save DC", self.spell_save_dc)
        self.tabs.addTab(tab,"Combat")

    def _build_skills_tab(self):
        tab=QWidget(); grid=QGridLayout(tab); grid.addWidget(QLabel("<b>Skill</b>"),0,0); grid.addWidget(QLabel("<b>Ability</b>"),0,1); grid.addWidget(QLabel("<b>Proficient</b>"),0,2); grid.addWidget(QLabel("<b>Expertise</b>"),0,3); grid.addWidget(QLabel("<b>Total</b>"),0,4)
        for r,(skill,ability) in enumerate(self.SKILLS,start=1):
            prof=QCheckBox(); expert=QCheckBox(); val=QLabel("+0"); self.skill_boxes[skill]=(ability,prof,expert,val)
            prof.stateChanged.connect(self.update_derived_stats); expert.stateChanged.connect(self.update_derived_stats)
            grid.addWidget(QLabel(skill),r,0); grid.addWidget(QLabel(ability.upper()),r,1); grid.addWidget(prof,r,2); grid.addWidget(expert,r,3); grid.addWidget(val,r,4)
        self.tabs.addTab(tab,"Skills")

    def _build_saves_tab(self):
        tab=QWidget(); grid=QGridLayout(tab); grid.addWidget(QLabel("<b>Saving Throw</b>"),0,0); grid.addWidget(QLabel("<b>Proficient</b>"),0,1); grid.addWidget(QLabel("<b>Total</b>"),0,2)
        for r,(label,key) in enumerate(self.SAVES,start=1):
            prof=QCheckBox(); val=QLabel("+0"); self.save_boxes[key]=(prof,val); prof.stateChanged.connect(self.update_derived_stats)
            grid.addWidget(QLabel(label),r,0); grid.addWidget(prof,r,1); grid.addWidget(val,r,2)
        self.tabs.addTab(tab,"Saving Throws")

    def _build_notes_tab(self):
        tab=QWidget(); layout=QVBoxLayout(tab); self.notes=QTextEdit(); layout.addWidget(self.notes); self.tabs.addTab(tab,"Notes")

    def choose_portrait(self):
        path,_=QFileDialog.getOpenFileName(self,"Select Character Portrait","","Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if path: self.portrait_path.setText(path)

    def proficiency_bonus(self):
        return 2 + max(0, self.level.value() - 1) // 4

    def _mod(self,key):
        return ability_modifier(int(self.ability_widgets[key]['total'].text()))

    def _fill_combo(self, combo, values):
        current = combo.currentText(); clean = sorted(set(str(v).strip() for v in values if str(v).strip()))
        combo.blockSignals(True); combo.clear(); combo.addItem(""); combo.addItems(clean); combo.setCurrentText(current); combo.blockSignals(False)
        comp = QCompleter(clean); comp.setCaseSensitivity(Qt.CaseInsensitive); comp.setFilterMode(Qt.MatchContains); combo.setCompleter(comp)

    def refresh_reference_lists(self):
        self._fill_combo(self.species, self.repo.list_rule_names_like('species') + self.repo.list_rule_names_like('race'))
        self._fill_combo(self.class_name, self.repo.list_rule_names_like('class'))
        self._fill_combo(self.subclass, self.repo.list_rule_names_like('subclass'))
        self._fill_combo(self.background, self.repo.list_rule_names_like('background'))
        feats = self.repo.list_rule_names_like('feat')
        self._fill_combo(self.feat_1, feats); self._fill_combo(self.feat_2, feats); self._fill_combo(self.feat_3, feats)
        self._fill_combo(self.weapon, self.repo.list_names('weapons')); self._fill_combo(self.armor, self.repo.list_names('armor'))

    def update_ability_totals(self):
        for key,_ in ABILITY_LABELS:
            w=self.ability_widgets[key]; total=w['base'].value()+w['race'].value()+w['feat'].value(); mod=ability_modifier(total)
            w['total'].setText(str(total)); w['mod'].setText(f"{mod:+d}")
        self.init_mod.setValue(self._mod('dex'))
        self.update_derived_stats()

    def _set_bonus_column(self, column, bonuses):
        for key,_ in ABILITY_LABELS:
            self.ability_widgets[key][column].setValue(int(bonuses.get(key, 0)))

    def _fixed_bonuses_from_text(self, description):
        import re
        bonuses = {}
        names = {'strength':'str','dexterity':'dex','constitution':'con','intelligence':'int','wisdom':'wis','charisma':'cha'}
        patterns = [
            r"your (strength|dexterity|constitution|intelligence|wisdom|charisma) score increases by (\d+)",
            r"increase your (strength|dexterity|constitution|intelligence|wisdom|charisma) score by (\d+)",
        ]
        for pattern in patterns:
            for ability, value in re.findall(pattern, description.lower()): bonuses[names[ability]] = bonuses.get(names[ability], 0) + int(value)
        return bonuses

    def apply_species_bonuses(self):
        if self._loading_player: return
        name=self.species.currentText().strip(); description=self.repo.get_rule_description(name,'species') or self.repo.get_rule_description(name,'race')
        self._set_bonus_column('race', self._fixed_bonuses_from_text(description)); self.update_ability_totals()

    def _choose_ability(self, title, prompt, options):
        choice,ok=QInputDialog.getItem(self,title,prompt,options,0,False)
        return choice if ok else None

    def _feat_bonus_from_text(self, feat_name, description):
        import re
        if not description or 'increase' not in description.lower(): return {}
        fixed=self._fixed_bonuses_from_text(description)
        lower=description.lower(); labels={'Strength':'str','Dexterity':'dex','Constitution':'con','Intelligence':'int','Wisdom':'wis','Charisma':'cha'}
        if fixed and not re.search(r"\b(or|choice)\b", lower[lower.find('increase'):lower.find('increase')+140]): return fixed
        if 'increase one ability score of your choice by 2' in lower:
            mode=self._choose_ability(feat_name,'Choose how to apply this feat.',['One ability +2','Two abilities +1 each'])
            if not mode: return {}
            first=self._choose_ability(feat_name,'Choose an ability.',list(labels))
            if not first: return {}
            if mode.startswith('One'): return {labels[first]:2}
            remaining=[x for x in labels if x != first]; second=self._choose_ability(feat_name,'Choose a second ability.',remaining)
            return {labels[first]:1,labels[second]:1} if second else {labels[first]:1}
        value_match=re.search(r"increase .*? by (\d+)",lower); value=int(value_match.group(1)) if value_match else 1
        sentence=lower[lower.find('increase'):]; sentence=sentence[:sentence.find('.') if '.' in sentence else 180]
        allowed=[label for label in labels if label.lower() in sentence]
        if not allowed or 'one ability score of your choice' in sentence: allowed=list(labels)
        choice=self._choose_ability(feat_name,'Choose the ability increased by this feat.',allowed)
        return {labels[choice]:value} if choice else {}

    def apply_feat_bonuses(self, changed_index=None):
        if self._loading_player: return
        combos=[self.feat_1,self.feat_2,self.feat_3]
        if changed_index is not None:
            name=combos[changed_index].currentText().strip(); description=self.repo.get_rule_description(name,'feat')
            self._feat_bonus_choices[changed_index]=self._feat_bonus_from_text(name,description) if name else {}
        combined={}
        for bonuses in self._feat_bonus_choices:
            for key,value in bonuses.items(): combined[key]=combined.get(key,0)+value
        self._set_bonus_column('feat',combined); self.update_ability_totals()

    def update_derived_stats(self):
        pb=self.proficiency_bonus(); self.prof_label.setText(f"{pb:+d}")
        def skill_total(name):
            ability,prof,expert,_=self.skill_boxes[name]; return self._mod(ability)+(pb if prof.isChecked() else 0)+(pb if expert.isChecked() else 0)
        for skill,(ability,prof,expert,val) in self.skill_boxes.items(): val.setText(f"{skill_total(skill):+d}")
        for key,(prof,val) in self.save_boxes.items(): val.setText(f"{self._mod(key)+(pb if prof.isChecked() else 0):+d}")
        if hasattr(self,'passive_perception'):
            self.passive_perception.setText(str(10 + skill_total('Perception'))); self.passive_investigation.setText(str(10 + skill_total('Investigation'))); self.passive_insight.setText(str(10 + skill_total('Insight')))
            atk=max(self._mod('str'), self._mod('dex')) + pb; self.attack_bonus.setText(f"{atk:+d}")
            spell_key={'Intelligence':'int','Wisdom':'wis','Charisma':'cha'}.get(self.spellcasting_ability.currentText() if hasattr(self,'spellcasting_ability') else '', 'int')
            self.spell_save_dc.setText(str(8 + pb + self._mod(spell_key)))

    def _set_ability_values(self,key,row):
        w=self.ability_widgets[key]
        w['base'].setValue(row[f'{key}_base'] if f'{key}_base' in row.keys() and row[f'{key}_base'] is not None else 10)
        w['race'].setValue(row[f'{key}_race_bonus'] if f'{key}_race_bonus' in row.keys() and row[f'{key}_race_bonus'] is not None else 0)
        w['feat'].setValue(row[f'{key}_feat_bonus'] if f'{key}_feat_bonus' in row.keys() and row[f'{key}_feat_bonus'] is not None else 0)

    def _split(self,text): return [x.strip() for x in (text or '').split(';') if x.strip()]

    def load_player(self,row):
        if not row: self.clear_form(); return
        # Clear every tab before applying the selected row so optional/blank
        # fields cannot retain values from the previously edited character.
        self.clear_form(); self._loading_player = True; self.current_player_id = row['id']
        self.name.setText(row['name'] or ''); self.player_name.setText(row['player_name'] if 'player_name' in row.keys() else '')
        self.species.setCurrentText(row['species'] or ''); self.class_name.setCurrentText(row['class_name'] or ''); self.subclass.setCurrentText(row['subclass'] or ''); self.background.setCurrentText(row['background'] or '')
        self.level.setValue(row['level'] or 1); self.portrait_path.setText(row['portrait_path'] if 'portrait_path' in row.keys() and row['portrait_path'] else '')
        feats=self._split(row['feats'] if 'feats' in row.keys() else '')
        self.feat_1.setCurrentText(feats[0] if len(feats)>0 else ''); self.feat_2.setCurrentText(feats[1] if len(feats)>1 else ''); self.feat_3.setCurrentText(feats[2] if len(feats)>2 else '')
        self.weapon.setCurrentText(row['equipped_weapon'] if 'equipped_weapon' in row.keys() and row['equipped_weapon'] else ''); self.armor.setCurrentText(row['equipped_armor'] if 'equipped_armor' in row.keys() and row['equipped_armor'] else '')
        self.spellcasting_ability.setCurrentText(row['spellcasting_ability'] if 'spellcasting_ability' in row.keys() and row['spellcasting_ability'] else '')
        self.equipment.setPlainText(row['equipment'] if 'equipment' in row.keys() and row['equipment'] else ''); self.inventory.setPlainText(row['inventory'] if 'inventory' in row.keys() and row['inventory'] else '')
        for coin in ['cp','sp','ep','gp','pp']:
            raw_currency=row[f'currency_{coin}'] if f'currency_{coin}' in row.keys() else 0
            try: currency_value=int(raw_currency or 0)
            except (TypeError,ValueError): currency_value=0
            self.currency[coin].setValue(currency_value)
        self.ac.setValue(row['armor_class'] or 10); self.max_hp.setValue(row['max_hp'] or 1); self.current_hp.setValue(row['current_hp'] or row['max_hp'] or 1)
        for key,_ in ABILITY_LABELS: self._set_ability_values(key,row)
        profs=set(self._split(row['skill_proficiencies'] if 'skill_proficiencies' in row.keys() else '')); experts=set(self._split(row['skill_expertise'] if 'skill_expertise' in row.keys() else '')); saves=set(self._split(row['saving_throw_proficiencies'] if 'saving_throw_proficiencies' in row.keys() else ''))
        for skill,(_,prof,expert,_) in self.skill_boxes.items(): prof.setChecked(skill in profs); expert.setChecked(skill in experts)
        for key,(prof,_) in self.save_boxes.items(): prof.setChecked(key in saves)
        self.update_ability_totals(); self.init_mod.setValue(row['initiative_mod'] if row['initiative_mod'] is not None else self._mod('dex'))
        self.notes.setPlainText(row['notes'] or ''); self._feat_bonus_choices=[{}, {}, {}]; self._loading_player=False

    def clear_form(self):
        self._loading_player=True
        self.current_player_id=None; self.name.clear(); self.player_name.clear(); self.portrait_path.clear()
        for combo in [self.species,self.class_name,self.subclass,self.background,self.feat_1,self.feat_2,self.feat_3,self.weapon,self.armor,self.spellcasting_ability]: combo.setCurrentText('')
        self.level.setValue(1); self.equipment.clear(); self.inventory.clear(); self.notes.clear(); self.ac.setValue(10); self.max_hp.setValue(1); self.current_hp.setValue(1)
        for coin in self.currency.values(): coin.setValue(0)
        for key,_ in ABILITY_LABELS: self.ability_widgets[key]['base'].setValue(10); self.ability_widgets[key]['race'].setValue(0); self.ability_widgets[key]['feat'].setValue(0)
        for _,prof,expert,_ in self.skill_boxes.values(): prof.setChecked(False); expert.setChecked(False)
        for prof,_ in self.save_boxes.values(): prof.setChecked(False)
        self._feat_bonus_choices=[{}, {}, {}]; self._loading_player=False; self.update_ability_totals(); self.name.setFocus()

    def _ability_payload(self):
        payload={}
        for key,_ in ABILITY_LABELS:
            w=self.ability_widgets[key]; base=w['base'].value(); race=w['race'].value(); feat=w['feat'].value(); total=base+race+feat
            payload[f'{key}_base']=base; payload[f'{key}_race_bonus']=race; payload[f'{key}_feat_bonus']=feat; payload[f'{key}_total']=total; payload[f'{key}_mod']=ability_modifier(total)
        return payload

    def save(self):
        name=self.name.text().strip()
        if not name: QMessageBox.warning(self,"Missing Name","Character name is required."); return
        feats='; '.join(v for v in [self.feat_1.currentText().strip(),self.feat_2.currentText().strip(),self.feat_3.currentText().strip()] if v)
        data={"name":name,"player_name":self.player_name.text().strip(),"species":self.species.currentText().strip(),"class_name":self.class_name.currentText().strip(),"subclass":self.subclass.currentText().strip(),"background":self.background.currentText().strip(),"level":self.level.value(),"armor_class":self.ac.value(),"max_hp":self.max_hp.value(),"current_hp":min(self.current_hp.value() or self.max_hp.value(),self.max_hp.value()),"initiative_mod":self.init_mod.value(),"feats":feats,"equipped_weapon":self.weapon.currentText().strip(),"equipped_armor":self.armor.currentText().strip(),"equipment":self.equipment.toPlainText().strip(),"inventory":self.inventory.toPlainText().strip(),"notes":self.notes.toPlainText().strip(),"portrait_path":self.portrait_path.text().strip(),"spellcasting_ability":self.spellcasting_ability.currentText().strip(),"skill_proficiencies":'; '.join(k for k,(_,p,_,_) in self.skill_boxes.items() if p.isChecked()),"skill_expertise":'; '.join(k for k,(_,_,e,_) in self.skill_boxes.items() if e.isChecked()),"saving_throw_proficiencies":'; '.join(k for k,(p,_) in self.save_boxes.items() if p.isChecked())}
        for coin,box in self.currency.items(): data[f'currency_{coin}']=box.value()
        data.update(self._ability_payload()); self.repo.upsert_player(data)
        if self.saved_callback: self.saved_callback()
        QMessageBox.information(self,"Saved",f"Saved player character {name}.")

class PlayerManagerPage(QWidget):
    def __init__(self, repo: Repository, refresh_callback=None):
        super().__init__()
        self.repo = repo
        self.refresh_callback = refresh_callback
        layout = adaptive_page_layout(self)
        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("<h2>Players</h2>"))
        title_row.addStretch()
        title_row.addWidget(QLabel("Search:"))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Character, class, species, background...")
        self.search.textChanged.connect(self.refresh_table)
        title_row.addWidget(self.search)
        layout.addLayout(title_row)

        toolbar = QHBoxLayout()
        new_btn = QPushButton("+ New Player")
        pdf_btn = QPushButton("Import Character PDF...")
        edit_btn = QPushButton("Edit Selected")
        dup_btn = QPushButton("Duplicate")
        del_btn = QPushButton("Delete")
        refresh_btn = QPushButton("Refresh")
        new_btn.clicked.connect(self.new_player)
        pdf_btn.clicked.connect(self.import_character_pdf)
        edit_btn.clicked.connect(self.edit_selected)
        dup_btn.clicked.connect(self.duplicate_selected)
        del_btn.clicked.connect(self.delete_selected)
        refresh_btn.clicked.connect(self.refresh)
        for b in [new_btn, pdf_btn, edit_btn, dup_btn, del_btn, refresh_btn]:
            toolbar.addWidget(b)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setColumnCount(16)
        self.table.setIconSize(QSize(40,40))
        self.table.setHorizontalHeaderLabels(["Character", "Level", "Class", "Subclass", "Species", "Background", "STR", "DEX", "CON", "INT", "WIS", "CHA", "Weapon", "Armor", "AC", "HP"])
        self.table.itemSelectionChanged.connect(self.load_selected_into_editor)
        self.table.cellDoubleClicked.connect(lambda *_: self.edit_selected())
        self.table.setMinimumWidth(520)
        body.addWidget(self.table, 3)
        self.editor = PlayerEditorWidget(repo, self.after_save)
        self.editor.setMaximumWidth(760)
        self.editor.setMinimumWidth(520)
        self.editor_scroll = QScrollArea()
        self.editor_scroll.setWidgetResizable(True)
        self.editor_scroll.setWidget(self.editor)
        self.editor_scroll.setMinimumWidth(560)
        body.addWidget(self.editor_scroll, 2)
        layout.addLayout(body)
        self.refresh()

    def refresh(self):
        self.editor.refresh_reference_lists()
        self.refresh_table()

    def refresh_table(self):
        query = self.search.text().strip().lower() if hasattr(self, 'search') else ''
        rows = []
        for row in self.repo.list_players():
            haystack = ' '.join(str(row[k] or '') for k in row.keys()).lower()
            if not query or query in haystack:
                rows.append(row)
        self.rows = rows
        self.table.blockSignals(True)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            vals = [
                row['name'], row['level'], row['class_name'], row['subclass'],
                row['species'], row['background'],
                f"{row['str_total'] if 'str_total' in row.keys() else 10} ({row['str_mod'] if 'str_mod' in row.keys() else 0:+d})",
                f"{row['dex_total'] if 'dex_total' in row.keys() else 10} ({row['dex_mod'] if 'dex_mod' in row.keys() else 0:+d})",
                f"{row['con_total'] if 'con_total' in row.keys() else 10} ({row['con_mod'] if 'con_mod' in row.keys() else 0:+d})",
                f"{row['int_total'] if 'int_total' in row.keys() else 10} ({row['int_mod'] if 'int_mod' in row.keys() else 0:+d})",
                f"{row['wis_total'] if 'wis_total' in row.keys() else 10} ({row['wis_mod'] if 'wis_mod' in row.keys() else 0:+d})",
                f"{row['cha_total'] if 'cha_total' in row.keys() else 10} ({row['cha_mod'] if 'cha_mod' in row.keys() else 0:+d})",
                row['equipped_weapon'] if 'equipped_weapon' in row.keys() else '',
                row['equipped_armor'] if 'equipped_armor' in row.keys() else '',
                row['armor_class'], f"{row['current_hp']}/{row['max_hp']}",
            ]
            for c, value in enumerate(vals):
                item = QTableWidgetItem(str(value if value is not None else ''))
                if c == 0:
                    item.setData(Qt.UserRole, row['id'])
                    apply_portrait_icon(item,row['portrait_path'] if 'portrait_path' in row.keys() else '')
                self.table.setItem(r, c, item)
            self.table.setRowHeight(r,48)
        self.table.blockSignals(False)
        self.table.resizeColumnsToContents()

    def selected_player_id(self):
        row = self.table.currentRow()
        if row < 0 or not self.table.item(row, 0):
            return None
        return self.table.item(row, 0).data(Qt.UserRole)

    def selected_player_row(self):
        pid = self.selected_player_id()
        if pid is None:
            return None
        return self.repo.get_player_by_id(pid)

    def load_selected_into_editor(self):
        row = self.selected_player_row()
        if row: self.editor.load_player(row)

    def new_player(self):
        self.table.clearSelection()
        self.editor.clear_form()

    def import_character_pdf(self):
        path,_=QFileDialog.getOpenFileName(self,"Import Character PDF","","PDF Files (*.pdf)")
        if not path: return
        try:
            result=CharacterPdfImporter().extract(Path(path),user_data_dir() / 'portraits'); data=result['data']
            preview=[f"{key.replace('_',' ').title()}: {value}" for key,value in data.items() if value not in (None,'')]
            warning_text="\n".join(result['warnings'])
            message=f"Detected {result['field_count']} character fields ({result['form_field_count']} PDF form fields).\n\n" + "\n".join(preview[:24])
            if warning_text: message += f"\n\nReview notes:\n{warning_text}"
            message += "\n\nChoose Import Character to save this character to the Players database. A matching character name will be updated."
            dialog=QDialog(self); dialog.setWindowTitle("Character PDF Preview"); dialog.resize(720,560)
            layout=QVBoxLayout(dialog); summary=QLabel("Review the extracted character data before importing."); layout.addWidget(summary)
            preview_box=QTextEdit(); preview_box.setReadOnly(True); preview_box.setPlainText(message); layout.addWidget(preview_box,1)
            buttons=QDialogButtonBox(QDialogButtonBox.Cancel); import_button=buttons.addButton("Import Character",QDialogButtonBox.AcceptRole); import_button.setDefault(True); buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); layout.addWidget(buttons)
            if dialog.exec() != QDialog.Accepted: return
            name=str(data.get('name','')).strip()
            if not name: QMessageBox.warning(self,"Character Name Missing","Enter a character name in the PDF or add it manually before importing."); return
            payload=dict(data); payload['name']=name
            self.repo.upsert_player(payload); self.after_save()
            imported=next((row for row in self.repo.list_players() if row['name']==name),None)
            if imported: self.editor.load_player(imported)
            QMessageBox.information(self,"Character Imported",f"Imported {name} into Players. Review the editor and save any additional corrections.")
        except Exception as exc:
            QMessageBox.critical(self,"Character PDF Import Failed",f"Could not read this character sheet.\n\n{exc}")

    def edit_selected(self):
        player_id=self.selected_player_id()
        row=self.repo.get_player_by_id(player_id) if player_id is not None else None
        if not row:
            QMessageBox.information(self, "No Selection", "Select a player first, or click + New Player.")
            return
        self.editor.load_player(row)
        self.editor.name.setFocus()

    def duplicate_selected(self):
        pid = self.selected_player_id()
        if pid is None:
            QMessageBox.information(self, "No Selection", "Select a player to duplicate.")
            return
        self.repo.duplicate_player(pid)
        self.after_save()

    def delete_selected(self):
        pid = self.selected_player_id()
        row = self.selected_player_row()
        if pid is None or not row:
            QMessageBox.information(self, "No Selection", "Select a player to delete.")
            return
        if QMessageBox.question(self, "Delete Player", f"Delete {row['name']}? This does not remove existing combat log entries.") == QMessageBox.Yes:
            self.repo.delete_player(pid)
            self.editor.clear_form()
            self.after_save()

    def after_save(self):
        self.refresh_table()
        if self.refresh_callback:
            self.refresh_callback()

# Backward-compatible navigation page: the old Add Player screen now uses the same full editor.
class PlayerAddPage(PlayerManagerPage):
    pass

class MonsterAddPage(QWidget):
    def __init__(self, repo: Repository):
        super().__init__(); self.repo=repo
        layout=adaptive_page_layout(self); layout.addWidget(QLabel("<h2>Add / Edit Monster</h2>"))
        form=QFormLayout(); self.name=QComboBox(); self.name.setEditable(True); self.name.currentTextChanged.connect(self.autofill)
        self.ac=QSpinBox(); self.ac.setRange(0,99); self.hp=QSpinBox(); self.hp.setRange(1,9999); self.cr=QLineEdit(); self.type=QLineEdit(); self.notes=QLineEdit()
        form.addRow("Monster Name", self.name); form.addRow("Type", self.type); form.addRow("Armor Class", self.ac); form.addRow("Hit Points", self.hp); form.addRow("Challenge", self.cr); form.addRow("Notes", self.notes)
        layout.addLayout(form); save=QPushButton("Save Monster"); save.clicked.connect(self.save); layout.addWidget(save); layout.addStretch(); self.refresh()
    def refresh(self):
        self.monsters={r['name']: r for r in self.repo.list_rows('monsters')}
        current=self.name.currentText() if hasattr(self,'name') else ''
        self.name.blockSignals(True); self.name.clear(); self.name.addItems(sorted(self.monsters)); self.name.setCurrentText(current); self.name.blockSignals(False)
        comp=QCompleter(sorted(self.monsters)); comp.setCaseSensitivity(Qt.CaseInsensitive); comp.setFilterMode(Qt.MatchContains); self.name.setCompleter(comp)
    def autofill(self, text):
        row=self.monsters.get(text)
        if row:
            self.type.setText(row['type'] or ''); self.ac.setValue(row['armor_class'] or 10); self.hp.setValue(row['hit_points'] or 1); self.cr.setText(row['challenge_rating'] or ''); self.notes.setText(row['notes'] or '')
    def save(self):
        name=self.name.currentText().strip()
        if not name: QMessageBox.warning(self,"Missing Name","Monster name is required."); return
        self.repo.upsert_monster({"name":name,"size":"","type":self.type.text(),"alignment":"","armor_class":self.ac.value(),"hit_points":self.hp.value(),"speed":"","challenge_rating":self.cr.text(),"xp":0,"str_score":0,"dex_score":0,"con_score":0,"int_score":0,"wis_score":0,"cha_score":0,"source":"manual","notes":self.notes.text()})
        self.refresh(); QMessageBox.information(self,"Saved",f"Saved {name}.")

class EncounterBuilderPage(QWidget):
    def __init__(self, repo: Repository, refresh_callback):
        super().__init__(); self.repo=repo; self.refresh_callback=refresh_callback; self.current_encounter_id=None
        root=adaptive_page_layout(self); root.addWidget(QLabel("<h2>Encounter Builder</h2>"))
        top=QHBoxLayout(); self.new_name=QLineEdit(); self.new_name.setPlaceholderText("Encounter name, e.g. Goblin Ambush")
        new_btn=QPushButton("Create New Encounter"); new_btn.clicked.connect(self.create_encounter)
        self.encounters=QComboBox(); self.encounters.currentIndexChanged.connect(self.select_encounter)
        top.addWidget(self.new_name); top.addWidget(new_btn); top.addWidget(QLabel("Active:")); top.addWidget(self.encounters); root.addLayout(top)
        body=QHBoxLayout(); root.addLayout(body)
        monster_box=QGroupBox("Monster Browser"); mb=QVBoxLayout(monster_box); mb.setSpacing(8); self.monster_search=QComboBox(); self.monster_search.setEditable(True); self.monster_search.setInsertPolicy(QComboBox.NoInsert)
        self.monster_qty=QSpinBox(); self.monster_qty.setRange(1,50); self.monster_qty.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.monster_qty_down=QToolButton(); self.monster_qty_down.setArrowType(Qt.DownArrow); self.monster_qty_down.setToolTip("Decrease monster quantity"); self.monster_qty_down.setAccessibleName("Decrease monster quantity"); self.monster_qty_down.clicked.connect(self.monster_qty.stepDown)
        self.monster_qty_up=QToolButton(); self.monster_qty_up.setArrowType(Qt.UpArrow); self.monster_qty_up.setToolTip("Increase monster quantity"); self.monster_qty_up.setAccessibleName("Increase monster quantity"); self.monster_qty_up.clicked.connect(self.monster_qty.stepUp)
        for button in (self.monster_qty_down,self.monster_qty_up): button.setFixedSize(36,30)
        quantity_row=QHBoxLayout(); quantity_row.setContentsMargins(0,0,0,0); quantity_row.addWidget(self.monster_qty_down); quantity_row.addWidget(self.monster_qty,1); quantity_row.addWidget(self.monster_qty_up)
        self.add_monster_button=QPushButton("Add Monster(s)"); self.add_monster_button.clicked.connect(self.add_monsters)
        self.monster_search_label=QLabel("Search/type monster name"); self.monster_quantity_label=QLabel("Quantity")
        mb.addWidget(self.monster_search_label); mb.addWidget(self.monster_search); mb.addSpacing(6); mb.addWidget(self.monster_quantity_label); mb.addLayout(quantity_row); mb.addStretch(1); mb.addWidget(self.add_monster_button); body.addWidget(monster_box)
        player_box=QGroupBox("Players"); pb=QVBoxLayout(player_box); self.player_list=QListWidget(); self.add_player_button=QPushButton("Add Selected Player(s)"); self.add_player_button.clicked.connect(self.add_players); pb.addWidget(self.player_list); pb.addWidget(self.add_player_button); body.addWidget(player_box)
        cart_box=QGroupBox("Encounter Combatants"); cb=QVBoxLayout(cart_box); self.combatants=QTableWidget(); self.combatants.setColumnCount(6); self.combatants.setHorizontalHeaderLabels(["Name","Init","AC","HP","Max HP","Type"]); cb.addWidget(self.combatants)
        self.combatants.setIconSize(QSize(36,36))
        row=QHBoxLayout(); self.roll_button=QPushButton("Roll Initiative / Start"); self.roll_button.clicked.connect(self.roll_init); self.remove_button=QPushButton("Remove Selected"); self.remove_button.clicked.connect(self.remove_selected); row.addWidget(self.roll_button); row.addWidget(self.remove_button); cb.addLayout(row); body.addWidget(cart_box,2)
        self.external_notice=QLabel("Fantasy Grounds owns this encounter. Update its participants and combat data in Fantasy Grounds."); self.external_notice.setWordWrap(True); self.external_notice.setVisible(False); root.addWidget(self.external_notice)
        self.refresh()
    def refresh(self):
        selected_monster_text=self.monster_search.currentText().strip() if hasattr(self,'monster_search') else ''
        selected_monster_id=self.monster_search.currentData() if hasattr(self,'monster_search') else None
        self.monsters={r['name']: r for r in self.repo.list_monsters()}; self.monsters_by_name={name.casefold(): row for name,row in self.monsters.items()}; self.players={r['name']: r for r in self.repo.list_players()}
        self.monster_search.blockSignals(True); self.monster_search.clear()
        for name in sorted(self.monsters, key=str.casefold): self.monster_search.addItem(name, self.monsters[name]['id'])
        restore_row=self.monsters_by_name.get(selected_monster_text.casefold()) if selected_monster_text else None
        restore_id=restore_row['id'] if restore_row else selected_monster_id
        restore_index=self.monster_search.findData(restore_id) if restore_id is not None else -1
        self.monster_search.setCurrentIndex(restore_index)
        if restore_index < 0: self.monster_search.setEditText('')
        self.monster_search.blockSignals(False)
        comp=QCompleter(self.monster_search.model(), self.monster_search); comp.setCaseSensitivity(Qt.CaseInsensitive); comp.setFilterMode(Qt.MatchContains); comp.activated[str].connect(self._commit_monster_selection); self.monster_search.setCompleter(comp)
        self.player_list.clear()
        for name in sorted(self.players):
            item=QListWidgetItem(name); item.setFlags(item.flags() | Qt.ItemIsUserCheckable); item.setCheckState(Qt.Unchecked); self.player_list.addItem(item)
        self.encounters.blockSignals(True); self.encounters.clear()
        for e in self.repo.list_encounters(): self.encounters.addItem(self.repo.encounter_display_name(e), e['id'])
        self.encounters.blockSignals(False)
        if self.current_encounter_id is None and self.encounters.count(): self.current_encounter_id=self.encounters.itemData(0)
        if self.current_encounter_id is not None:
            current_index=self.encounters.findData(self.current_encounter_id)
            if current_index >= 0: self.encounters.setCurrentIndex(current_index)
        self.refresh_combatants()
    def _commit_monster_selection(self, text):
        row=self.monsters_by_name.get(str(text).strip().casefold())
        if row:
            index=self.monster_search.findData(row['id'])
            if index >= 0: self.monster_search.setCurrentIndex(index)
    def selected_monster(self):
        text=self.monster_search.currentText().strip()
        row=self.monsters_by_name.get(text.casefold()) if text else None
        if not row: return None
        index=self.monster_search.findData(row['id'])
        if index >= 0 and self.monster_search.currentIndex()!=index: self.monster_search.setCurrentIndex(index)
        return row
    def encounter_is_external(self):
        return self.repo.is_external_encounter(self.current_encounter_id)
    def refresh_ownership(self):
        external=self.encounter_is_external()
        for widget in (self.monster_search,self.monster_qty,self.monster_qty_down,self.monster_qty_up,self.add_monster_button,self.player_list,self.add_player_button,self.roll_button,self.remove_button): widget.setEnabled(not external)
        self.external_notice.setVisible(external)
        context=self.repo.encounter_sync_context(self.current_encounter_id)
        if context and context['kind']=='prepared':
            linked=f" Its synchronized combat session is {context['counterpart_name']}." if context['counterpart_name'] else " No live combat session is linked yet."
            self.external_notice.setText("Fantasy Grounds prepared encounter. Update its roster in Fantasy Grounds."+linked)
        elif context and context['kind']=='live':
            linked=f" It was started from {context['counterpart_name']}." if context['counterpart_name'] else ""
            self.external_notice.setText("Fantasy Grounds live combat session. Run combat in Fantasy Grounds."+linked)
    def create_encounter(self):
        name=self.new_name.text().strip() or "New Encounter"
        self.current_encounter_id=self.repo.create_encounter(name); self.new_name.clear(); self.refresh(); self.refresh_callback()
    def select_encounter(self):
        self.current_encounter_id=self.encounters.currentData(); self.refresh_combatants()
    def select_encounter_id(self, encounter_id):
        if encounter_id is not None: self.current_encounter_id=int(encounter_id)
    def add_monsters(self):
        if not self.current_encounter_id: self.create_encounter()
        if self.encounter_is_external(): QMessageBox.warning(self,"Fantasy Grounds Encounter","Update this encounter in Fantasy Grounds."); return
        row=self.selected_monster()
        if not row: QMessageBox.warning(self,"Monster Not Found","Select a monster from the imported library."); return
        self.repo.add_combatants_from_monster(self.current_encounter_id, row['id'], self.monster_qty.value())
        self.refresh_combatants(); self.refresh_callback()
    def add_players(self):
        if not self.current_encounter_id: self.create_encounter()
        if self.encounter_is_external(): QMessageBox.warning(self,"Fantasy Grounds Encounter","Update this encounter in Fantasy Grounds."); return
        for i in range(self.player_list.count()):
            item=self.player_list.item(i)
            if item.checkState()==Qt.Checked:
                self.repo.add_combatant_from_player(self.current_encounter_id, self.players[item.text()]['id']); item.setCheckState(Qt.Unchecked)
        self.refresh_combatants(); self.refresh_callback()
    def refresh_combatants(self):
        rows=self.repo.list_combatants(self.current_encounter_id) if self.current_encounter_id else []
        self.combatants.setRowCount(len(rows))
        for r,row in enumerate(rows):
            vals=[row['name'], row['initiative'], row['armor_class'], row['current_hp'], row['max_hp'], row['source_type']]
            for c,v in enumerate(vals): self.combatants.setItem(r,c,QTableWidgetItem(str(v if v is not None else "")))
            self.combatants.item(r,0).setData(Qt.UserRole,row['id'])
            apply_portrait_icon(self.combatants.item(r,0),row['portrait_path'] if 'portrait_path' in row.keys() else '')
            self.combatants.setRowHeight(r,42)
        self.combatants.resizeColumnsToContents()
        self.refresh_ownership()
    def selected_combatant_id(self):
        row=self.combatants.currentRow()
        if row < 0 or not self.combatants.item(row,0): return None
        return self.combatants.item(row,0).data(Qt.UserRole)
    def remove_selected(self):
        if self.encounter_is_external(): QMessageBox.warning(self,"Fantasy Grounds Encounter","Update this encounter in Fantasy Grounds."); return
        cid=self.selected_combatant_id()
        if cid: self.repo.remove_combatant(cid); self.refresh_combatants(); self.refresh_callback()
    def roll_init(self):
        if not self.current_encounter_id: return
        if self.encounter_is_external(): QMessageBox.warning(self,"Fantasy Grounds Encounter","Run combat from Fantasy Grounds."); return
        self.repo.roll_initiative(self.current_encounter_id); self.refresh_combatants(); self.refresh_callback(); QMessageBox.information(self,"Combat Started","Initiative rolled. Open Combat Dashboard to run turns.")

class CombatDashboardPage(QWidget):
    LOG_BADGES = {
        "critical": ("#665318", "#ffe082"),
        "hit": ("#234d31", "#b7f7c7"),
        "miss": ("#533037", "#ffc4ca"),
        "damage": ("#5a3028", "#ffcabd"),
        "healing": ("#174c50", "#b8f4ef"),
        "manual": ("#624815", "#ffe1a3"),
        "default": ("#34373c", "#e8eaed"),
    }

    def __init__(self, repo: Repository):
        super().__init__(); self.repo=repo; self.current_encounter_id=None
        root=adaptive_page_layout(self); root.addWidget(QLabel("<h2>Combat Dashboard</h2>"))
        top=QHBoxLayout(); self.encounters=QComboBox(); self.encounters.currentIndexChanged.connect(self.select_encounter); top.addWidget(QLabel("Encounter:")); top.addWidget(self.encounters)
        self.round_label=QLabel("Round - | Active: -"); top.addWidget(self.round_label); root.addLayout(top)
        self.order=QTableWidget(); self.order.setColumnCount(6); self.order.setHorizontalHeaderLabels(["Turn","Name","Init","AC","HP","Max"]); root.addWidget(self.order)
        self.order.setIconSize(QSize(36,36))
        buttons=QHBoxLayout(); self.prev_button=QPushButton("Previous Turn"); self.prev_button.clicked.connect(self.prev_turn); self.next_button=QPushButton("Next / End Turn"); self.next_button.clicked.connect(self.next_turn); self.damage_button=QPushButton("Apply Damage"); self.damage_button.clicked.connect(lambda:self.adjust_hp(-abs(self.hp_delta.value()), "Damage")); self.heal_button=QPushButton("Apply Healing"); self.heal_button.clicked.connect(lambda:self.adjust_hp(abs(self.hp_delta.value()), "Healing")); self.hp_delta=QSpinBox(); self.hp_delta.setRange(0,9999); self.hp_delta.setValue(1)
        for w in [self.prev_button,self.next_button,QLabel("Amount"),self.hp_delta,self.damage_button,self.heal_button]: buttons.addWidget(w)
        root.addLayout(buttons)
        logrow=QHBoxLayout(); self.action=QComboBox(); self.action.addItems(["Attack","Spell","Save","Condition","Reaction","Lair Action","Note"]); self.details=QLineEdit(); self.details.setPlaceholderText("Action details"); self.add_log_button=QPushButton("Log Action"); self.add_log_button.clicked.connect(self.log_action); logrow.addWidget(self.action); logrow.addWidget(self.details); logrow.addWidget(self.add_log_button); root.addLayout(logrow)
        self.external_notice=QLabel("Fantasy Grounds controls this encounter. Source-owned combat fields are read-only in Lectern."); self.external_notice.setWordWrap(True); self.external_notice.setVisible(False); root.addWidget(self.external_notice)
        log_filters=QHBoxLayout(); self.log_search=QLineEdit(); self.log_search.setPlaceholderText("Search actor, target, action, damage type, or result"); self.log_search.setClearButtonEnabled(True); self.log_search.textChanged.connect(self.refresh_log)
        self.log_action_filter=QComboBox(); self.log_action_filter.addItem("All action types", ""); self.log_action_filter.currentIndexChanged.connect(self.refresh_log)
        self.log_result_filter=QComboBox(); self.log_result_filter.addItem("All results", "")
        for label,key in (("Critical hits","critical"),("Hits","hit"),("Misses","miss"),("Damage","damage"),("Healing","healing"),("Manual / unattributed","manual")): self.log_result_filter.addItem(label,key)
        self.log_result_filter.currentIndexChanged.connect(self.refresh_log)
        self.hide_system_events=QCheckBox("Hide turn markers"); self.hide_system_events.setChecked(True); self.hide_system_events.toggled.connect(self.refresh_log)
        self.log_count=QLabel("0 events")
        for w in (self.log_search,self.log_action_filter,self.log_result_filter,self.hide_system_events,self.log_count): log_filters.addWidget(w)
        root.addLayout(log_filters)
        self.log_tree=QTreeWidget(); self.log_tree.setColumnCount(8); self.log_tree.setHeaderLabels(["Actor","Type","Roll","Target","Defense / HP","Action","Damage Type","Result"]); self.log_tree.setAlternatingRowColors(True); self.log_tree.setRootIsDecorated(True); self.log_tree.setUniformRowHeights(False); self.log_tree.setSelectionBehavior(QAbstractItemView.SelectRows); self.log_tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        header=self.log_tree.header(); header.setSectionResizeMode(0,QHeaderView.ResizeToContents); header.setSectionResizeMode(1,QHeaderView.ResizeToContents); header.setSectionResizeMode(2,QHeaderView.ResizeToContents); header.setSectionResizeMode(3,QHeaderView.ResizeToContents); header.setSectionResizeMode(4,QHeaderView.ResizeToContents); header.setSectionResizeMode(5,QHeaderView.ResizeToContents); header.setSectionResizeMode(6,QHeaderView.ResizeToContents); header.setSectionResizeMode(7,QHeaderView.Stretch)
        self.log_tree.itemDoubleClicked.connect(self.toggle_log_details); root.addWidget(self.log_tree,1); self.refresh()
    def refresh(self):
        previous_id=self.current_encounter_id; encounters=list(self.repo.list_encounters())
        status_order={"active":0,"draft":1,"completed":2}
        encounters.sort(key=lambda row:(status_order.get(str(row['status'] or '').casefold(),3),-int(row['id'])))
        self.encounters.blockSignals(True); self.encounters.clear()
        for e in encounters: self.encounters.addItem(self.repo.encounter_display_name(e), e['id'])
        preferred=self.encounters.findData(previous_id) if previous_id is not None else -1
        if preferred < 0 and self.encounters.count(): preferred=0
        if preferred >= 0: self.encounters.setCurrentIndex(preferred); self.current_encounter_id=self.encounters.itemData(preferred)
        else: self.current_encounter_id=None
        self.encounters.blockSignals(False)
        self.refresh_board()
    def select_encounter(self): self.current_encounter_id=self.encounters.currentData(); self.refresh_board()
    def select_encounter_id(self, encounter_id):
        if encounter_id is not None: self.current_encounter_id=int(encounter_id)
    def rows(self): return self.repo.list_combatants(self.current_encounter_id) if self.current_encounter_id else []
    def refresh_board(self):
        rows=self.rows(); enc=self.repo.get_encounter(self.current_encounter_id) if self.current_encounter_id else None; active=(enc['active_index'] if enc else 0) or 0
        external=self.repo.is_external_encounter(self.current_encounter_id); self.external_notice.setVisible(external)
        context=self.repo.encounter_sync_context(self.current_encounter_id)
        if external and not rows and enc and enc['status']=='completed':
            self.external_notice.setText("Historical Fantasy Grounds log: no combatant snapshot was preserved for this encounter. Select an active or session-specific Fantasy Grounds Live Combat encounter to view turn order, AC, and HP.")
        elif context and context['kind']=='prepared':
            linked=f" Open {context['counterpart_name']} for synchronized combat and journal data." if context['counterpart_name'] else " Start and export combat from Fantasy Grounds to create its live session."
            self.external_notice.setText("Fantasy Grounds prepared encounter: this view shows its roster, not a combat journal."+linked)
        elif context and context['kind']=='live':
            linked=f" Prepared from {context['counterpart_name']}." if context['counterpart_name'] else ""
            self.external_notice.setText("Fantasy Grounds live combat session: synchronized turn order, HP, and journal."+linked)
        else:
            self.external_notice.setText("Fantasy Grounds controls this encounter. Source-owned combat fields are read-only in Lectern.")
        for widget in [self.prev_button,self.next_button,self.hp_delta,self.damage_button,self.heal_button,self.action,self.details,self.add_log_button]: widget.setEnabled(not external)
        active_name=rows[active]['name'] if rows and active < len(rows) else '-'; self.round_label.setText(f"Round {enc['round'] if enc else '-'} | Active: {active_name}")
        self.order.setRowCount(len(rows))
        for r,row in enumerate(rows):
            vals=["▶" if r==active else "", row['name'], row['initiative'], row['armor_class'], row['current_hp'], row['max_hp']]
            for c,v in enumerate(vals): self.order.setItem(r,c,QTableWidgetItem(str(v if v is not None else "")))
            self.order.item(r,1).setData(Qt.UserRole,row['id'])
            apply_portrait_icon(self.order.item(r,1),row['portrait_path'] if 'portrait_path' in row.keys() else '')
            self.order.setRowHeight(r,42)
        self.order.resizeColumnsToContents(); self.refresh_log()
    def selected_id_name(self):
        r=self.order.currentRow(); rows=self.rows()
        if r < 0 and rows:
            enc=self.repo.get_encounter(self.current_encounter_id); r=(enc['active_index'] if enc else 0) or 0
        if r < 0 or r >= len(rows): return None, ''
        return rows[r]['id'], rows[r]['name']
    def adjust_hp(self, delta:int, label:str):
        cid,name=self.selected_id_name(); rows=self.rows(); row=next((x for x in rows if x['id']==cid), None)
        if not row: return
        enc=self.repo.get_encounter(self.current_encounter_id); active_index=(enc['active_index'] if enc else 0) or 0
        active=rows[active_index] if rows and active_index < len(rows) else None
        actor_name=active['name'] if active else "Manual / Unattributed"
        actor_side={"player":"party","monster":"hostile"}.get(active['source_type'] if active else "","unknown")
        actor_key=f"{active['source_type']}:{active['source_id'] or ''}" if active else ""
        applied=abs(delta); new=max(0,min(row['max_hp'] or 1,(row['current_hp'] or 0)+delta)); self.repo.update_combatant_hp(cid,new)
        verb="damage applied" if label=="Damage" else "healing applied"
        details=f"{applied} | {name} | Target HP {new}/{row['max_hp']} | {label} | {applied} {verb}"
        self.repo.log_turn(self.current_encounter_id,actor_name,label,details,actor_source_key=actor_key,actor_side=actor_side,amount=applied); self.refresh_board()
    def log_action(self):
        cid,name=self.selected_id_name(); rows=self.rows(); row=next((x for x in rows if x['id']==cid),None); actor=name or "Encounter"
        actor_side={"player":"party","monster":"hostile"}.get(row['source_type'] if row else "","unknown")
        actor_key=f"{row['source_type']}:{row['source_id'] or ''}" if row else ""
        self.repo.log_turn(self.current_encounter_id,actor,self.action.currentText(),self.details.text(),actor_source_key=actor_key,actor_side=actor_side); self.details.clear(); self.refresh_log()
    def next_turn(self):
        if self.current_encounter_id: self.repo.next_turn(self.current_encounter_id); self.refresh_board()
    def prev_turn(self):
        if self.current_encounter_id: self.repo.previous_turn(self.current_encounter_id); self.refresh_board()
    def refresh_log(self):
        self.log_tree.clear()
        if not self.current_encounter_id:
            self.log_count.setText("0 events")
            return
        rows=list(self.repo.list_turn_log(self.current_encounter_id)[:500])
        current_action=self.log_action_filter.currentData()
        action_types=sorted({str(row['action_type'] or '') for row in rows if row['action_type']},key=str.casefold)
        self.log_action_filter.blockSignals(True); self.log_action_filter.clear(); self.log_action_filter.addItem("All action types","")
        for action_type in action_types: self.log_action_filter.addItem(action_type,action_type)
        restore=self.log_action_filter.findData(current_action); self.log_action_filter.setCurrentIndex(max(0,restore)); self.log_action_filter.blockSignals(False)
        search=self.log_search.text().strip().casefold(); action_filter=str(self.log_action_filter.currentData() or ''); result_filter=str(self.log_result_filter.currentData() or '')
        grouped={}
        for row in rows:
            fields=self.combat_log_fields(row)
            if self.hide_system_events.isChecked() and fields['system']: continue
            if action_filter and fields['type']!=action_filter: continue
            if result_filter and fields['category']!=result_filter: continue
            if search and search not in fields['search']: continue
            grouped.setdefault(int(row['round'] or 0),[]).append((row,fields))
        shown=0
        for round_no in sorted(grouped,reverse=True):
            events=grouped[round_no]
            round_item=QTreeWidgetItem([f"Round {round_no} - {len(events)} event{'s' if len(events)!=1 else ''}"]); round_item.setFirstColumnSpanned(True); round_item.setFont(0,QFont('',10,QFont.Bold)); round_item.setBackground(0,QBrush(QColor('#2f3540'))); self.log_tree.addTopLevelItem(round_item)
            for row,fields in events:
                item=QTreeWidgetItem([fields['actor'],fields['type'],fields['roll'],fields['target'],fields['defense'],fields['action'],fields['damage_type'],fields['result']]); item.setData(0,Qt.UserRole,row['id']); item.setToolTip(7,"Double-click to show the original event details")
                background,foreground=self.LOG_BADGES.get(fields['category'],self.LOG_BADGES['default']); item.setBackground(7,QBrush(QColor(background))); item.setForeground(7,QBrush(QColor(foreground))); item.setFont(7,QFont('',9,QFont.Bold))
                detail_text=f"Original: {row['details'] or '(none)'}"
                component_summary=self.damage_component_summary(row['damage_components_json'])
                if component_summary: detail_text+=f"  -  Components: {component_summary}"
                if row['created_at']: detail_text+=f"  -  {row['created_at']}"
                detail=QTreeWidgetItem([detail_text]); detail.setFirstColumnSpanned(True); detail.setForeground(0,QBrush(QColor('#bdc1c6'))); item.addChild(detail); round_item.addChild(item); shown+=1
            round_item.setExpanded(True)
        self.log_count.setText(f"{shown} event{'s' if shown!=1 else ''}")

    @staticmethod
    def damage_component_summary(raw_json):
        try: components=json.loads(str(raw_json or '[]'))
        except (TypeError,ValueError,json.JSONDecodeError): return ''
        summaries=[]
        for component in components if isinstance(components,list) else []:
            if not isinstance(component,dict): continue
            types=component.get('types') if isinstance(component.get('types'),list) else []
            label=' + '.join(str(value) for value in types if value) or 'unknown'
            rolled=component.get('rolled'); applied=component.get('applied')
            summary=f"{label}: {rolled if rolled is not None else '?'} rolled -> {applied if applied is not None else '?'} applied"
            adjustments=[]
            if component.get('resisted'): adjustments.append(f"{component['resisted']} resisted")
            if component.get('vulnerable'): adjustments.append(f"+{component['vulnerable']} vulnerable")
            if adjustments: summary+=f" ({', '.join(adjustments)})"
            summaries.append(summary)
        return '; '.join(summaries)

    @staticmethod
    def combat_log_fields(row):
        actor=str(row['actor'] or 'Unknown'); action_type=str(row['action_type'] or 'Action'); details=str(row['details'] or '').strip(); parts=[part.strip() for part in details.split(' | ')]
        roll=target=defense=action=result=''
        if len(parts)>=5:
            roll,target,defense,action=parts[:4]; result=' | '.join(parts[4:])
        else:
            action=action_type; result=details or action_type
        combined=f"{action_type} {details}".casefold()
        if 'critical hit' in combined: category='critical'
        elif 'automatic miss' in combined or action_type.casefold()=='miss' or ' | miss' in combined: category='miss'
        elif action_type.casefold()=='attack' and (' hit' in f" {combined}" or result.casefold().startswith('hit')): category='hit'
        elif 'manual / unattributed' in actor.casefold() or 'manual_or_unattributed' in combined: category='manual'
        elif 'healing' in action_type.casefold() or 'healing applied' in combined: category='healing'
        elif 'damage' in action_type.casefold() or 'damage applied' in combined: category='damage'
        else: category='default'
        system=action_type.casefold() in {'turn start','turn end'}
        damage_type=str(row['damage_types'] or '')
        if category=='damage' and not damage_type: damage_type='Not reported'
        search=' '.join((actor,action_type,details,roll,target,defense,action,damage_type,result)).casefold()
        return {'actor':actor,'type':action_type,'roll':roll,'target':target,'defense':defense,'action':action,'damage_type':damage_type,'result':result,'category':category,'system':system,'search':search}

    @staticmethod
    def toggle_log_details(item,_column):
        if item.childCount(): item.setExpanded(not item.isExpanded())


class CampaignDashboardPage(QWidget):
    DAMAGE_TYPE_COLORS = {
        "acid": ("#1f5a3b", "#effff5"),
        "bludgeoning": ("#5a4634", "#fff7ed"),
        "cold": ("#245b8a", "#f0f9ff"),
        "fire": ("#8f2f2a", "#fff4f2"),
        "force": ("#62458a", "#faf5ff"),
        "lightning": ("#7a6518", "#fffce8"),
        "necrotic": ("#4b365c", "#f8f0ff"),
        "piercing": ("#4b5966", "#f4f8fb"),
        "poison": ("#83b96b", "#14230f"),
        "psychic": ("#7f376f", "#fff0fb"),
        "radiant": ("#8a6a20", "#fff9df"),
        "slashing": ("#3e5f73", "#f0f8ff"),
        "thunder": ("#404b8a", "#f2f4ff"),
    }

    def __init__(self, repo: Repository, refresh_callback):
        super().__init__(); self.repo=repo; self.refresh_callback=refresh_callback
        root=adaptive_page_layout(self); root.addWidget(QLabel("<h2>Campaign Dashboard</h2>"))
        create=QHBoxLayout(); self.name=QLineEdit(); self.name.setPlaceholderText("Campaign name"); self.description=QLineEdit(); self.description.setPlaceholderText("Description (optional)"); add=QPushButton("Create Campaign"); add.clicked.connect(self.create_campaign)
        for w in [self.name,self.description,add]: create.addWidget(w)
        root.addLayout(create)
        choose=QHBoxLayout(); self.campaigns=QComboBox(); self.campaigns.currentIndexChanged.connect(self.refresh_dashboard); self.encounter=QComboBox(); self.outcome=QComboBox(); self.outcome.addItems(["Victory","Defeat","Retreat","Unresolved"]); assign=QPushButton("Add Encounter"); assign.clicked.connect(self.assign); finish=QPushButton("Complete Encounter"); finish.clicked.connect(self.complete)
        for w in [QLabel("Campaign:"),self.campaigns,QLabel("Encounter:"),self.encounter,assign,self.outcome,finish]: choose.addWidget(w)
        root.addLayout(choose); self.summary=QLabel(); self.summary.setWordWrap(True); root.addWidget(self.summary)
        stats=QGroupBox("Party Combat Statistics"); stats_layout=QGridLayout(stats); stats_layout.setSpacing(10)
        self.party_dpr_card,self.party_dpr=self._stat_card("Party DPR","#5f8dd3")
        self.party_hpr_card,self.party_hpr=self._stat_card("Party HPR","#58a878")
        self.critical_hits_card,self.critical_hits=self._stat_card("Critical-hit Leader","#d39a45")
        self.critical_misses_card,self.critical_misses=self._stat_card("Critical-miss Leader","#b05c67")
        stats_layout.addWidget(self.party_dpr_card,0,0); stats_layout.addWidget(self.party_hpr_card,0,1)
        stats_layout.addWidget(self.critical_hits_card,0,2); stats_layout.addWidget(self.critical_misses_card,0,3)
        for column in range(4): stats_layout.setColumnStretch(column,1)
        self.stats_coverage=QLabel(); self.stats_coverage.setWordWrap(True)
        stats_layout.addWidget(self.stats_coverage,1,0,1,4)
        root.addWidget(stats)
        self.dashboard_lower=QWidget(); dashboard_lower_layout=QHBoxLayout(self.dashboard_lower); dashboard_lower_layout.setContentsMargins(0,0,0,0)
        self.damage_types_group=QGroupBox("Party Damage Type Leaders"); damage_types_layout=QVBoxLayout(self.damage_types_group)
        damage_types_note=QLabel("Leaders are based on applied party damage across campaign encounters. Unknown damage and non-damage qualifiers are excluded."); damage_types_note.setWordWrap(True); damage_types_layout.addWidget(damage_types_note)
        self.damage_type_leaders=QTableWidget(); self.damage_type_leaders.setColumnCount(4); self.damage_type_leaders.setHorizontalHeaderLabels(["Damage Type","Leading Combatant(s)","Applied Damage","Damaging Events"]); self.damage_type_leaders.setAlternatingRowColors(False); self.damage_type_leaders.setSelectionBehavior(QAbstractItemView.SelectRows); self.damage_type_leaders.setEditTriggers(QAbstractItemView.NoEditTriggers); self.damage_type_leaders.verticalHeader().setVisible(False); self.damage_type_leaders.verticalHeader().setDefaultSectionSize(27); self.damage_type_leaders.setMinimumHeight(430); self.damage_type_leaders.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
        damage_header=self.damage_type_leaders.horizontalHeader(); damage_header.setSectionResizeMode(0,QHeaderView.ResizeToContents); damage_header.setSectionResizeMode(1,QHeaderView.Stretch); damage_header.setSectionResizeMode(2,QHeaderView.ResizeToContents); damage_header.setSectionResizeMode(3,QHeaderView.ResizeToContents)
        damage_types_layout.addWidget(self.damage_type_leaders,1)
        self.encounters_group=QGroupBox("Campaign Encounters"); encounters_layout=QVBoxLayout(self.encounters_group)
        self.history=QTableWidget(); self.history.setColumnCount(7); self.history.setHorizontalHeaderLabels(["Encounter","Status","Outcome","Rounds","Combatants","Actions","Completed"]); self.history.setAlternatingRowColors(True); self.history.setSelectionBehavior(QAbstractItemView.SelectRows); self.history.setEditTriggers(QAbstractItemView.NoEditTriggers); self.history.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding); encounters_layout.addWidget(self.history)
        dashboard_lower_layout.addWidget(self.damage_types_group,1); dashboard_lower_layout.addWidget(self.encounters_group,1)
        root.addWidget(self.dashboard_lower,1); self.refresh()

    @staticmethod
    def _stat_card(title,accent_color):
        card=QFrame(); card.setFrameShape(QFrame.StyledPanel); card.setMinimumHeight(112)
        card.setStyleSheet(f"QFrame {{ background-color: rgba(42,44,48,235); border: 1px solid #484c52; border-left: 4px solid {accent_color}; border-radius: 8px; }} QFrame QLabel {{ background: transparent; border: none; }}")
        layout=QVBoxLayout(card); layout.setContentsMargins(14,10,12,10); layout.setSpacing(5)
        heading=QLabel(title); heading.setStyleSheet(f"color: {accent_color}; font-size: 12px; font-weight: 700;")
        value=QLabel(); value.setWordWrap(True); value.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(heading); layout.addWidget(value,1)
        return card,value
    def refresh(self):
        campaign_id=self.campaigns.currentData(); self.campaigns.blockSignals(True); self.campaigns.clear()
        for row in self.repo.list_campaigns(): self.campaigns.addItem(row['name'],row['id'])
        self.campaigns.blockSignals(False)
        if campaign_id is not None: self.campaigns.setCurrentIndex(max(0,self.campaigns.findData(campaign_id)))
        self.encounter.clear()
        for row in self.repo.list_encounters(): self.encounter.addItem(self.repo.encounter_display_name(row),row['id'])
        self.refresh_dashboard()
    def create_campaign(self):
        name=self.name.text().strip()
        if not name: QMessageBox.warning(self,"Missing Name","Campaign name is required."); return
        campaign_id=self.repo.create_campaign(name,self.description.text().strip()); self.name.clear(); self.description.clear(); self.refresh(); self.campaigns.setCurrentIndex(self.campaigns.findData(campaign_id)); self.refresh_callback()
    def assign(self):
        if self.campaigns.currentData() and self.encounter.currentData(): self.repo.assign_encounter_to_campaign(self.encounter.currentData(),self.campaigns.currentData()); self.refresh_dashboard(); self.refresh_callback()
    def complete(self):
        if self.encounter.currentData(): self.repo.complete_encounter(self.encounter.currentData(),self.outcome.currentText()); self.refresh_dashboard(); self.refresh_callback()
    def refresh_dashboard(self):
        campaign_id=self.campaigns.currentData()
        if not campaign_id:
            self.summary.setText("Create a campaign, then add encounters to see cumulative results.")
            for label in (self.party_dpr,self.party_hpr,self.critical_hits,self.critical_misses,self.stats_coverage): label.clear()
            self.damage_type_leaders.setRowCount(0); self.history.setRowCount(0); return
        s=self.repo.campaign_summary(campaign_id); self.summary.setText(f"<b>{s['total']} encounters</b> · {s['completed'] or 0} completed · {s['victories'] or 0} victories · {s['defeats'] or 0} defeats · {s['retreats'] or 0} retreats · {s['rounds']} rounds · {s['actions']} actions · {s['damage']} damage · {s['healing']} healing")
        hit_names=", ".join(s['critical_hit_leaders']) or "No recorded critical hits"
        miss_names=", ".join(s['critical_miss_leaders']) or "No recorded critical misses"
        self.party_dpr.setText(f"<span style='font-size:22px; font-weight:700'>{s['party_dpr']:.1f}</span><br>{s['party_damage']} applied damage<br>{s['combat_rounds']} combat rounds")
        self.party_hpr.setText(f"<span style='font-size:22px; font-weight:700'>{s['party_hpr']:.1f}</span><br>{s['party_healing']} applied healing<br>{s['combat_rounds']} combat rounds")
        self.critical_hits.setText(f"<span style='font-size:16px; font-weight:700'>{hit_names}</span><br>{s['critical_hit_count']} critical hit{'s' if s['critical_hit_count'] != 1 else ''}")
        self.critical_misses.setText(f"<span style='font-size:16px; font-weight:700'>{miss_names}</span><br>{s['critical_miss_count']} critical miss{'es' if s['critical_miss_count'] != 1 else ''}")
        coverage=(100*s['attributed_stat_events']/s['stat_events']) if s['stat_events'] else 0
        self.stats_coverage.setText(f"Statistics coverage: {s['attributed_stat_events']} of {s['stat_events']} attack, damage, and healing events have party/hostile attribution ({coverage:.0f}%). Unattributed events are excluded from party metrics.")
        damage_rows=s['damage_type_leaders']; self.damage_type_leaders.setRowCount(len(damage_rows))
        for r,damage_row in enumerate(damage_rows):
            leaders=damage_row['leaders']; leader_names=", ".join(str(leader['name']) for leader in leaders) or "No recorded party damage"
            if not leaders: event_text="0"
            elif len(leaders)==1: event_text=str(leaders[0]['events'])
            elif len({int(leader['events']) for leader in leaders})==1: event_text=f"{leaders[0]['events']} each"
            else: event_text="; ".join(f"{leader['name']}: {leader['events']}" for leader in leaders)
            damage_type=str(damage_row['damage_type']).casefold()
            values=[damage_type.replace('-', ' ').title(),leader_names,damage_row['damage'],event_text]
            background,foreground=self.DAMAGE_TYPE_COLORS.get(damage_type,("#3f4348","#f1f3f4"))
            for c,value in enumerate(values):
                item=QTableWidgetItem(str(value)); item.setBackground(QBrush(QColor(background))); item.setForeground(QBrush(QColor(foreground)))
                if c==0: item.setFont(QFont('',9,QFont.Bold))
                self.damage_type_leaders.setItem(r,c,item)
        rows=self.repo.campaign_encounters(campaign_id); self.history.setRowCount(len(rows))
        for r,row in enumerate(rows):
            for c,value in enumerate([self.repo.encounter_display_name(row),row['status'],row['outcome'],row['round'],row['combatant_count'],row['action_count'],row['completed_at'] or '']): self.history.setItem(r,c,QTableWidgetItem(str(value or '')))
        self.history.resizeColumnsToContents()


class CsvImportExportPage(QWidget):
    def __init__(self, db_path: Path, refresh_callback):
        super().__init__()
        self.db_path = db_path
        self.repo = Repository(db_path)
        self.refresh_callback = refresh_callback
        self.csv = CsvTransferService(db_path)
        layout = adaptive_page_layout(self)
        layout.addWidget(QLabel("<h2>CSV Import / Export</h2>"))
        intro = QLabel(
            "Export a table to CSV, edit it in Excel or another editor, then import it back. "
            "Rows are matched by Name; Rules Reference rows are matched by Category + Name."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Table:"))
        self.table_select = QComboBox()
        for table, label in CSV_TABLES.items():
            self.table_select.addItem(label, table)
        controls.addWidget(self.table_select)
        controls.addStretch()
        layout.addLayout(controls)

        buttons = QHBoxLayout()
        export_one = QPushButton("Export Selected Table...")
        export_all = QPushButton("Export All Tables...")
        validate_one = QPushButton("Validate / Preview CSV...")
        import_one = QPushButton("Import Selected CSV...")
        template = QPushButton("Export Empty Template...")
        export_one.clicked.connect(self.export_selected)
        export_all.clicked.connect(self.export_all)
        validate_one.clicked.connect(self.validate_selected)
        import_one.clicked.connect(self.import_selected)
        template.clicked.connect(self.export_template)
        for button in [export_one, export_all, validate_one, import_one, template]:
            buttons.addWidget(button)
        buttons.addStretch()
        layout.addLayout(buttons)

        self.status = QLabel("Ready.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        layout.addWidget(QLabel("<b>Current Data Counts</b>"))
        self.counts = QTableWidget()
        self.counts.setColumnCount(2)
        self.counts.setHorizontalHeaderLabels(["Table", "Rows"])
        self.counts.setMaximumHeight(280)
        layout.addWidget(self.counts)

        layout.addWidget(QLabel("<b>Import Validation / Preview</b>"))
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(4)
        self.preview_table.setHorizontalHeaderLabels(["CSV Row", "Status", "Key", "Message"])
        layout.addWidget(self.preview_table, 1)
        self.preview_summary = QLabel("Validate a CSV to preview New / Modified / Unchanged / Duplicate / Error rows before import.")
        self.preview_summary.setWordWrap(True)
        layout.addWidget(self.preview_summary)
        self.last_preview_path = None
        self.last_preview_has_errors = False
        self.refresh()

    def selected_table(self) -> str:
        return self.table_select.currentData()

    def refresh(self):
        rows = []
        for table, label in CSV_TABLES.items():
            try:
                rows.append((label, self.repo.count(table)))
            except Exception:
                rows.append((label, "Error"))
        self.counts.setRowCount(len(rows))
        for r, (label, count) in enumerate(rows):
            self.counts.setItem(r, 0, QTableWidgetItem(str(label)))
            self.counts.setItem(r, 1, QTableWidgetItem(str(count)))
        self.counts.resizeColumnsToContents()

    def export_selected(self):
        table = self.selected_table()
        default_name = f"{table}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", default_name, "CSV Files (*.csv)")
        if not path:
            return
        try:
            rows = self.csv.export_table(table, Path(path))
            self.status.setText(f"Exported {rows} rows from {table} to {path}")
            QMessageBox.information(self, "CSV Export Complete", f"Exported {rows} rows.")
        except Exception as exc:
            QMessageBox.critical(self, "CSV Export Failed", str(exc))

    def export_all(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if not folder:
            return
        try:
            results = self.csv.export_all(Path(folder))
            summary = "\n".join(f"{table}: {count}" for table, count in results.items())
            self.status.setText(f"Exported all CSV files to {folder}")
            QMessageBox.information(self, "CSV Export Complete", summary)
        except Exception as exc:
            QMessageBox.critical(self, "CSV Export Failed", str(exc))

    def export_template(self):
        table = self.selected_table()
        default_name = f"{table}_template.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV Template", default_name, "CSV Files (*.csv)")
        if not path:
            return
        try:
            columns = self.csv.table_columns(table)
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            import csv as _csv
            with Path(path).open("w", newline="", encoding="utf-8-sig") as f:
                writer = _csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
            self.status.setText(f"Exported empty template for {table} to {path}")
            QMessageBox.information(self, "Template Exported", "Template exported.")
        except Exception as exc:
            QMessageBox.critical(self, "Template Export Failed", str(exc))

    def validate_selected(self):
        table = self.selected_table()
        path, _ = QFileDialog.getOpenFileName(self, "Validate CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        try:
            preview = self.csv.preview_table(table, Path(path))
            self.show_preview(preview)
            self.last_preview_path = Path(path)
            self.last_preview_has_errors = any(row["status"] in {"Error", "Duplicate"} for row in preview)
            self.status.setText(f"Previewed {len(preview)} CSV rows from {path}")
        except Exception as exc:
            QMessageBox.critical(self, "CSV Validation Failed", str(exc))

    def show_preview(self, preview: list[dict]):
        self.preview_table.setRowCount(len(preview))
        counts = {"New": 0, "Modified": 0, "Unchanged": 0, "Duplicate": 0, "Error": 0}
        for r, row in enumerate(preview):
            status = row.get("status", "")
            if status in counts:
                counts[status] += 1
            values = [row.get("row_number", ""), status, row.get("key", ""), row.get("message", "")]
            for c, value in enumerate(values):
                self.preview_table.setItem(r, c, QTableWidgetItem(str(value)))
        self.preview_table.resizeColumnsToContents()
        self.preview_summary.setText(" | ".join(f"{key}: {value}" for key, value in counts.items()))

    def import_selected(self):
        table = self.selected_table()
        path, _ = QFileDialog.getOpenFileName(self, "Import CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        try:
            preview = self.csv.preview_table(table, Path(path))
            self.show_preview(preview)
            blocking = [row for row in preview if row["status"] in {"Error", "Duplicate"}]
            if blocking:
                self.status.setText("Import blocked. Resolve Error or Duplicate rows shown in the preview.")
                QMessageBox.warning(self, "CSV Import Blocked", "Resolve Error or Duplicate rows before importing.")
                return
            summary = self.preview_summary.text()
            if QMessageBox.question(
                self,
                "Commit CSV Import",
                f"Preview complete for {Path(path).name}.\n{summary}\n\nCommit these changes to {table}?"
            ) != QMessageBox.Yes:
                return
            rows = self.csv.import_table(table, Path(path))
            self.status.setText(f"Imported {rows} rows into {table} from {path}")
            self.refresh()
            self.refresh_callback()
            QMessageBox.information(self, "CSV Import Complete", f"Imported {rows} rows.")
        except Exception as exc:
            QMessageBox.critical(self, "CSV Import Failed", str(exc))


class DataWorkflowPage(QWidget):
    def __init__(self, db_path: Path, refresh_callback):
        super().__init__()
        self.db_path = db_path
        self.refresh_callback = refresh_callback
        self.workflow = DataWorkflowService(db_path)
        layout = adaptive_page_layout(self)
        layout.addWidget(QLabel("<h2>Data Workflow</h2>"))
        intro = QLabel("Backup, restore, reset, and reseed the local SQLite database. Reset and restore automatically create safety backups first.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.status = QLabel("Ready.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        buttons = QHBoxLayout()
        backup = QPushButton("Backup Database...")
        restore = QPushButton("Restore Database...")
        reset = QPushButton("Reset Empty Database")
        reseed = QPushButton("Reset and Reseed")
        backup.clicked.connect(self.backup_database)
        restore.clicked.connect(self.restore_database)
        reset.clicked.connect(self.reset_database)
        reseed.clicked.connect(self.reseed_database)
        for button in [backup, restore, reset, reseed]:
            buttons.addWidget(button)
        buttons.addStretch()
        layout.addLayout(buttons)

        layout.addWidget(QLabel("<b>Current Database</b>"))
        self.info = QTextEdit()
        self.info.setReadOnly(True)
        self.info.setMaximumHeight(180)
        layout.addWidget(self.info)
        layout.addStretch()
        self.refresh()

    def refresh(self):
        size = self.db_path.stat().st_size if self.db_path.exists() else 0
        self.info.setPlainText(f"Database: {self.db_path}\nSize: {size:,} bytes\nBackups: {self.workflow.backup_dir}")

    def backup_database(self):
        path, _ = QFileDialog.getSaveFileName(self, "Backup Database", str(self.workflow.backup_dir / "campaign_manager_backup.db"), "SQLite DB (*.db);;All Files (*)")
        if not path:
            return
        try:
            out = self.workflow.backup_database(Path(path))
            self.status.setText(f"Backup created: {out}")
            self.refresh()
            QMessageBox.information(self, "Backup Complete", f"Backup created:\n{out}")
        except Exception as exc:
            QMessageBox.critical(self, "Backup Failed", str(exc))

    def restore_database(self):
        path, _ = QFileDialog.getOpenFileName(self, "Restore Database", str(self.workflow.backup_dir), "SQLite DB (*.db);;All Files (*)")
        if not path:
            return
        if QMessageBox.question(self, "Restore Database", "Restore will replace the current database after creating a safety backup. Continue?") != QMessageBox.Yes:
            return
        try:
            self.workflow.restore_database(Path(path))
            self.status.setText(f"Restored database from {path}")
            self.refresh()
            self.refresh_callback()
            QMessageBox.information(self, "Restore Complete", "Database restored.")
        except Exception as exc:
            QMessageBox.critical(self, "Restore Failed", str(exc))

    def reset_database(self):
        if QMessageBox.question(self, "Reset Database", "Reset to an empty database? A safety backup will be created first.") != QMessageBox.Yes:
            return
        try:
            self.workflow.reset_database(keep_backup=True)
            self.status.setText("Database reset to empty schema.")
            self.refresh()
            self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Reset Failed", str(exc))

    def reseed_database(self):
        if QMessageBox.question(self, "Reset and Reseed", "Reset the database and reload bundled reference seed data? A safety backup will be created first.") != QMessageBox.Yes:
            return
        try:
            rows = self.workflow.reseed_database(keep_backup=True)
            self.status.setText(f"Database reset and reseeded with {rows} rows.")
            self.refresh()
            self.refresh_callback()
            QMessageBox.information(self, "Reseed Complete", f"Imported {rows} seed rows.")
        except Exception as exc:
            QMessageBox.critical(self, "Reseed Failed", str(exc))


class FantasyGroundsSyncPage(QWidget):
    def __init__(self, db_path: Path, refresh_callback):
        super().__init__()
        self.service = FantasyGroundsSyncService(db_path)
        self.refresh_callback = refresh_callback
        self._last_snapshot_stamp = None
        self._importing = False

        layout = adaptive_page_layout(self)
        layout.addWidget(QLabel("<h2>Fantasy Grounds Sync</h2>"))
        intro = QLabel(
            "Fantasy Grounds Unity 5E is the source of truth. Select the campaign folder once, "
            "then export from the Lectern Sync extension. Lectern never writes campaign data back to Fantasy Grounds."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        folder_row = QHBoxLayout()
        self.folder = QLineEdit()
        self.folder.setReadOnly(True)
        self.folder.setPlaceholderText("Select a Fantasy Grounds campaign folder or its lectern-sync folder")
        browse = QPushButton("Select Campaign Folder...")
        browse.clicked.connect(self.select_folder)
        open_folder = QPushButton("Open Handoff Folder")
        open_folder.clicked.connect(self.open_folder)
        folder_row.addWidget(self.folder, 1)
        folder_row.addWidget(browse)
        folder_row.addWidget(open_folder)
        layout.addLayout(folder_row)

        controls = QHBoxLayout()
        self.import_button = QPushButton("Import Now")
        self.import_button.clicked.connect(self.import_now)
        self.reprocess_button = QPushButton("Reprocess Imported Combat Logs")
        self.reprocess_button.clicked.connect(self.reprocess_logs)
        self.clear_import_button = QPushButton("Clear Selected FG Import")
        self.clear_import_button.clicked.connect(self.clear_selected_import)
        self.auto_import = QCheckBox("Automatically import new snapshots")
        self.auto_import.setChecked(self.service.automatic_import_enabled())
        self.auto_import.toggled.connect(self.service.set_automatic_import_enabled)
        controls.addWidget(self.import_button)
        controls.addWidget(self.reprocess_button)
        controls.addWidget(self.clear_import_button)
        controls.addWidget(self.auto_import)
        controls.addStretch()
        controls.addWidget(QLabel("Imported campaign:"))
        self.source_select = QComboBox()
        self.source_select.currentIndexChanged.connect(self.refresh_records)
        controls.addWidget(self.source_select)
        layout.addLayout(controls)

        self.status = QLabel("No Fantasy Grounds snapshot imported yet.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.session_status = QLabel("Encounter session: not reported by the extension.")
        self.session_status.setWordWrap(True)
        layout.addWidget(self.session_status)
        self.counts = QLabel()
        self.counts.setWordWrap(True)
        layout.addWidget(self.counts)

        self.records = QTableWidget()
        self.records.setColumnCount(5)
        self.records.setHorizontalHeaderLabels(["State", "Type", "Name", "Module", "Fantasy Grounds Path"])
        self.records.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.records.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.records, 1)

        steps = QLabel(
            "Run together: (1) load the 5E campaign with Lectern Sync enabled, "
            "(2) select that campaign folder here, (3) enter /lectern-export in Fantasy Grounds, "
            "(4) run /lectern-start Encounter Name before combat, and "
            "(5) run /lectern-end outcome before clearing the Combat Tracker."
        )
        steps.setWordWrap(True)
        layout.addWidget(steps)

        configured = self.service.configured_folder()
        if configured:
            self.folder.setText(str(configured))
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.poll_snapshot)
        self.timer.start()
        self.refresh()

    def select_folder(self):
        initial = str(self.service.configured_folder() or Path.home())
        selected = QFileDialog.getExistingDirectory(self, "Select Fantasy Grounds Campaign Folder", initial)
        if not selected:
            return
        try:
            folder = self.service.configure_folder(Path(selected))
            self.folder.setText(str(folder))
            self._last_snapshot_stamp = None
            self.status.setText(
                f"Handoff folder ready: {folder}. In Fantasy Grounds, enter /lectern-export."
            )
        except Exception as exc:
            QMessageBox.critical(self, "Folder Setup Failed", str(exc))

    def open_folder(self):
        folder = self.service.configured_folder()
        if not folder:
            QMessageBox.information(self, "No Folder Selected", "Select a Fantasy Grounds campaign folder first.")
            return
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def import_now(self, quiet: bool = False):
        if self._importing:
            return
        self._importing = True
        self.import_button.setEnabled(False)
        try:
            result = self.service.import_configured_snapshot()
            count_text = " | ".join(f"{name.title()}: {count}" for name, count in result.counts.items())
            self.status.setText(
                f"{result.message}: {result.campaign_name} | Sequence {result.sequence}"
            )
            self.counts.setText(count_text)
            self.refresh_sources()
            if result.applied:
                self.refresh_callback(result.preferred_encounter_id)
        except FantasyGroundsSyncError as exc:
            self.status.setText(f"Sync error: {exc}")
            if not quiet:
                QMessageBox.warning(self, "Fantasy Grounds Sync", str(exc))
        finally:
            self.import_button.setEnabled(True)
            self._importing = False

    def poll_snapshot(self):
        if not self.auto_import.isChecked() or self._importing:
            return
        path = self.service.snapshot_path()
        if not path or not path.exists():
            return
        try:
            stamp = (path.stat().st_mtime_ns, path.stat().st_size)
        except OSError:
            return
        if stamp == self._last_snapshot_stamp:
            return
        self._last_snapshot_stamp = stamp
        self.import_now(quiet=True)

    def reprocess_logs(self):
        if self._importing:
            return
        preview = self.service.preview_log_reprocessing()
        if preview.total_events == 0:
            QMessageBox.information(
                self,
                "Reprocess Imported Combat Logs",
                "No imported Fantasy Grounds combat events are available to reprocess.",
            )
            return
        prompt = (
            "Lectern will rebuild the linked combat log rows from their preserved Fantasy Grounds event data.\n\n"
            f"Affected encounters: {preview.affected_encounters}\n"
            f"Total events: {preview.total_events}\n"
            f"Improvable events: {preview.improvable_events}\n"
            f"Events with missing source data: {preview.missing_source_events}\n\n"
            "A database backup will be created first. Local and unlinked log rows will not be changed. Continue?"
        )
        if QMessageBox.question(self, "Reprocess Imported Combat Logs", prompt) != QMessageBox.Yes:
            return
        self._importing = True
        self.import_button.setEnabled(False)
        self.reprocess_button.setEnabled(False)
        try:
            result = self.service.reprocess_imported_logs()
            summary = (
                f"Updated: {result.updated}\n"
                f"Unchanged: {result.unchanged}\n"
                f"Incomplete: {result.incomplete}\n"
                f"Failed: {result.failed}\n\n"
                f"Backup: {result.backup_path}"
            )
            self.refresh_callback()
            self.refresh_sources()
            self.status.setText(
                "Historical Fantasy Grounds combat logs reprocessed: "
                f"{result.updated} updated, {result.unchanged} unchanged, "
                f"{result.incomplete} incomplete, {result.failed} failed."
            )
            QMessageBox.information(self, "Reprocessing Complete", summary)
        except FantasyGroundsSyncError as exc:
            self.status.setText(f"Reprocessing error: {exc}")
            QMessageBox.critical(self, "Reprocessing Failed", str(exc))
        finally:
            self.import_button.setEnabled(True)
            self.reprocess_button.setEnabled(True)
            self._importing = False

    def clear_selected_import(self):
        if self._importing:
            return
        source_id = self.source_select.currentData()
        if source_id is None:
            QMessageBox.information(
                self, "Clear Fantasy Grounds Import", "No imported Fantasy Grounds campaign is selected."
            )
            return
        try:
            preview = self.service.preview_clear_imported_data(int(source_id))
        except FantasyGroundsSyncError as exc:
            QMessageBox.warning(self, "Clear Fantasy Grounds Import", str(exc))
            return
        prompt = (
            f"Clear the imported Fantasy Grounds data for {preview.campaign_name}?\n\n"
            f"Campaigns: {preview.campaigns}\n"
            f"Encounters: {preview.encounters}\n"
            f"Combatants: {preview.combatants}\n"
            f"Combat log rows: {preview.combat_log_rows}\n"
            f"Imported players: {preview.players}\n"
            f"Sync records: {preview.external_records}\n\n"
            "A database backup will be created first. Local Lectern campaigns, encounters, and logs are preserved. "
            "Any local encounter attached to the imported campaign is kept and detached from that campaign.\n\n"
            "For a completely fresh test, first run /lectern-reset in Fantasy Grounds. Automatic import will be "
            "turned off after clearing so an older snapshot cannot immediately restore the data. Continue?"
        )
        if QMessageBox.question(self, "Clear Fantasy Grounds Import", prompt) != QMessageBox.Yes:
            return
        self._importing = True
        self.import_button.setEnabled(False)
        self.reprocess_button.setEnabled(False)
        self.clear_import_button.setEnabled(False)
        self.auto_import.setChecked(False)
        try:
            result = self.service.clear_imported_data(int(source_id))
            self._last_snapshot_stamp = None
            self.refresh_callback()
            self.refresh_sources()
            self.status.setText(
                f"Cleared imported Fantasy Grounds data for {result.preview.campaign_name}. Automatic import is off."
            )
            QMessageBox.information(
                self,
                "Fantasy Grounds Import Cleared",
                f"The selected imported campaign, encounters, combatants, logs, players, and sync metadata were cleared.\n\n"
                f"Backup: {result.backup_path}\n\n"
                "When ready, start a new Fantasy Grounds encounter and re-enable automatic import or click Import Now.",
            )
        except FantasyGroundsSyncError as exc:
            self.status.setText(f"Clear error: {exc}")
            QMessageBox.critical(self, "Clear Failed", str(exc))
        finally:
            self.import_button.setEnabled(True)
            self.reprocess_button.setEnabled(True)
            self.clear_import_button.setEnabled(True)
            self._importing = False

    def refresh(self):
        configured = self.service.configured_folder()
        self.folder.setText(str(configured) if configured else "")
        self.refresh_sources()
        extension_status = self.service.read_extension_status()
        if extension_status and not self._importing:
            state = extension_status.get("state", "unknown")
            sequence = extension_status.get("sequence", "-")
            message = extension_status.get("error") or extension_status.get("message") or ""
            self.status.setToolTip(f"Extension state: {state}; sequence: {sequence}; {message}")
            session_state = str(extension_status.get("combat_session_state") or "inactive").title()
            session_name = extension_status.get("combat_session_name")
            session_key = extension_status.get("combat_session_key")
            identity = session_name or session_key or "No encounter"
            self.session_status.setText(f"Encounter session: {session_state} - {identity}")
        elif not extension_status:
            self.session_status.setText("Encounter session: no extension status available.")

    def refresh_sources(self):
        selected = self.source_select.currentData()
        rows = self.service.list_sources()
        self.source_select.blockSignals(True)
        self.source_select.clear()
        for row in rows:
            self.source_select.addItem(f"{row['campaign_name']} ({row['ruleset']})", row["id"])
        if selected is not None:
            index = self.source_select.findData(selected)
            if index >= 0:
                self.source_select.setCurrentIndex(index)
        self.source_select.blockSignals(False)
        if rows:
            current = next((row for row in rows if row["id"] == self.source_select.currentData()), rows[0])
            self.status.setText(
                f"Last imported: {current['campaign_name']} | {current['ruleset']} | "
                f"Sequence {current['last_sequence']} | {current['last_sync_at'] or 'never'}"
            )
        self.refresh_records()

    def refresh_records(self):
        source_id = self.source_select.currentData()
        rows = self.service.list_records(source_id) if source_id else []
        self.records.setRowCount(len(rows))
        totals: dict[str, int] = {}
        for row_index, row in enumerate(rows):
            state = "Stale" if row["is_stale"] else "Current"
            totals[row["record_type"]] = totals.get(row["record_type"], 0) + (0 if row["is_stale"] else 1)
            values = [state, row["record_type"], row["name"], row["module_name"] or "Campaign", row["source_path"]]
            for column, value in enumerate(values):
                self.records.setItem(row_index, column, QTableWidgetItem(str(value)))
        self.records.resizeColumnsToContents()
        if totals:
            self.counts.setText(" | ".join(f"{name.title()}: {count}" for name, count in sorted(totals.items())))


class ErrorLogPage(QWidget):
    def __init__(self, db_path: Path):
        super().__init__()
        self.workflow = DataWorkflowService(db_path)
        layout = adaptive_page_layout(self)
        header = QHBoxLayout()
        header.addWidget(QLabel("<h2>Error Log Viewer</h2>"))
        header.addStretch()
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)
        header.addWidget(refresh)
        layout.addLayout(header)
        self.files = QComboBox()
        self.files.currentIndexChanged.connect(self.load_selected)
        layout.addWidget(self.files)
        self.viewer = QTextEdit()
        self.viewer.setReadOnly(True)
        layout.addWidget(self.viewer)
        self.refresh()

    def refresh(self):
        self.files.blockSignals(True)
        self.files.clear()
        for path in self.workflow.log_files():
            self.files.addItem(str(path.name), str(path))
        self.files.blockSignals(False)
        self.load_selected()

    def load_selected(self):
        path = self.files.currentData()
        if not path:
            self.viewer.setPlainText("No log files found yet.")
            return
        self.viewer.setPlainText(self.workflow.read_log(Path(path)))


class HelpPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = adaptive_page_layout(self)
        header = QHBoxLayout()
        header.addWidget(QLabel("<h2>Help</h2>"))
        header.addStretch()
        self.reload_btn = QPushButton("Reload Help")
        self.reload_btn.clicked.connect(self.load_help)
        header.addWidget(self.reload_btn)
        layout.addLayout(header)

        self.viewer = QTextBrowser()
        self.viewer.setOpenLinks(False)
        self.viewer.anchorClicked.connect(self.open_help_link)
        layout.addWidget(self.viewer)
        self.load_help()

    def help_path(self) -> Path:
        return help_path()

    @staticmethod
    def anchor_name(title: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")

    def add_heading_anchors(self) -> None:
        document = self.viewer.document()
        self.help_anchor_positions: dict[str, int] = {}
        used: dict[str, int] = {}
        block = document.begin()
        while block.isValid():
            if block.blockFormat().headingLevel() > 0:
                base = self.anchor_name(block.text())
                if base:
                    used[base] = used.get(base, 0) + 1
                    anchor = base if used[base] == 1 else f"{base}-{used[base]}"
                    cursor = QTextCursor(block)
                    cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
                    heading_format = cursor.charFormat()
                    heading_format.setAnchorNames([anchor])
                    cursor.mergeCharFormat(heading_format)
                    self.help_anchor_positions[anchor] = block.position()
            block = block.next()

    def open_help_link(self, url: QUrl) -> None:
        anchor = url.fragment()
        if anchor and anchor in getattr(self, "help_anchor_positions", {}):
            block = self.viewer.document().findBlock(self.help_anchor_positions[anchor])
            if block.isValid():
                self.viewer.setTextCursor(QTextCursor(block))
                self.viewer.ensureCursorVisible()
            return
        if url.scheme():
            QDesktopServices.openUrl(url)

    def load_help(self):
        path = self.help_path()
        if path.exists():
            self.viewer.setMarkdown(path.read_text(encoding="utf-8"))
            self.add_heading_anchors()
        else:
            self.viewer.setPlainText(
                "Help file not found. Expected docs/USER_HELP.md. "
                "If running from a packaged build, rebuild the application so docs are included."
            )

class MainWindow(QMainWindow):
    def __init__(self, db_path: Path):
        super().__init__(); self.db_path=db_path; self.repo=Repository(db_path)
        self.setWindowTitle(f"{APP_NAME} - {VERSION}"); self.resize(1400,900); self.setMinimumSize(1100,700)
        app_icon = icon_path()
        if app_icon.exists():
            self.setWindowIcon(QIcon(str(app_icon)))
        root=QWidget(); self.setCentralWidget(root); outer=QHBoxLayout(root)
        self.nav=QListWidget(); self.nav.setMaximumWidth(220); self.nav.setMinimumWidth(170)
        self._watermark_path = watermark_path()
        self.stack=QStackedWidget(); outer.addWidget(self.nav); outer.addWidget(self.stack,1)
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #202124; color: #e8eaed; }
            QWidget#LecternPageContent { background-color: transparent; }
            QListWidget { background-color: #17181b; border-right: 1px solid #3c4043; padding: 6px; }
            QListWidget::item { padding: 8px; border-radius: 4px; }
            QListWidget::item:selected { background-color: #2f3b58; }
            QGroupBox, QTableWidget, QTreeWidget, QTextEdit, QTextBrowser, QLineEdit, QSpinBox, QComboBox { background-color: rgba(32,33,36,220); border: 1px solid #3c4043; border-radius: 4px; }
            QTreeWidget { alternate-background-color: #27292d; }
            QTreeWidget::item { color: #e8eaed; min-height: 28px; padding: 2px 4px; }
            QTreeWidget::item:selected { background-color: #2f3b58; }
            QHeaderView::section { background-color: #2a2c30; color: #e8eaed; border: 0; border-right: 1px solid #3c4043; border-bottom: 1px solid #3c4043; padding: 6px; font-weight: 600; }
            QGroupBox { margin-top: 12px; padding-top: 8px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 10px; padding: 0 4px; }
            QPushButton { background-color: #2f3b58; border: 1px solid #5f6f9f; border-radius: 4px; padding: 6px 10px; }
            QPushButton:hover { background-color: #3b4a70; }
            QTabWidget::pane { border: 1px solid #3c4043; background-color: rgba(32,33,36,220); }
        """)
        self.pages = []
        sections = [
            ("Dashboard", self.dashboard()),
            ("Campaigns", CampaignDashboardPage(self.repo, self.refresh_pages)),
            ("Encounter Builder", EncounterBuilderPage(self.repo, self.refresh_pages)),
            ("Combat Dashboard", CombatDashboardPage(self.repo)),
            ("Players", PlayerManagerPage(self.repo, self.refresh_pages)),
            ("Monster Library", TablePage("Monster Library", self.repo, "monsters")),
            ("Add Monster", MonsterAddPage(self.repo)),
            ("Weapons", TablePage("Weapons", self.repo, "weapons")),
            ("Armor", TablePage("Armor", self.repo, "armor")),
            ("Equipment", TablePage("Equipment", self.repo, "equipment")),
            ("Magic Items", TablePage("Magic Items", self.repo, "magic_items")),
            ("Spells", TablePage("Spells", self.repo, "spells")),
            ("CSV Import/Export", CsvImportExportPage(db_path, self.refresh_pages)),
            ("Fantasy Grounds Sync", FantasyGroundsSyncPage(db_path, self.refresh_pages)),
            ("Data Workflow", DataWorkflowPage(db_path, self.refresh_pages)),
            ("Error Logs", ErrorLogPage(db_path)),
            ("Help", HelpPage()),
        ]
        for name, page in sections:
            self.add_page(name, page)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex); self.nav.setCurrentRow(0)
    def add_page(self, name, widget):
        self.nav.addItem(name)
        self.stack.addWidget(WatermarkedPage(widget, self._watermark_path))
        self.pages.append(widget)
    def dashboard(self):
        w=QWidget(); l=adaptive_page_layout(w)
        self.dashboard_intro=QLabel(
            f"<h1>{APP_NAME}</h1>"
            f"<p><b>{APP_EXPANDED_NAME}</b><br>Version {VERSION}</p>"
            "<p>Lectern is a local-first Windows workspace for preparing, running, and reviewing tabletop campaigns. "
            "Manage player characters and reference libraries, assemble reusable encounters, track initiative and hit points, "
            "record damage, healing, actions, and outcomes, and preserve a structured combat journal for later review.</p>"
            "<p><b>Campaign intelligence:</b> Group encounters into campaigns to review rounds, outcomes, party damage and healing, "
            "critical results, attribution coverage, and leaders across all standard damage types. "
            "<b>Flexible data:</b> Import character PDFs and CSV files, export editable tables, and use built-in backup, restore, and reseed tools.</p>"
            "<p><b>Fantasy Grounds integration:</b> Lectern Sync can import 5E characters, prepared encounters, live Combat Tracker state, "
            "and authoritative combat events while Fantasy Grounds remains the source of truth. Local Lectern encounters remain independent and editable.</p>"
            "<p>Begin with <b>Campaigns</b> and <b>Players</b>, prepare battles in <b>Encounter Builder</b>, run or review them in "
            "<b>Combat Dashboard</b>, and open <b>Help</b> for linked screen-by-screen guidance.</p>"
        )
        self.dashboard_intro.setWordWrap(True); l.addWidget(self.dashboard_intro)
        self.counts=QLabel(); l.addWidget(self.counts)
        l.addWidget(QLabel("<h2>Current Campaigns</h2>"))
        self.dashboard_campaigns=QTableWidget(); self.dashboard_campaigns.setColumnCount(3); self.dashboard_campaigns.setHorizontalHeaderLabels(["Campaign", "Encounters", "Description"])
        l.addWidget(self.dashboard_campaigns,1)
        self.dashboard_campaign_empty=QLabel("No campaigns yet. Open Campaigns to create one."); self.dashboard_campaign_empty.setAlignment(Qt.AlignCenter); l.addWidget(self.dashboard_campaign_empty)
        return w
    def refresh_pages(self, preferred_encounter_id=None):
        self.counts.setText(f"Players: {self.repo.count('players')} | Monsters: {self.repo.count('monsters')} | Encounters: {self.repo.count('encounters')} | Combatants: {self.repo.count('combatants')} | Weapons: {self.repo.count('weapons')} | Armor: {self.repo.count('armor')} | Spells: {self.repo.count('spells')}")
        campaigns=self.repo.list_campaigns_with_counts(); self.dashboard_campaigns.setRowCount(len(campaigns)); self.dashboard_campaign_empty.setVisible(not campaigns); self.dashboard_campaigns.setVisible(bool(campaigns))
        for r,row in enumerate(campaigns):
            for c,value in enumerate([row['name'],row['encounter_count'],row['description'] or '']): self.dashboard_campaigns.setItem(r,c,QTableWidgetItem(str(value)))
        self.dashboard_campaigns.resizeColumnsToContents()
        for p in self.pages:
            if preferred_encounter_id is not None and hasattr(p,'select_encounter_id'):
                p.select_encounter_id(preferred_encounter_id)
            if hasattr(p,'refresh'): p.refresh()
    def showEvent(self, event):
        super().showEvent(event); self.refresh_pages()
