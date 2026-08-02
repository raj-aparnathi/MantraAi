"""
utils.py – Mantra AI v1.0
Shared helpers: logging setup, date/time, command parsing.
"""

import logging
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler
from zoneinfo import ZoneInfo

import config


# ── Logger Setup ───────────────────────────────────────────────────────────────

def setup_logger(name: str = "MantraAI") -> logging.Logger:
    """
    Create and return a named logger with:
      - Console handler (INFO+)
      - Rotating file handler (DEBUG+) → mantra.log
    """
    logger = logging.getLogger(name)
    if logger.handlers:          # avoid duplicate handlers on re-import
        return logger

    logger.setLevel(logging.DEBUG)

    # Console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)s – %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_fmt)

    # Rotating file
    file_handler = RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_CNT,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_fmt)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger


# Shared module-level logger
log = setup_logger()


# ── Date / Time ────────────────────────────────────────────────────────────────

def _now() -> datetime:
    """
    Return the current datetime in the configured timezone (default: Asia/Kolkata / IST).
    Uses Python's built-in zoneinfo module (Python 3.9+).
    """
    tz = ZoneInfo(config.TIMEZONE)
    return datetime.now(tz)


def get_time() -> str:
    """Return current time in IST as a friendly string, e.g. '9:45 PM'."""
    raw = _now().strftime("%I:%M %p")
    return raw.lstrip("0")   # remove leading zero


def get_date() -> str:
    """Return current date in IST as a friendly string, e.g. 'Friday, August 1, 2026'."""
    now = _now()
    day = now.strftime("%d").lstrip("0")   # no leading zero
    return now.strftime(f"%A, %B {day}, %Y")


def get_greeting_period() -> str:
    """Return 'morning', 'afternoon', or 'evening' based on IST hour."""
    hour = _now().hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    else:
        return "evening"


# ── Command Parsing ────────────────────────────────────────────────────────────

def normalize(text: str) -> str:
    """
    Lowercase, strip leading/trailing whitespace, and remove
    punctuation that might confuse keyword matching.
    """
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)   # remove punctuation
    return text


def contains_any(text: str, keywords: list[str]) -> bool:
    """Return True if the normalized text contains any of the keywords."""
    t = normalize(text)
    return any(kw in t for kw in keywords)


def extract_after(text: str, keyword: str) -> str:
    """
    Extract the substring that follows `keyword` in `text`.
    E.g. extract_after("search python on google", "search") → "python on google"
    """
    t = normalize(text)
    idx = t.find(keyword)
    if idx == -1:
        return ""
    return t[idx + len(keyword):].strip()


# ── Quick self-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Time    :", get_time())
    print("Date    :", get_date())
    print("Period  :", get_greeting_period())
    print("Normalize:", normalize("Hello, Mantra! How are YOU?"))
    print("Contains:", contains_any("open chrome browser", ["chrome", "firefox"]))
    print("Extract :", extract_after("search python tutorials on google", "search"))
