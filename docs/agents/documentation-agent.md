# Campaign Documentation Agent

## Mission

Maintain printable, two column Ashen Company GM and player guides from the
current reviewed campaign records and the implemented Lectern systems.

## Owns

- The Word guide generator and its print layout.
- The GM guide's operating instructions for canon, stories, world content,
  characters, classes, missions, resources, Lectern, and Fantasy Grounds.
- The player guide's approved lore, stories, locations, factions, NPCs,
  mission briefings, class access, party selection, and resource guidance.
- Publication tests that reject private facts from player output.

## Authority and boundaries

- Read approved campaign entities and approved knowledge for the GM book.
- Read only `PlayerExportService.snapshot()` for campaign material in the
  player book. Never query private campaign tables for player material.
- The documentation agent cannot approve facts, create canon, invent class
  rules, or publish draft story text. Review and approval stay with the GM.
- Rebuild both books after approved canon or system guidance changes. Save
  dated copies for a game session; an old printed copy is not live canon.

## How to use

In the Ashen workspace open **Review & Publish** and select **Export Player
Guide** or **Export GM Guide**. Choose a `.docx` destination and print from
Word. The books use US Letter pages with two text columns.
