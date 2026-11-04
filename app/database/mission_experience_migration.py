"""Schema v14: additive XP ledger for Ashen Company missions."""
from __future__ import annotations

import sqlite3


def migrate_mission_experience_v14(conn: sqlite3.Connection) -> None:
    conn.execute('SAVEPOINT mission_experience_v14')
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS character_xp_baselines (
            player_id INTEGER PRIMARY KEY REFERENCES players(id) ON DELETE CASCADE,
            starting_xp INTEGER NOT NULL CHECK(starting_xp >= 0),
            starting_level INTEGER NOT NULL CHECK(starting_level BETWEEN 1 AND 20),
            recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS mission_xp_awards (
            mission_id TEXT NOT NULL REFERENCES mission_plans(mission_id) ON DELETE RESTRICT,
            player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE RESTRICT,
            xp INTEGER NOT NULL CHECK(xp >= 0),
            total_award INTEGER NOT NULL CHECK(total_award > 0),
            reason TEXT NOT NULL CHECK(length(trim(reason)) > 0),
            awarded_by TEXT NOT NULL,
            awarded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(mission_id, player_id)
        )""")
        conn.execute('CREATE INDEX IF NOT EXISTS idx_mission_xp_player ON mission_xp_awards(player_id)')
        conn.execute("UPDATE metadata SET value='14' WHERE key='schema_version'")
        conn.execute('RELEASE SAVEPOINT mission_experience_v14')
    except BaseException:
        conn.execute('ROLLBACK TO SAVEPOINT mission_experience_v14')
        conn.execute('RELEASE SAVEPOINT mission_experience_v14')
        raise
