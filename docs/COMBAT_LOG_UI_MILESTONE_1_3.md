# Combat Log UI - Milestone 1.3

## Objective

Turn the Combat Dashboard's plain-text history into a readable review surface for both local Lectern actions and detailed Fantasy Grounds combat events.

## Delivered interface

- Seven columns: Actor, Type, Roll, Target, Defense / HP, Action, and Result.
- Newest round first, with expanded round headings and event counts.
- Color-backed result cells for critical hits, hits, misses, damage, healing, and manual or unattributed changes. Every color also has a text label.
- Search across actors, targets, actions, result text, and original details.
- Action-type and result filters that can be combined with search.
- A turn-marker visibility toggle.
- Expandable original details and timestamps beneath every event.
- Compatibility with Fantasy Grounds pipe-delimited details and older/local free-text rows.
- A 500-event display limit instead of the previous 100-line limit.

## Automated acceptance

`scripts/combat_log_ui_test.py` verifies:

1. Structured Fantasy Grounds attack parsing.
2. Round grouping and newest-round ordering.
3. Default hiding and optional display of turn markers.
4. Search by named action.
5. Action-type and result filtering.
6. Critical-hit, damage, healing, and manual-result classification.
7. Expandable original event details.

## Follow-up candidates

- Click actor and target names to navigate to their Lectern records.
- Export the currently filtered view.
- Persist preferred column widths and filter state.
- Add multi-row visual linkage between an attack, its damage roll, and applied damage.
