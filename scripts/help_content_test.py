from __future__ import annotations

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication

from app.ui.main_window import HelpPage


help_text = (ROOT / "docs" / "USER_HELP.md").read_text(encoding="utf-8")
screen_sections = [
    "Dashboard", "Campaigns", "Encounter Builder", "Combat Dashboard", "Players",
    "Monster Library", "Add Monster", "Weapons", "Armor", "Equipment", "Magic Items",
    "Spells", "CSV Import and Export", "Fantasy Grounds Sync", "Data Workflow", "Error Logs", "Help",
]

for title in screen_sections:
    assert f"## {title}\n" in help_text, f"Help section is missing for {title}"
    anchor = HelpPage.anchor_name(title)
    assert f"](#{anchor})" in help_text, f"Help contents link is missing for {title}"

for index, title in enumerate(screen_sections):
    if title == "Fantasy Grounds Sync":
        continue
    start = help_text.index(f"## {title}\n")
    next_heading = re.search(r"(?m)^## ", help_text[start + 3:])
    end = start + 3 + next_heading.start() if next_heading else len(help_text)
    assert "### Fantasy Grounds impact" in help_text[start:end], f"Fantasy Grounds impact is missing for {title}"

assert "A manually built Lectern encounter is local and editable" in help_text
assert "| Local Lectern encounter |" in help_text
assert "| Fantasy Grounds Prepared encounter |" in help_text
assert "| Fantasy Grounds Live combat session |" in help_text

app = QApplication.instance() or QApplication([])
page = HelpPage()
page.resize(900, 700)
page.show()
app.processEvents()
assert set(HelpPage.anchor_name(title) for title in screen_sections) <= set(page.help_anchor_positions)
page.open_help_link(QUrl("#players"))
app.processEvents()
assert page.viewer.verticalScrollBar().value() > 0, "Help title link did not jump to its section"
page.close()

print("Help content and navigation test passed.")
