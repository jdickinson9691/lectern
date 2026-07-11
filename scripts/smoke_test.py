from pathlib import Path
from tempfile import mkdtemp
import shutil
import sqlite3
import gc
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database.schema import initialize_database
from app.importers.spreadsheet_importer import SpreadsheetImporter
from app.database.repositories import Repository
from app.importers.csv_transfer import CsvTransferService
from app.services.data_workflow import DataWorkflowService
from app.importers.monster_catalog import import_monster_catalog
from app.importers.character_pdf import CharacterPdfImporter
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter

SEED = ROOT / 'seeds' / 'dnd_5e_combat_tracker_v5_clean.xlsx'

temp_dir = Path(mkdtemp(prefix='campaign_manager_smoke_'))
try:
    db = temp_dir / 'test.db'
    initialize_database(db)
    rows = SpreadsheetImporter(db).import_file(SEED)
    repo = Repository(db)
    assert rows > 100, f'Expected substantial seed import, imported {rows}'
    assert repo.count('monsters') >= 10, f"Monster seed missing: {repo.count('monsters')}"
    assert repo.count('weapons') >= 10, f"Weapon seed missing: {repo.count('weapons')}"
    assert repo.count('armor') >= 5, f"Armor seed missing: {repo.count('armor')}"
    assert repo.count('equipment') >= 10, f"Equipment seed missing: {repo.count('equipment')}"
    assert repo.count('magic_items') >= 10, f"Magic item seed missing: {repo.count('magic_items')}"
    assert repo.count('spells') >= 10, f"Spell seed missing: {repo.count('spells')}"
    assert 'Increase one ability score' in repo.get_rule_description('Ability Score Improvement', 'feat'), 'Feat SRD description lookup failed'
    refreshed_rules = SpreadsheetImporter(db).import_rules_only(SEED)
    assert refreshed_rules > 10, 'SRD-only rules refresh failed'
    catalog_rows = import_monster_catalog(db, ROOT / 'seeds' / 'monsters.csv')
    assert catalog_rows == 4148, f'Expected 4148 monster catalog rows, imported {catalog_rows}'
    assert repo.count('monsters') >= 4189, f"Expanded monster catalog missing: {repo.count('monsters')}"
    repo.upsert_player({'name':'Smoke Test Hero','species':'Human','class_name':'Fighter','subclass':'Champion','background':'Soldier','level':5,'armor_class':16,'max_hp':44,'current_hp':44,'initiative_mod':3,'str_base':15,'dex_base':14,'con_base':13,'int_base':10,'wis_base':12,'cha_base':8,'str_race_bonus':1,'dex_race_bonus':0,'con_race_bonus':0,'int_race_bonus':0,'wis_race_bonus':0,'cha_race_bonus':0,'str_feat_bonus':1,'dex_feat_bonus':1,'con_feat_bonus':0,'int_feat_bonus':0,'wis_feat_bonus':0,'cha_feat_bonus':0,'feats':'Grappler','equipped_weapon':'Longsword','equipped_armor':'Chain Mail','equipment':'Rope, Torches, Rations','notes':'smoke test','player_name':'QA Tester','skill_proficiencies':'Perception; Stealth','skill_expertise':'Perception','saving_throw_proficiencies':'str; con','inventory':'Backpack, bedroll','currency_cp':1,'currency_sp':2,'currency_ep':3,'currency_gp':50,'currency_pp':4,'portrait_path':'','spellcasting_ability':'Wisdom'})
    assert repo.count('players') == 1, 'Player create failed'
    player = repo.list_players()[0]
    assert player['name'] == 'Smoke Test Hero', 'Player list failed'
    assert player['str_total'] == 17 and player['str_mod'] == 3, 'Strength total/mod calculation failed'
    assert player['dex_total'] == 15 and player['dex_mod'] == 2, 'Dexterity total/mod calculation failed'
    assert player['feats'] == 'Grappler', 'Player feats field failed'
    assert player['equipped_weapon'] == 'Longsword', 'Player weapon field failed'
    assert player['equipped_armor'] == 'Chain Mail', 'Player armor field failed'
    assert 'Rope' in player['equipment'], 'Player equipment field failed'
    assert player['player_name'] == 'QA Tester', 'Player name field failed'
    assert 'Perception' in player['skill_proficiencies'] and 'Perception' in player['skill_expertise'], 'Player skill proficiency/expertise failed'
    assert 'str' in player['saving_throw_proficiencies'], 'Player saving throw proficiency failed'
    assert player['currency_gp'] == 50 and 'Backpack' in player['inventory'], 'Player inventory/currency failed'
    assert player['spellcasting_ability'] == 'Wisdom', 'Player spellcasting ability failed'
    repo.upsert_player({'name':'Second Hero','species':'Elf','class_name':'Wizard','level':3,'armor_class':12,'max_hp':18,'current_hp':9,'initiative_mod':2,'str_base':8,'dex_base':14,'con_base':12,'int_base':17,'wis_base':13,'cha_base':10,'feats':'Alert','equipment':'Spellbook','inventory':'Ink','notes':'second player'})
    first_player=repo.get_player_by_id(player['id']); second_player=next(row for row in repo.list_players() if row['name']=='Second Hero')
    assert first_player['class_name']=='Fighter' and second_player['class_name']=='Wizard' and second_player['current_hp']==9, 'Selected player row retrieval failed'
    csv_service = CsvTransferService(db)
    players_csv = temp_dir / 'players.csv'
    exported = csv_service.export_table('players', players_csv)
    assert exported >= 1 and players_csv.exists(), 'CSV player export failed'
    csv_text = players_csv.read_text(encoding='utf-8-sig')
    csv_text = csv_text.replace('Smoke Test Hero', 'Smoke Test Hero CSV')
    players_csv.write_text(csv_text, encoding='utf-8-sig')
    preview = csv_service.preview_table('players', players_csv)
    assert preview and any(r['status'] in {'New', 'Modified'} for r in preview), 'CSV preview failed'
    imported = csv_service.import_table('players', players_csv)
    assert imported >= 1, 'CSV player import failed'
    assert any(r['name'] == 'Smoke Test Hero CSV' for r in repo.list_players()), 'CSV import did not create/update player'
    all_dir = temp_dir / 'csv_export_all'
    results = csv_service.export_all(all_dir)
    assert results.get('monsters', 0) >= 10 and (all_dir / 'monsters.csv').exists(), 'CSV export all failed'
    dup_id = repo.duplicate_player(player['id'])
    assert dup_id is not None and repo.count('players') >= 3, 'Player duplicate failed'
    repo.delete_player(dup_id)
    assert repo.count('players') >= 2, 'Player delete failed'
    campaign_id = repo.create_campaign('Smoke Test Campaign', 'Campaign aggregation test')
    encounter_id = repo.create_encounter('Smoke Test Encounter')
    repo.assign_encounter_to_campaign(encounter_id, campaign_id)
    repo.log_turn(encounter_id, 'Smoke Test Hero', 'Damage', 'Damage: 12; HP now 8/20')
    repo.log_turn(encounter_id, 'Smoke Test Hero', 'Healing', 'Healing: 5; HP now 13/20')
    repo.complete_encounter(encounter_id, 'Victory')
    campaign = repo.campaign_summary(campaign_id)
    assert campaign['total'] == 1 and campaign['completed'] == 1, 'Campaign encounter totals failed'
    assert campaign['victories'] == 1, 'Campaign outcome aggregation failed'
    assert campaign['actions'] == 2 and campaign['damage'] == 12 and campaign['healing'] == 5, 'Campaign combat-log aggregation failed'
    history = repo.campaign_encounters(campaign_id)
    assert len(history) == 1 and history[0]['action_count'] == 2, 'Campaign encounter history failed'
    second_encounter_id = repo.create_encounter('Smoke Test Encounter')
    assert second_encounter_id != encounter_id, 'New encounter reused an existing encounter'
    assert repo.get_encounter(second_encounter_id)['name'] == 'Smoke Test Encounter 2', 'Duplicate encounter name was not made unique'
    assert repo.list_combatants(second_encounter_id) == [], 'New encounter inherited combatants'
    dashboard_campaigns = repo.list_campaigns_with_counts()
    assert len(dashboard_campaigns) == 1 and dashboard_campaigns[0]['encounter_count'] == 1, 'Dashboard campaign encounter count failed'
    character_pdf = temp_dir / 'character.pdf'
    pdf = canvas.Canvas(str(character_pdf))
    for index, (field, value) in enumerate([
        ('CharacterName', 'PDF Test Hero'), ('ClassLevel', 'Fighter 5'), ('Race', 'Dwarf'),
        ('AC', '17'), ('HPMax', '44'), ('STR', '16'), ('DEX', '14'),
        ('AthleticsProf', 'P'), ('PerceptionProf', 'E'), ('StrProf', 'X'),
        ('Eq Name0', 'Chain Mail'), ('Eq Qty0', '1'), ('Eq Weight0', '55 lb.'),
        ('Eq Name1', 'Longsword'), ('Eq Qty1', '1'), ('Wpn Name', 'Longsword'),
        ('spellCastingAbility0', 'INT'), ('FeaturesTraits1', '=== FEATS ===\n\n* Alert - SRD\nDetails\n\n* Skilled - SRD\nDetails'),
    ]):
        pdf.acroForm.textfield(name=field, value=value, x=72, y=740-(index*32), width=220, height=20)
    pdf.showPage(); pdf.save()
    pdf_result = CharacterPdfImporter().extract(character_pdf)['data']
    assert pdf_result['name'] == 'PDF Test Hero' and pdf_result['class_name'] == 'Fighter' and pdf_result['level'] == 5, 'Character PDF identity import failed'
    assert pdf_result['armor_class'] == 17 and pdf_result['max_hp'] == 44 and pdf_result['str_base'] == 16, 'Character PDF statistics import failed'
    assert pdf_result['skill_proficiencies'] == 'Athletics; Perception' and pdf_result['skill_expertise'] == 'Perception', 'Character PDF skill proficiency import failed'
    assert pdf_result['saving_throw_proficiencies'] == 'str', 'Character PDF saving throw import failed'
    assert pdf_result['equipped_weapon'] == 'Longsword' and pdf_result['equipped_armor'] == 'Chain Mail', 'Character PDF equipped item import failed'
    assert pdf_result['spellcasting_ability'] == 'Intelligence' and pdf_result['feats'] == 'Alert; Skilled', 'Character PDF feat/spellcasting import failed'
    assert 'Chain Mail' in pdf_result['inventory'] and 'Longsword' in pdf_result['inventory'], 'Character PDF inventory import failed'
    widget_pdf = temp_dir / 'character_widgets_only.pdf'
    reader = PdfReader(str(character_pdf)); writer = PdfWriter(); writer.clone_document_from_reader(reader)
    if '/AcroForm' in writer._root_object: del writer._root_object['/AcroForm']
    with widget_pdf.open('wb') as output: writer.write(output)
    widget_result = CharacterPdfImporter().extract(widget_pdf)['data']
    assert widget_result['name'] == 'PDF Test Hero' and widget_result['species'] == 'Dwarf', 'Page-widget PDF fallback failed'
    repo.upsert_player(widget_result)
    imported_pdf_player = next(row for row in repo.list_players() if row['name'] == 'PDF Test Hero')
    assert imported_pdf_player['class_name'] == 'Fighter' and imported_pdf_player['armor_class'] == 17, 'Character PDF database import failed'
    assert imported_pdf_player['currency_gp'] == 0 and isinstance(imported_pdf_player['currency_gp'], int), 'Character PDF numeric defaults failed'
    workflow = DataWorkflowService(db)
    backup_path = workflow.backup_database(temp_dir / 'backup.db')
    assert backup_path.exists(), 'Database backup failed'
    workflow.restore_database(backup_path)
    assert db.exists(), 'Database restore failed'
    sqlite3.connect(db).close()
    print('Smoke test passed: seeded database tables populated.')
finally:
    gc.collect()
    shutil.rmtree(temp_dir, ignore_errors=True)
