from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ..database.repositories import ABILITY_FIELDS, PLAYER_COLUMNS
from ..database.schema import connect
from ..paths import user_data_dir
from ..services.data_workflow import DataWorkflowService


SCHEMA_VERSION = 1
PROVIDER = "fantasy_grounds"
SUPPORTED_RULESET = "5E"
CONFIG_FILE = "fantasy_grounds_sync.json"
EVENT_TYPES = {"action", "attack", "damage", "effect", "healing", "outcome", "save", "spell", "turn_end", "turn_start"}
ACTION_TYPES = {
    "action": "Action", "attack": "Attack", "damage": "Damage", "effect": "Effect",
    "healing": "Healing", "outcome": "Outcome", "save": "Save", "spell": "Spell",
    "turn_end": "Turn End", "turn_start": "Turn Start",
}
FG_DAMAGE_TYPES = (
    "acid", "bludgeoning", "cold", "fire", "force", "lightning", "necrotic",
    "piercing", "poison", "psychic", "radiant", "slashing", "thunder",
    "adamantine", "cold-forged iron", "magic", "silver",
)


class FantasyGroundsSyncError(ValueError):
    """Raised when a snapshot cannot be safely imported."""


@dataclass(frozen=True)
class SyncResult:
    applied: bool
    sequence: int
    campaign_name: str
    counts: dict[str, int]
    message: str
    preferred_encounter_id: int | None = None


@dataclass(frozen=True)
class FormattedLogEvent:
    actor: str
    action_type: str
    details: str
    incomplete: bool = False
    actor_source_key: str = ""
    actor_side: str = "unknown"
    amount: int | None = None
    result_code: str = ""
    natural_roll: int | None = None
    damage_types: str = ""
    damage_components_json: str = "[]"


@dataclass(frozen=True)
class ReprocessPreview:
    affected_encounters: int
    total_events: int
    improvable_events: int
    missing_source_events: int


@dataclass(frozen=True)
class ReprocessResult:
    updated: int
    unchanged: int
    incomplete: int
    failed: int
    backup_path: Path


@dataclass(frozen=True)
class ClearImportPreview:
    source_id: int
    campaign_name: str
    campaigns: int
    encounters: int
    combatants: int
    combat_log_rows: int
    players: int
    external_records: int
    external_events: int
    local_encounters_detached: int


@dataclass(frozen=True)
class ClearImportResult:
    preview: ClearImportPreview
    backup_path: Path


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
            for stat in ("armor_class", "hit_points", "initiative_mod"):
                _require(participant.get(stat) is None or isinstance(participant.get(stat), int), f"{field}.{stat} must be an integer or null")
            _require(participant.get("raw") is None or isinstance(participant.get("raw"), dict), f"{field}.raw must be an object or null")

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

    _require(combat.get("session_key") is None or isinstance(combat.get("session_key"), str), "combat.session_key must be a string or null")
    _require(combat.get("session_name") is None or isinstance(combat.get("session_name"), str), "combat.session_name must be a string or null")
    _require(combat.get("session_state") is None or combat.get("session_state") in {"inactive", "open", "closed"}, "combat.session_state is invalid")
    _require(combat.get("started_at") is None or isinstance(combat.get("started_at"), str), "combat.started_at must be a string or null")
    if combat.get("started_at"):
        try:
            datetime.fromisoformat(combat["started_at"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise FantasyGroundsSyncError("combat.started_at must be an ISO-8601 timestamp") from exc
    _require(combat.get("outcome") is None or combat.get("outcome") in {"victory", "defeat", "retreat", "unresolved"}, "combat.outcome is invalid")
    _require(combat.get("completed_at") is None or isinstance(combat.get("completed_at"), str), "combat.completed_at must be a string or null")
    if combat.get("completed_at"):
        try:
            datetime.fromisoformat(combat["completed_at"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise FantasyGroundsSyncError("combat.completed_at must be an ISO-8601 timestamp") from exc
    events = payload.get("events", [])
    _require(isinstance(events, list), "events must be an array")
    event_keys: set[str] = set()
    for index, event in enumerate(events):
        field = f"events[{index}]"
        _require(isinstance(event, dict), f"{field} must be an object")
        event_key = _require_text(event.get("event_id"), f"{field}.event_id")
        _require(event_key not in event_keys, f"Duplicate event_id: {event_key}")
        event_keys.add(event_key)
        _require(isinstance(event.get("sequence"), int) and event["sequence"] >= 1, f"{field}.sequence must be a positive integer")
        occurred_at = _require_text(event.get("timestamp"), f"{field}.timestamp")
        try:
            datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise FantasyGroundsSyncError(f"{field}.timestamp must be an ISO-8601 timestamp") from exc
        _require(event.get("type") in EVENT_TYPES, f"{field}.type is unsupported")
        _require(isinstance(event.get("round"), int) and event["round"] >= 0, f"{field}.round must be a non-negative integer")
        _require_text(event.get("encounter_source_key"), f"{field}.encounter_source_key")
        for role in ("actor", "target"):
            participant = event.get(role)
            _require(participant is None or isinstance(participant, dict), f"{field}.{role} must be an object or null")
            if isinstance(participant, dict):
                _require_text(participant.get("name"), f"{field}.{role}.name")
                _require(participant.get("source_key") is None or isinstance(participant.get("source_key"), str), f"{field}.{role}.source_key must be a string or null")
        _require(event.get("amount") is None or isinstance(event.get("amount"), int), f"{field}.amount must be an integer or null")
        _require(isinstance(event.get("description"), str), f"{field}.description must be a string")
        _require(isinstance(event.get("metadata"), dict), f"{field}.metadata must be an object")
    return payload


def load_snapshot(path: Path) -> dict[str, Any]:
    try:
        # Fantasy Grounds File.saveTextFile emits UTF-8 with a BOM on Windows.
        # utf-8-sig accepts that output while remaining compatible with plain UTF-8 fixtures.
        payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FantasyGroundsSyncError(f"Could not read snapshot: {exc}") from exc
    # Lectern Sync 1.4.0 encoded an empty Lua metadata table as [] instead of {}.
    # Normalize only that unambiguous empty value so already-recorded encounters
    # remain importable; non-empty arrays still fail contract validation.
    if isinstance(payload, dict) and isinstance(payload.get("events"), list):
        for event in payload["events"]:
            if isinstance(event, dict) and event.get("metadata") == []:
                event["metadata"] = {}
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


def _cap_component_applied(components: list[dict[str, Any]], applied_cap: int | None) -> None:
    """Cap normalized component-applied totals to the target's actual HP loss."""
    if applied_cap is None:
        return
    applied_values = [
        max(0, float(component.get("applied", 0)))
        if isinstance(component.get("applied"), (int, float)) and not isinstance(component.get("applied"), bool)
        else 0.0
        for component in components
    ]
    total = sum(applied_values)
    cap = max(0, int(applied_cap))
    if total <= cap or total <= 0:
        return
    exact = [value * cap / total for value in applied_values]
    allocated = [int(value) for value in exact]
    remainder = cap - sum(allocated)
    order = sorted(range(len(exact)), key=lambda index: (exact[index] - allocated[index], -index), reverse=True)
    for index in order[:remainder]:
        allocated[index] += 1
    for component, value in zip(components, allocated):
        if "applied" in component:
            component["applied"] = value


def _component_total(metadata: dict[str, Any], field: str) -> float | None:
    raw_components = metadata.get("damage_components")
    if not isinstance(raw_components, list):
        return None
    values = [
        component.get(field)
        for component in raw_components
        if isinstance(component, dict)
        and isinstance(component.get(field), (int, float))
        and not isinstance(component.get(field), bool)
    ]
    return sum(float(value) for value in values) if values else None


def _damage_metadata(
    metadata: dict[str, Any], description: str, is_damage: bool, applied_cap: int | None = None
) -> tuple[str, str]:
    """Return canonical damage types and component JSON, with legacy description fallback."""
    types: list[str] = []
    components: list[dict[str, Any]] = []

    def add_type(value: Any) -> None:
        candidate = str(value or "").strip().casefold()
        if candidate in FG_DAMAGE_TYPES and candidate not in types:
            types.append(candidate)

    raw_types = metadata.get("damage_types")
    if isinstance(raw_types, list):
        for value in raw_types:
            add_type(value)
    elif isinstance(raw_types, str):
        for value in raw_types.split(","):
            add_type(value)

    raw_components = metadata.get("damage_components")
    if isinstance(raw_components, list):
        for raw in raw_components:
            if not isinstance(raw, dict):
                continue
            component_types = raw.get("types")
            if isinstance(component_types, str):
                component_types = component_types.split(",")
            normalized_types: list[str] = []
            if isinstance(component_types, list):
                for value in component_types:
                    candidate = str(value or "").strip().casefold()
                    if candidate in FG_DAMAGE_TYPES and candidate not in normalized_types:
                        normalized_types.append(candidate)
                        add_type(candidate)
            component: dict[str, Any] = {"types": normalized_types}
            for key in ("rolled", "applied", "resisted", "vulnerable"):
                value = raw.get(key)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    component[key] = value
            if normalized_types or len(component) > 1:
                components.append(component)

    if is_damage:
        _cap_component_applied(components, applied_cap)

    if not types and is_damage:
        lower_description = description.casefold()
        for match in re.finditer(r"\[type:\s*([^\]]+)\]", lower_description):
            type_text = re.sub(r"\s*\([-+]?\d+(?:\.\d+)?\)\s*$", "", match.group(1))
            for value in type_text.split(","):
                add_type(value)
        if not types:
            for candidate in FG_DAMAGE_TYPES:
                if re.search(rf"(?<![a-z-]){re.escape(candidate)}(?![a-z-])", lower_description):
                    add_type(candidate)

    if is_damage and not types:
        types.append("unknown")
    return ", ".join(types), _json(components)


def format_event_log(event: dict[str, Any]) -> FormattedLogEvent:
    """Convert one Fantasy Grounds event into the canonical Lectern log fields."""
    if not isinstance(event, dict):
        raise FantasyGroundsSyncError("Stored event must be a JSON object")
    event_type = event.get("type")
    if event_type not in EVENT_TYPES:
        raise FantasyGroundsSyncError("Stored event has no supported event type")

    actor = event.get("actor") if isinstance(event.get("actor"), dict) else {}
    target = event.get("target") if isinstance(event.get("target"), dict) else {}
    metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
    actor_name = str(actor.get("name") or "Fantasy Grounds")
    actor_source_key = str(actor.get("source_key") or "")
    actor_side = "party" if ":character:" in actor_source_key.casefold() else "unknown"
    target_name = str(target.get("name") or "Target not reported")
    description = str(event.get("description") or "").strip()
    action_name = str(metadata.get("action_name") or "").strip()
    roll_total = metadata.get("roll_total")
    raw_roll = metadata.get("raw_roll")
    modifier = metadata.get("modifier")
    target_ac = metadata.get("target_ac")
    result = str(metadata.get("result") or "").strip()
    natural_roll = metadata.get("natural_roll", raw_roll)
    try:
        natural_roll = int(natural_roll) if natural_roll is not None else None
    except (TypeError, ValueError):
        natural_roll = None
    result_text = result.casefold()
    if "critical hit" in result_text or (natural_roll == 20 and metadata.get("authoritative_result")):
        result_code = "critical_hit"
    elif "automatic miss" in result_text or (natural_roll == 1 and metadata.get("authoritative_result")):
        result_code = "critical_miss"
    elif result_text == "hit":
        result_code = "hit"
    elif result_text == "miss":
        result_code = "miss"
    else:
        result_code = ""
    is_damage_roll = event_type == "action" and "damage" in (
        f"{metadata.get('roll_type', '')} {description}"
    ).lower()
    component_cap = None
    if event_type == "damage" and isinstance(event.get("amount"), (int, float)) and not isinstance(event.get("amount"), bool):
        component_cap = max(0, int(event["amount"]))
    damage_types, damage_components_json = _damage_metadata(
        metadata, description, is_damage_roll or event_type == "damage", component_cap
    )
    action_type = "Damage Roll" if is_damage_roll else ACTION_TYPES[event_type]
    lifecycle = str(metadata.get("lifecycle") or "")
    if lifecycle == "encounter_start":
        action_type = "Encounter Start"
    elif lifecycle == "encounter_end":
        action_type = "Encounter End"
    incomplete = not bool(actor.get("name"))

    roll_text = str(roll_total) if roll_total is not None else "Roll not reported"
    if roll_total is not None and raw_roll is not None and modifier is not None:
        modifier_text = f"{modifier:+g}" if isinstance(modifier, (int, float)) else str(modifier)
        roll_text += f" (dice {raw_roll}; modifiers {modifier_text})"

    if event_type == "attack":
        defense = f"Against AC {target_ac}" if target_ac is not None else "Target AC not reported"
        outcome = result or (f"Net attack roll {roll_total}" if roll_total is not None else "Result not reported")
        if result and roll_total is not None and target_ac is not None:
            outcome += f" ({roll_total} vs AC {target_ac})"
        details = " | ".join((roll_text, target_name, defense, action_name or "Attack not reported", outcome))
        incomplete = incomplete or not bool(target.get("name")) or any(
            value is None for value in (roll_total, raw_roll, modifier, target_ac)
        ) or not bool(action_name or description) or not bool(result)
    elif is_damage_roll:
        defense = f"Against AC {target_ac}" if target_ac is not None else "Target AC not reported"
        outcome = f"{roll_total} damage rolled" if roll_total is not None else "Damage result not reported"
        details = " | ".join((roll_text, target_name, defense, action_name or "Damage not reported", outcome))
        incomplete = incomplete or not bool(target.get("name")) or any(
            value is None for value in (roll_total, raw_roll, modifier)
        ) or not bool(action_name or description)
    elif event_type in {"damage", "healing"}:
        amount = event.get("amount")
        try:
            applied = max(0, int(amount)) if amount is not None else 0
        except (TypeError, ValueError) as exc:
            raise FantasyGroundsSyncError("Stored damage or healing amount is invalid") from exc
        hp = "Target HP not reported"
        if metadata.get("current_hp") is not None:
            hp_value = str(metadata["current_hp"])
            if metadata.get("maximum_hp") is not None:
                hp_value += f"/{metadata['maximum_hp']}"
            hp = f"Target HP {hp_value}"
        verb = "damage applied" if event_type == "damage" else "healing applied"
        outcome = f"{applied} {verb}"
        rolled = metadata.get("roll_total")
        component_rolled = _component_total(metadata, "rolled")
        if (rolled is None or rolled == 0) and component_rolled is not None and component_rolled > 0:
            rolled = int(component_rolled) if component_rolled.is_integer() else component_rolled
        adjustment = metadata.get("adjustment")
        if event_type == "damage" and rolled is not None and (
            not isinstance(adjustment, (int, float)) or (metadata.get("roll_total") == 0 and component_rolled)
        ):
            adjustment = applied - rolled
        if event_type == "damage" and rolled is not None:
            if applied == 0:
                outcome = f"0 damage applied from {rolled} rolled (negated)"
            elif isinstance(adjustment, (int, float)) and adjustment < 0:
                outcome = f"{applied} damage applied from {rolled} rolled (reduced by {-adjustment:g})"
            elif isinstance(adjustment, (int, float)) and adjustment > 0:
                outcome = f"{applied} damage applied from {rolled} rolled (increased by {adjustment:g})"
            else:
                outcome = f"{applied} damage applied from {rolled} rolled"
        if metadata.get("attribution") == "manual_or_unattributed":
            actor_name = "Manual / Unattributed"
            actor_source_key = ""
            actor_side = "unknown"
            incomplete = False
        details = " | ".join((str(applied), target_name, hp, action_name or ACTION_TYPES[event_type], outcome))
        incomplete = incomplete or amount is None or not bool(target.get("name")) or metadata.get("current_hp") is None
    elif roll_total is not None:
        if event_type == "save":
            defense = f"Against DC {target_ac}" if target_ac is not None else "Save DC not reported"
        elif target_ac is not None:
            defense = f"Against defense {target_ac}"
        else:
            defense = "Defense not reported"
        outcome = result or "Result not reported"
        details = " | ".join((
            roll_text, target_name, defense,
            action_name or f"{ACTION_TYPES[event_type]} not reported", outcome,
        ))
        incomplete = True
    else:
        details = description or action_name or f"{ACTION_TYPES[event_type]} details not reported"
        incomplete = incomplete or not bool(description or action_name)

    normalized_amount = applied if event_type in {"damage", "healing"} else None
    return FormattedLogEvent(
        actor_name, action_type, details, incomplete, actor_source_key, actor_side,
        normalized_amount, result_code, natural_roll, damage_types, damage_components_json,
    )


def _merge_enriched_event(existing: Any, incoming: Any) -> Any:
    """Merge a later form of the same source event without losing earlier evidence."""
    if isinstance(existing, dict) and isinstance(incoming, dict):
        merged = dict(existing)
        for key, value in incoming.items():
            merged[key] = _merge_enriched_event(merged.get(key), value) if key in merged else value
        return merged
    if incoming in (None, "") or incoming == [] or incoming == {}:
        return existing
    return incoming


class FantasyGroundsSyncService:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.config_path = user_data_dir() / "config" / CONFIG_FILE

    def _config_data(self) -> dict[str, Any]:
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError, TypeError):
            return {}

    def configured_folder(self) -> Path | None:
        folder_text = self._config_data().get("handoff_folder", "")
        if not isinstance(folder_text, str) or not folder_text.strip():
            return None
        return Path(folder_text)

    def automatic_import_enabled(self) -> bool:
        return bool(self._config_data().get("automatic_import_enabled", True))

    def set_automatic_import_enabled(self, enabled: bool) -> None:
        data = self._config_data()
        data["automatic_import_enabled"] = bool(enabled)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(_json(data), encoding="utf-8")

    def configure_folder(self, selected: Path) -> Path:
        selected = Path(selected).expanduser().resolve()
        if selected.name.lower() == "lectern-sync":
            folder = selected
        else:
            folder = selected / "lectern-sync"
        folder.mkdir(parents=True, exist_ok=True)
        data = self._config_data()
        data["handoff_folder"] = str(folder)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(_json(data), encoding="utf-8")
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

    def _exclusive_linked_ids(self, conn, source_id: int, entity_type: str) -> list[int]:
        return [
            int(row[0])
            for row in conn.execute(
                """
                SELECT DISTINCT own.entity_id
                FROM external_entity_links own
                WHERE own.source_id=? AND own.entity_type=?
                  AND NOT EXISTS (
                    SELECT 1 FROM external_entity_links other
                    WHERE other.source_id<>own.source_id
                      AND other.entity_type=own.entity_type
                      AND other.entity_id=own.entity_id
                  )
                """,
                (source_id, entity_type),
            ).fetchall()
        ]

    def preview_clear_imported_data(self, source_id: int) -> ClearImportPreview:
        with connect(self.db_path) as conn:
            source = conn.execute(
                "SELECT id,campaign_name FROM external_sources WHERE id=? AND provider=?",
                (source_id, PROVIDER),
            ).fetchone()
            if not source:
                raise FantasyGroundsSyncError("The selected Fantasy Grounds import no longer exists")
            campaign_ids = self._exclusive_linked_ids(conn, source_id, "campaign")
            encounter_ids = self._exclusive_linked_ids(conn, source_id, "encounter")
            player_ids = self._exclusive_linked_ids(conn, source_id, "player")
            event_log_ids = {
                int(row[0]) for row in conn.execute(
                    "SELECT turn_log_id FROM external_events WHERE source_id=?", (source_id,)
                ).fetchall()
            }
            combatants = 0
            combat_log_ids = set(event_log_ids)
            if encounter_ids:
                placeholders = ",".join("?" for _ in encounter_ids)
                combatants = int(conn.execute(
                    f"SELECT COUNT(*) FROM combatants WHERE encounter_id IN ({placeholders})", encounter_ids
                ).fetchone()[0])
                combat_log_ids.update(
                    int(row[0]) for row in conn.execute(
                        f"SELECT id FROM turn_log WHERE encounter_id IN ({placeholders})", encounter_ids
                    ).fetchall()
                )
            detached = 0
            if campaign_ids:
                placeholders = ",".join("?" for _ in campaign_ids)
                parameters = [*campaign_ids, *encounter_ids]
                exclusion = ""
                if encounter_ids:
                    exclusion = f" AND id NOT IN ({','.join('?' for _ in encounter_ids)})"
                detached = int(conn.execute(
                    f"SELECT COUNT(*) FROM encounters WHERE campaign_id IN ({placeholders}){exclusion}", parameters
                ).fetchone()[0])
            return ClearImportPreview(
                int(source["id"]), str(source["campaign_name"]), len(campaign_ids), len(encounter_ids),
                combatants, len(combat_log_ids), len(player_ids),
                int(conn.execute("SELECT COUNT(*) FROM external_records WHERE source_id=?", (source_id,)).fetchone()[0]),
                int(conn.execute("SELECT COUNT(*) FROM external_events WHERE source_id=?", (source_id,)).fetchone()[0]),
                detached,
            )

    def clear_imported_data(self, source_id: int) -> ClearImportResult:
        preview = self.preview_clear_imported_data(source_id)
        workflow = DataWorkflowService(self.db_path)
        backup_stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup = workflow.backup_database(
            workflow.backup_dir / f"pre_fg_clear_{backup_stamp}.db"
        )
        try:
            with connect(self.db_path) as conn:
                campaign_ids = self._exclusive_linked_ids(conn, source_id, "campaign")
                encounter_ids = self._exclusive_linked_ids(conn, source_id, "encounter")
                player_ids = self._exclusive_linked_ids(conn, source_id, "player")
                event_log_ids = [
                    int(row[0]) for row in conn.execute(
                        "SELECT turn_log_id FROM external_events WHERE source_id=?", (source_id,)
                    ).fetchall()
                ]
                if event_log_ids:
                    placeholders = ",".join("?" for _ in event_log_ids)
                    conn.execute(f"DELETE FROM turn_log WHERE id IN ({placeholders})", event_log_ids)
                if encounter_ids:
                    placeholders = ",".join("?" for _ in encounter_ids)
                    conn.execute(f"DELETE FROM turn_log WHERE encounter_id IN ({placeholders})", encounter_ids)
                    conn.execute(f"DELETE FROM encounters WHERE id IN ({placeholders})", encounter_ids)
                if campaign_ids:
                    placeholders = ",".join("?" for _ in campaign_ids)
                    conn.execute(f"UPDATE encounters SET campaign_id=NULL WHERE campaign_id IN ({placeholders})", campaign_ids)
                    conn.execute(f"DELETE FROM campaigns WHERE id IN ({placeholders})", campaign_ids)
                if player_ids:
                    placeholders = ",".join("?" for _ in player_ids)
                    conn.execute(f"DELETE FROM players WHERE id IN ({placeholders})", player_ids)
                deleted = conn.execute(
                    "DELETE FROM external_sources WHERE id=? AND provider=?", (source_id, PROVIDER)
                ).rowcount
                if deleted != 1:
                    raise FantasyGroundsSyncError("The selected Fantasy Grounds import no longer exists")
        except FantasyGroundsSyncError:
            raise
        except Exception as exc:
            raise FantasyGroundsSyncError(f"Clearing imported Fantasy Grounds data failed and was rolled back: {exc}") from exc
        self.set_automatic_import_enabled(False)
        return ClearImportResult(preview, backup)

    def preview_log_reprocessing(self) -> ReprocessPreview:
        improvable = 0
        missing = 0
        encounters: set[int] = set()
        with connect(self.db_path) as conn:
            rows = self._reprocess_rows(conn)
            for row in rows:
                encounters.add(int(row["encounter_id"]))
                try:
                    event = json.loads(row["raw_json"])
                    formatted = format_event_log(event)
                except (json.JSONDecodeError, FantasyGroundsSyncError, TypeError):
                    missing += 1
                    continue
                actor_side = self._event_actor_side(conn, row["source_id"], event, formatted)
                source_missing = formatted.incomplete
                current = (
                    row["actor"], row["action_type"], row["details"], row["actor_source_key"],
                    row["actor_side"], row["amount"], row["result_code"], row["natural_roll"],
                    row["damage_types"], row["damage_components_json"],
                )
                desired = (
                    formatted.actor, formatted.action_type, formatted.details, formatted.actor_source_key,
                    actor_side, formatted.amount, formatted.result_code, formatted.natural_roll,
                    formatted.damage_types, formatted.damage_components_json,
                )
                if row["log_id"] is not None and current != desired:
                    improvable += 1
                if row["log_id"] is None:
                    source_missing = True
                if source_missing:
                    missing += 1
        return ReprocessPreview(len(encounters), len(rows), improvable, missing)

    def reprocess_imported_logs(self) -> ReprocessResult:
        workflow = DataWorkflowService(self.db_path)
        backup_stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup = workflow.backup_database(
            workflow.backup_dir / f"pre_fg_log_reprocess_{backup_stamp}.db"
        )
        updated = unchanged = incomplete = failed = 0
        try:
            with connect(self.db_path) as conn:
                rows = self._reprocess_rows(conn)
                for row in rows:
                    try:
                        event = json.loads(row["raw_json"])
                        formatted = format_event_log(event)
                    except (json.JSONDecodeError, FantasyGroundsSyncError, TypeError):
                        failed += 1
                        continue
                    if row["log_id"] is None:
                        failed += 1
                        continue
                    actor_side = self._event_actor_side(conn, row["source_id"], event, formatted)
                    desired = (
                        formatted.actor, formatted.action_type, formatted.details, formatted.actor_source_key,
                        actor_side, formatted.amount, formatted.result_code, formatted.natural_roll,
                        formatted.damage_types, formatted.damage_components_json,
                    )
                    current = (
                        row["actor"], row["action_type"], row["details"], row["actor_source_key"],
                        row["actor_side"], row["amount"], row["result_code"], row["natural_roll"],
                        row["damage_types"], row["damage_components_json"],
                    )
                    if current != desired:
                        conn.execute(
                            """
                            UPDATE turn_log SET actor=?,action_type=?,details=?,actor_source_key=?,
                                actor_side=?,amount=?,result_code=?,natural_roll=?,damage_types=?,
                                damage_components_json=? WHERE id=?
                            """,
                            (*desired, row["turn_log_id"]),
                        )
                    if formatted.incomplete:
                        incomplete += 1
                    elif current != desired:
                        updated += 1
                    else:
                        unchanged += 1
        except Exception as exc:
            raise FantasyGroundsSyncError(f"Historical log reprocessing failed and was rolled back: {exc}") from exc
        return ReprocessResult(updated, unchanged, incomplete, failed, backup)

    def _reprocess_rows(self, conn=None):
        owns_connection = conn is None
        if owns_connection:
            conn = connect(self.db_path)
        try:
            return conn.execute(
                """
                SELECT ee.source_id,ee.encounter_id,ee.turn_log_id,ee.raw_json,
                       tl.id AS log_id,tl.actor,tl.action_type,tl.details,tl.actor_source_key,
                       tl.actor_side,tl.amount,tl.result_code,tl.natural_roll,
                       tl.damage_types,tl.damage_components_json
                FROM external_events ee
                JOIN external_sources es ON es.id=ee.source_id AND es.provider=?
                LEFT JOIN turn_log tl ON tl.id=ee.turn_log_id
                ORDER BY ee.id
                """,
                (PROVIDER,),
            ).fetchall()
        finally:
            if owns_connection:
                conn.close()

    def _event_actor_side(self, conn, source_id: int, event: dict[str, Any], formatted: FormattedLogEvent) -> str:
        if formatted.actor_side != "unknown" or not formatted.actor_source_key:
            return formatted.actor_side
        owns_connection = conn is None
        if owns_connection:
            conn = connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT record_type,raw_json FROM external_records WHERE source_id=? AND source_key=?",
                (source_id, formatted.actor_source_key),
            ).fetchone()
            if not row:
                return "unknown"
            if row["record_type"] == "character":
                return "party"
            try:
                raw_record = json.loads(row["raw_json"])
            except (json.JSONDecodeError, TypeError):
                return "unknown"
            raw = raw_record.get("raw") if isinstance(raw_record, dict) else {}
            friend_foe = str((raw or {}).get("friendfoe") or "").casefold()
            return {"friend": "party", "foe": "hostile", "neutral": "neutral"}.get(friend_foe, "unknown")
        finally:
            if owns_connection:
                conn.close()

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
            "events": len(payload.get("events", [])),
        }
        handoff_path = str(Path(path).resolve().parent)
        try:
            with connect(self.db_path) as conn:
                source_id, previous_sequence = self._upsert_source(conn, source, handoff_path)
                if sequence <= previous_sequence:
                    repaired = self._repair_character_equipment(conn, source_id, payload["characters"])
                    if repaired:
                        return SyncResult(
                            True, sequence, source["campaign_name"], counts,
                            f"Snapshot already applied; restored SRD-matched equipment for {repaired} character{'s' if repaired != 1 else ''}",
                        )
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
                prepared_encounter_ids: dict[str, int] = {}
                for record in payload["encounters"]:
                    self._upsert_external_record(conn, source_id, record, sequence)
                    prepared_encounter_ids[record["source_key"]] = self._upsert_encounter(
                        conn, source_id, campaign_id, record
                    )
                live_encounter_id = self._upsert_live_combat(
                    conn, source_id, campaign_id, source["campaign_name"], payload["combat"], sequence
                )
                prepared_source_key = self._match_prepared_encounter(payload["encounters"], payload["combat"])
                if live_encounter_id is not None:
                    live_source_key = self._live_combat_source_key(payload["combat"])
                    conn.execute(
                        "DELETE FROM external_entity_links WHERE source_id=? AND source_key=? AND entity_type='prepared_encounter'",
                        (source_id, live_source_key),
                    )
                    if prepared_source_key in prepared_encounter_ids:
                        self._link(
                            conn, source_id, live_source_key, "prepared_encounter",
                            prepared_encounter_ids[prepared_source_key],
                        )
                self._import_events(conn, source_id, campaign_id, source["campaign_name"], payload.get("events", []), sequence)
                conn.execute(
                    "UPDATE external_sources SET last_sequence=?, last_sync_at=?, last_error='' WHERE id=?",
                    (sequence, datetime.now(timezone.utc).isoformat(), source_id),
                )
        except FantasyGroundsSyncError:
            raise
        except Exception as exc:
            raise FantasyGroundsSyncError(f"Snapshot import failed and was rolled back: {exc}") from exc
        return SyncResult(
            True, sequence, source["campaign_name"], counts, "Snapshot imported", live_encounter_id
        )

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

    @staticmethod
    def _equipment_names_from_record(record: dict[str, Any], item_kind: str) -> list[str]:
        fields = record.get("fields") if isinstance(record.get("fields"), dict) else {}
        direct = str(fields.get(f"equipped_{item_kind}") or "").strip()
        if direct:
            return [name.strip() for name in direct.split(";") if name.strip()]

        raw = record.get("raw") if isinstance(record.get("raw"), dict) else {}
        inventory = raw.get("inventorylist")
        items = inventory.values() if isinstance(inventory, dict) else inventory if isinstance(inventory, list) else []
        names: list[str] = []
        for item in items:
            if not isinstance(item, dict) or _as_int(item.get("carried"), 0) != 2:
                continue
            item_type = str(item.get("type") or "").strip().casefold()
            subtype = str(item.get("subtype") or "").strip().casefold()
            is_kind = item_type == item_kind
            if item_kind == "weapon":
                is_kind = is_kind or "weapon" in subtype
            elif item_kind == "armor":
                is_kind = is_kind or "armor" in subtype or subtype == "shield"
            name = str(item.get("name") or "").strip()
            if is_kind and name and name.casefold() not in {value.casefold() for value in names}:
                names.append(name)
        return names

    @staticmethod
    def _reference_key(value: str) -> str:
        return " ".join(re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).split())

    def _canonical_equipment_name(self, conn, table: str, source_name: str) -> str:
        source_name = str(source_name or "").strip()
        if not source_name:
            return ""
        canonical = {
            self._reference_key(row["name"]): str(row["name"])
            for row in conn.execute(f"SELECT name FROM {table}").fetchall()
        }
        candidates = [source_name]
        without_note = re.sub(r"\s*\([^()]*(?:focus|equipped|wielded|active)[^()]*\)\s*$", "", source_name, flags=re.IGNORECASE).strip()
        if without_note and without_note != source_name:
            candidates.append(without_note)
        if table == "armor":
            candidates.extend(
                candidate[:-6].strip() if candidate.casefold().endswith(" armor") else f"{candidate} Armor"
                for candidate in list(candidates)
            )
        for candidate in candidates:
            match = canonical.get(self._reference_key(candidate))
            if match:
                return match
        return source_name

    def _character_equipment(self, conn, record: dict[str, Any]) -> tuple[str, str]:
        results = []
        for item_kind, table in (("weapon", "weapons"), ("armor", "armor")):
            names = self._equipment_names_from_record(record, item_kind)
            canonical_names: list[str] = []
            for name in names:
                canonical = self._canonical_equipment_name(conn, table, name)
                if canonical and canonical.casefold() not in {value.casefold() for value in canonical_names}:
                    canonical_names.append(canonical)
            results.append("; ".join(canonical_names))
        return results[0], results[1]

    def _repair_character_equipment(self, conn, source_id: int, records: list[dict[str, Any]]) -> int:
        repaired = 0
        for record in records:
            player_id = self._find_link(conn, source_id, record["source_key"], "player")
            if not player_id:
                continue
            weapon, armor = self._character_equipment(conn, record)
            current = conn.execute(
                "SELECT equipped_weapon,equipped_armor FROM players WHERE id=?", (player_id,)
            ).fetchone()
            if not current:
                continue
            updated_weapon = weapon or str(current["equipped_weapon"] or "")
            updated_armor = armor or str(current["equipped_armor"] or "")
            if updated_weapon == str(current["equipped_weapon"] or "") and updated_armor == str(current["equipped_armor"] or ""):
                continue
            conn.execute(
                "UPDATE players SET equipped_weapon=?,equipped_armor=? WHERE id=?",
                (updated_weapon, updated_armor, player_id),
            )
            repaired += 1
        return repaired

    def _player_payload(self, conn, record: dict[str, Any]) -> dict[str, Any]:
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
        payload["equipped_weapon"], payload["equipped_armor"] = self._character_equipment(conn, record)
        for currency in ("currency_cp", "currency_sp", "currency_ep", "currency_gp", "currency_pp"):
            payload[currency] = _as_int(_field(fields, currency, default=0), 0)
        return payload

    def _upsert_character(self, conn, source_id: int, record: dict[str, Any]) -> None:
        player_id = self._find_link(conn, source_id, record["source_key"], "player")
        if player_id and not conn.execute("SELECT 1 FROM players WHERE id=?", (player_id,)).fetchone():
            player_id = None
        payload = self._player_payload(conn, record)
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

    def _upsert_encounter(self, conn, source_id: int, campaign_id: int, record: dict[str, Any]) -> int:
        encounter_id = self._find_link(conn, source_id, record["source_key"], "encounter")
        if encounter_id and not conn.execute("SELECT 1 FROM encounters WHERE id=?", (encounter_id,)).fetchone():
            encounter_id = None
        name = self._unique_name(conn, "encounters", record["name"], encounter_id)
        if encounter_id:
            conn.execute(
                "UPDATE encounters SET name=?,campaign_id=?,status='draft',round=1,active_index=0,outcome='',completed_at=NULL WHERE id=?",
                (name, campaign_id, encounter_id),
            )
            conn.execute("DELETE FROM combatants WHERE encounter_id=?", (encounter_id,))
        else:
            cursor = conn.execute("INSERT INTO encounters(name,status,round,active_index,campaign_id) VALUES(?,'draft',1,0,?)", (name, campaign_id))
            encounter_id = int(cursor.lastrowid)
            self._link(conn, source_id, record["source_key"], "encounter", encounter_id)
        order = 0
        for participant in record["participants"]:
            armor_class = _as_int(participant.get("armor_class"), 10)
            hit_points = max(1, _as_int(participant.get("hit_points"), 1))
            initiative_mod = _as_int(participant.get("initiative_mod"), 0)
            for copy_index in range(participant["quantity"]):
                display_name = participant["name"] if participant["quantity"] == 1 else f"{participant['name']} #{copy_index + 1}"
                conn.execute(
                    """
                    INSERT INTO combatants(encounter_id,source_type,source_id,name,armor_class,max_hp,current_hp,initiative_mod,sort_order)
                    VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (encounter_id, PROVIDER, None, display_name, armor_class, hit_points, hit_points, initiative_mod, order),
                )
                order += 1
        return encounter_id

    @staticmethod
    def _live_combat_source_key(combat: dict[str, Any]) -> str:
        session_key = str(combat.get("session_key") or "live-combat")
        return f"live-combat:{session_key}" if session_key != "live-combat" else "live-combat"

    @staticmethod
    def _match_name(value: Any) -> str:
        text = re.sub(r"\s+(?:#?\d+)\s*$", "", str(value or "").strip().casefold())
        return " ".join(re.findall(r"[a-z0-9]+", text))

    def _match_prepared_encounter(
        self, encounters: list[dict[str, Any]], combat: dict[str, Any]
    ) -> str | None:
        """Return one unambiguous prepared encounter source key for live combat."""
        if not encounters:
            return None
        live_names = {
            self._match_name(item.get("name")) for item in combat.get("combatants", [])
            if self._match_name(item.get("name"))
        }
        session_name = self._match_name(combat.get("session_name"))
        scored: list[tuple[tuple[int, int, float], str]] = []
        for record in encounters:
            prepared_name = self._match_name(record.get("name"))
            participant_names = {
                self._match_name(item.get("name")) for item in record.get("participants", [])
                if self._match_name(item.get("name"))
            }
            overlap = len(live_names & participant_names)
            name_match = int(bool(
                session_name and prepared_name
                and (session_name == prepared_name or session_name.startswith(prepared_name + " "))
            ))
            overlap_ratio = overlap / max(1, len(participant_names | live_names))
            if name_match or overlap:
                scored.append(((name_match, overlap, overlap_ratio), str(record["source_key"])))
        if not scored:
            return None
        scored.sort(reverse=True)
        if len(scored) > 1 and scored[0][0] == scored[1][0]:
            return None
        return scored[0][1]

    def _upsert_live_combat(self, conn, source_id: int, campaign_id: int, campaign_name: str, combat: dict[str, Any], sequence: int) -> int | None:
        session_state = combat.get("session_state")
        if session_state == "inactive" and not combat.get("session_key"):
            return None
        source_key = self._live_combat_source_key(combat)
        encounter_id = self._find_link(conn, source_id, source_key, "encounter")
        if encounter_id and not conn.execute("SELECT 1 FROM encounters WHERE id=?", (encounter_id,)).fetchone():
            encounter_id = None
        requested_name = str(combat.get("session_name") or f"{campaign_name} - Fantasy Grounds Live Combat")
        name = self._unique_name(conn, "encounters", requested_name, encounter_id)
        outcome = str(combat.get("outcome") or "")
        completed_at = combat.get("completed_at")
        status = "completed" if session_state == "closed" or outcome else ("active" if session_state == "open" or combat["active"] else "completed")
        active_key = combat.get("active_source_key")
        active_index = 0
        for index, item in enumerate(combat["combatants"]):
            if item["source_key"] == active_key:
                active_index = index
                break
        if encounter_id:
            conn.execute(
                "UPDATE encounters SET name=?,campaign_id=?,status=?,round=?,active_index=?,outcome=?,completed_at=? WHERE id=?",
                (name, campaign_id, status, max(1, combat["round"]), active_index, outcome, completed_at, encounter_id),
            )
            if combat["combatants"]:
                conn.execute("DELETE FROM combatants WHERE encounter_id=?", (encounter_id,))
        else:
            cursor = conn.execute(
                "INSERT INTO encounters(name,status,round,active_index,campaign_id,outcome,completed_at) VALUES(?,?,?,?,?,?,?)",
                (name, status, max(1, combat["round"]), active_index, campaign_id, outcome, completed_at),
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
        return encounter_id

    def _event_encounter(self, conn, source_id: int, campaign_id: int, campaign_name: str, event: dict[str, Any]) -> int:
        session_key = event["encounter_source_key"]
        source_key = f"live-combat:{session_key}" if session_key != "live-combat" else "live-combat"
        linked = self._find_link(conn, source_id, source_key, "encounter")
        if linked and conn.execute("SELECT 1 FROM encounters WHERE id=?", (linked,)).fetchone():
            return linked
        requested = f"{campaign_name} - Fantasy Grounds Combat {event['timestamp'][:10]}"
        name = self._unique_name(conn, "encounters", requested)
        cursor = conn.execute(
            "INSERT INTO encounters(name,status,round,active_index,campaign_id) VALUES(?,'completed',?,0,?)",
            (name, max(1, int(event["round"])), campaign_id),
        )
        encounter_id = int(cursor.lastrowid)
        self._link(conn, source_id, source_key, "encounter", encounter_id)
        return encounter_id

    def _import_events(self, conn, source_id: int, campaign_id: int, campaign_name: str, events: list[dict[str, Any]], sequence: int) -> None:
        for event in sorted(events, key=lambda item: item["sequence"]):
            existing = conn.execute(
                "SELECT encounter_id,turn_log_id,raw_json FROM external_events WHERE source_id=? AND event_key=?",
                (source_id, event["event_id"]),
            ).fetchone()
            if existing:
                try:
                    stored_event = json.loads(str(existing["raw_json"]))
                except (TypeError, ValueError, json.JSONDecodeError):
                    stored_event = {}
                merged_event = _merge_enriched_event(stored_event, event)
                merged_json = _json(merged_event)
                if merged_json == str(existing["raw_json"]):
                    continue
                formatted = format_event_log(merged_event)
                actor_side = self._event_actor_side(conn, source_id, merged_event, formatted)
                conn.execute(
                    """
                    UPDATE turn_log SET round=?,actor=?,action_type=?,details=?,actor_source_key=?,actor_side=?,
                      amount=?,result_code=?,natural_roll=?,damage_types=?,damage_components_json=?,created_at=?
                    WHERE id=?
                    """,
                    (max(1, int(merged_event["round"])), formatted.actor, formatted.action_type,
                     formatted.details, formatted.actor_source_key, actor_side, formatted.amount,
                     formatted.result_code, formatted.natural_roll, formatted.damage_types,
                     formatted.damage_components_json, merged_event["timestamp"], existing["turn_log_id"]),
                )
                conn.execute(
                    """
                    UPDATE external_events SET event_type=?,occurred_at=?,raw_json=?,imported_sequence=?
                    WHERE source_id=? AND event_key=?
                    """,
                    (merged_event["type"], merged_event["timestamp"], merged_json, sequence,
                     source_id, merged_event["event_id"]),
                )
                continue
            encounter_id = self._event_encounter(conn, source_id, campaign_id, campaign_name, event)
            event_type = event["type"]
            formatted = format_event_log(event)
            actor_side = self._event_actor_side(conn, source_id, event, formatted)
            cursor = conn.execute(
                """
                INSERT INTO turn_log(
                    encounter_id,round,actor,action_type,details,actor_source_key,actor_side,
                    amount,result_code,natural_roll,damage_types,damage_components_json,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (encounter_id, max(1, int(event["round"])), formatted.actor,
                 formatted.action_type, formatted.details, formatted.actor_source_key, actor_side,
                 formatted.amount, formatted.result_code, formatted.natural_roll,
                 formatted.damage_types, formatted.damage_components_json, event["timestamp"]),
            )
            turn_log_id = int(cursor.lastrowid)
            conn.execute(
                "INSERT INTO external_events(source_id,event_key,encounter_id,turn_log_id,event_type,occurred_at,raw_json,imported_sequence) VALUES(?,?,?,?,?,?,?,?)",
                (source_id, event["event_id"], encounter_id, turn_log_id, event_type, event["timestamp"], _json(event), sequence),
            )


def iter_contract_records(payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for records in payload["catalog"].values():
        yield from records
    yield from payload["characters"]
    yield from payload["encounters"]
