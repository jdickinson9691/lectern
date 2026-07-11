from __future__ import annotations

import csv
import re
from pathlib import Path

from ..database.repositories import Repository


def _first_integer(value: str, default: int) -> int:
    match = re.search(r"\d+", value or "")
    return int(match.group()) if match else default


def import_monster_catalog(db_path: Path, csv_path: Path) -> int:
    """Upsert the distributable monster catalog into a Lectern database."""
    repo = Repository(db_path)
    count = 0
    seen: set[str] = set()
    with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            name = (row.get("Name") or "").strip()
            if not name or name in seen:
                continue
            seen.add(name)
            notes = []
            for label in ("Environment", "Tags", "Initiative"):
                if value := (row.get(label) or "").strip():
                    notes.append(f"{label}: {value}")
            traits = [
                label for label in ("Legendary", "Lair", "Unique")
                if (row.get(label) or "").strip().lower() in {"true", "yes", "1", "x"}
            ]
            if traits:
                notes.append("Traits: " + ", ".join(traits))
            if url := (row.get("Url") or "").strip():
                notes.append(f"URL: {url}")
            raw_ac = (row.get("AC") or "").strip()
            if raw_ac and not raw_ac.isdigit():
                notes.append(f"AC details: {raw_ac}")
            repo.upsert_monster({
                "name": name,
                "size": (row.get("Size") or "").strip(),
                "type": (row.get("Type") or "").strip(),
                "alignment": (row.get("Alignment") or "").strip(),
                "armor_class": _first_integer(raw_ac, 10),
                "hit_points": _first_integer(row.get("HP") or "", 1),
                "speed": "",
                "challenge_rating": (row.get("CR") or "").strip(),
                "xp": 0,
                "str_score": 0, "dex_score": 0, "con_score": 0,
                "int_score": 0, "wis_score": 0, "cha_score": 0,
                "source": (row.get("Source") or "CSV catalog").strip(),
                "notes": "; ".join(notes),
            })
            count += 1
    return count
