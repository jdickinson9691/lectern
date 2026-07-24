from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QImageReader, QPainter


THUMBNAIL_SIZE = 96
SUPPORTED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def _safe_character_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_") or "character"


def is_managed_portrait(path: Path, portrait_dir: Path) -> bool:
    try:
        path.resolve().relative_to(portrait_dir.resolve())
        return path.is_file() and path.name.endswith("_thumb.png")
    except (OSError, ValueError):
        return False


def store_portrait(
    source_path: Path,
    portrait_dir: Path,
    character_name: str,
    thumbnail_size: int = THUMBNAIL_SIZE,
) -> Path:
    """Preserve a source image and return a managed square thumbnail path."""
    source_path = Path(source_path)
    portrait_dir = Path(portrait_dir)
    if not source_path.is_file():
        raise ValueError(f"Portrait image was not found: {source_path}")

    reader = QImageReader(str(source_path))
    reader.setAutoTransform(True)
    image = reader.read()
    if image.isNull():
        message = reader.errorString() or "unsupported or damaged image"
        raise ValueError(f"Could not read portrait image: {message}")

    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()[:12]
    stem = f"{_safe_character_name(character_name)}_{digest}"
    suffix = source_path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        suffix = ".png"

    portrait_dir.mkdir(parents=True, exist_ok=True)
    original_path = portrait_dir / f"{stem}_original{suffix}"
    if source_path.resolve() != original_path.resolve():
        if source_path.suffix.lower() in SUPPORTED_SUFFIXES:
            if not original_path.exists():
                shutil.copy2(source_path, original_path)
        elif not image.save(str(original_path), "PNG"):
            raise ValueError("Could not preserve the original portrait image")

    thumbnail = QImage(
        thumbnail_size,
        thumbnail_size,
        QImage.Format_ARGB32_Premultiplied,
    )
    thumbnail.fill(Qt.transparent)
    scaled = image.scaled(
        thumbnail_size,
        thumbnail_size,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation,
    )
    x = (thumbnail_size - scaled.width()) // 2
    y = (thumbnail_size - scaled.height()) // 2
    painter = QPainter(thumbnail)
    painter.drawImage(x, y, scaled)
    painter.end()

    thumbnail_path = portrait_dir / f"{stem}_thumb.png"
    if not thumbnail.save(str(thumbnail_path), "PNG"):
        raise ValueError("Could not create the portrait thumbnail")
    return thumbnail_path
