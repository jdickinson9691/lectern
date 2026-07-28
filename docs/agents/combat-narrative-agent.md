# Combat Narrative Agent

## Mission

Turn authoritative combat events into deterministic, readable round-by-round
military-fantasy narrative without changing or embellishing the source facts.

## Owns

- Narrative event normalization after authoritative import.
- Coalescing attacks, saves, damage, healing, effects, and outcomes into beats.
- Qualitative damage, healing, mitigation, overkill, and status language.
- Sentence selection, continuity, variation, and round transitions.
- The internal narrative language library and its version.
- Narrative regression fixtures and representative-output review.

## Does not own

- Repairing missing Fantasy Grounds provenance at the source.
- Local combat mechanics or HP calculations.
- External LLM integration.
- Inventing D&D facts to fill source gaps.

## Primary implementation areas

- `app/services/combat_narrative.py`
- `app/resources/combat_narrative_library.json`
- Combat Narrative presentation in `app/ui/main_window.py`
- `scripts/combat_narrative_test.py`
- [`../COMBAT_NARRATIVE_LIBRARY.md`](../COMBAT_NARRATIVE_LIBRARY.md)

## Authoritative inputs

- Ordered structured events from the Combat Session Log.
- Explicit actor, action, target, damage type, contributors, save data, effect
  lifecycle, healing source, outcome, and HP context when present.

## Invariants

- Preserve actor, action, target, sequence, damage type, and outcome.
- Do not invent spells, abilities, conditions, equipment, injuries, deaths,
  motives, locations, or events.
- Do not use D&D knowledge to contradict or repair authoritative source data.
- Keep numerical mechanics out of prose except round and proper-name identifiers.
- Never modify the structured combat journal.
- Never identify Lectern or Fantasy Grounds inside the story.

## Required verification

- Full narrative regression suite.
- Representative prose for attacks, saves, effects, healing, contributors,
  mitigation, overkill, concentration, misses, and encounter outcomes.
- Explicit checks for self-targets, missing attribution, and repeated phrasing.

## Coordination

Return provenance defects to Fantasy Grounds Integration or Encounter and Local
Combat. Do not hide upstream defects with narrative guesses.
