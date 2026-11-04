"""Schema v13: structured mission planning without changing legacy mission rows."""
from __future__ import annotations

import sqlite3


def migrate_mission_planning_v13(conn: sqlite3.Connection) -> None:
    conn.execute('SAVEPOINT mission_planning_v13')
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS mission_plans (
            mission_id TEXT PRIMARY KEY REFERENCES campaign_entities(entity_id) ON DELETE CASCADE,
            max_total_levels INTEGER CHECK(max_total_levels IS NULL OR max_total_levels > 0),
            difficulty TEXT CHECK(difficulty IS NULL OR difficulty IN
                ('easy','normal','difficult','risky','deadly')),
            lore TEXT NOT NULL DEFAULT '',
            loot TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS mission_monsters (
            mission_id TEXT NOT NULL REFERENCES mission_plans(mission_id) ON DELETE CASCADE,
            monster_id INTEGER NOT NULL REFERENCES monsters(id) ON DELETE RESTRICT,
            quantity INTEGER NOT NULL CHECK(quantity > 0),
            PRIMARY KEY(mission_id,monster_id)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS mission_hooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mission_id TEXT NOT NULL REFERENCES mission_plans(mission_id) ON DELETE CASCADE,
            future_mission_id TEXT REFERENCES campaign_entities(entity_id) ON DELETE RESTRICT,
            lore_hook TEXT NOT NULL CHECK(length(trim(lore_hook)) > 0)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS mission_participants (
            mission_id TEXT NOT NULL REFERENCES mission_plans(mission_id) ON DELETE CASCADE,
            player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE RESTRICT,
            PRIMARY KEY(mission_id,player_id)
        )""")
        conn.execute('CREATE INDEX IF NOT EXISTS idx_mission_hooks_mission ON mission_hooks(mission_id)')
        conn.execute("UPDATE metadata SET value='13' WHERE key='schema_version'")
        conn.execute('RELEASE SAVEPOINT mission_planning_v13')
    except BaseException:
        conn.execute('ROLLBACK TO SAVEPOINT mission_planning_v13')
        conn.execute('RELEASE SAVEPOINT mission_planning_v13')
        raise
