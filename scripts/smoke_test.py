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
