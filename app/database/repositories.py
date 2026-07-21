from __future__ import annotations
import json
import re
from pathlib import Path
from .schema import connect

ABILITY_FIELDS = ['str', 'dex', 'con', 'int', 'wis', 'cha']
DND5E_DAMAGE_TYPES = (
    'acid', 'bludgeoning', 'cold', 'fire', 'force', 'lightning', 'necrotic',
    'piercing', 'poison', 'psychic', 'radiant', 'slashing', 'thunder',
)
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
            if category_text.lower() == "class":
                rows = conn.execute(
                    "SELECT name FROM rules_reference WHERE lower(category) LIKE ? AND lower(category) NOT LIKE '%subclass%' ORDER BY name",
                    ("%class%",),
                ).fetchall()
            else:
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

    def get_monster_by_id(self, monster_id: int):
        with connect(self.db_path) as conn:
            return conn.execute("SELECT * FROM monsters WHERE id=?", (monster_id,)).fetchone()

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
            rows = conn.execute(
                """
                SELECT actor,actor_source_key,action_type,details,actor_side,amount,result_code,round,
                       damage_types,damage_components_json
                FROM turn_log WHERE encounter_id IN (SELECT id FROM encounters WHERE campaign_id=?)
                """,
                (campaign_id,),
            ).fetchall()
            round_rows = conn.execute(
                """
                SELECT MAX(COALESCE(t.round,1)) AS rounds
                FROM encounters e JOIN turn_log t ON t.encounter_id=e.id
                WHERE e.campaign_id=? GROUP BY e.id
                """,
                (campaign_id,),
            ).fetchall()

        def logged_amount(row) -> int:
            if row["amount"] is not None:
                return max(0, int(row["amount"]))
            match = re.match(r"\s*(?:Damage|Healing)\s*:\s*(\d+)|\s*(\d+)\b", str(row["details"] or ""), re.IGNORECASE)
            return int(next((value for value in match.groups() if value is not None), 0)) if match else 0

        damage = sum(logged_amount(row) for row in rows if row["action_type"] == "Damage")
        healing = sum(logged_amount(row) for row in rows if row["action_type"] == "Healing")
        party_damage = sum(logged_amount(row) for row in rows if row["action_type"] == "Damage" and row["actor_side"] == "party")
        party_healing = sum(logged_amount(row) for row in rows if row["action_type"] == "Healing" and row["actor_side"] == "party")
        combat_rounds = sum(max(1, int(row["rounds"] or 1)) for row in round_rows)
        stat_rows = [row for row in rows if row["action_type"] in {"Attack", "Damage", "Healing"}]
        attributed = sum(row["actor_side"] in {"party", "hostile", "neutral"} for row in stat_rows)

        def leaders(result_code: str) -> tuple[list[str], int]:
            counts: dict[str, int] = {}
            names: dict[str, str] = {}
            for row in rows:
                if row["actor_side"] == "party" and row["result_code"] == result_code:
                    name = str(row["actor"] or "Unknown character")
                    key = str(row["actor_source_key"] or name.casefold())
                    names[key] = name
                    counts[key] = counts.get(key, 0) + 1
            high = max(counts.values(), default=0)
            return sorted({names[key] for key, count in counts.items() if count == high}, key=str.casefold), high

        damage_by_type: dict[str, dict[str, dict[str, int | str]]] = {
            damage_type: {} for damage_type in DND5E_DAMAGE_TYPES
        }
        for row in rows:
            if row["action_type"] != "Damage" or row["actor_side"] != "party":
                continue
            component_totals: dict[str, int] = {}
            try:
                components = json.loads(str(row["damage_components_json"] or "[]"))
            except (TypeError, ValueError, json.JSONDecodeError):
                components = []
            if isinstance(components, list):
                for component in components:
                    if not isinstance(component, dict):
                        continue
                    applied = component.get("applied")
                    if not isinstance(applied, (int, float)) or isinstance(applied, bool):
                        continue
                    applied_amount = max(0, int(applied))
                    component_types = component.get("types", [])
                    if isinstance(component_types, str):
                        component_types = component_types.split(",")
                    if not isinstance(component_types, list):
                        continue
                    for value in {str(item or "").strip().casefold() for item in component_types}:
                        if value in damage_by_type:
                            component_totals[value] = component_totals.get(value, 0) + applied_amount
            if not component_totals:
                fallback_types = {
                    value.strip().casefold() for value in str(row["damage_types"] or "").split(",")
                    if value.strip().casefold() in damage_by_type
                }
                if len(fallback_types) == 1:
                    component_totals[next(iter(fallback_types))] = logged_amount(row)
            actor_name = str(row["actor"] or "Unknown character")
            actor_key = str(row["actor_source_key"] or f"name:{actor_name.casefold()}")
            for damage_type, applied_amount in component_totals.items():
                if applied_amount <= 0:
                    continue
                actor = damage_by_type[damage_type].setdefault(
                    actor_key, {"name": actor_name, "damage": 0, "events": 0}
                )
                actor["damage"] = int(actor["damage"]) + applied_amount
                actor["events"] = int(actor["events"]) + 1

        damage_type_leaders = []
        for damage_type in DND5E_DAMAGE_TYPES:
            actors = damage_by_type[damage_type]
            high = max((int(actor["damage"]) for actor in actors.values()), default=0)
            type_leaders = sorted(
                (dict(actor) for actor in actors.values() if int(actor["damage"]) == high and high > 0),
                key=lambda actor: str(actor["name"]).casefold(),
            )
            damage_type_leaders.append({
                "damage_type": damage_type,
                "leaders": type_leaders,
                "damage": high,
            })

        critical_hit_leaders, critical_hit_count = leaders("critical_hit")
        critical_miss_leaders, critical_miss_count = leaders("critical_miss")
        return {
            **dict(encounters), "actions": len(rows), "damage": damage, "healing": healing,
            "combat_rounds": combat_rounds, "party_damage": party_damage, "party_healing": party_healing,
            "party_dpr": party_damage / combat_rounds if combat_rounds else 0.0,
            "party_hpr": party_healing / combat_rounds if combat_rounds else 0.0,
            "critical_hit_leaders": critical_hit_leaders, "critical_hit_count": critical_hit_count,
            "critical_miss_leaders": critical_miss_leaders, "critical_miss_count": critical_miss_count,
            "stat_events": len(stat_rows), "attributed_stat_events": attributed,
            "damage_type_leaders": damage_type_leaders,
        }

    def get_encounter(self, encounter_id: int):
        with connect(self.db_path) as conn:
            return conn.execute("SELECT * FROM encounters WHERE id=?", (encounter_id,)).fetchone()

    def encounter_sync_context(self, encounter_id: int | None) -> dict | None:
        """Describe a Fantasy Grounds encounter and its prepared/live counterpart."""
        if not encounter_id:
            return None
        with connect(self.db_path) as conn:
            own = conn.execute(
                """
                SELECT source_id,source_key FROM external_entity_links
                WHERE entity_type='encounter' AND entity_id=? ORDER BY id LIMIT 1
                """,
                (encounter_id,),
            ).fetchone()
            if not own:
                return None
            source_key = str(own["source_key"])
            if source_key == "live-combat" or source_key.startswith("live-combat:"):
                prepared = conn.execute(
                    """
                    SELECT e.id,e.name FROM external_entity_links relation
                    JOIN encounters e ON e.id=relation.entity_id
                    WHERE relation.source_id=? AND relation.source_key=?
                      AND relation.entity_type='prepared_encounter'
                    LIMIT 1
                    """,
                    (own["source_id"], source_key),
                ).fetchone()
                return {
                    "kind": "live",
                    "counterpart_id": int(prepared["id"]) if prepared else None,
                    "counterpart_name": str(prepared["name"]) if prepared else "",
                }
            live = conn.execute(
                """
                SELECT e.id,e.name FROM external_entity_links relation
                JOIN external_entity_links owned
                  ON owned.source_id=relation.source_id
                 AND owned.source_key=relation.source_key
                 AND owned.entity_type='encounter'
                JOIN encounters e ON e.id=owned.entity_id
                WHERE relation.entity_type='prepared_encounter' AND relation.entity_id=?
                ORDER BY CASE WHEN e.status='active' THEN 0 WHEN e.status='completed' THEN 1 ELSE 2 END,
                         e.id DESC
                LIMIT 1
                """,
                (encounter_id,),
            ).fetchone()
            return {
                "kind": "prepared",
                "counterpart_id": int(live["id"]) if live else None,
                "counterpart_name": str(live["name"]) if live else "",
            }

    def encounter_display_name(self, encounter) -> str:
        context = self.encounter_sync_context(int(encounter["id"]))
        if not context:
            return str(encounter["name"])
        if context["kind"] == "prepared":
            suffix = " · Prepared"
            if context["counterpart_name"]:
                suffix += f" → {context['counterpart_name']}"
            return f"{encounter['name']}{suffix}"
        suffix = " · Live combat"
        if context["counterpart_name"]:
            suffix += f" ← {context['counterpart_name']}"
        return f"{encounter['name']}{suffix}"

    def is_external_encounter(self, encounter_id: int | None) -> bool:
        if not encounter_id:
            return False
        with connect(self.db_path) as conn:
            return conn.execute(
                "SELECT 1 FROM external_entity_links WHERE entity_type='encounter' AND entity_id=? LIMIT 1",
                (encounter_id,),
            ).fetchone() is not None

    def list_combatants(self, encounter_id: int):
        with connect(self.db_path) as conn:
            return conn.execute("""
                SELECT c.*, CASE WHEN c.source_type='player' THEN COALESCE(p.portrait_path,'') ELSE '' END AS portrait_path
                FROM combatants c LEFT JOIN players p ON c.source_type='player' AND c.source_id=p.id
                WHERE c.encounter_id=? AND c.is_active=1
                ORDER BY COALESCE(c.initiative, -999) DESC, c.sort_order ASC, c.name ASC
            """, (encounter_id,)).fetchall()

    def add_combatants_from_monster(self, encounter_id: int, monster_id: int, quantity: int = 1) -> list[int]:
        quantity = max(0, int(quantity))
        if quantity == 0:
            return []
        with connect(self.db_path) as conn:
            m = conn.execute("SELECT * FROM monsters WHERE id=?", (monster_id,)).fetchone()
            if not m:
                raise ValueError(f"Monster id {monster_id} does not exist")
            existing_count = int(conn.execute(
                "SELECT COUNT(*) FROM combatants WHERE encounter_id=? AND source_type='monster' AND source_id=?",
                (encounter_id, monster_id),
            ).fetchone()[0])
            next_order = int(conn.execute(
                "SELECT COALESCE(MAX(sort_order),-1)+1 FROM combatants WHERE encounter_id=?",
                (encounter_id,),
            ).fetchone()[0])
            ids: list[int] = []
            for offset in range(quantity):
                name = f"{m['name']} #{existing_count + offset + 1}"
                cursor = conn.execute("""
                    INSERT INTO combatants(encounter_id,source_type,source_id,name,armor_class,max_hp,current_hp,initiative_mod,initiative,sort_order)
                    VALUES(?,?,?,?,?,?,?,?,NULL,?)
                """, (
                    encounter_id, 'monster', monster_id, name, m['armor_class'] or 10,
                    m['hit_points'] or 1, m['hit_points'] or 1, 0, next_order + offset,
                ))
                ids.append(int(cursor.lastrowid))
            return ids

    def add_combatant_from_monster(self, encounter_id: int, monster_id: int, display_name: str | None = None):
        if display_name is None:
            ids = self.add_combatants_from_monster(encounter_id, monster_id, 1)
            return ids[0] if ids else None
        with connect(self.db_path) as conn:
            m = conn.execute("SELECT * FROM monsters WHERE id=?", (monster_id,)).fetchone()
            if not m:
                raise ValueError(f"Monster id {monster_id} does not exist")
            next_order = int(conn.execute(
                "SELECT COALESCE(MAX(sort_order),-1)+1 FROM combatants WHERE encounter_id=?",
                (encounter_id,),
            ).fetchone()[0])
            cursor = conn.execute("""
                INSERT INTO combatants(encounter_id,source_type,source_id,name,armor_class,max_hp,current_hp,initiative_mod,initiative,sort_order)
                VALUES(?,?,?,?,?,?,?,?,NULL,?)
            """, (
                encounter_id, 'monster', monster_id, display_name, m['armor_class'] or 10,
                m['hit_points'] or 1, m['hit_points'] or 1, 0, next_order,
            ))
            return int(cursor.lastrowid)

    def add_combatant_from_player(self, encounter_id: int, player_id: int):
        with connect(self.db_path) as conn:
            p = conn.execute("SELECT * FROM players WHERE id=?", (player_id,)).fetchone()
            if not p:
                return
            exists = conn.execute("SELECT id FROM combatants WHERE encounter_id=? AND source_type='player' AND source_id=? AND is_active=1", (encounter_id, player_id)).fetchone()
            if exists:
                return
            order = conn.execute(
                "SELECT COALESCE(MAX(sort_order),-1)+1 FROM combatants WHERE encounter_id=?",
                (encounter_id,),
            ).fetchone()[0]
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

    def log_turn(
        self, encounter_id: int, actor: str, action_type: str, details: str, *,
        actor_source_key: str = "", actor_side: str | None = None, amount: int | None = None,
        result_code: str = "", natural_roll: int | None = None, damage_types: str = "",
        damage_components_json: str = "[]",
    ):
        with connect(self.db_path) as conn:
            enc = conn.execute("SELECT round FROM encounters WHERE id=?", (encounter_id,)).fetchone()
            if actor_side is None:
                combatant = conn.execute(
                    """
                    SELECT source_type,source_id FROM combatants
                    WHERE encounter_id=? AND name=? ORDER BY is_active DESC,id DESC LIMIT 1
                    """,
                    (encounter_id, actor),
                ).fetchone()
                actor_side = {"player": "party", "monster": "hostile"}.get(
                    combatant["source_type"] if combatant else "", "unknown"
                )
                if combatant and not actor_source_key:
                    actor_source_key = f"{combatant['source_type']}:{combatant['source_id'] or ''}"
            if amount is None and action_type in {"Damage", "Healing"}:
                match = re.match(r"\s*(?:Damage|Healing)\s*:\s*(\d+)|\s*(\d+)\b", details, re.IGNORECASE)
                if match:
                    amount = int(next(value for value in match.groups() if value is not None))
            if action_type == "Damage" and not damage_types:
                damage_types = "unknown"
            detail_result = details.casefold()
            if not result_code and action_type == "Attack":
                if "critical hit" in detail_result:
                    result_code = "critical_hit"
                elif "automatic miss" in detail_result or "critical miss" in detail_result:
                    result_code = "critical_miss"
            conn.execute(
                """
                INSERT INTO turn_log(
                    encounter_id,round,actor,action_type,details,actor_source_key,
                    actor_side,amount,result_code,natural_roll,damage_types,damage_components_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (encounter_id, enc['round'] if enc else 1, actor, action_type, details,
                 actor_source_key, actor_side, amount, result_code, natural_roll,
                 damage_types, damage_components_json),
            )

    def list_turn_log(self, encounter_id: int):
        with connect(self.db_path) as conn:
            return conn.execute("SELECT * FROM turn_log WHERE encounter_id=? ORDER BY id DESC", (encounter_id,)).fetchall()
