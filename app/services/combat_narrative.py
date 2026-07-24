from __future__ import annotations

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


def parse_combat_event(row) -> dict[str, object]:
    actor = str(_value(row, "actor", "Unknown") or "Unknown")
    action_type = str(_value(row, "action_type", "Action") or "Action")
    details = str(_value(row, "details", "") or "").strip()
    parts = [part.strip() for part in details.split(" | ")]
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
    }


class CombatNarrativeBuilder:
    """Turn authoritative combat-log events into deterministic round prose."""

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
                "No combat events have been recorded for this encounter yet. "
                "Run the encounter locally or import a Fantasy Grounds live combat session."
            )

        sections = []
        for round_number, round_events in grouped.items():
            heading = "Before the First Round" if round_number <= 0 else f"Round {round_number}"
            sentences = [
                sentence
                for event in round_events
                if (sentence := self.event_sentence(event))
            ]
            if not sentences:
                continue
            opening = self.round_opening(round_number)
            sections.append(f"## {heading}\n\n{opening} {' '.join(sentences)}")

        clean_outcome = str(outcome or "").strip()
        if clean_outcome:
            sections.append(f"## Outcome\n\n{_sentence(clean_outcome)}")

        title = str(encounter_name or "").strip()
        prefix = f"# {title}\n\n" if title else ""
        return prefix + "\n\n".join(sections)

    @staticmethod
    def round_opening(round_number: int) -> str:
        if round_number <= 0:
            return "Events were already in motion before the first full round."
        if round_number == 1:
            return "The first round set the battle in motion."
        return f"Round {round_number} carried the struggle forward."

    def event_sentence(self, event: Mapping[str, object]) -> str:
        actor = str(event["actor"])
        target = str(event["target"])
        action = str(event["action"] or event["type"])
        result = str(event["result"])
        roll = str(event["roll"])
        defense = str(event["defense"])
        category = str(event["category"])
        action_type = str(event["type"]).casefold()

        if action_type == "encounter start":
            detail = str(event["details"] or result)
            detail = re.sub(r"^Encounter started:\s*", "", detail, flags=re.IGNORECASE)
            return _sentence(f"The encounter began{f': {detail}' if detail else ''}")

        if action_type == "encounter end":
            detail = str(event["details"] or result)
            detail = re.sub(r"^Encounter ended:\s*", "", detail, flags=re.IGNORECASE)
            return _sentence(f"The encounter concluded{f': {detail}' if detail else ''}")

        if action_type == "damage roll":
            amount = event["amount"] or _first_number(roll, result)
            damage_type = self.damage_label(event)
            target_text = f" against {target}" if target else ""
            damage_text = f"{damage_type} damage" if damage_type else "damage"
            amount_text = f" {amount} {damage_text}" if amount is not None else " dangerous force"
            return _sentence(f"{_possessive(actor)} {action} threatened{amount_text}{target_text}")

        if action_type == "attack":
            subject = f"{actor} attacked"
            if target:
                subject += f" {target}"
            if action and action.casefold() != "attack":
                subject += f" with {action}"
            evidence = self.attack_evidence(roll, defense)
            if category == "critical":
                return _sentence(f"{subject}, landing a devastating critical hit{evidence}")
            if category == "hit":
                return _sentence(f"{subject} and found an opening{evidence}")
            if category == "miss":
                return _sentence(f"{subject}, but the strike failed to connect{evidence}")
            detail = result if result and result.casefold() != "attack" else ""
            return _sentence(f"{subject}{evidence}{f'; {detail}' if detail else ''}")

        if category == "damage" or action_type == "damage":
            amount = event["amount"]
            damage_type = self.damage_label(event)
            damage_text = f"{damage_type} damage" if damage_type else "damage"
            if "manual / unattributed" in actor.casefold():
                subject = "An unattributed effect"
            elif action and action.casefold() not in {"damage", "damage roll"}:
                subject = f"{_possessive(actor)} {action}"
            else:
                subject = actor
            target_text = f" to {target}" if target else ""
            amount_text = f" {amount} {damage_text}" if amount is not None else f" {damage_text}"
            hp_text = self.hp_phrase(str(event["defense"]))
            adjustment_text = self.adjustment_phrase(result)
            if amount == 0:
                target_name = target or "the target"
                negated_text = " because the damage was negated" if "negated" in result.casefold() else ""
                return _sentence(f"{subject} failed to harm {target_name}{negated_text}{hp_text}")
            return _sentence(f"{subject} dealt{amount_text}{target_text}{adjustment_text}{hp_text}")

        if category == "healing":
            amount = event["amount"]
            target_text = target or actor
            amount_text = f" {amount} hit points" if amount is not None else " vitality"
            hp_text = self.hp_phrase(str(event["defense"]))
            return _sentence(f"{actor} restored{amount_text} to {target_text}{hp_text}")

        if category == "manual":
            detail = result or str(event["details"])
            return _sentence(f"An unattributed change altered the battle: {detail}")

        if action_type == "note":
            detail = str(event["details"] or result)
            return _sentence(f"The record notes that {detail}")

        if action_type == "effect":
            detail = result or str(event["details"])
            return _sentence(f"An effect changed the field: {detail}")

        target_text = f" against {target}" if target else ""
        detail = result or str(event["details"])
        if action.casefold() == "action not reported" and detail.casefold() == "result not reported":
            return _sentence(
                f"{actor} acted{target_text}, though the original record did not identify the action or result"
            )
        if detail and detail.casefold() not in {action.casefold(), action_type}:
            return _sentence(f"{actor} used {action}{target_text}; {detail}")
        return _sentence(f"{actor} used {action}{target_text}")

    @staticmethod
    def attack_evidence(roll: str, defense: str) -> str:
        values = [value for value in (roll, defense) if value]
        return f" ({'; '.join(values)})" if values else ""

    @staticmethod
    def hp_phrase(defense: str) -> str:
        match = re.search(r"Target HP\s+(\d+)\s*/\s*(\d+)", defense, re.IGNORECASE)
        if not match:
            return ""
        return f", leaving the target at {match.group(1)} of {match.group(2)} hit points"

    @staticmethod
    def adjustment_phrase(result: str) -> str:
        reduced = re.search(r"reduced by\s+(\d+(?:\.\d+)?)", result, re.IGNORECASE)
        if reduced:
            return f" after defenses reduced the impact by {reduced.group(1)}"
        increased = re.search(r"increased by\s+(\d+(?:\.\d+)?)", result, re.IGNORECASE)
        if increased:
            return f" after vulnerability increased the impact by {increased.group(1)}"
        return ""

    @staticmethod
    def damage_label(event: Mapping[str, object]) -> str:
        damage_type = str(event["damage_type"] or "").strip()
        if not damage_type or damage_type.casefold() in {"unknown", "not reported"}:
            return ""
        return damage_type
