from __future__ import annotations
from pathlib import Path
import os
import sys
from .version import APP_ID


def project_root() -> Path:
    """Return the source root or PyInstaller extraction root."""
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root)
    return Path(__file__).resolve().parents[1]


def resource_path(*parts: str) -> Path:
    return project_root().joinpath(*parts)


def user_data_dir() -> Path:
    override = os.environ.get("LECTERN_DATA_DIR")
    if override:
        root = Path(override).expanduser().resolve()
    else:
        base = os.environ.get("LOCALAPPDATA")
        root = Path(base) / APP_ID if base else project_root() / "runtime"
    root.mkdir(parents=True, exist_ok=True)
    for child in ["data", "logs", "backups", "exports", "config"]:
        (root / child).mkdir(parents=True, exist_ok=True)
    return root


def database_path() -> Path:
    return user_data_dir() / "data" / "campaign_manager.db"


def bundled_seed_path() -> Path:
    return resource_path("seeds", "dnd_5e_combat_tracker_v5_clean.xlsx")


def bundled_monster_catalog_path() -> Path:
    return resource_path("seeds", "monsters.csv")


def icon_path() -> Path:
    return resource_path("app", "resources", "lectern_icon.png")


def watermark_path() -> Path:
    return resource_path("app", "resources", "lectern_watermark.png")


def help_path() -> Path:
    return resource_path("docs", "USER_HELP.md")
