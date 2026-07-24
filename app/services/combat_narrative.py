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


def _clean_record_text(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\bFantasy Grounds\b", "the record", text, flags=re.IGNORECASE)
    text = re.sub(r"\bLectern\b", "the record", text, flags=re.IGNORECASE)
    return text


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
    }


class CombatNarrativeBuilder:
    """Turn authoritative combat-log events into a grim heroic chronicle."""

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
                "No blows have been set down for this fight yet. "
                "When steel is drawn, the chronicle will begin."
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
            opening = self.round_opening(round_number)
            sections.append(f"## {heading}\n\n{opening} {' '.join(sentences)}")

        clean_outcome = _clean_record_text(outcome)
        if clean_outcome and not has_conclusion:
            sections.append(f"## Aftermath\n\n{self.outcome_sentence(clean_outcome)}")

        return _clean_record_text("\n\n".join(sections))

    def round_sentences(self, events: list[dict[str, object]]) -> list[str]:
        resolved_events = {
            self.event_link_key(event)
            for event in events
            if str(event["type"]).casefold() in {"damage", "healing"}
        }
        encounter_opening = False
        opening_snapshot = False
        sentences = []
        for event in events:
            action_type = str(event["type"]).casefold()
            if action_type == "encounter start":
                encounter_opening = True
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
            if action_type == "damage roll" and self.event_link_key(event) in resolved_events:
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
        if encounter_opening and sentences:
            sentences.insert(0, "Steel came free, and the killing work began.")
        return sentences

    @staticmethod
    def round_opening(round_number: int) -> str:
        if round_number <= 0:
            return "The field was already moving before anyone could name the first blow."
        if round_number == 1:
            return "The first exchange stripped away ceremony. What remained was nerve and sharpened steel."
        openings = (
            "There was no room left for ceremony. Both sides went back to the hard work of breaking the other.",
            "Breath shortened and courage earned its keep. Still, neither side yielded.",
            "The line bent without breaking. The next exchange came on hard.",
            "Pain had found them by then. Discipline kept them standing.",
            "The easy choices were gone. Every move now carried a price.",
            "Dust hung in the air and blood ran hot. The fighters closed again.",
            "Whatever plans they had brought to the field were spent. Instinct and training took over.",
            "The fight had become a test of who could suffer longest and still raise a weapon.",
        )
        return openings[(round_number - 2) % len(openings)]

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
            amount = event["amount"] or _first_number(roll, result)
            damage_type = self.damage_label(event)
            damage_text = f"{damage_type} damage" if damage_type else "damage"
            target_text = f" at {target}" if target else ""
            if source_actor:
                return ""
            if amount is not None:
                return _sentence(
                    f"{actor} gathered {action} and hurled the promise of {amount} {damage_text}{target_text}"
                )
            return _sentence(f"{actor} gathered {action} and sent it{target_text}")

        if action_type == "attack":
            if source_actor:
                return ""
            weapon = f" with {action}" if action and action.casefold() != "attack" else ""
            target_text = target or "the foe"
            evidence = self.attack_evidence(roll, defense, category)
            if category == "critical":
                return _sentence(
                    f"{actor} drove at {target_text}{weapon} and found the open line. "
                    f"The blow landed with murderous precision{evidence}"
                )
            if category == "hit":
                return _sentence(
                    f"{actor} came on{weapon} and caught {target_text} clean{evidence}"
                )
            if category == "miss":
                return _sentence(
                    f"{actor} struck at {target_text}{weapon}, but the blow went wide{evidence}"
                )
            return _sentence(f"{actor} pressed {target_text}{weapon}{evidence}")

        if category == "damage" or action_type == "damage":
            amount = event["amount"]
            damage_type = self.damage_label(event)
            damage_text = f"{damage_type} damage" if damage_type else "damage"
            if source_actor or "manual / unattributed" in actor.casefold():
                subject = self.unseen_subject(event, damage_type)
            elif action and action.casefold() not in {"damage", "damage roll"}:
                subject = f"{_possessive(actor)} {action}"
            else:
                subject = actor
            target_text = target or "the target"
            hp_text = self.hp_phrase(str(event["defense"]), target_text)
            adjustment_text = self.adjustment_phrase(result)
            if amount == 0:
                return _sentence(
                    f"{subject} washed over {target_text} and found no purchase{hp_text}"
                )
            amount_text = f" for {amount} points of {damage_text}" if amount is not None else f" with {damage_text}"
            return _sentence(
                f"{subject} struck {target_text}{amount_text}{adjustment_text}{hp_text}"
            )

        if category == "healing":
            amount = event["amount"]
            target_text = target or (actor if not source_actor else "the wounded")
            hp_text = self.hp_phrase(str(event["defense"]), target_text)
            if source_actor:
                amount_text = f" {amount} hard-won hit points" if amount is not None else " strength"
                return _sentence(f"{target_text} clawed back{amount_text}{hp_text}")
            action_text = (
                f" through {action}"
                if action and action.casefold() not in {"healing", "healing applied"}
                else ""
            )
            amount_text = f" {amount} hit points" if amount is not None else " a measure of strength"
            return _sentence(
                f"{actor} reached {target_text}{action_text}, dragging back{amount_text} from the dark{hp_text}"
            )

        if category == "manual":
            detail = result or str(event["details"])
            return _sentence(f"Something moved beyond sight, and the balance shifted: {_clean_record_text(detail)}")

        if action_type == "note":
            detail = _clean_record_text(event["details"] or result)
            return _sentence(f"The chronicler marked it plainly: {detail}")

        if action_type == "effect":
            return self.effect_sentence(event, target)

        target_text = f" against {target}" if target else ""
        detail = result or _clean_record_text(event["details"])
        if source_actor:
            return _sentence(f"The balance shifted: {detail}") if detail else ""
        if action.casefold() == "action not reported" and detail.casefold() == "result not reported":
            return ""
        if detail and detail.casefold() not in {
            action.casefold(),
            action_type,
            "result not reported",
        }:
            return _sentence(f"{actor} brought {action} to bear{target_text}. {detail}")
        return _sentence(f"{actor} brought {action} to bear{target_text}")

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
                return f"—the die showed {natural_match.group(1)}, and the attack reached {total} against armor {armor}"
            return f"—the die showed {natural_match.group(1)}"
        if total is not None and armor is not None:
            return f"—the attack reached {total} against armor {armor}"
        if total is not None:
            return f"—the attack reached {total}"
        return f" against armor {armor}"

    @staticmethod
    def hp_phrase(defense: str, target: str) -> str:
        match = re.search(r"Target HP\s+(\d+)\s*/\s*(\d+)", defense, re.IGNORECASE)
        if not match:
            return ""
        current, maximum = int(match.group(1)), int(match.group(2))
        if current <= 0:
            return f". {target} went down with nothing left"
        if current == maximum:
            return f". {target} stood whole at {current} of {maximum} hit points"
        if current * 3 <= maximum:
            return f". {target} stayed upright by spite alone, with {current} of {maximum} hit points"
        return f". {target} endured with {current} of {maximum} hit points"

    @staticmethod
    def adjustment_phrase(result: str) -> str:
        reduced = re.search(r"reduced by\s+(\d+(?:\.\d+)?)", result, re.IGNORECASE)
        if reduced:
            return f". Defenses robbed {reduced.group(1)} points from the blow"
        increased = re.search(r"increased by\s+(\d+(?:\.\d+)?)", result, re.IGNORECASE)
        if increased:
            return f". Vulnerability made it crueler by {increased.group(1)}"
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

    @staticmethod
    def effect_sentence(event: Mapping[str, object], target: str) -> str:
        detail = _clean_record_text(event["result"] or event["details"])
        temporary = re.search(
            r"Temporary HP changed from\s+(\d+)\s+to\s+(\d+)",
            detail,
            re.IGNORECASE,
        )
        if temporary:
            before, after = int(temporary.group(1)), int(temporary.group(2))
            subject = target or "the warrior"
            if after > before:
                return _sentence(
                    f"A ward hardened around {subject}, raising its borrowed strength from {before} to {after}"
                )
            return _sentence(
                f"The ward around {subject} took the blow and dwindled from {before} to {after}"
            )
        return _sentence(f"The balance shifted: {detail}")

    @staticmethod
    def unseen_subject(event: Mapping[str, object], damage_type: str) -> str:
        if damage_type:
            if " and " in damage_type:
                return "A nameless blow"
            return f"{damage_type.capitalize()} from no named hand"
        variants = (
            "A blow from no named hand",
            "Something unseen",
            "A hidden force",
        )
        return variants[int(event["id"] or 0) % len(variants)]

    @staticmethod
    def outcome_sentence(outcome: str) -> str:
        clean = _clean_record_text(outcome)
        lowered = clean.casefold()
        if "victory" in lowered or "won" in lowered:
            return "Victory belonged to those still standing. They had paid for it, as soldiers always do."
        if "defeat" in lowered or "loss" in lowered:
            return "The field was lost. The survivors carried the cost away with them."
        if clean:
            return _sentence(f"When the noise died, this much remained: {clean}")
        return "At last the weapons lowered, and the living counted the cost."
