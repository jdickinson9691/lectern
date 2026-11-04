"""GM-awarded mission XP and character advancement, separate from encounter budgets."""
from __future__ import annotations

from pathlib import Path

from ..database.campaign_identity import CAMPAIGN_ID
from ..database.schema import connect


# 2024 Basic Rules, Character Advancement. These are cumulative XP totals.
LEVEL_XP = (0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000,
            64000, 85000, 100000, 120000, 140000, 165000, 195000,
            225000, 265000, 305000, 355000)


def level_for_xp(total_xp: int) -> int:
    if total_xp < 0:
        raise ValueError('XP cannot be negative')
    return max(level for level, threshold in enumerate(LEVEL_XP, 1)
               if total_xp >= threshold)


class MissionExperienceService:
    def __init__(self, db_path: Path, campaign_id: str = CAMPAIGN_ID):
        self.db_path = Path(db_path)
        self.campaign_id = campaign_id

    def character(self, player_id: int) -> dict:
        with connect(self.db_path) as conn:
            row = conn.execute('SELECT id,name,level FROM players WHERE id=?',
                               (player_id,)).fetchone()
            if row is None:
                raise KeyError(player_id)
            if not 1 <= (row['level'] or 0) <= 20:
                raise ValueError('Character level must be between 1 and 20')
            baseline = conn.execute('SELECT starting_xp,starting_level FROM character_xp_baselines WHERE player_id=?',
                                    (player_id,)).fetchone()
            starting_xp = baseline['starting_xp'] if baseline else LEVEL_XP[(row['level'] or 1) - 1]
            gained = conn.execute('SELECT COALESCE(SUM(xp),0) FROM mission_xp_awards WHERE player_id=?',
                                  (player_id,)).fetchone()[0]
            total = starting_xp + gained
            earned_level = level_for_xp(total)
            return {'player_id': player_id, 'name': row['name'], 'current_level': row['level'],
                    'starting_xp': starting_xp, 'mission_xp': gained, 'total_xp': total,
                    'earned_level': earned_level,
                    'next_level_xp': LEVEL_XP[earned_level] if earned_level < 20 else None}

    def mission_awards(self, mission_id: str) -> list[dict]:
        with connect(self.db_path) as conn:
            return [dict(row) for row in conn.execute("""SELECT a.player_id,p.name,a.xp,
                a.total_award,a.reason,a.awarded_by,a.awarded_at
                FROM mission_xp_awards a JOIN players p ON p.id=a.player_id
                WHERE a.mission_id=? ORDER BY a.player_id""", (mission_id,))]

    def award(self, mission_id: str, total_xp: int, reason: str,
              *, actor: str = 'gm') -> list[dict]:
        if isinstance(total_xp, bool) or not isinstance(total_xp, int) or total_xp < 1:
            raise ValueError('Award a positive whole number of XP')
        reason = reason.strip()
        if not reason:
            raise ValueError('Describe the completed mission challenges or objectives')
        with connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            mission = conn.execute("""SELECT e.status FROM campaign_entities e
                JOIN mission_plans mp ON mp.mission_id=e.entity_id
                WHERE e.entity_id=? AND e.kind='MIS' AND e.campaign_id=?""",
                (mission_id, self.campaign_id)).fetchone()
            if mission is None:
                raise KeyError(mission_id)
            if mission['status'] != 'approved':
                raise ValueError('Approve the mission before awarding XP')
            if conn.execute('SELECT 1 FROM mission_xp_awards WHERE mission_id=? LIMIT 1',
                            (mission_id,)).fetchone():
                raise ValueError('This mission has already awarded XP')
            participants = conn.execute("""SELECT p.id,p.level FROM mission_participants mp
                JOIN players p ON p.id=mp.player_id WHERE mp.mission_id=? ORDER BY p.id""",
                (mission_id,)).fetchall()
            if not participants:
                raise ValueError('Select participating characters before awarding XP')
            if total_xp < len(participants):
                raise ValueError('Total XP must give every participant at least 1 XP')
            share, remainder = divmod(total_xp, len(participants))
            awards = []
            for index, player in enumerate(participants):
                if not 1 <= (player['level'] or 0) <= 20:
                    raise ValueError(f"Invalid character level for {player['id']}")
                baseline = conn.execute('SELECT 1 FROM character_xp_baselines WHERE player_id=?',
                                        (player['id'],)).fetchone()
                if baseline is None:
                    conn.execute("""INSERT INTO character_xp_baselines
                        (player_id,starting_xp,starting_level) VALUES(?,?,?)""",
                        (player['id'], LEVEL_XP[player['level'] - 1], player['level']))
                amount = share + (1 if index < remainder else 0)
                conn.execute("""INSERT INTO mission_xp_awards
                    (mission_id,player_id,xp,total_award,reason,awarded_by)
                    VALUES(?,?,?,?,?,?)""",
                    (mission_id, player['id'], amount, total_xp, reason, actor))
                awards.append({'player_id': player['id'], 'xp': amount})
            conn.execute("""INSERT INTO entity_audit(entity_id,action,actor,detail)
                VALUES(?,'mission_xp_award',?,?)""",
                (mission_id, actor,
                 f'total={total_xp}; participants={len(participants)}; reason={reason}'))
            return awards
