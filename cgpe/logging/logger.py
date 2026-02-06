# cgpe/logging/logger.py

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "cgpe.log"


def setup_logger(
    name: str = "cgpe",
    level: int = logging.INFO,
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger  # prevent duplicate handlers

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    # ---- console ----
    console = logging.StreamHandler()
    console.setFormatter(formatter)

    # ---- file (rotating) ----
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5_000_000,  # 5MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(file_handler)

    logger.propagate = False

    return logger
