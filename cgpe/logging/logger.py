import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "cgpe.log"

RESET = "\033[0m"
COLORS = {
    logging.DEBUG: "\033[36m",
    logging.INFO: "\033[32m",
    logging.WARNING: "\033[33m",
    logging.ERROR: "\033[31m",
    logging.CRITICAL: "\033[41m",
}
MAGENTA = "\033[35m"


class ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        orig_levelname = record.levelname
        orig_name = record.name
        try:
            color = COLORS.get(record.levelno, RESET)
            record.levelname = f"{color}{orig_levelname}{RESET}"
            record.name = f"{MAGENTA}{orig_name}{RESET}"
            return super().format(record)
        finally:
            record.levelname = orig_levelname
            record.name = orig_name


def _resolve_log_level(default: int = logging.INFO) -> int:
    level = os.getenv("LOG_LEVEL")
    if not level:
        return default
    return getattr(logging, level.upper(), default)


def setup_logger(
    name: str,
    level: int | None = None,
) -> logging.Logger:
    # env default → explicit arg override
    level = level if level is not None else _resolve_log_level()

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    base_fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

    # console (colored)
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(ColorFormatter(base_fmt))

    # file (plain)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(base_fmt))

    logger.addHandler(console)
    logger.addHandler(file_handler)
    logger.propagate = False

    return logger
