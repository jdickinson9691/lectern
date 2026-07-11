from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader


ABILITY_KEYS = ("str", "dex", "con", "int", "wis", "cha")
SKILLS = {
    "acrobatics": "Acrobatics", "animalhandling": "Animal Handling", "arcana": "Arcana",
    "athletics": "Athletics", "deception": "Deception", "history": "History", "insight": "Insight",
    "intimidation": "Intimidation", "investigation": "Investigation", "medicine": "Medicine",
    "nature": "Nature", "perception": "Perception", "performance": "Performance",
    "persuasion": "Persuasion", "religion": "Religion", "sleightofhand": "Sleight of Hand",
    "stealth": "Stealth", "survival": "Survival",
}


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _integer(value, default=None):
    match = re.search(r"-?\d+", str(value or ""))
    return int(match.group()) if match else default


class CharacterPdfImporter:
    """Extract common D&D character fields from form-enabled or text PDFs."""

    ALIASES = {
        "name": ["charactername", "character name", "charname"],
        "player_name": ["playername", "player name"],
        "species": ["race", "species", "ancestry"],
        "class_level": ["classlevel", "class and level", "classlevelvalue"],
        "background": ["background"],
        "armor_class": ["ac", "armorclass", "armor class"],
        "max_hp": ["hpmax", "maxhp", "hitpointmaximum", "hit point maximum"],
        "current_hp": ["hpcurrent", "currenthp", "current hit points"],
        "initiative_mod": ["initiative", "init", "initiativebonus"],
        "feats": ["featuresandtraits", "features traits", "feats", "featsandtraits"],
        "equipment": ["equipment", "equipmentnotes"],
        "notes": ["additionalfeaturesandtraits", "additional notes", "notes"],
    }

    def extract(self, path: Path) -> dict:
        reader = PdfReader(str(path))
        fields = reader.get_fields() or {}
        normalized = {}
        for raw_name, field in fields.items():
            value = field.get("/V") if hasattr(field, "get") else field
            if value not in (None, "", "/Off"):
                normalized[_key(raw_name)] = str(value).lstrip("/").strip()
        # D&D Beyond exports can contain valid page-level Widget annotations
        # without registering an /AcroForm on the document root. In that case
        # PdfReader.get_fields() is empty even though every visible value has a
        # /T field name and /V value on its page annotation.
        for page in reader.pages:
            for reference in page.get("/Annots", []):
                annotation = reference.get_object()
                if annotation.get("/Subtype") != "/Widget":
                    continue
                raw_name = annotation.get("/T") or annotation.get("/TU")
                value = annotation.get("/V")
                if raw_name and value not in (None, "", "/Off"):
                    normalized[_key(raw_name)] = str(value).lstrip("/").strip()
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        data = {}
        for target, aliases in self.ALIASES.items():
            for alias in aliases:
                if _key(alias) in normalized:
                    data[target] = normalized[_key(alias)]
                    break
        feature_sections = [value for key, value in sorted(normalized.items()) if key.startswith("featurestraits")]
        if feature_sections and "notes" not in data:
            data["notes"] = "\n\n".join(feature_sections)
        self._map_dnd_beyond_fields(normalized, data)
        for ability in ABILITY_KEYS:
            for alias in (ability, ability.upper(), ability + "score", ability + " score"):
                if _key(alias) in normalized:
                    value = _integer(normalized[_key(alias)])
                    if value is not None: data[f"{ability}_base"] = value
                    break
        self._text_fallback(text, data)
        self._normalize(data)
        warnings = []
        if not data.get("name"): warnings.append("Character name was not detected.")
        if not normalized: warnings.append("No embedded PDF form fields were found; results came from text extraction.")
        if len(data) < 4: warnings.append("Few fields were detected. This PDF may require OCR or manual entry.")
        return {"data": data, "warnings": warnings, "field_count": len(data), "form_field_count": len(normalized)}

    def _map_dnd_beyond_fields(self, fields: dict, data: dict) -> None:
        proficiencies, expertise = [], []
        for key, label in SKILLS.items():
            marker = str(fields.get(f"{key}prof", "")).strip().upper()
            if marker:
                proficiencies.append(label)
                if marker == "E": expertise.append(label)
        if proficiencies: data["skill_proficiencies"] = "; ".join(proficiencies)
        if expertise: data["skill_expertise"] = "; ".join(expertise)

        save_proficiencies = []
        for ability in ABILITY_KEYS:
            if str(fields.get(f"{ability}prof", "")).strip(): save_proficiencies.append(ability)
        if save_proficiencies: data["saving_throw_proficiencies"] = "; ".join(save_proficiencies)

        equipment_rows = []
        for index in range(100):
            name = str(fields.get(f"eqname{index}", "")).strip()
            if not name: continue
            quantity = str(fields.get(f"eqqty{index}", "")).strip()
            weight = str(fields.get(f"eqweight{index}", "")).strip()
            details = [name]
            if quantity and quantity not in {"1", "--"}: details.append(f"x{quantity}")
            if weight and weight != "--": details.append(f"({weight})")
            equipment_rows.append(" ".join(details))
        if equipment_rows: data["inventory"] = "\n".join(equipment_rows)

        weapons = [str(fields.get(key, "")).strip() for key in ("wpnname", "wpnname2", "wpnname3")]
        weapons = [weapon for weapon in weapons if weapon]
        if weapons:
            data["equipped_weapon"] = weapons[0]
            data["equipment"] = "Weapons: " + ", ".join(weapons)

        armor_terms = ("armor", "leather", "mail", "plate", "hide", "shield")
        armor = next((row.split(" (")[0] for row in equipment_rows if any(term in row.lower() for term in armor_terms)), "")
        if armor: data["equipped_armor"] = armor

        casting = str(fields.get("spellcastingability0", "")).strip().upper()
        ability_names = {"INT": "Intelligence", "WIS": "Wisdom", "CHA": "Charisma"}
        if casting in ability_names: data["spellcasting_ability"] = ability_names[casting]

        feature_text = "\n\n".join(value for key, value in sorted(fields.items()) if key.startswith("featurestraits"))
        feat_section = re.search(r"===\s*FEATS\s*===(.*?)(?:\n\s*===|\Z)", feature_text, re.I | re.S)
        if feat_section:
            feats = re.findall(r"^\s*\*\s*([^\n�•]+?)(?:\s*[�•-]\s*[^\n]+)?\s*$", feat_section.group(1), re.M)
            clean_feats = [feat.strip() for feat in feats if feat.strip()]
            if clean_feats: data["feats"] = "; ".join(dict.fromkeys(clean_feats))

    def _text_fallback(self, text: str, data: dict) -> None:
        patterns = {
            "name": r"(?:character\s*name)\s*:\s*([^\n]+)",
            "species": r"(?:race|species)\s*:\s*([^\n]+)",
            "background": r"background\s*:\s*([^\n]+)",
            "class_level": r"class(?:\s*&?\s*level)?\s*:\s*([^\n]+)",
            "armor_class": r"armor\s*class\s*:\s*(\d+)",
            "max_hp": r"(?:hit\s*point\s*maximum|max(?:imum)?\s*hp)\s*:\s*(\d+)",
        }
        for target, pattern in patterns.items():
            if target not in data and (match := re.search(pattern, text, re.I)):
                data[target] = match.group(1).strip()

    def _normalize(self, data: dict) -> None:
        for field, default in (("armor_class", 10), ("max_hp", 1), ("current_hp", None), ("initiative_mod", 0)):
            if field in data: data[field] = _integer(data[field], default)
        class_level = str(data.pop("class_level", "")).strip()
        if class_level:
            levels = [int(x) for x in re.findall(r"\b(\d{1,2})\b", class_level)]
            data["level"] = min(20, max(1, sum(levels) if levels else 1))
            data["class_name"] = re.sub(r"\s*\d+.*$", "", class_level).strip(" /,")
        feats = str(data.get("feats", "")).strip()
        if feats:
            data["feats"] = "; ".join(x.strip() for x in re.split(r"[;,\n]", feats) if x.strip())
