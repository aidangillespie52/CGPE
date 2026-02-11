import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "cgpe.log"


# ---- ANSI color codes ----
RESET = "\033[0m"
COLORS = {
    logging.DEBUG: "\033[36m",     # Cyan
    logging.INFO: "\033[32m",      # Green
    logging.WARNING: "\033[33m",   # Yellow
    logging.ERROR: "\033[31m",     # Red
    logging.CRITICAL: "\033[41m",  # Red background
}


class ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        color = COLORS.get(record.levelno, RESET)
        record.levelname = f"{color}{record.levelname}{RESET}"
        record.name = f"\033[35m{record.name}{RESET}"  # Magenta logger name
        return super().format(record)


def setup_logger(
    name: str = "cgpe",
    level: int = logging.INFO,
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger  # prevent duplicate handlers

    base_fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

    # ---- console (colored) ----
    console_formatter = ColorFormatter(base_fmt)
    console = logging.StreamHandler()
    console.setFormatter(console_formatter)

    # ---- file (plain, rotating) ----
    file_formatter = logging.Formatter(base_fmt)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(file_formatter)

    logger.addHandler(console)
    logger.addHandler(file_handler)
    logger.propagate = False

    return logger
