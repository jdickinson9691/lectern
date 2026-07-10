from __future__ import annotations
import importlib
import os
import platform
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED = ("PySide6", "sqlalchemy", "openpyxl")


def main() -> int:
    from app.version import APP_VERSION
    print(f"Lectern v{APP_VERSION} launch diagnostics")
    print("Python:", sys.version.replace("\n", " "))
    print("Executable:", sys.executable)
    print("Platform:", platform.platform())
    print("Working directory:", Path.cwd())
    failed = False
    for module in REQUIRED:
        try:
            loaded = importlib.import_module(module)
            print(f"[OK] {module} {getattr(loaded, '__version__', '')}")
        except Exception as exc:
            failed = True
            print(f"[FAIL] {module}: {exc!r}")
    if failed:
        print("Dependency check failed. Run: .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt")
        return 2

    from PySide6.QtCore import QLibraryInfo
    from app.paths import icon_path, watermark_path, bundled_seed_path
    from app.database.schema import initialize_database, connect

    print("Qt plugins:", QLibraryInfo.path(QLibraryInfo.PluginsPath))
    for label, path in (("Icon", icon_path()), ("Watermark", watermark_path()), ("Seed", bundled_seed_path())):
        print(f"[{'OK' if path.exists() else 'FAIL'}] {label}: {path}")
        failed |= not path.exists()

    with tempfile.TemporaryDirectory(prefix="lectern_diag_") as temp:
        db = Path(temp) / "diagnostic.db"
        initialize_database(db)
        conn = connect(db)
        try:
            version = conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0]
        finally:
            # sqlite3.Connection's context manager commits/rolls back but does not
            # close the handle. Windows will not remove the temporary directory
            # while diagnostic.db remains open.
            conn.close()
        print(f"[OK] Clean database initialized; schema={version}; sqlite={sqlite3.sqlite_version}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
