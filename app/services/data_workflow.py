from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from ..database.schema import initialize_database
from ..importers.spreadsheet_importer import SpreadsheetImporter
from ..paths import bundled_seed_path, user_data_dir


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


class DataWorkflowService:
    """Safe database maintenance operations used by the v2.8 Data Workflow screen."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.backup_dir = user_data_dir() / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def backup_database(self, destination: Path | None = None) -> Path:
        if not self.db_path.exists():
            initialize_database(self.db_path)
        destination = Path(destination) if destination else self.backup_dir / f"campaign_manager_backup_{timestamp()}.db"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.db_path, destination)
        return destination

    def restore_database(self, source: Path) -> Path:
        source = Path(source)
        if not source.exists():
            raise FileNotFoundError(source)
        # Always preserve the current DB before overwriting it.
        self.backup_database(self.backup_dir / f"pre_restore_backup_{timestamp()}.db")
        shutil.copy2(source, self.db_path)
        initialize_database(self.db_path)
        return self.db_path

    def reset_database(self, keep_backup: bool = True) -> None:
        if keep_backup and self.db_path.exists():
            self.backup_database(self.backup_dir / f"pre_reset_backup_{timestamp()}.db")
        if self.db_path.exists():
            self.db_path.unlink()
        initialize_database(self.db_path)

    def reseed_database(self, keep_backup: bool = True) -> int:
        self.reset_database(keep_backup=keep_backup)
        seed = bundled_seed_path()
        if not seed.exists():
            raise FileNotFoundError(seed)
        return SpreadsheetImporter(self.db_path).import_file(seed)

    def log_files(self) -> list[Path]:
        log_dir = user_data_dir() / "logs"
        return sorted(log_dir.glob("*.log*"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)

    def read_log(self, path: Path, max_chars: int = 120_000) -> str:
        path = Path(path)
        if not path.exists():
            return ""
        text = path.read_text(encoding="utf-8", errors="replace")
        return text[-max_chars:]
