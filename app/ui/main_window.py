from __future__ import annotations
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QStackedWidget, QFileDialog, QTableWidget, QTableWidgetItem,
    QLineEdit, QFormLayout, QSpinBox, QMessageBox, QComboBox, QCompleter,
    QGroupBox, QTextEdit, QTextBrowser, QListWidgetItem, QGridLayout, QScrollArea, QSizePolicy, QTabWidget, QCheckBox
)
from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtGui import QPainter, QPixmap, QIcon
from ..database.repositories import Repository
from ..importers.spreadsheet_importer import SpreadsheetImporter
from ..importers.csv_transfer import CsvTransferService, CSV_TABLES
from ..services.data_workflow import DataWorkflowService
from ..version import APP_NAME, VERSION
from ..paths import icon_path, watermark_path, help_path


class WatermarkedPage(QWidget):
    """Wrap one application screen with a centered, scale-aware watermark."""

    def __init__(self, content: QWidget, image_path: Path, parent=None):
        super().__init__(parent)
        self._source = QPixmap(str(image_path)) if image_path.exists() else QPixmap()
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
        painter.setOpacity(0.12)
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

class TablePage(QWidget):
    def __init__(self, title: str, repo: Repository, table: str):
        super().__init__(); self.repo=repo; self.table=table
        layout=QVBoxLayout(self); layout.addWidget(QLabel(f"<h2>{title}</h2>"))
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
        layout=QVBoxLayout(self); layout.addWidget(QLabel("<h2>Spreadsheet Import</h2>"))
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
        self.current_player_id = row['id'] if row else None
        if not row: self.clear_form(); return
        self.name.setText(row['name'] or ''); self.player_name.setText(row['player_name'] if 'player_name' in row.keys() else '')
        self.species.setCurrentText(row['species'] or ''); self.class_name.setCurrentText(row['class_name'] or ''); self.subclass.setCurrentText(row['subclass'] or ''); self.background.setCurrentText(row['background'] or '')
        self.level.setValue(row['level'] or 1); self.portrait_path.setText(row['portrait_path'] if 'portrait_path' in row.keys() and row['portrait_path'] else '')
        feats=self._split(row['feats'] if 'feats' in row.keys() else '')
        self.feat_1.setCurrentText(feats[0] if len(feats)>0 else ''); self.feat_2.setCurrentText(feats[1] if len(feats)>1 else ''); self.feat_3.setCurrentText(feats[2] if len(feats)>2 else '')
        self.weapon.setCurrentText(row['equipped_weapon'] if 'equipped_weapon' in row.keys() and row['equipped_weapon'] else ''); self.armor.setCurrentText(row['equipped_armor'] if 'equipped_armor' in row.keys() and row['equipped_armor'] else '')
        self.spellcasting_ability.setCurrentText(row['spellcasting_ability'] if 'spellcasting_ability' in row.keys() and row['spellcasting_ability'] else '')
        self.equipment.setPlainText(row['equipment'] if 'equipment' in row.keys() and row['equipment'] else ''); self.inventory.setPlainText(row['inventory'] if 'inventory' in row.keys() and row['inventory'] else '')
        for coin in ['cp','sp','ep','gp','pp']: self.currency[coin].setValue(row[f'currency_{coin}'] if f'currency_{coin}' in row.keys() and row[f'currency_{coin}'] is not None else 0)
        self.ac.setValue(row['armor_class'] or 10); self.max_hp.setValue(row['max_hp'] or 1); self.current_hp.setValue(row['current_hp'] or row['max_hp'] or 1)
        for key,_ in ABILITY_LABELS: self._set_ability_values(key,row)
        profs=set(self._split(row['skill_proficiencies'] if 'skill_proficiencies' in row.keys() else '')); experts=set(self._split(row['skill_expertise'] if 'skill_expertise' in row.keys() else '')); saves=set(self._split(row['saving_throw_proficiencies'] if 'saving_throw_proficiencies' in row.keys() else ''))
        for skill,(_,prof,expert,_) in self.skill_boxes.items(): prof.setChecked(skill in profs); expert.setChecked(skill in experts)
        for key,(prof,_) in self.save_boxes.items(): prof.setChecked(key in saves)
        self.update_ability_totals(); self.init_mod.setValue(row['initiative_mod'] if row['initiative_mod'] is not None else self._mod('dex'))
        self.notes.setPlainText(row['notes'] or '')

    def clear_form(self):
        self.current_player_id=None; self.name.clear(); self.player_name.clear(); self.portrait_path.clear()
        for combo in [self.species,self.class_name,self.subclass,self.background,self.feat_1,self.feat_2,self.feat_3,self.weapon,self.armor,self.spellcasting_ability]: combo.setCurrentText('')
        self.level.setValue(1); self.equipment.clear(); self.inventory.clear(); self.notes.clear(); self.ac.setValue(10); self.max_hp.setValue(1); self.current_hp.setValue(1)
        for coin in self.currency.values(): coin.setValue(0)
        for key,_ in ABILITY_LABELS: self.ability_widgets[key]['base'].setValue(10); self.ability_widgets[key]['race'].setValue(0); self.ability_widgets[key]['feat'].setValue(0)
        for _,prof,expert,_ in self.skill_boxes.values(): prof.setChecked(False); expert.setChecked(False)
        for prof,_ in self.save_boxes.values(): prof.setChecked(False)
        self.update_ability_totals(); self.name.setFocus()

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
        layout = QVBoxLayout(self)
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
        edit_btn = QPushButton("Edit Selected")
        dup_btn = QPushButton("Duplicate")
        del_btn = QPushButton("Delete")
        refresh_btn = QPushButton("Refresh")
        new_btn.clicked.connect(self.new_player)
        edit_btn.clicked.connect(self.edit_selected)
        dup_btn.clicked.connect(self.duplicate_selected)
        del_btn.clicked.connect(self.delete_selected)
        refresh_btn.clicked.connect(self.refresh)
        for b in [new_btn, edit_btn, dup_btn, del_btn, refresh_btn]:
            toolbar.addWidget(b)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget()
        self.table.setColumnCount(16)
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
                self.table.setItem(r, c, item)
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
        if row:
            self.editor.load_player(row)

    def new_player(self):
        self.table.clearSelection()
        self.editor.clear_form()

    def edit_selected(self):
        row = self.selected_player_row()
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
        layout=QVBoxLayout(self); layout.addWidget(QLabel("<h2>Add / Edit Monster</h2>"))
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
        root=QVBoxLayout(self); root.addWidget(QLabel("<h2>Encounter Builder</h2>"))
        top=QHBoxLayout(); self.new_name=QLineEdit(); self.new_name.setPlaceholderText("Encounter name, e.g. Goblin Ambush")
        new_btn=QPushButton("New / Select Encounter"); new_btn.clicked.connect(self.create_encounter)
        self.encounters=QComboBox(); self.encounters.currentIndexChanged.connect(self.select_encounter)
        top.addWidget(self.new_name); top.addWidget(new_btn); top.addWidget(QLabel("Active:")); top.addWidget(self.encounters); root.addLayout(top)
        body=QHBoxLayout(); root.addLayout(body)
        monster_box=QGroupBox("Monster Browser"); mb=QVBoxLayout(monster_box); self.monster_search=QComboBox(); self.monster_search.setEditable(True)
        self.monster_qty=QSpinBox(); self.monster_qty.setRange(1,50); add_m=QPushButton("Add Monster(s)"); add_m.clicked.connect(self.add_monsters)
        mb.addWidget(QLabel("Search/type monster name")); mb.addWidget(self.monster_search); mb.addWidget(QLabel("Quantity")); mb.addWidget(self.monster_qty); mb.addWidget(add_m); body.addWidget(monster_box)
        player_box=QGroupBox("Players"); pb=QVBoxLayout(player_box); self.player_list=QListWidget(); add_p=QPushButton("Add Selected Player(s)"); add_p.clicked.connect(self.add_players); pb.addWidget(self.player_list); pb.addWidget(add_p); body.addWidget(player_box)
        cart_box=QGroupBox("Encounter Combatants"); cb=QVBoxLayout(cart_box); self.combatants=QTableWidget(); self.combatants.setColumnCount(6); self.combatants.setHorizontalHeaderLabels(["Name","Init","AC","HP","Max HP","Type"]); cb.addWidget(self.combatants)
        row=QHBoxLayout(); roll=QPushButton("Roll Initiative / Start"); roll.clicked.connect(self.roll_init); remove=QPushButton("Remove Selected"); remove.clicked.connect(self.remove_selected); row.addWidget(roll); row.addWidget(remove); cb.addLayout(row); body.addWidget(cart_box,2)
        self.refresh()
    def refresh(self):
        self.monsters={r['name']: r for r in self.repo.list_monsters()}; self.players={r['name']: r for r in self.repo.list_players()}
        self.monster_search.blockSignals(True); self.monster_search.clear(); self.monster_search.addItems(sorted(self.monsters)); self.monster_search.blockSignals(False)
        comp=QCompleter(sorted(self.monsters)); comp.setCaseSensitivity(Qt.CaseInsensitive); comp.setFilterMode(Qt.MatchContains); self.monster_search.setCompleter(comp)
        self.player_list.clear()
        for name in sorted(self.players):
            item=QListWidgetItem(name); item.setFlags(item.flags() | Qt.ItemIsUserCheckable); item.setCheckState(Qt.Unchecked); self.player_list.addItem(item)
        self.encounters.blockSignals(True); self.encounters.clear()
        for e in self.repo.list_encounters(): self.encounters.addItem(e['name'], e['id'])
        self.encounters.blockSignals(False)
        if self.current_encounter_id is None and self.encounters.count(): self.current_encounter_id=self.encounters.itemData(0)
        self.refresh_combatants()
    def create_encounter(self):
        name=self.new_name.text().strip() or "New Encounter"
        self.current_encounter_id=self.repo.create_encounter(name); self.new_name.clear(); self.refresh(); self.refresh_callback()
    def select_encounter(self):
        self.current_encounter_id=self.encounters.currentData(); self.refresh_combatants()
    def add_monsters(self):
        if not self.current_encounter_id: self.create_encounter()
        row=self.monsters.get(self.monster_search.currentText())
        if not row: QMessageBox.warning(self,"Monster Not Found","Select a monster from the imported library."); return
        for _ in range(self.monster_qty.value()): self.repo.add_combatant_from_monster(self.current_encounter_id, row['id'])
        self.refresh_combatants(); self.refresh_callback()
    def add_players(self):
        if not self.current_encounter_id: self.create_encounter()
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
        self.combatants.resizeColumnsToContents()
    def selected_combatant_id(self):
        row=self.combatants.currentRow()
        if row < 0 or not self.combatants.item(row,0): return None
        return self.combatants.item(row,0).data(Qt.UserRole)
    def remove_selected(self):
        cid=self.selected_combatant_id()
        if cid: self.repo.remove_combatant(cid); self.refresh_combatants(); self.refresh_callback()
    def roll_init(self):
        if not self.current_encounter_id: return
        self.repo.roll_initiative(self.current_encounter_id); self.refresh_combatants(); self.refresh_callback(); QMessageBox.information(self,"Combat Started","Initiative rolled. Open Combat Dashboard to run turns.")

class CombatDashboardPage(QWidget):
    def __init__(self, repo: Repository):
        super().__init__(); self.repo=repo; self.current_encounter_id=None
        root=QVBoxLayout(self); root.addWidget(QLabel("<h2>Combat Dashboard</h2>"))
        top=QHBoxLayout(); self.encounters=QComboBox(); self.encounters.currentIndexChanged.connect(self.select_encounter); top.addWidget(QLabel("Encounter:")); top.addWidget(self.encounters)
        self.round_label=QLabel("Round - | Active: -"); top.addWidget(self.round_label); root.addLayout(top)
        self.order=QTableWidget(); self.order.setColumnCount(6); self.order.setHorizontalHeaderLabels(["Turn","Name","Init","AC","HP","Max"]); root.addWidget(self.order)
        buttons=QHBoxLayout(); prev=QPushButton("Previous Turn"); prev.clicked.connect(self.prev_turn); nxt=QPushButton("Next / End Turn"); nxt.clicked.connect(self.next_turn); dmg=QPushButton("Apply Damage"); dmg.clicked.connect(lambda:self.adjust_hp(-abs(self.hp_delta.value()), "Damage")); heal=QPushButton("Apply Healing"); heal.clicked.connect(lambda:self.adjust_hp(abs(self.hp_delta.value()), "Healing")); self.hp_delta=QSpinBox(); self.hp_delta.setRange(0,9999); self.hp_delta.setValue(1)
        for w in [prev,nxt,QLabel("Amount"),self.hp_delta,dmg,heal]: buttons.addWidget(w)
        root.addLayout(buttons)
        logrow=QHBoxLayout(); self.action=QComboBox(); self.action.addItems(["Attack","Spell","Save","Condition","Reaction","Lair Action","Note"]); self.details=QLineEdit(); self.details.setPlaceholderText("Action details"); addlog=QPushButton("Log Action"); addlog.clicked.connect(self.log_action); logrow.addWidget(self.action); logrow.addWidget(self.details); logrow.addWidget(addlog); root.addLayout(logrow)
        self.log=QTextEdit(); self.log.setReadOnly(True); root.addWidget(self.log); self.refresh()
    def refresh(self):
        self.encounters.blockSignals(True); self.encounters.clear()
        for e in self.repo.list_encounters(): self.encounters.addItem(e['name'], e['id'])
        self.encounters.blockSignals(False)
        if self.current_encounter_id is None and self.encounters.count(): self.current_encounter_id=self.encounters.itemData(0)
        self.refresh_board()
    def select_encounter(self): self.current_encounter_id=self.encounters.currentData(); self.refresh_board()
    def rows(self): return self.repo.list_combatants(self.current_encounter_id) if self.current_encounter_id else []
    def refresh_board(self):
        rows=self.rows(); enc=self.repo.get_encounter(self.current_encounter_id) if self.current_encounter_id else None; active=(enc['active_index'] if enc else 0) or 0
        active_name=rows[active]['name'] if rows and active < len(rows) else '-'; self.round_label.setText(f"Round {enc['round'] if enc else '-'} | Active: {active_name}")
        self.order.setRowCount(len(rows))
        for r,row in enumerate(rows):
            vals=["▶" if r==active else "", row['name'], row['initiative'], row['armor_class'], row['current_hp'], row['max_hp']]
            for c,v in enumerate(vals): self.order.setItem(r,c,QTableWidgetItem(str(v if v is not None else "")))
            self.order.item(r,1).setData(Qt.UserRole,row['id'])
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
        new=max(0,min(row['max_hp'] or 1,(row['current_hp'] or 0)+delta)); self.repo.update_combatant_hp(cid,new); self.repo.log_turn(self.current_encounter_id,name,label,f"{label}: {abs(delta)}; HP now {new}/{row['max_hp']}"); self.refresh_board()
    def log_action(self):
        cid,name=self.selected_id_name(); actor=name or "Encounter"; self.repo.log_turn(self.current_encounter_id,actor,self.action.currentText(),self.details.text()); self.details.clear(); self.refresh_log()
    def next_turn(self):
        if self.current_encounter_id: self.repo.next_turn(self.current_encounter_id); self.refresh_board()
    def prev_turn(self):
        if self.current_encounter_id: self.repo.previous_turn(self.current_encounter_id); self.refresh_board()
    def refresh_log(self):
        if not self.current_encounter_id: self.log.clear(); return
        lines=[]
        for row in self.repo.list_turn_log(self.current_encounter_id)[:100]: lines.append(f"R{row['round']} | {row['actor']} | {row['action_type']} | {row['details']}")
        self.log.setPlainText("\n".join(lines))


class CsvImportExportPage(QWidget):
    def __init__(self, db_path: Path, refresh_callback):
        super().__init__()
        self.db_path = db_path
        self.repo = Repository(db_path)
        self.refresh_callback = refresh_callback
        self.csv = CsvTransferService(db_path)
        layout = QVBoxLayout(self)
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
        layout.addStretch()
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
        layout = QVBoxLayout(self)
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


class ErrorLogPage(QWidget):
    def __init__(self, db_path: Path):
        super().__init__()
        self.workflow = DataWorkflowService(db_path)
        layout = QVBoxLayout(self)
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
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addWidget(QLabel("<h2>Help</h2>"))
        header.addStretch()
        self.reload_btn = QPushButton("Reload Help")
        self.reload_btn.clicked.connect(self.load_help)
        header.addWidget(self.reload_btn)
        layout.addLayout(header)

        self.viewer = QTextBrowser()
        self.viewer.setOpenExternalLinks(True)
        layout.addWidget(self.viewer)
        self.load_help()

    def help_path(self) -> Path:
        return help_path()

    def load_help(self):
        path = self.help_path()
        if path.exists():
            self.viewer.setMarkdown(path.read_text(encoding="utf-8"))
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
            QGroupBox, QTableWidget, QTextEdit, QTextBrowser, QLineEdit, QSpinBox, QComboBox { background-color: rgba(32,33,36,220); border: 1px solid #3c4043; border-radius: 4px; }
            QPushButton { background-color: #2f3b58; border: 1px solid #5f6f9f; border-radius: 4px; padding: 6px 10px; }
            QPushButton:hover { background-color: #3b4a70; }
            QTabWidget::pane { border: 1px solid #3c4043; background-color: rgba(32,33,36,220); }
        """)
        self.pages=[]; self.add_page("Dashboard", self.dashboard()); self.add_page("Encounter Builder", EncounterBuilderPage(self.repo, self.refresh_pages)); self.add_page("Combat Dashboard", CombatDashboardPage(self.repo)); self.add_page("Players", PlayerManagerPage(self.repo, self.refresh_pages)); self.add_page("Monster Library", TablePage("Monster Library", self.repo, "monsters")); self.add_page("Add Monster", MonsterAddPage(self.repo)); self.add_page("Weapons", TablePage("Weapons", self.repo, "weapons")); self.add_page("Armor", TablePage("Armor", self.repo, "armor")); self.add_page("Equipment", TablePage("Equipment", self.repo, "equipment")); self.add_page("Magic Items", TablePage("Magic Items", self.repo, "magic_items")); self.add_page("Spells", TablePage("Spells", self.repo, "spells")); self.add_page("Workbook Import", ImportPage(db_path, self.refresh_pages)); self.add_page("CSV Import/Export", CsvImportExportPage(db_path, self.refresh_pages)); self.add_page("Data Workflow", DataWorkflowPage(db_path, self.refresh_pages)); self.add_page("Error Logs", ErrorLogPage(db_path)); self.add_page("Help", HelpPage())
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex); self.nav.setCurrentRow(0)
    def add_page(self, name, widget):
        self.nav.addItem(name)
        self.stack.addWidget(WatermarkedPage(widget, self._watermark_path))
        self.pages.append(widget)
    def dashboard(self):
        w=QWidget(); l=QVBoxLayout(w); l.addWidget(QLabel(f"<h1>{APP_NAME}</h1><p>Version {VERSION}</p><p>Use Encounter Builder to create encounters, add PCs/monsters, roll initiative, then run combat from Combat Dashboard.</p>")); self.counts=QLabel(); l.addWidget(self.counts); l.addStretch(); return w
    def refresh_pages(self):
        self.counts.setText(f"Players: {self.repo.count('players')} | Monsters: {self.repo.count('monsters')} | Encounters: {self.repo.count('encounters')} | Combatants: {self.repo.count('combatants')} | Weapons: {self.repo.count('weapons')} | Armor: {self.repo.count('armor')} | Spells: {self.repo.count('spells')}")
        for p in self.pages:
            if hasattr(p,'refresh'): p.refresh()
    def showEvent(self, event):
        super().showEvent(event); self.refresh_pages()
