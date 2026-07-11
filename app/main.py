from __future__ import annotations
import logging
import os
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from .paths import database_path, bundled_seed_path, bundled_monster_catalog_path, icon_path, user_data_dir
from .database.schema import initialize_database, connect
from .importers.spreadsheet_importer import SpreadsheetImporter
from .importers.monster_catalog import import_monster_catalog
from .services.logging_service import configure_logging, shutdown_logging
from .ui.main_window import MainWindow
from .version import APP_NAME, APP_VERSION

MONSTER_CATALOG_VERSION = "2026-07-10-4148"
SRD_RULES_VERSION = "2026-07-10-structured-ability-bonuses"


def _database_is_unseeded(db: Path) -> bool:
    with connect(db) as conn:
        tables = ("monsters", "weapons", "armor", "equipment", "magic_items", "spells")
        return all(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0 for table in tables)


def bootstrap(logger: logging.Logger) -> Path:
    db = database_path()
    logger.info("Starting %s %s", APP_NAME, APP_VERSION)
    logger.info("Python executable: %s", sys.executable)
    logger.info("Python version: %s", sys.version.replace("\n", " "))
    logger.info("Qt platform plugin: %s", os.environ.get("QT_QPA_PLATFORM", "default"))
    logger.info("User data directory: %s", user_data_dir())
    logger.info("Database path: %s", db)
    initialize_database(db)
    logger.info("Database initialization and schema migration complete")

    seed = bundled_seed_path()
    logger.info("Bundled seed path: %s (exists=%s)", seed, seed.exists())
    if seed.exists() and _database_is_unseeded(db):
        rows = SpreadsheetImporter(db).import_file(seed)
        logger.info("Initial seed import completed: %s rows", rows)
    else:
        logger.info("Seed import skipped; reference data already exists or seed is unavailable")
    with connect(db) as conn:
        row = conn.execute("SELECT value FROM metadata WHERE key='srd_rules_version'").fetchone()
        installed_rules_version = row[0] if row else None
    if seed.exists() and installed_rules_version != SRD_RULES_VERSION:
        rows = SpreadsheetImporter(db).import_rules_only(seed)
        with connect(db) as conn:
            conn.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES('srd_rules_version',?)", (SRD_RULES_VERSION,))
        logger.info("SRD character rules %s refreshed: %s rows", SRD_RULES_VERSION, rows)
    monster_catalog = bundled_monster_catalog_path()
    with connect(db) as conn:
        row = conn.execute("SELECT value FROM metadata WHERE key='monster_catalog_version'").fetchone()
        installed_catalog_version = row[0] if row else None
    if monster_catalog.exists() and installed_catalog_version != MONSTER_CATALOG_VERSION:
        rows = import_monster_catalog(db, monster_catalog)
        with connect(db) as conn:
            conn.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES('monster_catalog_version',?)", (MONSTER_CATALOG_VERSION,))
        logger.info("Monster catalog %s imported: %s rows", MONSTER_CATALOG_VERSION, rows)
    else:
        logger.info("Monster catalog import skipped; version is current or catalog is unavailable")
    return db


def _show_startup_error(app: QApplication, exc: BaseException) -> None:
    details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    log_file = user_data_dir() / "logs" / "application.log"
    box = QMessageBox()
    box.setIcon(QMessageBox.Critical)
    box.setWindowTitle(f"{APP_NAME} Startup Error")
    box.setText("Lectern could not complete startup.")
    box.setInformativeText(f"{exc}\n\nDiagnostic log: {log_file}")
    box.setDetailedText(details)
    box.exec()

def _ensure_window_is_visible(app: QApplication, window: MainWindow) -> None:
    """Move the main window onto an active monitor if it is off-screen."""
    window_frame = window.frameGeometry()

    is_visible = any(
        screen.availableGeometry().intersects(window_frame)
        for screen in app.screens()
    )

    if is_visible:
        return

    primary_screen = app.primaryScreen()
    if primary_screen is None:
        return

    available = primary_screen.availableGeometry()
    window_frame.moveCenter(available.center())
    window.move(window_frame.topLeft())

def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    if icon_path().exists():
        app.setWindowIcon(QIcon(str(icon_path())))

    logger = configure_logging()
    
    try:
        db = bootstrap(logger)
        win = MainWindow(db)
        win.show()
        _ensure_window_is_visible(app, win)
        autoclose = os.environ.get("LECTERN_TEST_AUTOCLOSE_MS")
        if autoclose:
            QTimer.singleShot(max(1, int(autoclose)), app.quit)
        return app.exec()
    except BaseException as exc:
        logger.exception("Fatal startup failure")
        _show_startup_error(app, exc)
        return 1
    finally:
        shutdown_logging()


if __name__ == "__main__":
    raise SystemExit(main())
