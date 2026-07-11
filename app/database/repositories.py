from __future__ import annotations
from pathlib import Path
from .schema import connect

ABILITY_FIELDS = ['str', 'dex', 'con', 'int', 'wis', 'cha']
PLAYER_COLUMNS = [
    'name','species','class_name','subclass','background','level','armor_class','max_hp','current_hp','initiative_mod',
    'str_base','dex_base','con_base','int_base','wis_base','cha_base',
    'str_race_bonus','dex_race_bonus','con_race_bonus','int_race_bonus','wis_race_bonus','cha_race_bonus',
    'str_feat_bonus','dex_feat_bonus','con_feat_bonus','int_feat_bonus','wis_feat_bonus','cha_feat_bonus',
    'str_total','dex_total','con_total','int_total','wis_total','cha_total',
    'str_mod','dex_mod','con_mod','int_mod','wis_mod','cha_mod',
    'feats','equipped_weapon','equipped_armor','equipment','notes',
    'player_name','skill_proficiencies','skill_expertise','saving_throw_proficiencies',
    'inventory','currency_cp','currency_sp','currency_ep','currency_gp','currency_pp','portrait_path','spellcasting_ability'
]

class Repository:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def list_rows(self, table: str):
        with connect(self.db_path) as conn:
            return conn.execute(f"SELECT * FROM {table} ORDER BY name").fetchall()

    def count(self, table: str) -> int:
        with connect(self.db_path) as conn:
            return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

    def upsert_player(self, data: dict):
        payload = {col: data.get(col) for col in PLAYER_COLUMNS}
        # Backward-compatible defaults for older callers/tests.
        for ability in ABILITY_FIELDS:
            payload[f'{ability}_base'] = int(payload.get(f'{ability}_base') or 10)
            payload[f'{ability}_race_bonus'] = int(payload.get(f'{ability}_race_bonus') or 0)
            payload[f'{ability}_feat_bonus'] = int(payload.get(f'{ability}_feat_bonus') or 0)
            total = payload[f'{ability}_base'] + payload[f'{ability}_race_bonus'] + payload[f'{ability}_feat_bonus']
            payload[f'{ability}_total'] = int(payload.get(f'{ability}_total') or total)
            payload[f'{ability}_mod'] = int(payload.get(f'{ability}_mod') if payload.get(f'{ability}_mod') is not None else ((payload[f'{ability}_total'] - 10) // 2))
        payload['level'] = int(payload.get('level') or 1)
        payload['armor_class'] = int(payload.get('armor_class') or 10)
        payload['max_hp'] = int(payload.get('max_hp') or 1)
        payload['current_hp'] = int(payload.get('current_hp') or payload['max_hp'])
        payload['initiative_mod'] = int(payload.get('initiative_mod') if payload.get('initiative_mod') is not None else payload.get('dex_mod') or 0)
        for text_col in ['species','class_name','subclass','background','feats','equipped_weapon','equipped_armor','equipment','notes',
    'player_name','skill_proficiencies','skill_expertise','saving_throw_proficiencies',
    'inventory','portrait_path','spellcasting_ability']:
            payload[text_col] = payload.get(text_col) or ''
        for currency_col in ['currency_cp','currency_sp','currency_ep','currency_gp','currency_pp']:
            payload[currency_col] = int(payload.get(currency_col) or 0)
        fields = PLAYER_COLUMNS
        placeholders = ','.join(':'+f for f in fields)
        updates = ','.join(f"{f}=excluded.{f}" for f in fields if f != 'name')
        with connect(self.db_path) as conn:
            conn.execute(f"""
            INSERT INTO players({','.join(fields)})
            VALUES({placeholders})
            ON CONFLICT(name) DO UPDATE SET {updates}
            """, payload)

    def upsert_monster(self, data: dict):
        with connect(self.db_path) as conn:
            conn.execute("""
            INSERT INTO monsters(name,size,type,alignment,armor_class,hit_points,speed,challenge_rating,xp,str_score,dex_score,con_score,int_score,wis_score,cha_score,source,notes)
            VALUES(:name,:size,:type,:alignment,:armor_class,:hit_points,:speed,:challenge_rating,:xp,:str_score,:dex_score,:con_score,:int_score,:wis_score,:cha_score,:source,:notes)
            ON CONFLICT(name) DO UPDATE SET size=excluded.size,type=excluded.type,alignment=excluded.alignment,armor_class=excluded.armor_class,
            hit_points=excluded.hit_points,speed=excluded.speed,challenge_rating=excluded.challenge_rating,xp=excluded.xp,
            str_score=excluded.str_score,dex_score=excluded.dex_score,con_score=excluded.con_score,int_score=excluded.int_score,
            wis_score=excluded.wis_score,cha_score=excluded.cha_score,source=excluded.source,notes=excluded.notes
            """, data)

    def upsert_reference(self, table: str, data: dict):
        fields = list(data.keys())
        placeholders = ','.join(':'+f for f in fields)
        updates = ','.join(f"{f}=excluded.{f}" for f in fields if f != 'name')
        sql = f"INSERT INTO {table}({','.join(fields)}) VALUES({placeholders}) ON CONFLICT(name) DO UPDATE SET {updates or 'name=excluded.name'}"
        with connect(self.db_path) as conn:
            conn.execute(sql, data)

    def add_import_history(self, file_path: str, rows: int, notes: str=''):
        with connect(self.db_path) as conn:
            conn.execute("INSERT INTO import_history(file_path,rows_imported,notes) VALUES(?,?,?)", (file_path, rows, notes))

    def list_rule_names_like(self, category_text: str):
        with connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT name FROM rules_reference WHERE lower(category) LIKE ? ORDER BY name",
                (f"%{category_text.lower()}%",),
            ).fetchall()
            return [row['name'] for row in rows]

    def get_rule_description(self, name: str, category_text: str) -> str:
        with connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT description FROM rules_reference WHERE name=? AND lower(category) LIKE ? ORDER BY category LIMIT 1",
                (name, f"%{category_text.lower()}%"),
            ).fetchone()
            return str(row['description'] or '') if row else ''




    def list_names(self, table: str):
        allowed = {'weapons', 'armor', 'equipment', 'magic_items', 'spells', 'monsters', 'players'}
        if table not in allowed:
            raise ValueError(f'Unsupported lookup table: {table}')
        with connect(self.db_path) as conn:
            rows = conn.execute(f"SELECT name FROM {table} ORDER BY name").fetchall()
            return [row['name'] for row in rows]

    def get_player_by_id(self, player_id: int):
        with connect(self.db_path) as conn:
            return conn.execute("SELECT * FROM players WHERE id=?", (player_id,)).fetchone()

    def delete_player(self, player_id: int):
        with connect(self.db_path) as conn:
            conn.execute("DELETE FROM players WHERE id=?", (player_id,))

    def duplicate_player(self, player_id: int) -> int | None:
        with connect(self.db_path) as conn:
            row = conn.execute("SELECT * FROM players WHERE id=?", (player_id,)).fetchone()
            if not row:
                return None
            base = f"{row['name']} Copy"
            name = base
            suffix = 2
            while conn.execute("SELECT id FROM players WHERE name=?", (name,)).fetchone():
                name = f"{base} {suffix}"
                suffix += 1
            columns = [c for c in PLAYER_COLUMNS if c != 'name']
            values = {c: row[c] if c in row.keys() else None for c in columns}
            values['name'] = name
            fields = ['name'] + columns
            conn.execute(
                f"INSERT INTO players({','.join(fields)}) VALUES({','.join(':'+f for f in fields)})",
                values,
            )
            new_id = conn.execute("SELECT id FROM players WHERE name=?", (name,)).fetchone()[0]
            return int(new_id)

    def list_monsters(self):
        return self.list_rows('monsters')

    def list_players(self):
        return self.list_rows('players')

    def create_encounter(self, name: str) -> int:
        with connect(self.db_path) as conn:
            base = name.strip() or "New Encounter"
            unique_name = base
            suffix = 2
            while conn.execute("SELECT 1 FROM encounters WHERE name=?", (unique_name,)).fetchone():
                unique_name = f"{base} {suffix}"
                suffix += 1
            cursor = conn.execute(
                "INSERT INTO encounters(name,status,round,active_index) VALUES(?, 'draft', 1, 0)",
                (unique_name,),
            )
            return int(cursor.lastrowid)

    def list_encounters(self):
        with connect(self.db_path) as conn:
            return conn.execute("SELECT * FROM encounters ORDER BY id DESC").fetchall()

    def create_campaign(self, name: str, description: str = '') -> int:
        with connect(self.db_path) as conn:
            conn.execute("INSERT OR IGNORE INTO campaigns(name,description) VALUES(?,?)", (name, description))
            return int(conn.execute("SELECT id FROM campaigns WHERE name=?", (name,)).fetchone()[0])

    def list_campaigns(self):
        with connect(self.db_path) as conn:
            return conn.execute("SELECT * FROM campaigns ORDER BY name").fetchall()

    def list_campaigns_with_counts(self):
        with connect(self.db_path) as conn:
            return conn.execute("""
                SELECT c.*, COUNT(e.id) AS encounter_count
                FROM campaigns c
                LEFT JOIN encounters e ON e.campaign_id = c.id
                GROUP BY c.id
                ORDER BY c.name
            """).fetchall()

    def assign_encounter_to_campaign(self, encounter_id: int, campaign_id: int | None):
        with connect(self.db_path) as conn:
            conn.execute("UPDATE encounters SET campaign_id=? WHERE id=?", (campaign_id, encounter_id))

    def complete_encounter(self, encounter_id: int, outcome: str):
        with connect(self.db_path) as conn:
            conn.execute("UPDATE encounters SET status='completed', outcome=?, completed_at=CURRENT_TIMESTAMP WHERE id=?", (outcome, encounter_id))

    def campaign_encounters(self, campaign_id: int):
        with connect(self.db_path) as conn:
            return conn.execute("SELECT e.*, (SELECT COUNT(*) FROM turn_log t WHERE t.encounter_id=e.id) action_count, (SELECT COUNT(*) FROM combatants c WHERE c.encounter_id=e.id AND c.is_active=1) combatant_count FROM encounters e WHERE e.campaign_id=? ORDER BY e.id DESC", (campaign_id,)).fetchall()

    def campaign_summary(self, campaign_id: int):
        with connect(self.db_path) as conn:
            encounters = conn.execute("SELECT COUNT(*) total, SUM(status='completed') completed, SUM(outcome='Victory') victories, SUM(outcome='Defeat') defeats, SUM(outcome='Retreat') retreats, COALESCE(SUM(round),0) rounds FROM encounters WHERE campaign_id=?", (campaign_id,)).fetchone()
            logs = conn.execute("SELECT COUNT(*) actions, COALESCE(SUM(CASE WHEN action_type='Damage' THEN CAST(substr(details,instr(details,':')+1) AS INTEGER) ELSE 0 END),0) damage, COALESCE(SUM(CASE WHEN action_type='Healing' THEN CAST(substr(details,instr(details,':')+1) AS INTEGER) ELSE 0 END),0) healing FROM turn_log WHERE encounter_id IN (SELECT id FROM encounters WHERE campaign_id=?)", (campaign_id,)).fetchone()
            return {**dict(encounters), **dict(logs)}

    def get_encounter(self, encounter_id: int):
        with connect(self.db_path) as conn:
            return conn.execute("SELECT * FROM encounters WHERE id=?", (encounter_id,)).fetchone()

    def list_combatants(self, encounter_id: int):
        with connect(self.db_path) as conn:
            return conn.execute("""
                SELECT * FROM combatants
                WHERE encounter_id=? AND is_active=1
                ORDER BY COALESCE(initiative, -999) DESC, sort_order ASC, name ASC
            """, (encounter_id,)).fetchall()

    def add_combatant_from_monster(self, encounter_id: int, monster_id: int, display_name: str | None = None):
        with connect(self.db_path) as conn:
            m = conn.execute("SELECT * FROM monsters WHERE id=?", (monster_id,)).fetchone()
            if not m:
                return
            count = conn.execute("SELECT COUNT(*) FROM combatants WHERE encounter_id=? AND source_type='monster' AND source_id=?", (encounter_id, monster_id)).fetchone()[0]
            name = display_name or f"{m['name']} #{int(count)+1}"
            conn.execute("""
                INSERT INTO combatants(encounter_id,source_type,source_id,name,armor_class,max_hp,current_hp,initiative_mod,initiative,sort_order)
                VALUES(?,?,?,?,?,?,?,?,NULL,?)
            """, (encounter_id, 'monster', monster_id, name, m['armor_class'] or 10, m['hit_points'] or 1, m['hit_points'] or 1, 0, int(count)))

    def add_combatant_from_player(self, encounter_id: int, player_id: int):
        with connect(self.db_path) as conn:
            p = conn.execute("SELECT * FROM players WHERE id=?", (player_id,)).fetchone()
            if not p:
                return
            exists = conn.execute("SELECT id FROM combatants WHERE encounter_id=? AND source_type='player' AND source_id=? AND is_active=1", (encounter_id, player_id)).fetchone()
            if exists:
                return
            order = conn.execute("SELECT COUNT(*) FROM combatants WHERE encounter_id=?", (encounter_id,)).fetchone()[0]
            conn.execute("""
                INSERT INTO combatants(encounter_id,source_type,source_id,name,armor_class,max_hp,current_hp,initiative_mod,initiative,sort_order)
                VALUES(?,?,?,?,?,?,?,?,NULL,?)
            """, (encounter_id, 'player', player_id, p['name'], p['armor_class'] or 10, p['max_hp'] or 1, p['current_hp'] or p['max_hp'] or 1, p['initiative_mod'] or 0, int(order)))

    def update_combatant_hp(self, combatant_id: int, current_hp: int):
        with connect(self.db_path) as conn:
            conn.execute("UPDATE combatants SET current_hp=? WHERE id=?", (current_hp, combatant_id))

    def remove_combatant(self, combatant_id: int):
        with connect(self.db_path) as conn:
            conn.execute("UPDATE combatants SET is_active=0 WHERE id=?", (combatant_id,))

    def roll_initiative(self, encounter_id: int):
        import random
        with connect(self.db_path) as conn:
            rows = conn.execute("SELECT id, initiative_mod FROM combatants WHERE encounter_id=? AND is_active=1", (encounter_id,)).fetchall()
            for row in rows:
                conn.execute("UPDATE combatants SET initiative=? WHERE id=?", (random.randint(1,20) + (row['initiative_mod'] or 0), row['id']))
            conn.execute("UPDATE encounters SET status='active', round=1, active_index=0 WHERE id=?", (encounter_id,))

    def next_turn(self, encounter_id: int):
        with connect(self.db_path) as conn:
            enc = conn.execute("SELECT * FROM encounters WHERE id=?", (encounter_id,)).fetchone()
            total = conn.execute("SELECT COUNT(*) FROM combatants WHERE encounter_id=? AND is_active=1", (encounter_id,)).fetchone()[0]
            if not enc or total == 0:
                return
            idx = (enc['active_index'] or 0) + 1
            round_no = enc['round'] or 1
            if idx >= total:
                idx = 0
                round_no += 1
            conn.execute("UPDATE encounters SET active_index=?, round=? WHERE id=?", (idx, round_no, encounter_id))

    def previous_turn(self, encounter_id: int):
        with connect(self.db_path) as conn:
            enc = conn.execute("SELECT * FROM encounters WHERE id=?", (encounter_id,)).fetchone()
            total = conn.execute("SELECT COUNT(*) FROM combatants WHERE encounter_id=? AND is_active=1", (encounter_id,)).fetchone()[0]
            if not enc or total == 0:
                return
            idx = (enc['active_index'] or 0) - 1
            round_no = enc['round'] or 1
            if idx < 0:
                idx = max(total - 1, 0)
                round_no = max(1, round_no - 1)
            conn.execute("UPDATE encounters SET active_index=?, round=? WHERE id=?", (idx, round_no, encounter_id))

    def log_turn(self, encounter_id: int, actor: str, action_type: str, details: str):
        with connect(self.db_path) as conn:
            enc = conn.execute("SELECT round FROM encounters WHERE id=?", (encounter_id,)).fetchone()
            conn.execute("INSERT INTO turn_log(encounter_id,round,actor,action_type,details) VALUES(?,?,?,?,?)", (encounter_id, enc['round'] if enc else 1, actor, action_type, details))

    def list_turn_log(self, encounter_id: int):
        with connect(self.db_path) as conn:
            return conn.execute("SELECT * FROM turn_log WHERE encounter_id=? ORDER BY id DESC", (encounter_id,)).fetchall()
