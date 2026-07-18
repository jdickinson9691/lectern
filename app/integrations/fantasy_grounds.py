from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ..database.repositories import ABILITY_FIELDS, PLAYER_COLUMNS
from ..database.schema import connect
from ..paths import user_data_dir


SCHEMA_VERSION = 1
PROVIDER = "fantasy_grounds"
SUPPORTED_RULESET = "5E"
CONFIG_FILE = "fantasy_grounds_sync.json"


class FantasyGroundsSyncError(ValueError):
    """Raised when a snapshot cannot be safely imported."""


@dataclass(frozen=True)
class SyncResult:
    applied: bool
    sequence: int
    campaign_name: str
    counts: dict[str, int]
    message: str


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise FantasyGroundsSyncError(message)


def _require_text(value: Any, field: str) -> str:
    _require(isinstance(value, str) and bool(value.strip()), f"{field} must be a non-empty string")
    return value.strip()


def _record(record: Any, field: str, expected_type: str | None = None) -> dict[str, Any]:
    _require(isinstance(record, dict), f"{field} must be an object")
    for key in ("source_key", "record_type", "name", "source_path", "fields", "raw"):
        _require(key in record, f"{field}.{key} is required")
    _require_text(record["source_key"], f"{field}.source_key")
    record_type = _require_text(record["record_type"], f"{field}.record_type")
    if expected_type:
        _require(record_type == expected_type, f"{field}.record_type must be {expected_type}")
    _require_text(record["name"], f"{field}.name")
    _require_text(record["source_path"], f"{field}.source_path")
    _require(record.get("module_name") is None or isinstance(record.get("module_name"), str), f"{field}.module_name must be a string or null")
    _require(isinstance(record["fields"], dict), f"{field}.fields must be an object")
    _require(isinstance(record["raw"], dict), f"{field}.raw must be an object")
    return record


def validate_snapshot(payload: Any) -> dict[str, Any]:
    """Validate contract invariants without adding a runtime JSON Schema dependency."""
    _require(isinstance(payload, dict), "Snapshot root must be an object")
    _require(payload.get("schema_version") == SCHEMA_VERSION, f"Unsupported schema_version; expected {SCHEMA_VERSION}")
    _require(isinstance(payload.get("sequence"), int) and payload["sequence"] >= 1, "sequence must be a positive integer")
    generated_at = _require_text(payload.get("generated_at"), "generated_at")
    try:
        datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FantasyGroundsSyncError("generated_at must be an ISO-8601 timestamp") from exc

    source = payload.get("source")
    _require(isinstance(source, dict), "source must be an object")
    _require(source.get("provider") == PROVIDER, f"source.provider must be {PROVIDER}")
    _require_text(source.get("extension_version"), "source.extension_version")
    _require(source.get("ruleset") == SUPPORTED_RULESET, f"Only the {SUPPORTED_RULESET} ruleset is supported")
    _require_text(source.get("campaign_key"), "source.campaign_key")
    _require_text(source.get("campaign_name"), "source.campaign_name")
    _require(isinstance(source.get("modules"), list) and all(isinstance(item, str) for item in source["modules"]), "source.modules must be a string array")

    catalog = payload.get("catalog")
    _require(isinstance(catalog, dict), "catalog must be an object")
    seen: set[str] = set()
    for category in ("classes", "subclasses", "species", "feats", "backgrounds"):
        records = catalog.get(category)
        _require(isinstance(records, list), f"catalog.{category} must be an array")
        for index, item in enumerate(records):
            record = _record(item, f"catalog.{category}[{index}]")
            _require(record["source_key"] not in seen, f"Duplicate source_key: {record['source_key']}")
            seen.add(record["source_key"])

    characters = payload.get("characters")
    _require(isinstance(characters, list), "characters must be an array")
    for index, item in enumerate(characters):
        record = _record(item, f"characters[{index}]", "character")
        _require(record["source_key"] not in seen, f"Duplicate source_key: {record['source_key']}")
        seen.add(record["source_key"])

    encounters = payload.get("encounters")
    _require(isinstance(encounters, list), "encounters must be an array")
    for index, item in enumerate(encounters):
        record = _record(item, f"encounters[{index}]", "encounter")
        _require(record["source_key"] not in seen, f"Duplicate source_key: {record['source_key']}")
        seen.add(record["source_key"])
        _require(isinstance(record.get("participants"), list), f"encounters[{index}].participants must be an array")
        for participant_index, participant in enumerate(record["participants"]):
            field = f"encounters[{index}].participants[{participant_index}]"
            _require(isinstance(participant, dict), f"{field} must be an object")
            _require_text(participant.get("source_key"), f"{field}.source_key")
            _require_text(participant.get("name"), f"{field}.name")
            _require(isinstance(participant.get("quantity"), int) and participant["quantity"] >= 1, f"{field}.quantity must be a positive integer")

    combat = payload.get("combat")
    _require(isinstance(combat, dict), "combat must be an object")
    _require(isinstance(combat.get("active"), bool), "combat.active must be a boolean")
    _require(isinstance(combat.get("round"), int) and combat["round"] >= 0, "combat.round must be a non-negative integer")
    _require(combat.get("active_source_key") is None or isinstance(combat.get("active_source_key"), str), "combat.active_source_key must be a string or null")
    _require(isinstance(combat.get("combatants"), list), "combat.combatants must be an array")
    combat_keys: set[str] = set()
    for index, combatant in enumerate(combat["combatants"]):
        field = f"combat.combatants[{index}]"
        _require(isinstance(combatant, dict), f"{field} must be an object")
        key = _require_text(combatant.get("source_key"), f"{field}.source_key")
        _require(key not in combat_keys, f"Duplicate combatant source_key: {key}")
        combat_keys.add(key)
        _require_text(combatant.get("name"), f"{field}.name")
        _require(isinstance(combatant.get("order"), int) and combatant["order"] >= 0, f"{field}.order must be a non-negative integer")
        _require(combatant.get("initiative") is None or isinstance(combatant.get("initiative"), (int, float)), f"{field}.initiative must be numeric or null")
        _require(combatant.get("armor_class") is None or isinstance(combatant.get("armor_class"), int), f"{field}.armor_class must be an integer or null")
        hit_points = combatant.get("hit_points")
        _require(isinstance(hit_points, dict), f"{field}.hit_points must be an object")
        for hp_field in ("maximum", "current", "temporary", "wounds"):
            _require(hit_points.get(hp_field) is None or isinstance(hit_points.get(hp_field), int), f"{field}.hit_points.{hp_field} must be an integer or null")
        _require(isinstance(combatant.get("effects"), list), f"{field}.effects must be an array")
        _require(isinstance(combatant.get("raw"), dict), f"{field}.raw must be an object")
    return payload


def load_snapshot(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FantasyGroundsSyncError(f"Could not read snapshot: {exc}") from exc
    return validate_snapshot(payload)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _field(fields: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        value = fields.get(name)
        if value not in (None, ""):
            return value
    return default


class FantasyGroundsSyncService:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.config_path = user_data_dir() / "config" / CONFIG_FILE

    def configured_folder(self) -> Path | None:
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            folder_text = data.get("handoff_folder", "")
            if not isinstance(folder_text, str) or not folder_text.strip():
                return None
            return Path(folder_text)
        except (OSError, json.JSONDecodeError, TypeError):
            return None

    def configure_folder(self, selected: Path) -> Path:
        selected = Path(selected).expanduser().resolve()
        if selected.name.lower() == "lectern-sync":
            folder = selected
        else:
            folder = selected / "lectern-sync"
        folder.mkdir(parents=True, exist_ok=True)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(_json({"handoff_folder": str(folder)}), encoding="utf-8")
        return folder

    def snapshot_path(self) -> Path | None:
        folder = self.configured_folder()
        return folder / "snapshot.json" if folder else None

    def status_path(self) -> Path | None:
        folder = self.configured_folder()
        return folder / "status.json" if folder else None

    def read_extension_status(self) -> dict[str, Any]:
        path = self.status_path()
        if not path or not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def list_sources(self):
        with connect(self.db_path) as conn:
            return conn.execute("SELECT * FROM external_sources ORDER BY last_sync_at DESC, campaign_name").fetchall()

    def list_records(self, source_id: int):
        with connect(self.db_path) as conn:
            return conn.execute(
                """
                SELECT id,source_id,source_key,record_type,name,module_name,source_path,
                       content_hash,last_seen_sequence,is_stale
                FROM external_records WHERE source_id=? ORDER BY is_stale, record_type, name
                """,
                (source_id,),
            ).fetchall()

    def import_configured_snapshot(self) -> SyncResult:
        path = self.snapshot_path()
        if not path:
            raise FantasyGroundsSyncError("Select a Fantasy Grounds campaign or lectern-sync folder first")
        if not path.exists():
            raise FantasyGroundsSyncError(f"No snapshot has been exported yet: {path}")
        return self.import_snapshot(path)

    def import_snapshot(self, path: Path) -> SyncResult:
        payload = load_snapshot(path)
        source = payload["source"]
        sequence = int(payload["sequence"])
        counts = {
            "classes": len(payload["catalog"]["classes"]),
            "subclasses": len(payload["catalog"]["subclasses"]),
            "species": len(payload["catalog"]["species"]),
            "feats": len(payload["catalog"]["feats"]),
            "backgrounds": len(payload["catalog"]["backgrounds"]),
            "characters": len(payload["characters"]),
            "encounters": len(payload["encounters"]),
            "combatants": len(payload["combat"]["combatants"]),
        }
        handoff_path = str(Path(path).resolve().parent)
        try:
            with connect(self.db_path) as conn:
                source_id, previous_sequence = self._upsert_source(conn, source, handoff_path)
                if sequence <= previous_sequence:
                    return SyncResult(False, sequence, source["campaign_name"], counts, "Snapshot already applied")
                conn.execute("UPDATE external_records SET is_stale=1 WHERE source_id=?", (source_id,))
                campaign_id = self._linked_campaign(conn, source_id, source)
                for category, records in payload["catalog"].items():
                    for record in records:
                        self._upsert_external_record(conn, source_id, record, sequence)
                        self._upsert_rule_reference(conn, category, record)
                for record in payload["characters"]:
                    self._upsert_external_record(conn, source_id, record, sequence)
                    self._upsert_character(conn, source_id, record)
                for record in payload["encounters"]:
                    self._upsert_external_record(conn, source_id, record, sequence)
                    self._upsert_encounter(conn, source_id, campaign_id, record)
                self._upsert_live_combat(conn, source_id, campaign_id, source["campaign_name"], payload["combat"], sequence)
                conn.execute(
                    "UPDATE external_sources SET last_sequence=?, last_sync_at=?, last_error='' WHERE id=?",
                    (sequence, datetime.now(timezone.utc).isoformat(), source_id),
                )
        except FantasyGroundsSyncError:
            raise
        except Exception as exc:
            raise FantasyGroundsSyncError(f"Snapshot import failed and was rolled back: {exc}") from exc
        return SyncResult(True, sequence, source["campaign_name"], counts, "Snapshot imported")

    def _upsert_source(self, conn, source: dict[str, Any], handoff_path: str) -> tuple[int, int]:
        conn.execute(
            """
            INSERT INTO external_sources(provider,campaign_key,campaign_name,ruleset,extension_version,handoff_path)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(provider,campaign_key) DO UPDATE SET
              campaign_name=excluded.campaign_name,ruleset=excluded.ruleset,
              extension_version=excluded.extension_version,handoff_path=excluded.handoff_path
            """,
            (PROVIDER, source["campaign_key"], source["campaign_name"], source["ruleset"], source["extension_version"], handoff_path),
        )
        row = conn.execute(
            "SELECT id,last_sequence FROM external_sources WHERE provider=? AND campaign_key=?",
            (PROVIDER, source["campaign_key"]),
        ).fetchone()
        return int(row["id"]), int(row["last_sequence"] or 0)

    def _upsert_external_record(self, conn, source_id: int, record: dict[str, Any], sequence: int) -> int:
        raw_json = _json(record)
        digest = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()
        conn.execute(
            """
            INSERT INTO external_records(source_id,source_key,record_type,name,module_name,source_path,content_hash,raw_json,last_seen_sequence,is_stale)
            VALUES(?,?,?,?,?,?,?,?,?,0)
            ON CONFLICT(source_id,source_key) DO UPDATE SET
              record_type=excluded.record_type,name=excluded.name,module_name=excluded.module_name,
              source_path=excluded.source_path,content_hash=excluded.content_hash,raw_json=excluded.raw_json,
              last_seen_sequence=excluded.last_seen_sequence,is_stale=0
            """,
            (source_id, record["source_key"], record["record_type"], record["name"], record.get("module_name"), record["source_path"], digest, raw_json, sequence),
        )
        return int(conn.execute("SELECT id FROM external_records WHERE source_id=? AND source_key=?", (source_id, record["source_key"])).fetchone()[0])

    def _upsert_rule_reference(self, conn, category: str, record: dict[str, Any]) -> None:
        fields = record["fields"]
        description = str(_field(fields, "description", "text", "summary", "features", default="") or "")
        sync_category = f"Fantasy Grounds {category.replace('_', ' ').title()}"
        conn.execute(
            """
            INSERT INTO rules_reference(category,name,description) VALUES(?,?,?)
            ON CONFLICT(category,name) DO UPDATE SET description=excluded.description
            """,
            (sync_category, record["name"], description),
        )

    def _find_link(self, conn, source_id: int, source_key: str, entity_type: str) -> int | None:
        row = conn.execute(
            "SELECT entity_id FROM external_entity_links WHERE source_id=? AND source_key=? AND entity_type=?",
            (source_id, source_key, entity_type),
        ).fetchone()
        return int(row[0]) if row else None

    def _link(self, conn, source_id: int, source_key: str, entity_type: str, entity_id: int) -> None:
        conn.execute(
            """
            INSERT INTO external_entity_links(source_id,source_key,entity_type,entity_id) VALUES(?,?,?,?)
            ON CONFLICT(source_id,source_key,entity_type) DO UPDATE SET entity_id=excluded.entity_id
            """,
            (source_id, source_key, entity_type, entity_id),
        )

    def _unique_name(self, conn, table: str, requested: str, current_id: int | None = None) -> str:
        candidate = requested.strip() or "Fantasy Grounds Record"
        row = conn.execute(f"SELECT id FROM {table} WHERE name=?", (candidate,)).fetchone()
        if not row or (current_id is not None and int(row[0]) == current_id):
            return candidate
        base = f"{candidate} [Fantasy Grounds]"
        candidate = base
        suffix = 2
        while True:
            row = conn.execute(f"SELECT id FROM {table} WHERE name=?", (candidate,)).fetchone()
            if not row or (current_id is not None and int(row[0]) == current_id):
                return candidate
            candidate = f"{base} {suffix}"
            suffix += 1

    def _linked_campaign(self, conn, source_id: int, source: dict[str, Any]) -> int:
        source_key = f"campaign:{source['campaign_key']}"
        campaign_id = self._find_link(conn, source_id, source_key, "campaign")
        name = self._unique_name(conn, "campaigns", source["campaign_name"], campaign_id)
        description = "Synchronized one-way from Fantasy Grounds Unity 5E."
        if campaign_id and conn.execute("SELECT 1 FROM campaigns WHERE id=?", (campaign_id,)).fetchone():
            conn.execute("UPDATE campaigns SET name=?,description=? WHERE id=?", (name, description, campaign_id))
        else:
            cursor = conn.execute("INSERT INTO campaigns(name,description) VALUES(?,?)", (name, description))
            campaign_id = int(cursor.lastrowid)
            self._link(conn, source_id, source_key, "campaign", campaign_id)
        return campaign_id

    def _player_payload(self, record: dict[str, Any]) -> dict[str, Any]:
        fields = record["fields"]
        abilities = fields.get("abilities") if isinstance(fields.get("abilities"), dict) else {}
        payload: dict[str, Any] = {column: None for column in PLAYER_COLUMNS}
        payload.update({
            "name": record["name"],
            "player_name": str(_field(fields, "player_name", "owner", default="") or ""),
            "species": str(_field(fields, "species", "race", default="") or ""),
            "class_name": str(_field(fields, "class_name", "class", default="") or ""),
            "subclass": str(_field(fields, "subclass", "specialization", default="") or ""),
            "background": str(_field(fields, "background", default="") or ""),
            "level": max(1, _as_int(_field(fields, "level", default=1), 1)),
            "armor_class": _as_int(_field(fields, "armor_class", "ac", default=10), 10),
            "max_hp": max(1, _as_int(_field(fields, "max_hp", "hp", default=1), 1)),
            "initiative_mod": _as_int(_field(fields, "initiative_mod", "init", default=0), 0),
            "feats": str(_field(fields, "feats", default="") or ""),
            "notes": "Synchronized from Fantasy Grounds. Edit source-owned values in Fantasy Grounds.",
        })
        payload["current_hp"] = _as_int(_field(fields, "current_hp", default=payload["max_hp"]), payload["max_hp"])
        for ability in ABILITY_FIELDS:
            score = _as_int(_field(abilities, ability, ability.upper(), default=_field(fields, ability, f"{ability}_score", default=10)), 10)
            payload[f"{ability}_base"] = score
            payload[f"{ability}_race_bonus"] = 0
            payload[f"{ability}_feat_bonus"] = 0
            payload[f"{ability}_total"] = score
            payload[f"{ability}_mod"] = (score - 10) // 2
        for text_column in (
            "equipped_weapon", "equipped_armor", "equipment", "skill_proficiencies", "skill_expertise",
            "saving_throw_proficiencies", "inventory", "portrait_path", "spellcasting_ability",
        ):
            payload[text_column] = str(_field(fields, text_column, default="") or "")
        for currency in ("currency_cp", "currency_sp", "currency_ep", "currency_gp", "currency_pp"):
            payload[currency] = _as_int(_field(fields, currency, default=0), 0)
        return payload

    def _upsert_character(self, conn, source_id: int, record: dict[str, Any]) -> None:
        player_id = self._find_link(conn, source_id, record["source_key"], "player")
        if player_id and not conn.execute("SELECT 1 FROM players WHERE id=?", (player_id,)).fetchone():
            player_id = None
        payload = self._player_payload(record)
        payload["name"] = self._unique_name(conn, "players", payload["name"], player_id)
        fields = PLAYER_COLUMNS
        if player_id:
            assignments = ",".join(f"{field}=:{field}" for field in fields)
            payload["id"] = player_id
            conn.execute(f"UPDATE players SET {assignments} WHERE id=:id", payload)
        else:
            cursor = conn.execute(
                f"INSERT INTO players({','.join(fields)}) VALUES({','.join(':'+field for field in fields)})",
                payload,
            )
            player_id = int(cursor.lastrowid)
            self._link(conn, source_id, record["source_key"], "player", player_id)

    def _upsert_encounter(self, conn, source_id: int, campaign_id: int, record: dict[str, Any]) -> None:
        encounter_id = self._find_link(conn, source_id, record["source_key"], "encounter")
        if encounter_id and not conn.execute("SELECT 1 FROM encounters WHERE id=?", (encounter_id,)).fetchone():
            encounter_id = None
        name = self._unique_name(conn, "encounters", record["name"], encounter_id)
        if encounter_id:
            conn.execute("UPDATE encounters SET name=?,campaign_id=?,status='draft' WHERE id=?", (name, campaign_id, encounter_id))
            conn.execute("DELETE FROM combatants WHERE encounter_id=?", (encounter_id,))
        else:
            cursor = conn.execute("INSERT INTO encounters(name,status,round,active_index,campaign_id) VALUES(?,'draft',1,0,?)", (name, campaign_id))
            encounter_id = int(cursor.lastrowid)
            self._link(conn, source_id, record["source_key"], "encounter", encounter_id)
        order = 0
        for participant in record["participants"]:
            for copy_index in range(participant["quantity"]):
                display_name = participant["name"] if participant["quantity"] == 1 else f"{participant['name']} #{copy_index + 1}"
                conn.execute(
                    """
                    INSERT INTO combatants(encounter_id,source_type,source_id,name,armor_class,max_hp,current_hp,initiative_mod,sort_order)
                    VALUES(?,?,?,?,10,1,1,0,?)
                    """,
                    (encounter_id, PROVIDER, None, display_name, order),
                )
                order += 1

    def _upsert_live_combat(self, conn, source_id: int, campaign_id: int, campaign_name: str, combat: dict[str, Any], sequence: int) -> None:
        source_key = "live-combat"
        encounter_id = self._find_link(conn, source_id, source_key, "encounter")
        if encounter_id and not conn.execute("SELECT 1 FROM encounters WHERE id=?", (encounter_id,)).fetchone():
            encounter_id = None
        name = self._unique_name(conn, "encounters", f"{campaign_name} - Fantasy Grounds Live Combat", encounter_id)
        status = "active" if combat["active"] else "completed"
        active_key = combat.get("active_source_key")
        active_index = 0
        for index, item in enumerate(combat["combatants"]):
            if item["source_key"] == active_key:
                active_index = index
                break
        if encounter_id:
            conn.execute(
                "UPDATE encounters SET name=?,campaign_id=?,status=?,round=?,active_index=? WHERE id=?",
                (name, campaign_id, status, max(1, combat["round"]), active_index, encounter_id),
            )
            conn.execute("DELETE FROM combatants WHERE encounter_id=?", (encounter_id,))
        else:
            cursor = conn.execute(
                "INSERT INTO encounters(name,status,round,active_index,campaign_id) VALUES(?,?,?,?,?)",
                (name, status, max(1, combat["round"]), active_index, campaign_id),
            )
            encounter_id = int(cursor.lastrowid)
            self._link(conn, source_id, source_key, "encounter", encounter_id)
        for item in combat["combatants"]:
            external_record = {
                "source_key": item["source_key"], "record_type": "combatant", "name": item["name"],
                "source_path": str(item["raw"].get("source_path") or item["source_key"]), "module_name": None,
                "fields": {key: value for key, value in item.items() if key != "raw"}, "raw": item["raw"],
            }
            external_record_id = self._upsert_external_record(conn, source_id, external_record, sequence)
            hp = item["hit_points"]
            maximum = max(1, _as_int(hp.get("maximum"), 1))
            current = hp.get("current")
            if current is None:
                wounds = _as_int(hp.get("wounds"), 0)
                current = max(0, maximum - wounds)
            cursor = conn.execute(
                """
                INSERT INTO combatants(encounter_id,source_type,source_id,name,armor_class,max_hp,current_hp,initiative_mod,initiative,sort_order,is_active)
                VALUES(?,?,?,?,?,?,?,?,?,?,1)
                """,
                (encounter_id, PROVIDER, external_record_id, item["name"], _as_int(item.get("armor_class"), 10), maximum,
                 max(0, _as_int(current, maximum)), 0, item.get("initiative"), item["order"]),
            )
            combatant_id = int(cursor.lastrowid)
            for effect in item["effects"]:
                if isinstance(effect, dict):
                    label = str(effect.get("name") or effect.get("label") or effect.get("effect") or "Effect")
                    duration = effect.get("duration_rounds", effect.get("duration"))
                    notes = str(effect.get("source") or effect.get("notes") or "")
                else:
                    label, duration, notes = str(effect), None, ""
                conn.execute(
                    "INSERT INTO active_conditions(combatant_id,condition_name,duration_rounds,notes) VALUES(?,?,?,?)",
                    (combatant_id, label, _as_int(duration, 0) if duration not in (None, "") else None, notes),
                )


def iter_contract_records(payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for records in payload["catalog"].values():
        yield from records
    yield from payload["characters"]
    yield from payload["encounters"]
