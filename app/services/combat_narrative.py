from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping


SYSTEM_ACTIONS = {"turn start", "turn end"}


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
        "system": action_type.casefold() in SYSTEM_ACTIONS,
        "amount": amount,
        "damage_type": str(_value(row, "damage_types", "") or ""),
        "damage_components": _damage_components(row),
    }


class CombatNarrativeBuilder:
    """Turn authoritative combat-log events into grounded D&D 5e prose."""

    SOURCE_ACTORS = {"fantasy grounds", "lectern", "system", "encounter"}

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
        resolved_events = {
            self.event_link_key(event)
            for event in events
            if str(event["type"]).casefold() == "healing"
        }
        opening_snapshot = False
        sentences = []
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
            if action_type == "action" and self.event_link_key(event) in resolved_events:
                continue
            if (
                str(event["action"]).casefold() == "action not reported"
                and str(event["result"]).casefold() == "result not reported"
            ):
                continue
            sentence = self.event_sentence(event)
            if sentence:
                sentences.append(sentence)
        return sentences

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

    @staticmethod
    def round_opening(round_number: int, encounter_started: bool = False) -> str:
        if encounter_started:
            return "The encounter began."
        if round_number <= 0:
            return "Before the first round, the combat log recorded the following events."
        if round_number == 1:
            return "The combatants entered the first round."
        return f"The battle continued into round {round_number}."

    def event_sentence(self, event: Mapping[str, object]) -> str:
        actor = _clean_record_text(event["actor"])
        target = _clean_record_text(event["target"])
        action = _clean_record_text(event["action"] or event["type"])
        result = _clean_record_text(event["result"])
        roll = str(event["roll"])
        defense = str(event["defense"])
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
            evidence = self.attack_evidence(roll, defense, category)
            if category == "critical":
                return _sentence(
                    f"{actor} attacks {target_text}{action_text}, finds an opening, "
                    f"and scores a critical hit{evidence}"
                )
            if category == "hit":
                return _sentence(
                    f"{actor} attacks {target_text}{action_text} and lands a hit{evidence}"
                )
            if category == "miss":
                return _sentence(
                    f"{actor} attacks {target_text}{action_text}, but the attack misses{evidence}"
                )
            return _sentence(f"{actor} attacks {target_text}{action_text}{evidence}")

        if category == "damage" or action_type == "damage":
            amount = event["amount"]
            damage_type = self.damage_label(event)
            damage_text = f"{damage_type} damage" if damage_type else "damage"
            target_text = target or "the target"
            hp_text = self.hp_phrase(str(event["defense"]), target_text)
            adjustment_text = self.adjustment_phrase(event)
            temporary_hp_text = self.temporary_hp_damage_phrase(
                event,
                target_text,
            )
            if amount == 0:
                if source_actor or "manual / unattributed" in actor.casefold():
                    base = f"{target_text} takes no {damage_text} from an unidentified source"
                elif action and action.casefold() not in {"damage", "damage roll"}:
                    base = (
                        f"{_possessive(actor)} {action} has no damaging effect "
                        f"on {target_text}"
                    )
                else:
                    base = f"{target_text} takes no {damage_text} from {actor}"
                return _sentence(
                    f"{base}{adjustment_text}{temporary_hp_text}{hp_text}"
                )
            amount_text = f"{amount} {damage_text}" if amount is not None else damage_text
            if source_actor or "manual / unattributed" in actor.casefold():
                base = (
                    f"{target_text} takes {amount_text} from an unidentified source"
                )
            elif action and action.casefold() not in {"damage", "damage roll"}:
                base = (
                    f"{_possessive(actor)} {action} deals {amount_text} "
                    f"to {target_text}"
                )
            else:
                base = f"{actor} deals {amount_text} to {target_text}"
            return _sentence(
                f"{base}{adjustment_text}{temporary_hp_text}{hp_text}"
            )

        if category == "healing":
            amount = event["amount"]
            target_text = target or (actor if not source_actor else "the wounded")
            hp_text = self.healing_hp_phrase(str(event["defense"]), target_text)
            if source_actor:
                amount_text = f" {amount} hit points" if amount is not None else " hit points"
                return _sentence(
                    f"{target_text} recovers{amount_text}{hp_text}, "
                    f"helping {target_text} remain in the battle"
                )
            amount_text = f"{amount} hit points" if amount is not None else "hit points"
            if action and action.casefold() not in {"healing", "healing applied"}:
                cause = f"{_possessive(actor)} {action}"
            else:
                cause = actor
            return _sentence(
                f"{cause} helps {target_text} recover, restoring {amount_text}"
                f"{hp_text} and helping {target_text} remain in the battle"
            )

        if category == "manual":
            detail = result or str(event["details"])
            return _sentence(f"An unattributed combat event occurs: {_clean_record_text(detail)}")

        if action_type == "note":
            detail = _clean_record_text(event["details"] or result)
            return _sentence(f"The combat log records: {detail}")

        if action_type == "effect":
            return self.effect_sentence(event, target)

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
            return _sentence(f"{actor} uses {action}{target_text}. {detail}")
        return _sentence(f"{actor} uses {action}{target_text}")

    @staticmethod
    def attack_evidence(roll: str, defense: str, category: str) -> str:
        total = _first_number(roll)
        defense_match = re.search(r"\bAC\s+(\d+)", defense, re.IGNORECASE)
        natural_match = re.search(r"\bdice\s+(\d+)", roll, re.IGNORECASE)
        if total is None and not defense_match:
            return ""
        armor = int(defense_match.group(1)) if defense_match else None
        if natural_match and category == "critical":
            if total is not None and armor is not None:
                return f" (natural {natural_match.group(1)}; {total} against AC {armor})"
            return f" (natural {natural_match.group(1)})"
        if total is not None and armor is not None:
            return f" ({total} against AC {armor})"
        if total is not None:
            return f" (attack roll {total})"
        return f" (against AC {armor})"

    @staticmethod
    def hp_phrase(defense: str, target: str) -> str:
        match = re.search(r"Target HP\s+(\d+)\s*/\s*(\d+)", defense, re.IGNORECASE)
        if not match:
            return ""
        current, maximum = int(match.group(1)), int(match.group(2))
        if current <= 0:
            return f". The damage reduces {target} to 0 hit points"
        if current == maximum:
            return (
                f". {_possessive(target)} hit points remain unchanged at "
                f"{current} of {maximum}"
            )
        return (
            f". {target} remains in the fight with {current} of {maximum} "
            "hit points"
        )

    @staticmethod
    def healing_hp_phrase(defense: str, target: str) -> str:
        match = re.search(r"Target HP\s+(\d+)\s*/\s*(\d+)", defense, re.IGNORECASE)
        if not match:
            return ""
        current, maximum = int(match.group(1)), int(match.group(2))
        return f", bringing {target} to {current} of {maximum} hit points"

    @staticmethod
    def temporary_hp_damage_phrase(
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
        before, after = change
        absorbed = before - after
        return (
            f". {_possessive(target)} temporary hit points absorb {absorbed} "
            f"damage, decreasing from {before} to {after}"
        )

    @staticmethod
    def adjustment_phrase(event: Mapping[str, object]) -> str:
        result = str(event["result"])
        actor = _clean_record_text(event["actor"])
        target = _clean_record_text(event["target"]) or "the target"
        action = _clean_record_text(event["action"])
        known_cause = (
            actor
            and not CombatNarrativeBuilder.is_source_actor(actor)
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

        def resistance_phrase(amount: str) -> str:
            if known_cause:
                return (
                    f". {_possessive(target)} resistance reduces the damage "
                    f"from {_possessive(actor)} {action} by {amount}"
                )
            return (
                f". {_possessive(target)} resistance reduces the applied "
                f"damage by {amount}"
            )

        def vulnerability_phrase(amount: str) -> str:
            if known_cause:
                return (
                    f". {_possessive(actor)} {action} exploits "
                    f"{_possessive(target)} vulnerability, increasing the "
                    f"applied damage by {amount}"
                )
            return (
                f". {_possessive(target)} vulnerability increases the "
                f"applied damage by {amount}"
            )

        if "negated" in result.casefold():
            return f". The effect is negated, leaving {target} unharmed"
        reduced_match = re.search(
            r"reduced by\s+(\d+(?:\.\d+)?)",
            result,
            re.IGNORECASE,
        )
        if reduced_match:
            if resisted:
                return resistance_phrase(reduced_match.group(1))
            return f". The applied damage is reduced by {reduced_match.group(1)}"
        increased_match = re.search(
            r"increased by\s+(\d+(?:\.\d+)?)",
            result,
            re.IGNORECASE,
        )
        if increased_match:
            return vulnerability_phrase(increased_match.group(1))

        phrases = []
        if resisted:
            phrases.append(resistance_phrase(f"{resisted:g}").removeprefix(". "))
        if vulnerable:
            phrases.append(vulnerability_phrase(f"{vulnerable:g}").removeprefix(". "))
        if phrases:
            return "".join(f". {phrase}" for phrase in phrases)
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

    @classmethod
    def effect_sentence(
        cls,
        event: Mapping[str, object],
        target: str,
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
                gained = after - before
                actor = _clean_record_text(event["actor"])
                action = _clean_record_text(event["action"])
                known_cause = (
                    actor
                    and not cls.is_source_actor(actor)
                    and "manual / unattributed" not in actor.casefold()
                    and action.casefold() not in {"", "effect"}
                )
                if known_cause:
                    cause = (
                        f"{_possessive(actor)} {action} grants {subject} "
                        f"{gained} temporary hit points"
                    )
                else:
                    cause = f"{subject} gains {gained} temporary hit points"
                return _sentence(
                    f"{cause}, increasing the total from {before} to {after} "
                    f"and giving {subject} an additional buffer against damage"
                )
            lost = before - after
            return _sentence(
                f"{_possessive(subject)} temporary hit point buffer is reduced "
                f"by {lost}, decreasing from {before} to {after}"
            )
        target_text = f"{target} is affected: " if target else ""
        return _sentence(f"{target_text}{detail}")

    @staticmethod
    def outcome_sentence(outcome: str) -> str:
        clean = _clean_record_text(outcome)
        lowered = clean.casefold()
        if "victory" in lowered or "won" in lowered:
            return "The encounter ends in victory."
        if "defeat" in lowered or "loss" in lowered:
            return "The encounter ends in defeat."
        if clean:
            return _sentence(f"The encounter ends with this result: {clean}")
        return "The encounter ends."
