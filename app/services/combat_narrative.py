from __future__ import annotations

import json
import hashlib
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from string import Formatter

from ..paths import resource_path


SYSTEM_ACTIONS = {"turn start", "turn end"}


class NarrativeLibraryError(ValueError):
    """Raised when the bundled narrative library is missing or unsafe."""


class NarrativeLibrary:
    """Load and deterministically render the versioned offline phrase library."""

    REQUIRED_SECTIONS = {
        "round_opening",
        "beat",
        "attack",
        "damage",
        "damage_consequence",
        "healing",
        "temporary_vitality",
        "adjustment",
        "effect",
        "concentration",
        "generic",
        "outcome",
    }
    REQUIRED_ENTRIES = {
        "round_opening": {"encounter_start", "before_first", "first", "later"},
        "beat": {
            "attack_damage",
            "critical_damage",
            "self_attack_damage",
            "self_critical_damage",
            "save_success",
            "save_failure",
            "save_success_damage",
            "save_failure_damage",
        },
        "attack": {"critical", "hit", "miss", "default"},
        "damage": {
            "known_action",
            "known_actor",
            "unattributed",
            "zero_known_action",
            "zero_known_actor",
            "zero_unattributed",
        },
        "damage_consequence": {
            "down",
            "minor",
            "moderate",
            "heavy",
            "devastating",
        },
        "healing": {
            "known_unmeasured",
            "unknown_unmeasured",
            "known_full",
            "unknown_full",
            "known_major",
            "unknown_major",
            "known_moderate",
            "unknown_moderate",
            "known_minor",
            "unknown_minor",
        },
        "temporary_vitality": {
            "gain_known",
            "gain_unknown",
            "damage_spent",
            "damage_remaining",
            "spent",
            "reduced",
        },
        "adjustment": {
            "resistance_known",
            "resistance_unknown",
            "vulnerability_known",
            "vulnerability_unknown",
            "negated",
            "reduced",
        },
        "effect": {
            "condition_added_known",
            "condition_added_unknown",
            "condition_removed",
            "defense_known",
            "defense_unknown",
            "boon_known",
            "boon_unknown",
            "readied",
            "expended",
            "mark_known",
            "mark_unknown",
            "ended_known",
            "ended_unknown",
            "generic_known",
            "generic_unknown",
        },
        "concentration": {"success", "failure", "unknown"},
        "generic": {
            "manual",
            "note",
            "action_result",
            "action",
            "action_effect",
            "effect_targeted",
            "effect_untargeted",
        },
        "outcome": {"victory", "defeat", "other", "unknown"},
    }

    def __init__(self, path: Path | None = None, style: str | None = None):
        self.path = path or resource_path(
            "app",
            "resources",
            "combat_narrative_library.json",
        )
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise NarrativeLibraryError(
                f"Combat narrative library could not be loaded: {self.path}"
            ) from exc
        self.schema_version = self.data.get("schema_version")
        self.content_version = str(self.data.get("content_version", ""))
        self.default_style = str(self.data.get("default_style", ""))
        self.style = style or self.default_style
        self._validate()
        self.sections = self.data["styles"][self.style]["sections"]

    @property
    def available_styles(self) -> tuple[str, ...]:
        return tuple(self.data["styles"])

    def _validate(self) -> None:
        if self.schema_version != 1:
            raise NarrativeLibraryError(
                f"Unsupported combat narrative library schema: {self.schema_version}"
            )
        styles = self.data.get("styles")
        if (
            not isinstance(styles, dict)
            or self.default_style not in styles
            or self.style not in styles
        ):
            raise NarrativeLibraryError(
                f"Unknown combat narrative style: {self.style}"
            )
        if not self.content_version:
            raise NarrativeLibraryError("Narrative library content version is missing.")
        sections = styles[self.style].get("sections")
        if not isinstance(sections, dict):
            raise NarrativeLibraryError("Narrative style has no phrase sections.")
        missing = self.REQUIRED_SECTIONS - set(sections)
        if missing:
            raise NarrativeLibraryError(
                "Narrative library is missing sections: "
                + ", ".join(sorted(missing))
            )
        for section_name, required_entries in self.REQUIRED_ENTRIES.items():
            entries = sections.get(section_name, {})
            missing_entries = required_entries - set(entries)
            if missing_entries:
                raise NarrativeLibraryError(
                    f"Narrative section {section_name} is missing entries: "
                    + ", ".join(sorted(missing_entries))
                )
        constraints = self.data.get("constraints", {})
        allowed = set(constraints.get("allowed_placeholders", []))
        forbidden = tuple(
            str(term).casefold()
            for term in constraints.get("forbidden_literal_terms", [])
        )
        for section_name, entries in sections.items():
            if not isinstance(entries, dict) or not entries:
                raise NarrativeLibraryError(
                    f"Narrative section is empty: {section_name}"
                )
            for key, templates in entries.items():
                if (
                    not isinstance(templates, list)
                    or not templates
                    or not all(isinstance(item, str) and item.strip() for item in templates)
                ):
                    raise NarrativeLibraryError(
                        f"Narrative entry must contain phrases: {section_name}.{key}"
                    )
                for template in templates:
                    placeholders = {
                        field_name
                        for _, field_name, _, _ in Formatter().parse(template)
                        if field_name
                    }
                    unsupported = placeholders - allowed
                    if unsupported:
                        raise NarrativeLibraryError(
                            f"Unsupported placeholders in {section_name}.{key}: "
                            + ", ".join(sorted(unsupported))
                        )
                    lowered = template.casefold()
                    if any(term in lowered for term in forbidden):
                        raise NarrativeLibraryError(
                            f"Forbidden literal language in {section_name}.{key}"
                        )

    def render(
        self,
        section: str,
        key: str,
        values: Mapping[str, object] | None = None,
        seed: str = "",
    ) -> str:
        try:
            templates = self.sections[section][key]
        except KeyError as exc:
            raise NarrativeLibraryError(
                f"Unknown narrative phrase: {section}.{key}"
            ) from exc
        fingerprint = (
            f"{self.schema_version}|{self.content_version}|{self.style}|"
            f"{section}|{key}|{seed}"
        )
        digest = hashlib.sha256(fingerprint.encode("utf-8")).digest()
        template = templates[int.from_bytes(digest[:4], "big") % len(templates)]
        context = {name: "" for name in self.data["constraints"]["allowed_placeholders"]}
        if values:
            context.update({name: str(value) for name, value in values.items()})
        try:
            return template.format_map(context)
        except (KeyError, ValueError) as exc:
            raise NarrativeLibraryError(
                f"Narrative phrase could not be rendered: {section}.{key}"
            ) from exc


def _value(row, key: str, default=""):
    try:
        value = row[key]
    except (KeyError, IndexError, TypeError):
        value = default
    return default if value is None else value


def _sentence(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text if text.endswith((".", "!", "?")) else text + "."


def _possessive(name: str) -> str:
    return f"{name}'" if name.casefold().endswith("s") else f"{name}'s"


def _first_number(*values) -> int | None:
    for value in values:
        match = re.search(r"\b(\d+)\b", str(value or ""))
        if match:
            return int(match.group(1))
    return None


def _clean_record_text(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\bFantasy Grounds\b", "the record", text, flags=re.IGNORECASE)
    text = re.sub(r"\bLectern\b", "the record", text, flags=re.IGNORECASE)
    return text


def _damage_components(row) -> list[dict[str, object]]:
    raw = _value(row, "damage_components_json", "[]")
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(value, list):
        return []
    return [component for component in value if isinstance(component, dict)]


def parse_combat_event(row) -> dict[str, object]:
    actor = str(_value(row, "actor", "Unknown") or "Unknown")
    action_type = str(_value(row, "action_type", "Action") or "Action")
    details = str(_value(row, "details", "") or "").strip()
    parts = [part.strip() for part in re.split(r"\s*\|\s*", details)]
    roll = target = defense = action = result = ""
    if len(parts) >= 5:
        roll, target, defense, action = parts[:4]
        result = " | ".join(parts[4:])
    else:
        action = action_type
        result = details or action_type

    combined = f"{action_type} {details}".casefold()
    result_code = str(_value(row, "result_code", "") or "").casefold()
    if "critical hit" in combined or result_code == "critical_hit":
        category = "critical"
    elif (
        "automatic miss" in combined
        or "critical miss" in combined
        or result_code == "critical_miss"
        or action_type.casefold() == "miss"
        or " | miss" in combined
    ):
        category = "miss"
    elif action_type.casefold() == "attack" and (
        " hit" in f" {combined}" or result.casefold().startswith("hit")
    ):
        category = "hit"
    elif "manual / unattributed" in actor.casefold() or "manual_or_unattributed" in combined:
        category = "manual"
    elif "healing" in action_type.casefold() or "healing applied" in combined:
        category = "healing"
    elif action_type.casefold() == "concentration check":
        category = "concentration"
    elif "damage" in action_type.casefold() or "damage applied" in combined:
        category = "damage"
    else:
        category = "default"

    amount_value = _value(row, "amount", None)
    try:
        amount = int(amount_value) if amount_value is not None else None
    except (TypeError, ValueError):
        amount = None
    if amount is None and category in {"damage", "healing"}:
        amount = _first_number(roll, result, details)

    return {
        "id": int(_value(row, "id", 0) or 0),
        "round": int(_value(row, "round", 0) or 0),
        "actor": actor,
        "type": action_type,
        "details": details,
        "roll": roll,
        "target": target,
        "defense": defense,
        "action": action,
        "result": result,
        "category": category,
        "result_code": result_code,
        "system": action_type.casefold() in SYSTEM_ACTIONS,
        "amount": amount,
        "damage_type": str(_value(row, "damage_types", "") or ""),
        "damage_components": _damage_components(row),
    }


class CombatNarrativeBuilder:
    """Turn authoritative combat-log events into grounded D&D 5e prose."""

    SOURCE_ACTORS = {"fantasy grounds", "lectern", "system", "encounter"}

    def __init__(
        self,
        style: str | None = None,
        library_path: Path | None = None,
    ):
        self.library = NarrativeLibrary(library_path, style)

    @staticmethod
    def event_seed(event: Mapping[str, object]) -> str:
        return "|".join(
            str(event.get(key, ""))
            for key in (
                "id",
                "round",
                "actor",
                "type",
                "target",
                "action",
                "category",
                "result",
            )
        )

    @staticmethod
    def event_context(
        event: Mapping[str, object],
        **overrides: object,
    ) -> dict[str, object]:
        actor = _clean_record_text(event.get("actor", ""))
        target = _clean_record_text(event.get("target", ""))
        action = _clean_record_text(event.get("action", "") or event.get("type", ""))
        context: dict[str, object] = {
            "actor": actor,
            "actor_possessive": _possessive(actor) if actor else "",
            "target": target,
            "target_possessive": _possessive(target) if target else "",
            "action": action,
            "action_text": "",
            "damage_text": "damage",
            "detail": "",
            "cause": "",
            "outcome": "",
        }
        context.update(overrides)
        return context

    def phrase(
        self,
        section: str,
        key: str,
        values: Mapping[str, object] | None = None,
        seed: str = "",
    ) -> str:
        return _sentence(self.library.render(section, key, values, seed))

    def event_phrase(
        self,
        section: str,
        key: str,
        event: Mapping[str, object],
        **overrides: object,
    ) -> str:
        return self.phrase(
            section,
            key,
            self.event_context(event, **overrides),
            self.event_seed(event),
        )

    def followup_phrase(
        self,
        section: str,
        key: str,
        event: Mapping[str, object],
        **overrides: object,
    ) -> str:
        return " " + self.event_phrase(section, key, event, **overrides)

    def build(
        self,
        rows: Iterable[Mapping],
        encounter_name: str = "",
        outcome: str = "",
    ) -> str:
        events = [parse_combat_event(row) for row in rows]
        events = [event for event in events if not event["system"]]
        events.sort(key=lambda event: (event["round"], event["id"]))
        grouped: dict[int, list[dict[str, object]]] = {}
        for event in events:
            grouped.setdefault(int(event["round"]), []).append(event)

        if not grouped:
            return (
                "No combat events have been recorded for this encounter. "
                "The narrative will appear when the combat log contains events."
            )

        sections = []
        has_conclusion = any(
            str(event["type"]).casefold() == "encounter end"
            for event in events
        )
        for round_number, round_events in grouped.items():
            heading = "Before the First Round" if round_number <= 0 else f"Round {round_number}"
            sentences = self.round_sentences(round_events)
            if not sentences:
                continue
            encounter_started = any(
                str(event["type"]).casefold() == "encounter start"
                for event in round_events
            )
            opening = self.round_opening(round_number, encounter_started)
            sections.append(f"## {heading}\n\n{opening} {' '.join(sentences)}")

        clean_outcome = _clean_record_text(outcome)
        if clean_outcome and not has_conclusion:
            sections.append(f"## Aftermath\n\n{self.outcome_sentence(clean_outcome)}")

        return _clean_record_text("\n\n".join(sections))

    def round_sentences(self, events: list[dict[str, object]]) -> list[str]:
        events = self.attribute_secondary_damage(events)
        events = self.link_temporary_hp_damage(events)
        opening_snapshot = False
        narratable = []
        for event in events:
            action_type = str(event["type"]).casefold()
            if action_type == "encounter start":
                opening_snapshot = True
                continue
            if (
                opening_snapshot
                and str(event["category"]) == "healing"
                and self.is_source_actor(str(event["actor"]))
                and self.target_is_full(event)
            ):
                continue
            if action_type not in {"encounter start", "healing"}:
                opening_snapshot = False
            # A Fantasy Grounds damage-roll event records who owned the active
            # turn, not necessarily who caused the later HP change. The applied
            # damage event is authoritative; narrating the roll independently
            # can assign a spell or weapon to the wrong combatant.
            if action_type == "damage roll":
                continue
            if (
                str(event["action"]).casefold() == "action not reported"
                and str(event["result"]).casefold() == "result not reported"
            ):
                continue
            narratable.append(event)

        sentences = []
        for beat in self.coalesce_events(narratable):
            sentence = self.beat_sentence(beat)
            if sentence:
                sentences.append(sentence)
        return sentences

    def coalesce_events(
        self,
        events: list[dict[str, object]],
    ) -> list[list[dict[str, object]]]:
        """Group only strongly linked source rows into authoritative narrative beats."""
        beats: list[list[dict[str, object]]] = []
        for event in events:
            action_type = str(event["type"]).casefold()
            is_resolution = action_type in {"damage", "healing", "effect"}
            is_save = action_type == "save"
            match_index = None
            if is_resolution or is_save:
                for index in range(len(beats) - 1, max(-1, len(beats) - 7), -1):
                    if self.events_share_action(beats[index], event):
                        match_index = index
                        break
            if match_index is None:
                beats.append([event])
            else:
                beats[match_index].append(event)
        return beats

    @classmethod
    def events_share_action(
        cls,
        beat: list[dict[str, object]],
        event: Mapping[str, object],
    ) -> bool:
        """Require the same actor and target, plus the same named action."""
        actor = str(event["actor"]).strip().casefold()
        target = str(event["target"]).strip().casefold()
        action = str(event["action"]).strip().casefold()
        if not actor or not target or not action:
            return False
        for candidate in reversed(beat):
            candidate_actor = str(candidate["actor"]).strip().casefold()
            candidate_target = str(candidate["target"]).strip().casefold()
            candidate_action = str(candidate["action"]).strip().casefold()
            if actor != candidate_actor or target != candidate_target:
                continue
            if (
                str(event["type"]).casefold() == "effect"
                and str(candidate["type"]).casefold() == "effect"
                and action in {"effect", "effect state"}
                and candidate_action in {"effect", "effect state"}
            ):
                continue
            if cls.actions_related(action, candidate_action):
                return True
            if (
                str(event["type"]).casefold() == "effect"
                and action in {"effect", "effect state"}
                and str(candidate["type"]).casefold() != "effect"
            ):
                return True
        return False

    @staticmethod
    def actions_related(first: str, second: str) -> bool:
        if first == second:
            return True
        # Applied damage records append authoritative contributors to the
        # originating weapon or spell (for example, "Longbow with Hunter's Mark").
        return first.startswith(second + " with ") or second.startswith(first + " with ")

    def beat_sentence(self, events: list[dict[str, object]]) -> str:
        """Render a linked action and all of its confirmed resolutions as one beat."""
        attack = next(
            (event for event in events if str(event["type"]).casefold() == "attack"),
            None,
        )
        save = next(
            (event for event in events if str(event["type"]).casefold() == "save"),
            None,
        )
        damage = next(
            (event for event in events if str(event["type"]).casefold() == "damage"),
            None,
        )
        healing = next(
            (event for event in events if str(event["type"]).casefold() == "healing"),
            None,
        )
        effects = [
            event for event in events if str(event["type"]).casefold() == "effect"
        ]
        effects_consumed = False
        linked_action = ""
        for candidate in (damage, save, attack):
            if candidate:
                candidate_action = str(candidate.get("action") or "").strip()
                if candidate_action and candidate_action.casefold() not in {
                    "action",
                    "action not reported",
                    "damage",
                    "effect",
                }:
                    linked_action = candidate_action
                    break

        if healing:
            base = self.event_sentence(healing)
        elif attack and save and damage and damage.get("amount") != 0:
            base = (
                self.event_sentence(attack)
                + " "
                + self.save_damage_sentence(save, damage)
            )
        elif attack and save:
            base = self.event_sentence(attack) + " " + self.save_sentence(save)
        elif damage and attack and damage.get("amount") != 0:
            base = self.attack_damage_sentence(attack, damage)
        elif damage and save and damage.get("amount") != 0:
            base = self.save_damage_sentence(save, damage)
        elif damage:
            base = self.event_sentence(damage)
        elif save:
            base = self.save_sentence(save)
        elif attack:
            base = self.event_sentence(attack)
        else:
            non_effect = next(
                (
                    event
                    for event in events
                    if str(event["type"]).casefold() != "effect"
                ),
                None,
            )
            if non_effect and effects:
                actor = _clean_record_text(non_effect["actor"])
                target = _clean_record_text(non_effect["target"]) or "the target"
                action = _clean_record_text(non_effect["action"] or non_effect["type"])
                base = self.event_phrase(
                    "generic",
                    "action_effect",
                    non_effect,
                    actor=actor,
                    action=action,
                    target=target,
                )
                effects_consumed = True
            elif non_effect:
                base = self.event_sentence(non_effect)
            else:
                base = ""

        effect_sentences = [] if effects_consumed else [
            self.effect_sentence(
                effect,
                _clean_record_text(effect["target"]),
                linked_action,
            )
            for effect in effects
        ]
        return " ".join(
            sentence for sentence in (base, *effect_sentences) if sentence
        )

    def attack_damage_sentence(
        self,
        attack: Mapping[str, object],
        damage: Mapping[str, object],
    ) -> str:
        actor = _clean_record_text(attack["actor"])
        target = _clean_record_text(attack["target"]) or "the foe"
        action = self.narrative_action(
            _clean_record_text(damage["action"] or attack["action"])
        )
        damage_type = self.damage_label(damage)
        damage_text = f"{damage_type} damage" if damage_type else "damage"
        self_targeted = bool(actor and target and actor.casefold() == target.casefold())
        if self_targeted:
            key = (
                "self_critical_damage"
                if str(attack["category"]) == "critical"
                else "self_attack_damage"
            )
        else:
            key = (
                "critical_damage"
                if str(attack["category"]) == "critical"
                else "attack_damage"
            )
        base = self.event_phrase(
            "beat",
            key,
            attack,
            actor=actor,
            actor_possessive=_possessive(actor),
            target=target,
            target_possessive=_possessive(target),
            action=action,
            damage_text=damage_text,
        )
        return (
            base
            + self.adjustment_phrase(damage)
            + self.temporary_hp_damage_phrase(damage, target)
            + self.damage_consequence_phrase(damage, target)
        )

    def save_sentence(self, save: Mapping[str, object]) -> str:
        outcome = self.save_outcome(save)
        if not outcome:
            return self.event_sentence(save)
        actor = _clean_record_text(save["actor"])
        target = _clean_record_text(save["target"]) or "the target"
        action = _clean_record_text(save["action"] or save["type"])
        return self.event_phrase(
            "beat",
            f"save_{outcome}",
            save,
            actor=actor,
            actor_possessive=_possessive(actor),
            target=target,
            target_possessive=_possessive(target),
            action=action,
        )

    def save_damage_sentence(
        self,
        save: Mapping[str, object],
        damage: Mapping[str, object],
    ) -> str:
        outcome = self.save_outcome(save)
        if not outcome:
            return self.event_sentence(damage)
        actor = _clean_record_text(save["actor"])
        target = _clean_record_text(save["target"]) or "the target"
        action = _clean_record_text(damage["action"] or save["action"])
        damage_type = self.damage_label(damage)
        damage_text = f"{damage_type} damage" if damage_type else "damage"
        base = self.event_phrase(
            "beat",
            f"save_{outcome}_damage",
            save,
            actor=actor,
            actor_possessive=_possessive(actor),
            target=target,
            target_possessive=_possessive(target),
            action=action,
            damage_text=damage_text,
        )
        return (
            base
            + self.adjustment_phrase(damage)
            + self.temporary_hp_damage_phrase(damage, target)
            + self.damage_consequence_phrase(damage, target)
        )

    @staticmethod
    def save_outcome(event: Mapping[str, object]) -> str:
        result_code = str(event.get("result_code", "")).casefold()
        result = str(event.get("result", "")).casefold()
        if result_code == "save_success" or re.search(r"\bsuccess(?:ful)?\b", result):
            return "success"
        if result_code == "save_failure" or re.search(r"\bfail(?:ure|ed)?\b", result):
            return "failure"
        return ""

    @staticmethod
    def link_temporary_hp_damage(
        events: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        """Attach a matching temporary-HP loss to its applied-damage event."""
        linked: list[dict[str, object]] = []
        index = 0
        while index < len(events):
            event = events[index]
            temporary = re.search(
                r"Temporary HP changed from\s+(\d+)\s+to\s+(\d+)",
                str(event["result"] or event["details"]),
                re.IGNORECASE,
            )
            if (
                str(event["type"]).casefold() == "effect"
                and temporary
                and int(temporary.group(2)) < int(temporary.group(1))
                and index + 1 < len(events)
            ):
                following = events[index + 1]
                before, after = int(temporary.group(1)), int(temporary.group(2))
                same_target = (
                    str(event["target"]).strip().casefold()
                    == str(following["target"]).strip().casefold()
                    and bool(str(event["target"]).strip())
                )
                if (
                    str(following["type"]).casefold() == "damage"
                    and same_target
                    and following["amount"] == before - after
                ):
                    damage_event = dict(following)
                    damage_event["temporary_hp_change"] = (before, after)
                    linked.append(damage_event)
                    index += 2
                    continue
            linked.append(event)
            index += 1
        return linked

    def attribute_secondary_damage(
        self,
        events: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        """Carry a confirmed action across its contiguous secondary targets."""
        attributed: list[dict[str, object]] = []
        confirmed_damage: dict[str, object] | None = None
        for original in events:
            event = dict(original)
            action_type = str(event["type"]).casefold()
            actor = str(event["actor"])
            action = str(event["action"])

            if action_type == "damage":
                unattributed = "manual / unattributed" in actor.casefold()
                if unattributed:
                    if confirmed_damage and self.damage_types_overlap(
                        confirmed_damage,
                        event,
                    ):
                        event["actor"] = confirmed_damage["actor"]
                        event["action"] = confirmed_damage["action"]
                        event["category"] = "damage"
                    else:
                        confirmed_damage = None
                elif (
                    not self.is_source_actor(actor)
                    and action.casefold() not in {"", "damage", "damage roll"}
                ):
                    # This applied-damage row establishes both the acting
                    # combatant and the spell or weapon. Contiguous unattributed
                    # damage of the same type can therefore be a secondary
                    # target of this action.
                    confirmed_damage = event
                else:
                    confirmed_damage = None
            else:
                # A roll alone is provisional. Any other event also ends the
                # contiguous applied-damage sequence.
                confirmed_damage = None

            attributed.append(event)
        return attributed

    def round_opening(
        self,
        round_number: int,
        encounter_started: bool = False,
    ) -> str:
        if encounter_started:
            key = "encounter_start"
        elif round_number <= 0:
            key = "before_first"
        elif round_number == 1:
            key = "first"
        else:
            key = "later"
        return self.phrase(
            "round_opening",
            key,
            seed=f"round:{round_number}:started:{encounter_started}",
        )

    def event_sentence(self, event: Mapping[str, object]) -> str:
        actor = _clean_record_text(event["actor"])
        target = _clean_record_text(event["target"])
        action = _clean_record_text(event["action"] or event["type"])
        result = _clean_record_text(event["result"])
        category = str(event["category"])
        action_type = str(event["type"]).casefold()
        source_actor = self.is_source_actor(str(event["actor"]))

        if action_type == "encounter start":
            return ""

        if action_type == "encounter end":
            detail = _clean_record_text(event["details"] or result)
            detail = re.sub(r"^Encounter ended:\s*", "", detail, flags=re.IGNORECASE)
            return self.outcome_sentence(detail)

        if action_type == "damage roll":
            return ""

        if action_type == "attack":
            if source_actor:
                return ""
            action_text = (
                f" with {action}"
                if action and action.casefold() != "attack"
                else ""
            )
            target_text = target or "the foe"
            attack_key = category if category in {"critical", "hit", "miss"} else "default"
            return self.event_phrase(
                "attack",
                attack_key,
                event,
                actor=actor,
                target=target_text,
                action_text=action_text,
            )

        if category == "damage" or action_type == "damage":
            amount = event["amount"]
            damage_type = self.damage_label(event)
            damage_text = f"{damage_type} damage" if damage_type else "damage"
            target_text = target or "the target"
            adjustment_text = self.adjustment_phrase(event)
            temporary_hp_text = self.temporary_hp_damage_phrase(
                event,
                target_text,
            )
            consequence_text = self.damage_consequence_phrase(
                event,
                target_text,
            )
            phrase_values = {
                "actor": actor,
                "actor_possessive": _possessive(actor),
                "target": target_text,
                "target_possessive": _possessive(target_text),
                "action": action,
                "damage_text": damage_text,
            }
            if amount == 0:
                if source_actor or "manual / unattributed" in actor.casefold():
                    key = "zero_unattributed"
                elif action and action.casefold() not in {"damage", "damage roll"}:
                    key = "zero_known_action"
                else:
                    key = "zero_known_actor"
                base = self.phrase(
                    "damage",
                    key,
                    phrase_values,
                    self.event_seed(event),
                )
                return f"{base}{adjustment_text}"
            if source_actor or "manual / unattributed" in actor.casefold():
                key = "unattributed"
            elif action and action.casefold() not in {"damage", "damage roll"}:
                key = "known_action"
            else:
                key = "known_actor"
            base = self.phrase(
                "damage",
                key,
                phrase_values,
                self.event_seed(event),
            )
            return f"{base}{adjustment_text}{temporary_hp_text}{consequence_text}"

        if category == "healing":
            target_text = target or (actor if not source_actor else "the wounded")
            if source_actor:
                return self.healing_sentence(
                    event,
                    target_text,
                    cause="",
                )
            if action and action.casefold() not in {"healing", "healing applied"}:
                cause = f"{_possessive(actor)} {action}"
            else:
                cause = actor
            return self.healing_sentence(event, target_text, cause)

        if category == "manual":
            detail = result or str(event["details"])
            return self.event_phrase(
                "generic",
                "manual",
                event,
                detail=_clean_record_text(detail),
            )

        if action_type == "note":
            detail = _clean_record_text(event["details"] or result)
            return self.event_phrase("generic", "note", event, detail=detail)

        if action_type == "effect":
            return self.effect_sentence(event, target)

        if action_type == "concentration check":
            outcome = str(event.get("result_code") or "").casefold()
            if outcome == "concentration_success":
                key = "success"
            elif outcome == "concentration_failure":
                key = "failure"
            else:
                key = "unknown"
            return self.event_phrase(
                "concentration",
                key,
                event,
                actor=actor,
                actor_possessive=_possessive(actor),
            )

        target_text = f" against {target}" if target else ""
        detail = result or _clean_record_text(event["details"])
        if source_actor:
            return _sentence(detail) if detail else ""
        if action.casefold() == "action not reported" and detail.casefold() == "result not reported":
            return ""
        if detail and detail.casefold() not in {
            action.casefold(),
            action_type,
            "result not reported",
        }:
            return self.event_phrase(
                "generic",
                "action_result",
                event,
                actor=actor,
                action=action,
                action_text=target_text,
                detail=detail,
            )
        return self.event_phrase(
            "generic",
            "action",
            event,
            actor=actor,
            action=action,
            action_text=target_text,
        )

    def damage_consequence_phrase(
        self,
        event: Mapping[str, object],
        target: str,
    ) -> str:
        if event.get("temporary_hp_change"):
            return ""
        match = re.search(
            r"Target HP\s+(\d+)\s*/\s*(\d+)",
            str(event["defense"]),
            re.IGNORECASE,
        )
        amount = event.get("amount")
        if not match or not isinstance(amount, int) or amount <= 0:
            return ""
        current, maximum = int(match.group(1)), int(match.group(2))
        if current <= 0:
            key = "down"
        else:
            endurance_before = current + amount
            impact = amount / endurance_before if endurance_before > 0 else 1.0
            if impact <= 0.20:
                key = "minor"
            elif impact <= 0.40:
                key = "moderate"
            elif impact <= 0.65:
                key = "heavy"
            else:
                key = "devastating"
        return self.followup_phrase(
            "damage_consequence",
            key,
            event,
            target=target,
            target_possessive=_possessive(target),
        )

    def healing_sentence(
        self,
        event: Mapping[str, object],
        target: str,
        cause: str,
    ) -> str:
        match = re.search(
            r"Target HP\s+(\d+)\s*/\s*(\d+)",
            str(event["defense"]),
            re.IGNORECASE,
        )
        amount = event.get("amount")
        if not match or not isinstance(amount, int) or amount <= 0:
            key = "known_unmeasured" if cause else "unknown_unmeasured"
        else:
            current, maximum = int(match.group(1)), int(match.group(2))
            before = max(0, current - amount)
            missing_before = max(1, maximum - before)
            recovery = min(1.0, amount / missing_before)
            if current >= maximum:
                level = "full"
            elif recovery >= 0.66:
                level = "major"
            elif recovery >= 0.33:
                level = "moderate"
            else:
                level = "minor"
            key = f"{'known' if cause else 'unknown'}_{level}"
        return self.event_phrase(
            "healing",
            key,
            event,
            target=target,
            target_possessive=_possessive(target),
            cause=cause,
        )

    def temporary_hp_damage_phrase(
        self,
        event: Mapping[str, object],
        target: str,
    ) -> str:
        change = event.get("temporary_hp_change")
        if (
            not isinstance(change, tuple)
            or len(change) != 2
            or not all(isinstance(value, int) for value in change)
        ):
            return ""
        _, after = change
        key = "damage_spent" if after <= 0 else "damage_remaining"
        return self.followup_phrase(
            "temporary_vitality",
            key,
            event,
            target=target,
            target_possessive=_possessive(target),
        )

    def adjustment_phrase(self, event: Mapping[str, object]) -> str:
        result = str(event["result"])
        actor = _clean_record_text(event["actor"])
        target = _clean_record_text(event["target"]) or "the target"
        action = _clean_record_text(event["action"])
        known_cause = (
            actor
            and not self.is_source_actor(actor)
            and "manual / unattributed" not in actor.casefold()
            and action.casefold() not in {"", "damage", "damage roll"}
        )

        components = event.get("damage_components", [])
        resisted = vulnerable = 0.0
        if isinstance(components, list):
            for component in components:
                if not isinstance(component, Mapping):
                    continue
                try:
                    resisted += max(0.0, float(component.get("resisted", 0) or 0))
                    vulnerable += max(0.0, float(component.get("vulnerable", 0) or 0))
                except (TypeError, ValueError):
                    continue

        values = {
            "actor": actor,
            "actor_possessive": _possessive(actor),
            "target": target,
            "target_possessive": _possessive(target),
            "action": action,
        }

        def rendered(key: str) -> str:
            return self.followup_phrase(
                "adjustment",
                key,
                event,
                **values,
            )

        if "negated" in result.casefold():
            return rendered("negated")
        reduced_match = re.search(
            r"reduced by\s+(\d+(?:\.\d+)?)",
            result,
            re.IGNORECASE,
        )
        if reduced_match:
            if resisted:
                return rendered(
                    "resistance_known" if known_cause else "resistance_unknown"
                )
            return rendered("reduced")
        increased_match = re.search(
            r"increased by\s+(\d+(?:\.\d+)?)",
            result,
            re.IGNORECASE,
        )
        if increased_match:
            return rendered(
                "vulnerability_known" if known_cause else "vulnerability_unknown"
            )

        phrases = []
        if resisted:
            phrases.append(
                rendered(
                    "resistance_known" if known_cause else "resistance_unknown"
                )
            )
        if vulnerable:
            phrases.append(
                rendered(
                    "vulnerability_known" if known_cause else "vulnerability_unknown"
                )
            )
        if phrases:
            return "".join(phrases)
        return ""

    @staticmethod
    def damage_label(event: Mapping[str, object]) -> str:
        damage_type = str(event["damage_type"] or "").strip()
        if not damage_type or damage_type.casefold() in {"unknown", "not reported"}:
            return ""
        parts = [part.strip() for part in damage_type.split(",") if part.strip()]
        if len(parts) > 1:
            return ", ".join(parts[:-1]) + f" and {parts[-1]}"
        return damage_type

    @staticmethod
    def narrative_action(action: str) -> str:
        """Make an authoritative contributor suffix read naturally in prose."""
        base, separator, contributors = action.partition(" with ")
        if separator and base.strip() and contributors.strip():
            return f"{base.strip()} aided by {contributors.strip()}"
        return action

    @staticmethod
    def damage_types_overlap(
        first: Mapping[str, object],
        second: Mapping[str, object],
    ) -> bool:
        ignored = {"", "unknown", "not reported"}

        def values(event: Mapping[str, object]) -> set[str]:
            return {
                value.strip().casefold()
                for value in str(event["damage_type"] or "").split(",")
                if value.strip().casefold() not in ignored
            }

        return bool(values(first) & values(second))

    @classmethod
    def is_source_actor(cls, actor: str) -> bool:
        return actor.strip().casefold() in cls.SOURCE_ACTORS

    @staticmethod
    def event_link_key(event: Mapping[str, object]) -> tuple[str, str, str]:
        return (
            str(event["actor"]).casefold(),
            str(event["target"]).casefold(),
            str(event["action"]).casefold(),
        )

    @staticmethod
    def target_is_full(event: Mapping[str, object]) -> bool:
        match = re.search(
            r"Target HP\s+(\d+)\s*/\s*(\d+)",
            str(event["defense"]),
            re.IGNORECASE,
        )
        return bool(match and match.group(1) == match.group(2))

    def effect_sentence(
        self,
        event: Mapping[str, object],
        target: str,
        linked_action: str = "",
    ) -> str:
        detail = _clean_record_text(event["result"] or event["details"])
        temporary = re.search(
            r"Temporary HP changed from\s+(\d+)\s+to\s+(\d+)",
            detail,
            re.IGNORECASE,
        )
        if temporary:
            before, after = int(temporary.group(1)), int(temporary.group(2))
            subject = target or "The target"
            if after > before:
                actor = _clean_record_text(event["actor"])
                action = _clean_record_text(event["action"])
                known_cause = (
                    actor
                    and not self.is_source_actor(actor)
                    and "manual / unattributed" not in actor.casefold()
                    and action.casefold() not in {"", "effect"}
                )
                if known_cause:
                    return self.event_phrase(
                        "temporary_vitality",
                        "gain_known",
                        event,
                        actor=actor,
                        actor_possessive=_possessive(actor),
                        action=action,
                        target=subject,
                        target_possessive=_possessive(subject),
                    )
                return self.event_phrase(
                    "temporary_vitality",
                    "gain_unknown",
                    event,
                    target=subject,
                    target_possessive=_possessive(subject),
                )
            if after <= 0:
                key = "spent"
            else:
                key = "reduced"
            return self.event_phrase(
                "temporary_vitality",
                key,
                event,
                target=subject,
                target_possessive=_possessive(subject),
            )
        raw_action = _clean_record_text(event["action"])
        raw_lower = detail.casefold()
        if re.search(r"\bift\s*:\s*custom\s*\(", raw_lower):
            return ""

        state_source = f"{event.get('defense', '')} {detail}".casefold()
        removed = "effect ended" in state_source or "effect removed" in state_source
        label = self.effect_label(detail)
        actor = _clean_record_text(event["actor"])
        known_actor = (
            actor
            and not self.is_source_actor(actor)
            and "manual / unattributed" not in actor.casefold()
        )
        action = linked_action.strip() or raw_action.strip()
        if action.casefold() in {"", "effect", "effect state"}:
            action = label

        subject = target or "The target"
        values = {
            "actor": actor,
            "actor_possessive": _possessive(actor) if actor else "",
            "target": subject,
            "target_possessive": _possessive(subject),
            "action": action,
            "detail": label.casefold(),
        }
        conditions = {
            "blinded",
            "charmed",
            "frightened",
            "grappled",
            "incapacitated",
            "invisible",
            "paralyzed",
            "poisoned",
            "prone",
            "restrained",
            "stunned",
            "unconscious",
        }
        label_lower = label.casefold()
        if label_lower in conditions:
            if removed:
                key = "condition_removed"
            elif known_actor and action and action.casefold() != label_lower:
                key = "condition_added_known"
            else:
                key = "condition_added_unknown"
            return self.event_phrase("effect", key, event, **values)

        if "hunter's mark" in label_lower or "hunter’s mark" in label_lower:
            if removed:
                key = "ended_known" if known_actor else "ended_unknown"
            else:
                key = "mark_known" if known_actor else "mark_unknown"
            values["action"] = "Hunter's Mark"
            return self.event_phrase("effect", key, event, **values)

        if "sneak attack" in label_lower:
            key = "expended" if removed else "readied"
            values["action"] = "Sneak Attack"
            return self.event_phrase("effect", key, event, **values)

        if re.search(r"\bac\s*:", raw_lower):
            key = "defense_known" if known_actor and action else "defense_unknown"
            return self.event_phrase("effect", key, event, **values)

        if (
            "bardic inspiration" in label_lower
            or "innate sorcery" in label_lower
            or re.search(r"\b(?:adv(?:atk)?|savedc|atk|save)\s*:", raw_lower)
        ):
            if "bardic inspiration" in label_lower:
                values["action"] = "Bardic Inspiration"
            elif "innate sorcery" in label_lower:
                values["action"] = "Innate Sorcery"
            if removed:
                key = "ended_known" if known_actor and action else "ended_unknown"
            else:
                key = "boon_known" if known_actor and action else "boon_unknown"
            return self.event_phrase("effect", key, event, **values)

        if removed:
            key = "ended_known" if known_actor and action else "ended_unknown"
        else:
            key = "generic_known" if known_actor and action else "generic_unknown"
        return self.event_phrase("effect", key, event, **values)

    @staticmethod
    def effect_label(detail: str) -> str:
        text = re.sub(
            r"^Effect\s+(?:added to|ended on|removed from)\s+[^:]+:\s*",
            "",
            str(detail or "").strip(),
            flags=re.IGNORECASE,
        )
        custom = re.search(r"\bCUSTOM\s*\(([^)]+)\)", text, re.IGNORECASE)
        if custom:
            return custom.group(1).strip()
        first = text.split(";", 1)[0].strip()
        first = re.sub(r"\s*\([^)]*rolls?[^)]*\)\s*", "", first, flags=re.IGNORECASE)
        first = re.sub(r"\s+Die$", "", first, flags=re.IGNORECASE)
        if re.match(r"^(?:AC|ATK|SAVE|SAVEDC|DMG|IFT)\s*:", first, re.IGNORECASE):
            return ""
        return first or "effect"

    def outcome_sentence(self, outcome: str) -> str:
        clean = _clean_record_text(outcome)
        lowered = clean.casefold()
        if "victory" in lowered or "won" in lowered:
            key = "victory"
        elif "defeat" in lowered or "loss" in lowered:
            key = "defeat"
        elif clean:
            key = "other"
        else:
            key = "unknown"
        return self.phrase(
            "outcome",
            key,
            {"outcome": clean},
            seed=f"outcome:{lowered}",
        )
