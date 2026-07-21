"""Offscreen regression checks for content-aware application page layouts."""

import os
import shutil
import sys
from pathlib import Path
from tempfile import mkdtemp

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QRect, Qt
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from app.database.schema import initialize_database
from app.ui.main_window import AdaptivePageLayout, MainWindow, adaptive_page_layout


temp_dir = Path(mkdtemp(prefix="lectern_adaptive_layout_"))
app = QApplication.instance() or QApplication([])
window = None
try:
    # A deterministic fixture verifies the spacing calculation independently of
    # platform-specific table and font size hints.
    fixture = QWidget()
    fixture_layout = adaptive_page_layout(fixture)
    for label in ("Title", "Controls", "Summary", "Content"):
        section = QLabel(label)
        section.setFixedHeight(30)
        fixture_layout.addWidget(section)
    fixture_layout.setGeometry(QRect(0, 0, 900, 140))
    compact_spacing = fixture_layout.spacing()
    fixture_layout.setGeometry(QRect(0, 0, 900, 700))
    spacious_spacing = fixture_layout.spacing()
    assert compact_spacing == fixture_layout.minimum_spacing
    assert spacious_spacing > compact_spacing
    assert spacious_spacing <= fixture_layout.maximum_spacing

    db_path = temp_dir / "layout.db"
    initialize_database(db_path)
    window = MainWindow(db_path)
    window.resize(1100, 700)
    window.show()
    app.processEvents()

    assert window.pages, "Main window did not create navigation pages"
    overview = window.dashboard_intro.text()
    assert all(term in overview for term in (
        "Lüdinn Entertainment Campaign Tracker for Encounters, Rules & Navigation",
        "local-first", "Campaign intelligence", "Fantasy Grounds integration",
    )), (
        "Dashboard application description is incomplete"
    )
    for page in window.pages:
        assert isinstance(page.layout(), AdaptivePageLayout), (
            f"{type(page).__name__} is missing the shared adaptive page layout"
        )
        assert page.layout().minimum_spacing <= page.layout().spacing() <= page.layout().maximum_spacing

    window.resize(1600, 1000)
    app.processEvents()
    for page in window.pages:
        assert page.layout().minimum_spacing <= page.layout().spacing() <= page.layout().maximum_spacing

    if len(sys.argv) > 1:
        screenshot_dir = Path(sys.argv[1])
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        for page_name in ("Dashboard", "Campaigns", "Encounter Builder"):
            matches = window.nav.findItems(page_name, Qt.MatchExactly)
            assert matches, f"Navigation page not found: {page_name}"
            window.nav.setCurrentItem(matches[0])
            app.processEvents()
            output = screenshot_dir / f"{page_name.lower().replace(' ', '_')}.png"
            assert window.grab().save(str(output)), f"Could not save {output}"

    print(
        "Adaptive layout test passed: all screens use bounded content-aware spacing "
        f"({compact_spacing}px compact, {spacious_spacing}px spacious)."
    )
finally:
    if window is not None:
        window.close()
    fixture.close()
    app.processEvents()
    shutil.rmtree(temp_dir, ignore_errors=True)
