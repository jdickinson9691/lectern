"""Regression for FG-EFFECT-002 live named-power provenance."""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.integrations.fantasy_grounds import format_event_log
from app.services.combat_narrative import CombatNarrativeBuilder


extension_source = (
    ROOT
    / "integrations"
    / "fantasy_grounds"
    / "extension"
    / "LecternSync"
    / "scripts"
    / "lectern_sync.lua"
).read_text(encoding="utf-8")

assert "local fPreviousPowerPerformAction = nil" in extension_source
assert (
    "local function authoritativePowerPerformAction("
    "draginfo, rActor, rAction, nodePower)"
) in extension_source
assert (
    "fPreviousPowerPerformAction = PowerManager.performAction"
    in extension_source
)
assert (
    "PowerManager.performAction = authoritativePowerPerformAction"
    in extension_source
)
assert (
    "PowerManager.performAction == authoritativePowerPerformAction"
    in extension_source
)
assert "effectActionName(rAction, sEffectText, nodePower)" in extension_source
assert "local function linkedOwningPowerName(nodePower)" in extension_source
assert "not powerHasExecutableActions(nodeCandidate)" in extension_source
assert "descriptionReferencesPower(nodeCandidate, sExecutedName)" in extension_source
assert "if nOwnerCount > 1 then return \"\" end" in extension_source
assert 'nodeText(nodePower, "name", nodeText(nodePower, "label", ""))' in extension_source
assert "rAction.nodeAction and DB.getPath(rAction.nodeAction)" in extension_source
assert "nodePower and DB.getPath(nodePower)" in extension_source
assert "captured_event_sequence = nEventSequence" in extension_source
assert "bSameTarget and bNearSequence" in extension_source

wrapper_start = extension_source.index(
    "local function authoritativePowerPerformAction"
)
wrapper_end = extension_source.index(
    "local function authoritativeEffectAdded", wrapper_start
)
wrapper_source = extension_source[wrapper_start:wrapper_end]
assert wrapper_source.index(
    "queueOriginatingEffectAction(rActor, rAction, nodePower)"
) < wrapper_source.index(
    "fPreviousPowerPerformAction(draginfo, rActor, rAction, nodePower)"
), "The authoritative 5E power must be queued before Fantasy Grounds applies it"

# Test8 reproduced the live Fantasy Grounds hierarchy: the owning invocation
# and executable spell are sibling power records in one group, while the
# mechanical effect remains a child action of the spell. This model guards the
# data-driven relationship without mapping Armor of Shadows from AC mechanics.
test8_power_hierarchy = ET.fromstring(
    """
    <powers>
      <id-00001>
        <actions />
        <description>
          <p>You can cast Mage Armor on yourself.</p>
          <linklist><link class="power">Spell: Mage Armor</link></linklist>
        </description>
        <group>Eldritch Invocations (Warlock)</group>
        <name>Armor of Shadows</name>
      </id-00001>
      <id-00016>
        <actions>
          <id-00001><label>AC: 3</label><type>effect</type></id-00001>
        </actions>
        <group>Eldritch Invocations (Warlock)</group>
        <name>Mage Armor</name>
      </id-00016>
    </powers>
    """
)


def _has_executable_actions(power: ET.Element) -> bool:
    return any(
        (action.findtext("type") or "").strip()
        for action in power.findall("./actions/*")
    )


def _linked_owner_name(powers: ET.Element, executed: ET.Element) -> str:
    executed_name = (executed.findtext("name") or "").strip()
    executed_group = (executed.findtext("group") or "").strip()
    candidates = []
    for candidate in powers:
        if candidate is executed:
            continue
        candidate_description = " ".join(candidate.itertext()).lower()
        if (
            (candidate.findtext("group") or "").strip() == executed_group
            and not _has_executable_actions(candidate)
            and executed_name.lower() in candidate_description
        ):
            candidates.append((candidate.findtext("name") or "").strip())
    return candidates[0] if len(candidates) == 1 else ""


executed_power = test8_power_hierarchy.find("./id-00016")
assert executed_power is not None
assert _linked_owner_name(test8_power_hierarchy, executed_power) == "Armor of Shadows"
assert executed_power.findtext("./actions/id-00001/label") == "AC: 3"

ambiguous_hierarchy = ET.fromstring(ET.tostring(test8_power_hierarchy))
second_owner = ET.fromstring(
    """
    <id-00017>
      <actions />
      <description><p>Also references Mage Armor.</p></description>
      <group>Eldritch Invocations (Warlock)</group>
      <name>Ambiguous Invocation</name>
    </id-00017>
    """
)
ambiguous_hierarchy.append(second_owner)
ambiguous_executed = ambiguous_hierarchy.find("./id-00016")
assert ambiguous_executed is not None
assert _linked_owner_name(ambiguous_hierarchy, ambiguous_executed) == ""

named_event = {
    "type": "effect",
    "round": 1,
    "actor": {"source_key": "5E:character:warlock1", "name": "Warlock1"},
    "target": {"source_key": "5E:ct:warlock1", "name": "Warlock1"},
    "amount": None,
    "description": "Effect added to Warlock1: AC: 3; [D: 8 hours]",
    "metadata": {
        "action_name": "Armor of Shadows",
        "originating_action": "Armor of Shadows",
        "effect_name": "AC: 3",
        "effect_key": "combattracker.list.warlock1.effects.armor",
        "effect_state": "added",
        "lifecycle": "effect_added",
        "duration": 8,
        "apply": None,
        "is_active": True,
        "source_name": "Warlock1",
        "source_reference": "combattracker.list.warlock1",
        "source_attribution": "originating_effect_action",
    },
}
named_row = format_event_log(named_event)
assert named_row.actor == "Warlock1"
assert (
    named_row.details
    == " | Warlock1 | Effect added | Armor of Shadows | "
    "Effect added to Warlock1: AC: 3; [D: 8 hours]"
)

builder = CombatNarrativeBuilder()
named_narrative = builder.build(
    [
        {
            "id": 1,
            "round": named_event["round"],
            "actor": named_row.actor,
            "action_type": named_row.action_type,
            "details": named_row.details,
        }
    ],
    "Test7 Armor",
    "unresolved",
)
assert "Armor of Shadows" in named_narrative
assert not re.search(r"\bAC\s*:\s*3\b|\b8 hours\b", named_narrative)

generic_event = {
    **named_event,
    "actor": {"source_key": "5E:character:unknown", "name": "Unknown Mage"},
    "target": {"source_key": "5E:ct:unknown", "name": "Unknown Mage"},
    "description": "Effect added to Unknown Mage: AC: 3; [D: 8 hours]",
    "metadata": {
        **named_event["metadata"],
        "action_name": "Effect",
        "originating_action": "Effect",
        "effect_key": "combattracker.list.unknown.effects.armor",
        "source_name": "Unknown Mage",
        "source_reference": "combattracker.list.unknown",
        "source_attribution": "active_self",
    },
}
generic_row = format_event_log(generic_event)
assert "Armor of Shadows" not in generic_row.details
assert " | Unknown Mage | Effect added | Effect | " in generic_row.details

generic_narrative = builder.build(
    [
        {
            "id": 2,
            "round": generic_event["round"],
            "actor": generic_row.actor,
            "action_type": generic_row.action_type,
            "details": generic_row.details,
        }
    ],
    "Generic Effect",
    "unresolved",
)
assert "Armor of Shadows" not in generic_narrative

print("Fantasy Grounds live effect provenance test passed.")
