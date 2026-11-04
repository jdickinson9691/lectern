"""Mission level budget, GM risk, roster, lore, loot, and future hooks."""
from __future__ import annotations

from pathlib import Path

from ..database.campaign_identity import CAMPAIGN_ID
from ..database.schema import connect


DIFFICULTIES = ('easy', 'normal', 'difficult', 'risky', 'deadly')


class MissionPlanningService:
    def __init__(self, db_path: Path, campaign_id: str = CAMPAIGN_ID):
        self.db_path = Path(db_path)
        self.campaign_id = campaign_id

    def monster_catalog(self) -> list[dict]:
        with connect(self.db_path) as conn:
            return [dict(row) for row in conn.execute(
                'SELECT id,name,challenge_rating,xp FROM monsters ORDER BY name,id')]

    def available_players(self) -> list[dict]:
        with connect(self.db_path) as conn:
            return [dict(row) for row in conn.execute(
                'SELECT id,name,level FROM players ORDER BY name,id')]

    def future_missions(self, mission_id: str) -> list[dict]:
        with connect(self.db_path) as conn:
            return [dict(row) for row in conn.execute("""SELECT entity_id,name,status
                FROM campaign_entities WHERE kind='MIS' AND campaign_id=?
                AND entity_id<>? AND status<>'archived' ORDER BY name,entity_id""",
                (self.campaign_id, mission_id))]

    def get(self, mission_id: str) -> dict:
        with connect(self.db_path) as conn:
            self._require_mission(conn, mission_id)
            plan = conn.execute('SELECT * FROM mission_plans WHERE mission_id=?',
                                (mission_id,)).fetchone()
            monsters = [dict(row) for row in conn.execute("""SELECT mm.monster_id,
                m.name,m.challenge_rating,m.xp,mm.quantity FROM mission_monsters mm
                JOIN monsters m ON m.id=mm.monster_id WHERE mm.mission_id=?
                ORDER BY m.name,m.id""", (mission_id,))]
            hooks = [dict(row) for row in conn.execute("""SELECT h.id,h.future_mission_id,
                e.name AS future_mission_name,h.lore_hook FROM mission_hooks h
                LEFT JOIN campaign_entities e ON e.entity_id=h.future_mission_id
                WHERE h.mission_id=? ORDER BY h.id""", (mission_id,))]
            participants = [dict(row) for row in conn.execute("""SELECT p.id AS player_id,
                p.name,p.level FROM mission_participants mp
                JOIN players p ON p.id=mp.player_id WHERE mp.mission_id=?
                ORDER BY p.name,p.id""", (mission_id,))]
            approved_fiction = [dict(row) for row in conn.execute("""SELECT audience,
                field_key,content FROM entity_knowledge WHERE entity_id=?
                AND field_key IN ('background','details') AND status='approved'
                ORDER BY audience,field_key""", (mission_id,))]
            return {
                'mission_id': mission_id,
                'max_total_levels': plan['max_total_levels'] if plan else None,
                'difficulty': plan['difficulty'] if plan else None,
                'lore': plan['lore'] if plan else '',
                'loot': plan['loot'] if plan else '',
                'monsters': monsters,
                'hooks': hooks,
                'participants': participants,
                'approved_fiction': approved_fiction,
                'selected_level_total': sum(max(0, row['level'] or 0)
                                            for row in participants),
                'catalog_xp_total': sum(max(0, row['xp'] or 0) * row['quantity']
                                        for row in monsters),
            }

    def save(self, mission_id: str, *, max_total_levels: int | None,
             difficulty: str | None, lore: str, loot: str,
             monsters: list[tuple[int, int]],
             hooks: list[tuple[str | None, str]],
             participants: list[int] | None = None, actor: str = 'gm') -> None:
        if max_total_levels is not None and (not isinstance(max_total_levels, int) or
                                              max_total_levels < 1):
            raise ValueError('Maximum total character levels must be positive')
        if difficulty is not None and difficulty not in DIFFICULTIES:
            raise ValueError('Choose a mission difficulty')
        if not isinstance(lore, str) or not isinstance(loot, str):
            raise ValueError('Mission lore and loot must be text')
        if len({monster_id for monster_id, _ in monsters}) != len(monsters):
            raise ValueError('Each monster appears once with a quantity')
        with connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            self._require_mission(conn, mission_id)
            for monster_id, quantity in monsters:
                if not isinstance(monster_id, int) or not isinstance(quantity, int) or quantity < 1:
                    raise ValueError('Monster and quantity must be valid')
                if conn.execute('SELECT 1 FROM monsters WHERE id=?', (monster_id,)).fetchone() is None:
                    raise ValueError(f'Monster {monster_id} is not in the Lectern catalog')
            for future_id, hook_text in hooks:
                if not hook_text.strip():
                    raise ValueError('Every future lore hook needs text')
                if future_id is not None:
                    if future_id == mission_id:
                        raise ValueError('A mission cannot hook to itself')
                    self._require_mission(conn, future_id)
            selected = ([row['player_id'] for row in conn.execute(
                'SELECT player_id FROM mission_participants WHERE mission_id=?',
                (mission_id,))] if participants is None else participants)
            if len(set(selected)) != len(selected):
                raise ValueError('A character can join a mission only once')
            total_levels = 0
            for player_id in selected:
                row = conn.execute('SELECT level FROM players WHERE id=?', (player_id,)).fetchone()
                if row is None or not isinstance(player_id, int) or (row['level'] or 0) < 1:
                    raise ValueError(f'Active character required: {player_id}')
                total_levels += row['level']
            if selected and max_total_levels is None:
                raise ValueError('Set a level cap before selecting characters')
            if max_total_levels is not None and total_levels > max_total_levels:
                raise ValueError(f'Chosen characters total {total_levels} levels; '
                                 f'mission cap is {max_total_levels}')
            old = conn.execute('SELECT max_total_levels,difficulty FROM mission_plans WHERE mission_id=?',
                               (mission_id,)).fetchone()
            old_roster = [(row['monster_id'], row['quantity']) for row in conn.execute(
                'SELECT monster_id,quantity FROM mission_monsters WHERE mission_id=? ORDER BY monster_id',
                (mission_id,))]
            new_roster = sorted(monsters)
            public_changed = (
                (old is None and (max_total_levels is not None or difficulty is not None or
                                  bool(new_roster))) or
                (old is not None and (old['max_total_levels'] != max_total_levels or
                                      old['difficulty'] != difficulty or old_roster != new_roster))
            )
            conn.execute("""INSERT INTO mission_plans
                (mission_id,max_total_levels,difficulty,lore,loot)
                VALUES(?,?,?,?,?) ON CONFLICT(mission_id) DO UPDATE SET
                max_total_levels=excluded.max_total_levels,difficulty=excluded.difficulty,
                lore=excluded.lore,loot=excluded.loot,updated_at=CURRENT_TIMESTAMP""",
                (mission_id, max_total_levels, difficulty, lore.strip(), loot.strip()))
            conn.execute('DELETE FROM mission_monsters WHERE mission_id=?', (mission_id,))
            conn.executemany('INSERT INTO mission_monsters(mission_id,monster_id,quantity) VALUES(?,?,?)',
                             [(mission_id, monster_id, quantity) for monster_id, quantity in monsters])
            conn.execute('DELETE FROM mission_hooks WHERE mission_id=?', (mission_id,))
            conn.executemany("""INSERT INTO mission_hooks
                (mission_id,future_mission_id,lore_hook) VALUES(?,?,?)""",
                [(mission_id, future_id, hook_text.strip()) for future_id, hook_text in hooks])
            conn.execute('DELETE FROM mission_participants WHERE mission_id=?', (mission_id,))
            conn.executemany('INSERT INTO mission_participants(mission_id,player_id) VALUES(?,?)',
                             [(mission_id, player_id) for player_id in selected])
            if public_changed:
                conn.execute("""UPDATE campaign_entities SET status='draft',
                    updated_at=CURRENT_TIMESTAMP WHERE entity_id=? AND status='approved'""",
                    (mission_id,))
                conn.execute("""UPDATE entity_knowledge SET status='draft'
                    WHERE entity_id=? AND audience='player' AND field_key='briefing'
                    AND status='approved'""", (mission_id,))
            conn.execute("""INSERT INTO entity_audit(entity_id,action,actor,detail)
                VALUES(?,'mission_plan',?,?)""",
                (mission_id, actor,
                 f'levels={max_total_levels}; difficulty={difficulty}; monsters={len(monsters)}; '
                 f'hooks={len(hooks)}; characters={len(selected)}; '
                 f'level_total={total_levels}; public_changed={public_changed}'))

    def validate_for_approval(self, mission_id: str) -> dict:
        plan = self.get(mission_id)
        if not plan['max_total_levels'] or plan['difficulty'] not in DIFFICULTIES:
            raise ValueError('Set the level budget and mission difficulty before approval')
        if not plan['lore'].strip():
            raise ValueError('Describe the mission lore before approval')
        if not plan['loot'].strip():
            raise ValueError('Describe the mission loot or enter None before approval')
        if plan['selected_level_total'] > plan['max_total_levels']:
            raise ValueError('Chosen characters exceed the mission level cap')
        return plan

    def _require_mission(self, conn, mission_id: str) -> None:
        row = conn.execute("""SELECT 1 FROM campaign_entities WHERE entity_id=?
            AND kind='MIS' AND campaign_id=? AND status<>'archived'""",
            (mission_id, self.campaign_id)).fetchone()
        if row is None:
            raise KeyError(f'Active mission in this campaign required: {mission_id}')
