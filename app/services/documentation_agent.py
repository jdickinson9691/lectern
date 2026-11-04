"""Generate print-ready campaign books from reviewed Lectern records."""
from __future__ import annotations

from pathlib import Path

from ..database.campaign_identity import CAMPAIGN_ID
from ..database.schema import connect
from .player_export import PlayerExportService
from .mission_experience import LEVEL_XP


CLASS_ACCESS = (
    ('Fighter / Champion', 'Starting'),
    ('Rogue / Thief', 'Starting'),
    ('Bard / College of Lore', 'Starting'),
    ('Sorcerer / Draconic Sorcery', 'Starting'),
    ('Cleric', 'Unavailable to new characters'),
    ('Wizard', 'Unavailable to new characters'),
    ('Warlock', 'Unavailable to new characters'),
    ('Paladin', 'Unavailable to new characters'),
    ('Ranger', 'Locked'),
)

KIND_TITLES = {
    'CAM': 'World and Company Lore', 'DOC': 'World Lore and Stories',
    'RULE': 'Campaign Rules', 'LOC': 'Locations',
    'FAC': 'Factions', 'NPC': 'Company NPCs', 'MIS': 'Missions',
}

WORLD_LORE_ORDER = (
    'first_making', 'draconic_origins', 'elder_makers', 'story',
    'sundering', 'departure_of_the_gods', 'lost_traditions',
    'class_access', 'family_masons_mark', 'family_empty_place',
    'family_divided_hymn', 'greyhaven_buried_steps',
    'redwater_backward_river', 'ridge_cairns',
)


def _lore_key(key: str) -> tuple[int, str]:
    try:
        return WORLD_LORE_ORDER.index(key), key
    except ValueError:
        return len(WORLD_LORE_ORDER), key


class DocumentationAgent:
    """Own the printable GM and player projections; never approve source facts."""

    def __init__(self, db_path: Path, campaign_id: str = CAMPAIGN_ID):
        self.db_path = Path(db_path)
        self.campaign_id = campaign_id

    def player_material(self) -> list[dict]:
        return PlayerExportService(self.db_path, self.campaign_id).snapshot()['entities']

    def gm_material(self) -> list[dict]:
        with connect(self.db_path) as conn:
            rows = conn.execute("""SELECT entity_id,kind,name FROM campaign_entities
                WHERE (entity_id=? OR campaign_id=?) AND status='approved'
                ORDER BY kind,name,entity_id""", (self.campaign_id, self.campaign_id)).fetchall()
            result = []
            for row in rows:
                facts = conn.execute("""SELECT audience,field_key,content FROM entity_knowledge
                    WHERE entity_id=? AND status='approved'
                    ORDER BY audience,field_key""", (row['entity_id'],)).fetchall()
                item = {'id': row['entity_id'], 'kind': row['kind'],
                        'name': row['name'], 'facts': [dict(f) for f in facts]}
                if row['kind'] == 'MIS':
                    plan = conn.execute("""SELECT max_total_levels,difficulty,lore,loot
                        FROM mission_plans WHERE mission_id=?""", (row['entity_id'],)).fetchone()
                    if plan:
                        item['plan'] = dict(plan)
                        item['monsters'] = [dict(m) for m in conn.execute("""SELECT m.name,
                            m.challenge_rating,mm.quantity FROM mission_monsters mm
                            JOIN monsters m ON m.id=mm.monster_id WHERE mm.mission_id=?
                            ORDER BY m.name""", (row['entity_id'],))]
                        item['hooks'] = [dict(h) for h in conn.execute("""SELECT h.lore_hook,
                            e.name AS future_mission FROM mission_hooks h LEFT JOIN
                            campaign_entities e ON e.entity_id=h.future_mission_id
                            WHERE h.mission_id=? ORDER BY h.id""", (row['entity_id'],))]
                    item['xp_awards'] = [dict(a) for a in conn.execute("""SELECT p.name,a.xp,
                        a.total_award,a.reason FROM mission_xp_awards a
                        JOIN players p ON p.id=a.player_id WHERE a.mission_id=?
                        ORDER BY a.player_id""", (row['entity_id'],))]
                result.append(item)
            return result

    def export(self, audience: str, destination: Path) -> Path:
        if audience not in ('gm', 'player'):
            raise ValueError('Choose GM or player documentation')
        from docx import Document
        from docx.enum.section import WD_SECTION_START
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        from docx.shared import Inches, Pt, RGBColor

        destination = Path(destination)
        material = self.player_material() if audience == 'player' else self.gm_material()
        doc = Document()
        section = doc.sections[0]
        section.page_width, section.page_height = Inches(8.5), Inches(11)
        section.top_margin = section.bottom_margin = Inches(.65)
        section.left_margin = section.right_margin = Inches(.7)
        styles = doc.styles
        styles['Normal'].font.name = 'Cambria'
        styles['Normal'].font.size = Pt(9.5)
        styles['Normal'].paragraph_format.space_after = Pt(5)
        for name, size in [('Title', 22), ('Heading 1', 15), ('Heading 2', 11)]:
            styles[name].font.name = 'Cambria'
            styles[name].font.size = Pt(size)
            styles[name].font.bold = True
        styles['Title'].font.color.rgb = RGBColor(0, 0, 0)
        title_props = styles['Title']._element.pPr
        if title_props is not None:
            for border in title_props.xpath('./w:pBdr'):
                title_props.remove(border)
        doc.add_paragraph('Ashen Company Game Master Guide' if audience == 'gm'
                          else 'Ashen Company Player Guide', style='Title')
        doc.add_paragraph('Printable campaign reference from reviewed Lectern content. '
                          'Official fifth edition rules remain in their published sources.')
        doc.add_paragraph('GM copy — keep private.' if audience == 'gm' else
                          'Player copy — approved information only.')
        columns = OxmlElement('w:cols')
        columns.set(qn('w:num'), '2')
        columns.set(qn('w:space'), '360')
        for existing in section._sectPr.xpath('./w:cols'):
            section._sectPr.remove(existing)
        section._sectPr.append(columns)

        def heading(title):
            doc.add_paragraph(title, style='Heading 1')

        heading('Characters and Classes')
        doc.add_paragraph('Players choose the party for each mission. The combined levels of '
                          'participating characters must not exceed that mission’s cap. The GM '
                          'records the selected characters in Lectern.')
        for option, access in CLASS_ACCESS:
            doc.add_paragraph(f'{option}: {access}')
        doc.add_paragraph('The GM has closed Cleric, Paladin, Wizard, and Warlock to new '
                          'characters following the Sundering. Locked options need an '
                          'in-game unlock. Other options require GM review. Lectern does '
                          'not yet enforce these choices during character entry or import.')
        heading('Skills and Field Roles')
        doc.add_paragraph('Build characters with the official fifth edition rules. The Company '
                          'values scouting, negotiation, investigation, medicine, survival, and '
                          'craft or tool work as well as combat. Players choose who takes each '
                          'role for a specific operation; Lectern does not require a fixed party.')
        heading('Mission System')
        doc.add_paragraph('Each mission has a player briefing, maximum combined character levels, '
                          'and a GM-selected difficulty: Easy, Normal, Difficult, Risky, or Deadly. '
                          'Difficulty is a planning judgment, not an automatic encounter calculation.')
        doc.add_paragraph('Before departure, read the briefing, agree on a roster within the level '
                          'cap, choose equipment, and record supplies. Afterward, record what was '
                          'learned, spent, recovered, and changed in the world. Mission rewards '
                          'and consequences are confirmed by the GM.')
        doc.add_paragraph('Ashen Company uses experience points, not milestone advancement. '
                          'The GM awards XP for challenges overcome and objectives completed. '
                          'The participating characters share each mission’s actual XP total '
                          'as evenly as whole points allow. A mission does not grant a level '
                          'simply because it was completed.')
        doc.add_paragraph('When cumulative XP reaches a level threshold, update the character '
                          'sheet with that level’s choices and hit points before the next mission. '
                          'An imported higher-level character starts with the minimum XP for '
                          'their recorded level unless the GM records a different history.')
        doc.add_paragraph('2024 Character Advancement XP Thresholds', style='Heading 2')
        threshold_table = doc.add_table(rows=1, cols=4)
        threshold_table.style = 'Light Shading Accent 1'
        for cell, label in zip(threshold_table.rows[0].cells, ('Level', 'Total XP', 'Level', 'Total XP')):
            cell.text = label
        for offset in range(10):
            cells = threshold_table.add_row().cells
            for cell, value in zip(cells, (str(offset + 1), f'{LEVEL_XP[offset]:,}',
                                           str(offset + 11), f'{LEVEL_XP[offset + 10]:,}')):
                cell.text = value
        if audience == 'gm':
            heading('Running the Campaign')
            doc.add_paragraph('In Lectern, select or create a campaign, then develop Canon and Lore, '
                              'Stories, Locations, Factions, NPCs, and Missions in that order. '
                              'Use the Fiction Agent to propose sourced text and Canon Review to '
                              'resolve conflicts. Approve facts before publishing them.')
            doc.add_paragraph('Mission Plan stores private lore, loot, monster quantities and CRs, '
                              'future lore hooks, and the chosen characters. Changing a public cap, '
                              'difficulty, or monster roster returns an approved mission to draft.')
            doc.add_paragraph('After play, use Award Mission XP on the approved mission. Review '
                              'the catalog monster XP against threats actually defeated or '
                              'neutralized, add XP for completed objectives and other challenges, '
                              'then enter the actual total and a reason. Lectern divides it among '
                              'the selected characters and blocks a second award for the same '
                              'mission. It does not award XP automatically from the planned roster.')
            doc.add_paragraph('For each operation, review the approved fiction background, set the '
                              'level cap and difficulty, list catalog monsters and quantities, '
                              'write private clues and loot, and link future hooks. Check the '
                              'actual chosen character levels before play. Use the encounter '
                              'builder and combat dashboard to run or record combat.')
            heading('Lectern and Fantasy Grounds')
            doc.add_paragraph('Use Review and Publish to inspect visibility and approval before '
                              'exporting. Player JSON and the Fantasy Grounds Story module use the '
                              'approved player projection. Full CSV exports can contain GM data. '
                              'Fantasy Grounds Sync imports characters and combat into Lectern; '
                              'the module adapter publishes approved Story content outward.')
            doc.add_paragraph('To add content with ChatGPT, draft a sourced proposal, compare it '
                              'with approved canon in Canon Review, accept it as draft, then '
                              'approve the fact in Lectern. For manual edits, create the record '
                              'and source links in its Lectern editor, review visibility, and '
                              'approve only the intended player text. Export a fresh module '
                              'after changes and reload it in Fantasy Grounds.')
            heading('Company Resources')
            doc.add_paragraph('Track characters, equipment, encounters, and rewards in Lectern. '
                              'Record mission loot in the private plan until the GM reveals it. '
                              'The current software does not enforce a shared company inventory '
                              'or an automatic class access gate.')
            doc.add_paragraph('Keep a dated field ledger for money, shared supplies, gear issued, '
                              'wounds, downtime, and mission consequences. Decide who owns each '
                              'item and when recovered loot becomes player knowledge. Treat the '
                              'ledger as a GM procedure until the campaign has a dedicated '
                              'shared resource model.')
        else:
            heading('Company Resources')
            doc.add_paragraph('Agree on party composition and gear before departure. Keep a record '
                              'of equipment spent, recovered loot, and rewards with the GM. '
                              'Lectern does not yet enforce a shared company inventory.')
            doc.add_paragraph('Ask the GM which supplies are issued by the Company and which are '
                              'personal. Note spent ammunition, consumables, injuries, money, '
                              'salvage, and downtime after each operation. The GM confirms '
                              'ownership and when hidden rewards become known.')

        for kind, title in KIND_TITLES.items():
            group = [item for item in material if item['kind'] == kind]
            if not group:
                continue
            heading(title)
            if kind == 'DOC':
                group.sort(key=lambda item: (0 if item['name'] == 'The Sundering: Public History' else 1,
                                             item['name']))
            for item in group:
                display_name = ('The History of the World'
                                if kind == 'DOC' and item['name'] == 'The Sundering: Public History'
                                else item['name'])
                doc.add_paragraph(display_name, style='Heading 2')
                if audience == 'player':
                    facts = item['knowledge'].items()
                    if kind == 'DOC' and item['name'] == 'The Sundering: Public History':
                        facts = sorted(facts, key=lambda fact: _lore_key(fact[0]))
                    else:
                        facts = sorted(facts)
                    for key, value in facts:
                        label = 'Age and Surviving Ruins' if key == 'story' and kind == 'DOC' and item['name'] == 'The Sundering: Public History' else key.replace('_', ' ').title()
                        doc.add_paragraph(f'{label}: {value}')
                else:
                    facts = item['facts']
                    if kind == 'DOC' and item['name'] == 'The Sundering: Public History':
                        facts = sorted(facts, key=lambda fact: _lore_key(fact['field_key']))
                    for fact in facts:
                        label = 'Age and Surviving Ruins' if fact['field_key'] == 'story' and kind == 'DOC' and item['name'] == 'The Sundering: Public History' else fact['field_key'].replace('_', ' ').title()
                        doc.add_paragraph(f"{label} "
                                          f"({fact['audience']}): {fact['content']}")
                    plan = item.get('plan')
                    if plan:
                        doc.add_paragraph(f"Level cap: {plan['max_total_levels'] or 'unset'}; "
                                          f"difficulty: {plan['difficulty'] or 'unset'}")
                        if plan['lore']:
                            doc.add_paragraph(f"GM mission lore: {plan['lore']}")
                        if plan['loot']:
                            doc.add_paragraph(f"Loot: {plan['loot']}")
                        for monster in item.get('monsters', []):
                            doc.add_paragraph(f"Monster: {monster['name']} ×{monster['quantity']} "
                                              f"(CR {monster['challenge_rating']})")
                        for hook in item.get('hooks', []):
                            target = hook['future_mission'] or 'Unlinked future mission'
                            doc.add_paragraph(f"Future hook ({target}): {hook['lore_hook']}")
                    for award in item.get('xp_awards', []):
                        doc.add_paragraph(f"XP awarded: {award['name']} +{award['xp']} "
                                          f"of {award['total_award']} total; {award['reason']}")
        footer = section.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer.text = 'Ashen Company • ' + ('GM' if audience == 'gm' else 'Players')
        destination.parent.mkdir(parents=True, exist_ok=True)
        doc.save(destination)
        return destination
