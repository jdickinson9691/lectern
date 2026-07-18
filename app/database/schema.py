from __future__ import annotations
import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS players (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL UNIQUE,
 species TEXT, class_name TEXT, subclass TEXT, background TEXT,
 level INTEGER DEFAULT 1, armor_class INTEGER DEFAULT 10,
 max_hp INTEGER DEFAULT 1, current_hp INTEGER DEFAULT 1,
 initiative_mod INTEGER DEFAULT 0,
 str_base INTEGER DEFAULT 10, dex_base INTEGER DEFAULT 10, con_base INTEGER DEFAULT 10, int_base INTEGER DEFAULT 10, wis_base INTEGER DEFAULT 10, cha_base INTEGER DEFAULT 10,
 str_race_bonus INTEGER DEFAULT 0, dex_race_bonus INTEGER DEFAULT 0, con_race_bonus INTEGER DEFAULT 0, int_race_bonus INTEGER DEFAULT 0, wis_race_bonus INTEGER DEFAULT 0, cha_race_bonus INTEGER DEFAULT 0,
 str_feat_bonus INTEGER DEFAULT 0, dex_feat_bonus INTEGER DEFAULT 0, con_feat_bonus INTEGER DEFAULT 0, int_feat_bonus INTEGER DEFAULT 0, wis_feat_bonus INTEGER DEFAULT 0, cha_feat_bonus INTEGER DEFAULT 0,
 str_total INTEGER DEFAULT 10, dex_total INTEGER DEFAULT 10, con_total INTEGER DEFAULT 10, int_total INTEGER DEFAULT 10, wis_total INTEGER DEFAULT 10, cha_total INTEGER DEFAULT 10,
 str_mod INTEGER DEFAULT 0, dex_mod INTEGER DEFAULT 0, con_mod INTEGER DEFAULT 0, int_mod INTEGER DEFAULT 0, wis_mod INTEGER DEFAULT 0, cha_mod INTEGER DEFAULT 0,
 feats TEXT DEFAULT '',
 equipped_weapon TEXT DEFAULT '', equipped_armor TEXT DEFAULT '', equipment TEXT DEFAULT '',
 notes TEXT DEFAULT '',
 player_name TEXT DEFAULT '',
 skill_proficiencies TEXT DEFAULT '', skill_expertise TEXT DEFAULT '', saving_throw_proficiencies TEXT DEFAULT '',
 inventory TEXT DEFAULT '', currency_cp INTEGER DEFAULT 0, currency_sp INTEGER DEFAULT 0, currency_ep INTEGER DEFAULT 0, currency_gp INTEGER DEFAULT 0, currency_pp INTEGER DEFAULT 0,
 portrait_path TEXT DEFAULT '', spellcasting_ability TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS monsters (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL UNIQUE,
 size TEXT, type TEXT, alignment TEXT,
 armor_class INTEGER DEFAULT 10, hit_points INTEGER DEFAULT 1,
 speed TEXT, challenge_rating TEXT, xp INTEGER DEFAULT 0,
 str_score INTEGER, dex_score INTEGER, con_score INTEGER, int_score INTEGER, wis_score INTEGER, cha_score INTEGER,
 source TEXT DEFAULT 'import', notes TEXT DEFAULT '',
 player_name TEXT DEFAULT '',
 skill_proficiencies TEXT DEFAULT '', skill_expertise TEXT DEFAULT '', saving_throw_proficiencies TEXT DEFAULT '',
 inventory TEXT DEFAULT '', currency_cp INTEGER DEFAULT 0, currency_sp INTEGER DEFAULT 0, currency_ep INTEGER DEFAULT 0, currency_gp INTEGER DEFAULT 0, currency_pp INTEGER DEFAULT 0,
 portrait_path TEXT DEFAULT '', spellcasting_ability TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS encounters (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL UNIQUE,
 status TEXT DEFAULT 'draft', round INTEGER DEFAULT 1,
 active_index INTEGER DEFAULT 0,
 campaign_id INTEGER,
 outcome TEXT DEFAULT '',
 completed_at TEXT
);
CREATE TABLE IF NOT EXISTS campaigns (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, description TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS combatants (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 encounter_id INTEGER NOT NULL,
 source_type TEXT NOT NULL,
 source_id INTEGER,
 name TEXT NOT NULL,
 armor_class INTEGER DEFAULT 10,
 max_hp INTEGER DEFAULT 1,
 current_hp INTEGER DEFAULT 1,
 initiative_mod INTEGER DEFAULT 0,
 initiative INTEGER,
 sort_order INTEGER DEFAULT 0,
 is_active INTEGER DEFAULT 1,
 FOREIGN KEY(encounter_id) REFERENCES encounters(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS turn_log (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 encounter_id INTEGER,
 round INTEGER,
 actor TEXT,
 action_type TEXT,
 details TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS active_conditions (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 combatant_id INTEGER NOT NULL,
 condition_name TEXT NOT NULL,
 duration_rounds INTEGER,
 notes TEXT DEFAULT '',
 FOREIGN KEY(combatant_id) REFERENCES combatants(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS weapons (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, category TEXT, damage TEXT, properties TEXT, weight TEXT, cost TEXT, notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS armor (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, category TEXT, armor_class TEXT, strength TEXT, stealth TEXT, weight TEXT, cost TEXT, notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS equipment (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, category TEXT, cost TEXT, weight TEXT, notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS magic_items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, rarity TEXT, item_type TEXT, attunement TEXT, notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS spells (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, level TEXT, school TEXT, casting_time TEXT, range_text TEXT, components TEXT, duration TEXT, description TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS rules_reference (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL, name TEXT NOT NULL, description TEXT DEFAULT '', UNIQUE(category,name));
CREATE TABLE IF NOT EXISTS import_history (id INTEGER PRIMARY KEY AUTOINCREMENT, file_path TEXT, imported_at TEXT DEFAULT CURRENT_TIMESTAMP, rows_imported INTEGER DEFAULT 0, notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS external_sources (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 provider TEXT NOT NULL,
 campaign_key TEXT NOT NULL,
 campaign_name TEXT NOT NULL,
 ruleset TEXT NOT NULL,
 extension_version TEXT DEFAULT '',
 handoff_path TEXT DEFAULT '',
 last_sequence INTEGER DEFAULT 0,
 last_sync_at TEXT,
 last_error TEXT DEFAULT '',
 UNIQUE(provider, campaign_key)
);
CREATE TABLE IF NOT EXISTS external_records (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 source_id INTEGER NOT NULL,
 source_key TEXT NOT NULL,
 record_type TEXT NOT NULL,
 name TEXT NOT NULL,
 module_name TEXT,
 source_path TEXT NOT NULL,
 content_hash TEXT NOT NULL,
 raw_json TEXT NOT NULL,
 last_seen_sequence INTEGER NOT NULL,
 is_stale INTEGER DEFAULT 0,
 FOREIGN KEY(source_id) REFERENCES external_sources(id) ON DELETE CASCADE,
 UNIQUE(source_id, source_key)
);
CREATE TABLE IF NOT EXISTS external_entity_links (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 source_id INTEGER NOT NULL,
 source_key TEXT NOT NULL,
 entity_type TEXT NOT NULL,
 entity_id INTEGER NOT NULL,
 FOREIGN KEY(source_id) REFERENCES external_sources(id) ON DELETE CASCADE,
 UNIQUE(source_id, source_key, entity_type)
);
CREATE TABLE IF NOT EXISTS external_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 source_id INTEGER NOT NULL,
 event_key TEXT NOT NULL,
 encounter_id INTEGER NOT NULL,
 turn_log_id INTEGER NOT NULL,
 event_type TEXT NOT NULL,
 occurred_at TEXT NOT NULL,
 raw_json TEXT NOT NULL,
 imported_sequence INTEGER NOT NULL,
 FOREIGN KEY(source_id) REFERENCES external_sources(id) ON DELETE CASCADE,
 FOREIGN KEY(encounter_id) REFERENCES encounters(id) ON DELETE CASCADE,
 FOREIGN KEY(turn_log_id) REFERENCES turn_log(id) ON DELETE CASCADE,
 UNIQUE(source_id, event_key)
);
"""

class ClosingConnection(sqlite3.Connection):
    """SQLite connection whose context manager also closes the file handle.

    The standard sqlite3 context manager commits or rolls back but leaves the
    connection open. That behavior causes WinError 32 when temporary databases
    are removed and can retain file locks during backup/restore operations.
    """

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, factory=ClosingConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def initialize_database(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        # Lightweight migrations for existing user databases. SQLite does not add
        # columns from CREATE TABLE IF NOT EXISTS when a table already exists.
        existing = {row[1] for row in conn.execute('PRAGMA table_info(players)').fetchall()}
        for col, decl in {
            'str_base': 'INTEGER DEFAULT 10', 'dex_base': 'INTEGER DEFAULT 10', 'con_base': 'INTEGER DEFAULT 10', 'int_base': 'INTEGER DEFAULT 10', 'wis_base': 'INTEGER DEFAULT 10', 'cha_base': 'INTEGER DEFAULT 10',
            'str_race_bonus': 'INTEGER DEFAULT 0', 'dex_race_bonus': 'INTEGER DEFAULT 0', 'con_race_bonus': 'INTEGER DEFAULT 0', 'int_race_bonus': 'INTEGER DEFAULT 0', 'wis_race_bonus': 'INTEGER DEFAULT 0', 'cha_race_bonus': 'INTEGER DEFAULT 0',
            'str_feat_bonus': 'INTEGER DEFAULT 0', 'dex_feat_bonus': 'INTEGER DEFAULT 0', 'con_feat_bonus': 'INTEGER DEFAULT 0', 'int_feat_bonus': 'INTEGER DEFAULT 0', 'wis_feat_bonus': 'INTEGER DEFAULT 0', 'cha_feat_bonus': 'INTEGER DEFAULT 0',
            'str_total': 'INTEGER DEFAULT 10', 'dex_total': 'INTEGER DEFAULT 10', 'con_total': 'INTEGER DEFAULT 10', 'int_total': 'INTEGER DEFAULT 10', 'wis_total': 'INTEGER DEFAULT 10', 'cha_total': 'INTEGER DEFAULT 10',
            'str_mod': 'INTEGER DEFAULT 0', 'dex_mod': 'INTEGER DEFAULT 0', 'con_mod': 'INTEGER DEFAULT 0', 'int_mod': 'INTEGER DEFAULT 0', 'wis_mod': 'INTEGER DEFAULT 0', 'cha_mod': 'INTEGER DEFAULT 0',
            'feats': "TEXT DEFAULT ''",
            'equipped_weapon': "TEXT DEFAULT ''",
            'equipped_armor': "TEXT DEFAULT ''",
            'equipment': "TEXT DEFAULT ''",
            'player_name': "TEXT DEFAULT ''",
            'skill_proficiencies': "TEXT DEFAULT ''", 'skill_expertise': "TEXT DEFAULT ''", 'saving_throw_proficiencies': "TEXT DEFAULT ''",
            'inventory': "TEXT DEFAULT ''", 'currency_cp': 'INTEGER DEFAULT 0', 'currency_sp': 'INTEGER DEFAULT 0', 'currency_ep': 'INTEGER DEFAULT 0', 'currency_gp': 'INTEGER DEFAULT 0', 'currency_pp': 'INTEGER DEFAULT 0',
            'portrait_path': "TEXT DEFAULT ''", 'spellcasting_ability': "TEXT DEFAULT ''",
        }.items():
            if col not in existing:
                conn.execute(f'ALTER TABLE players ADD COLUMN {col} {decl}')
        encounter_columns = {row[1] for row in conn.execute('PRAGMA table_info(encounters)').fetchall()}
        for col, decl in {'campaign_id': 'INTEGER', 'outcome': "TEXT DEFAULT ''", 'completed_at': 'TEXT'}.items():
            if col not in encounter_columns:
                conn.execute(f'ALTER TABLE encounters ADD COLUMN {col} {decl}')
        conn.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES('schema_version','7')")
