from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from ..database.schema import connect

CSV_TABLES = {
    "players": "Players",
    "monsters": "Monsters",
    "weapons": "Weapons",
    "armor": "Armor",
    "equipment": "Equipment",
    "magic_items": "Magic Items",
    "spells": "Spells",
    "rules_reference": "Rules Reference",
}

INTEGER_HINTS = {
    "id", "level", "armor_class", "max_hp", "current_hp", "initiative_mod", "xp",
    "hit_points", "str_score", "dex_score", "con_score", "int_score", "wis_score", "cha_score",
    "str_base", "dex_base", "con_base", "int_base", "wis_base", "cha_base",
    "str_race_bonus", "dex_race_bonus", "con_race_bonus", "int_race_bonus", "wis_race_bonus", "cha_race_bonus",
    "str_feat_bonus", "dex_feat_bonus", "con_feat_bonus", "int_feat_bonus", "wis_feat_bonus", "cha_feat_bonus",
    "str_total", "dex_total", "con_total", "int_total", "wis_total", "cha_total",
    "str_mod", "dex_mod", "con_mod", "int_mod", "wis_mod", "cha_mod",
    "currency_cp", "currency_sp", "currency_ep", "currency_gp", "currency_pp",
}

ABILITY_FIELDS = ["str", "dex", "con", "int", "wis", "cha"]

def ability_modifier(score: int) -> int:
    return (int(score) - 10) // 2

class CsvTransferService:
    """Export/import editable database tables as UTF-8 CSV files.

    Import semantics are intentionally safe for DM-edited CSV files:
    * id may be present but is ignored for inserts and normal upserts.
    * Most tables upsert by name.
    * rules_reference upserts by category + name.
    * Unknown columns in a CSV are ignored.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def table_columns(self, table: str) -> list[str]:
        self._validate_table(table)
        with connect(self.db_path) as conn:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return [row[1] for row in rows]

    def export_table(self, table: str, output_path: Path) -> int:
        self._validate_table(table)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        columns = self.table_columns(table)
        with connect(self.db_path) as conn:
            rows = conn.execute(f"SELECT {','.join(columns)} FROM {table} ORDER BY {self._order_clause(table)}").fetchall()
        with output_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({col: row[col] for col in columns})
        return len(rows)

    def export_all(self, output_dir: Path) -> dict[str, int]:
        output_dir.mkdir(parents=True, exist_ok=True)
        results: dict[str, int] = {}
        for table in CSV_TABLES:
            results[table] = self.export_table(table, output_dir / f"{table}.csv")
        return results


    def validate_table(self, table: str, csv_path: Path) -> list[dict]:
        """Validate a CSV and return row-level status records without changing the database."""
        return self.preview_table(table, csv_path)

    def preview_table(self, table: str, csv_path: Path) -> list[dict]:
        """Return row-level import preview records.

        Status values: New, Modified, Unchanged, Duplicate, Error.
        """
        self._validate_table(table)
        if not csv_path.exists():
            raise FileNotFoundError(csv_path)
        columns = self.table_columns(table)
        editable_columns = [c for c in columns if c != "id"]
        preview: list[dict] = []
        seen_keys: set[tuple] = set()
        with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return []
            incoming = [c for c in reader.fieldnames if c in editable_columns]
            unknown = [c for c in reader.fieldnames if c not in columns]
            if table == "rules_reference" and not {"category", "name"}.issubset(set(incoming)):
                return [{"row_number": 1, "status": "Error", "key": "rules_reference", "message": "CSV must include category and name columns."}]
            if table != "rules_reference" and "name" not in incoming:
                return [{"row_number": 1, "status": "Error", "key": table, "message": "CSV must include a name column."}]
            with connect(self.db_path) as conn:
                for row_number, raw_row in enumerate(reader, start=2):
                    try:
                        data = {col: self._clean_value(col, raw_row.get(col)) for col in incoming}
                        if table == "players":
                            self._normalize_player_row(data)
                        key = self._row_key(table, data)
                        if not key or not all(str(v or "").strip() for v in key):
                            preview.append({"row_number": row_number, "status": "Error", "key": "", "message": "Missing required key field."})
                            continue
                        if key in seen_keys:
                            preview.append({"row_number": row_number, "status": "Duplicate", "key": self._key_label(table, key), "message": "Duplicate key in import file."})
                            continue
                        seen_keys.add(key)
                        existing = self._existing_row(conn, table, key)
                        if existing is None:
                            status = "New"
                            message = "Will insert new row."
                        else:
                            changed = []
                            for col, value in data.items():
                                if col == "id":
                                    continue
                                old = existing[col] if col in existing.keys() else None
                                if str(old if old is not None else "") != str(value if value is not None else ""):
                                    changed.append(col)
                            status = "Modified" if changed else "Unchanged"
                            message = ", ".join(changed[:8]) + ("..." if len(changed) > 8 else "") if changed else "No changes detected."
                        if unknown:
                            message = (message + " " if message else "") + f"Ignored unknown columns: {', '.join(unknown)}."
                        preview.append({"row_number": row_number, "status": status, "key": self._key_label(table, key), "message": message})
                    except Exception as exc:
                        preview.append({"row_number": row_number, "status": "Error", "key": str(raw_row.get("name") or ""), "message": str(exc)})
        return preview

    def _row_key(self, table: str, data: dict) -> tuple:
        if table == "rules_reference":
            return (str(data.get("category") or "").strip(), str(data.get("name") or "").strip())
        return (str(data.get("name") or "").strip(),)

    def _key_label(self, table: str, key: tuple) -> str:
        return " / ".join(str(v) for v in key) if table == "rules_reference" else str(key[0])

    def _existing_row(self, conn, table: str, key: tuple):
        if table == "rules_reference":
            return conn.execute("SELECT * FROM rules_reference WHERE category=? AND name=?", key).fetchone()
        return conn.execute(f"SELECT * FROM {table} WHERE name=?", (key[0],)).fetchone()

    def import_table(self, table: str, csv_path: Path) -> int:
        self._validate_table(table)
        if not csv_path.exists():
            raise FileNotFoundError(csv_path)
        columns = self.table_columns(table)
        editable_columns = [c for c in columns if c != "id"]
        count = 0
        with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return 0
            incoming = [c for c in reader.fieldnames if c in editable_columns]
            if table == "rules_reference" and not {"category", "name"}.issubset(set(incoming)):
                raise ValueError("rules_reference CSV must include category and name columns.")
            if table != "rules_reference" and "name" not in incoming:
                raise ValueError(f"{table} CSV must include a name column.")
            with connect(self.db_path) as conn:
                for raw_row in reader:
                    data = {col: self._clean_value(col, raw_row.get(col)) for col in incoming}
                    if not str(data.get("name") or "").strip():
                        continue
                    if table == "players":
                        self._normalize_player_row(data)
                    self._upsert(conn, table, data)
                    count += 1
                conn.execute(
                    "INSERT INTO import_history(file_path,rows_imported,notes) VALUES(?,?,?)",
                    (str(csv_path), count, f"CSV import into {table}"),
                )
        return count

    def _upsert(self, conn, table: str, data: dict) -> None:
        fields = list(data.keys())
        placeholders = ",".join(":" + f for f in fields)
        if table == "rules_reference":
            conflict = "category,name"
            updates = ",".join(f"{f}=excluded.{f}" for f in fields if f not in {"category", "name"}) or "description=excluded.description"
        else:
            conflict = "name"
            updates = ",".join(f"{f}=excluded.{f}" for f in fields if f != "name") or "name=excluded.name"
        conn.execute(
            f"INSERT INTO {table}({','.join(fields)}) VALUES({placeholders}) ON CONFLICT({conflict}) DO UPDATE SET {updates}",
            data,
        )

    def _normalize_player_row(self, data: dict) -> None:
        for ability in ABILITY_FIELDS:
            base_key = f"{ability}_base"
            race_key = f"{ability}_race_bonus"
            feat_key = f"{ability}_feat_bonus"
            total_key = f"{ability}_total"
            mod_key = f"{ability}_mod"
            base = int(data.get(base_key) or 10)
            race = int(data.get(race_key) or 0)
            feat = int(data.get(feat_key) or 0)
            total = base + race + feat
            data[base_key] = base
            data[race_key] = race
            data[feat_key] = feat
            data[total_key] = total
            data[mod_key] = ability_modifier(total)
        if "initiative_mod" not in data or data.get("initiative_mod") in (None, ""):
            data["initiative_mod"] = data.get("dex_mod", 0)

    def _clean_value(self, column: str, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
        if value == "":
            return 0 if column in INTEGER_HINTS and column != "id" else ""
        if column in INTEGER_HINTS:
            try:
                return int(float(value))
            except (TypeError, ValueError):
                return 0
        return value

    def _order_clause(self, table: str) -> str:
        return "category, name" if table == "rules_reference" else "name"

    def _validate_table(self, table: str) -> None:
        if table not in CSV_TABLES:
            raise ValueError(f"Unsupported CSV table: {table}")
