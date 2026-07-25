# Offline Combat Narrative Library

## Purpose

Lectern builds Combat Narrative entirely on the user's computer. The structured
Combat Session Log remains authoritative; the bundled narrative library only
selects language for facts the combat-event parser has already confirmed.

No combat event, character name, campaign detail, portrait, PDF, or generated
narrative is sent to an external AI provider.

## Ownership

| Data | Owner | Editing rule |
|---|---|---|
| Imported Fantasy Grounds combat events | Fantasy Grounds | Read-only in Lectern |
| Local combat events | Lectern | Edited through existing local combat workflows |
| Normalized actor/action/target/result event | Derived by Lectern | Regenerated from the authoritative event |
| Bundled phrase and style library | Lectern application | Versioned with the application |
| Rendered Combat Narrative | Derived by Lectern | Regenerated; never writes to the combat log |
| Future user phrase overrides or edited recaps | User | Not implemented; requires a separately approved persistence design |

## Library structure

The bundled
`app/resources/combat_narrative_library.json` file uses schema version 1.
It contains:

- a content version and default style;
- allowed template placeholders;
- forbidden literal language;
- named style profiles;
- phrase groups for rounds, complete action-resolution beats, attacks, damage,
  consequences, healing, temporary vitality, resistance, vulnerability,
  generic events, and outcomes.

The first profile is `heroic_military`. Additional profiles may be added under
the same schema after their factual and regression requirements are approved.

Lectern validates the complete library when the Combat Narrative page is
created. It rejects an unsupported schema, unknown style, missing category,
empty phrase set, unsupported placeholder, or forbidden literal phrase.

## Rendering rules

1. Parse and normalize the authoritative combat event.
2. Exclude system-only markers and provisional damage-roll rows.
3. Coalesce attack, save, damage, healing, and effect rows only when actor,
   target, and named action agree. Named damage contributors may extend the
   originating action name without breaking the link.
4. Link actions and secondary targets only when existing evidence supports the
   relationship.
5. Derive qualitative severity from confirmed applied damage and target state.
6. Select a phrase category based on the confirmed narrative beat.
7. Select one phrase deterministically from the approved category.
8. Substitute only allowlisted factual fields.
9. Render the result without changing the source event.

The deterministic selection key includes library version, style, phrase
category, event identifier, round, actor, action, target, category, and
recorded result. Including the event identifier varies repeated constructions
within a round while keeping regeneration stable. The same event set, library
version, and style therefore produces the same narrative.

## Narrative sample matrix

| Case | Required evidence | Required narrative behavior |
|---|---|---|
| Attack hit | Actor, target, action, confirmed hit | Preserve all four facts and coalesce matching applied damage into the same beat |
| Attack miss | Actor, target, action, confirmed miss | State failure without inventing a defense |
| Critical hit | Actor, target, action, confirmed critical result | Use grounded critical-hit language |
| Applied damage | Target and applied damage | Describe qualitative consequence without quantities |
| Known damage source | Confirmed actor and action | Attribute the damage to both |
| Unknown damage source | Applied target change without reliable cause | Keep the source unidentified |
| Resistance | Confirmed reduction or component resistance | Attribute resistance to the target |
| Vulnerability | Confirmed increase or component vulnerability | Attribute vulnerability without overstating the amount |
| Negated damage | Confirmed negation | State that the target is unharmed |
| Healing | Target and applied recovery; actor/action when confirmed | Describe recovery without exposing quantities |
| Temporary vitality gained | Target; actor/action only when confirmed | Describe a temporary buffer without inventing a ward |
| Temporary vitality lost | Matching target and applied loss | Place the protection consequence after the damage |
| Multi-target action | Confirmed first target plus contiguous compatible applied damage | Carry the confirmed action only across supported targets |
| Defeat state | Confirmed target endurance reaches zero | Say the target is brought down; never declare death |
| Encounter outcome | Recorded victory, defeat, or other outcome | Preserve the recorded outcome |
| Partial or older event | Only available structured/free-text evidence | Degrade safely without inventing missing fields |

## Authoring constraints

- Phrase variants may change voice, cadence, and sentence structure.
- Phrase variants may not assign a new actor, action, target, damage type,
  condition, motive, injury, death, spell, ability, or piece of equipment.
- Names of spells, abilities, and weapons come from the authoritative event;
  the library does not infer them from damage type.
- The library contains original prose, not copied rulebook or fiction text.
- Mechanical numbers may inform qualitative classification but do not appear in
  rendered prose, except numbered round headings and digits in combatant names.
- Application and integration names do not appear in the story.

## Verification

`scripts/combat_narrative_test.py` verifies:

- schema and content versions;
- supported and rejected style selection;
- a substantial phrase inventory;
- deterministic output;
- actor/action/target/result preservation;
- exact-link coalescing for attacks, saves, damage, healing, and effects;
- named-contributor coalescing without duplicate action sentences;
- expanded phrase pools and rejection of the repetitive `drives at` construction;
- multi-target attribution;
- resistance, vulnerability, healing, temporary vitality, and severity;
- absence of mechanical quantities and unsupported literary language;
- Combat Narrative page placement and encounter selection.
