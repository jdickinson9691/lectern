from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from tempfile import mkdtemp

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication, QTableWidgetItem

from app.database.repositories import Repository
from app.database.schema import initialize_database
from app.services.portraits import is_managed_portrait, store_portrait
from app.ui.main_window import apply_portrait_icon


app = QApplication.instance() or QApplication([])
temp_dir = Path(mkdtemp(prefix="lectern_portrait_workflow_"))
try:
    portrait_dir = temp_dir / "portraits"
    wide_source = temp_dir / "pallor.png"
    image = QImage(200, 100, QImage.Format_ARGB32)
    image.fill(QColor("#8d2330"))
    assert image.save(str(wide_source), "PNG"), "Could not create portrait fixture"

    thumbnail = store_portrait(wide_source, portrait_dir, "Pallor")
    original_files = list(portrait_dir.glob("*_original.png"))
    assert thumbnail.is_file(), "Managed thumbnail was not created"
    assert len(original_files) == 1, "Original portrait was not preserved"
    assert is_managed_portrait(thumbnail, portrait_dir), "Managed thumbnail was not recognized"

    thumbnail_image = QImage(str(thumbnail))
    assert thumbnail_image.size().width() == 96 and thumbnail_image.size().height() == 96, "Thumbnail bounds are incorrect"
    assert thumbnail_image.pixelColor(0, 0).alpha() == 0, "Aspect-fit thumbnail did not retain transparent padding"
    assert thumbnail_image.pixelColor(48, 48) == QColor("#8d2330"), "Thumbnail content was not retained"

    second_source = temp_dir / "pallor-replacement.png"
    replacement = QImage(100, 200, QImage.Format_ARGB32)
    replacement.fill(QColor("#284f76"))
    assert replacement.save(str(second_source), "PNG"), "Could not create replacement fixture"
    second_thumbnail = store_portrait(second_source, portrait_dir, "Pallor")
    assert second_thumbnail != thumbnail, "Different source images collided on one managed filename"

    database = temp_dir / "test.db"
    initialize_database(database)
    repo = Repository(database)
    repo.upsert_player({"name": "Pallor", "portrait_path": str(thumbnail)})
    repo.upsert_player({"name": "Pallor", "class_name": "Cleric", "level": 6})
    saved = next(row for row in repo.list_players() if row["name"] == "Pallor")
    assert saved["portrait_path"] == str(thumbnail), "Re-import without a portrait cleared the existing portrait"
    repo.upsert_player({"name": "Pallor", "portrait_path": ""})
    cleared = next(row for row in repo.list_players() if row["name"] == "Pallor")
    assert cleared["portrait_path"] == "", "Explicit portrait clearing was ignored"

    portrait_item = QTableWidgetItem("Pallor")
    apply_portrait_icon(portrait_item, thumbnail)
    assert not portrait_item.icon().isNull(), "Managed portrait icon was not applied"
    fallback_item = QTableWidgetItem("Pummel Stone")
    apply_portrait_icon(fallback_item, "")
    assert not fallback_item.icon().isNull(), "Fallback portrait icon was not applied"

    print("Portrait workflow test passed.")
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)
