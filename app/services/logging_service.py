from __future__ import annotations
import logging
from logging.handlers import RotatingFileHandler
from ..paths import user_data_dir


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("campaign_manager")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    log_path = user_data_dir() / "logs" / "application.log"
    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    return logger


def shutdown_logging() -> None:
    root = logging.getLogger("campaign_manager")
    for handler in list(root.handlers):
        handler.close()
        root.removeHandler(handler)
