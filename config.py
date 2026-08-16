"""
config.py – Mantra AI v2.0
Loads and exposes all configuration from data/config.json.

v2.0 additions:
  - SCREENSHOTS_DIR, RECORDINGS_DIR  – save paths for screen utilities
  - VOLUME_STEP, BRIGHTNESS_STEP     – per-command increment values
  - BOOKMARKS                         – named browser bookmark URLs
  - APP_PATHS extended (Word, Excel, PowerPoint, Teams, Task Manager)
"""

import json
import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent
DATA_DIR    = BASE_DIR / "data"
CONFIG_FILE = DATA_DIR / "config.json"
NOTES_FILE  = DATA_DIR / "notes.json"
ASSETS_DIR  = BASE_DIR / "assets"
LOG_FILE    = BASE_DIR / "mantra.log"


def _load_config() -> dict:
    """Load config.json, return raw dict."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"config.json not found at {CONFIG_FILE}. "
            "Please ensure the data/ directory is present."
        )
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


_cfg = _load_config()

# ── Assistant ──────────────────────────────────────────────────────────────────
ASSISTANT_NAME : str = _cfg["assistant"]["name"]
WAKE_WORD      : str = _cfg["assistant"]["wake_word"]        # "hello mantra"
LANGUAGE       : str = _cfg["assistant"]["language"]         # "en-US"
VERSION        : str = _cfg["assistant"]["version"]          # "2.0"
TIMEZONE       : str = _cfg["assistant"].get("timezone", "Asia/Kolkata")  # IST default

# ── TTS ───────────────────────────────────────────────────────────────────────
TTS_RATE       : int   = _cfg["tts"]["rate"]
TTS_VOLUME     : float = _cfg["tts"]["volume"]
TTS_VOICE_PREF : str   = _cfg["tts"]["voice_preference"]    # "female"

# ── STT ────────────────────────────────────────────────────────────────
STT_ENERGY_THRESHOLD  : int   = _cfg["stt"]["energy_threshold"]   # 200 (lower = more sensitive)
STT_PAUSE_THRESHOLD   : float = _cfg["stt"]["pause_threshold"]    # 1.2 s (longer pauses allowed)
STT_TIMEOUT           : int   = _cfg["stt"]["timeout"]             # 10 s to start speaking
STT_PHRASE_TIME_LIMIT : int   = _cfg["stt"]["phrase_time_limit"]   # 20 s max phrase length
STT_SAMPLE_RATE       : int   = _cfg["stt"].get("sample_rate", 16000)        # 16 kHz mono
STT_NORMALIZE_AUDIO   : bool  = _cfg["stt"].get("normalize_audio", True)     # volume normalization
STT_CALIBRATION_DUR   : float = _cfg["stt"].get("calibration_duration", 2.0) # ambient noise window

# ── API Keys ───────────────────────────────────────────────────────────────────
OPENWEATHER_API_KEY : str = os.getenv("OPENWEATHER_API_KEY", _cfg["api_keys"].get("openweathermap", ""))
NEWSAPI_KEY         : str = os.getenv("NEWSAPI_KEY", _cfg["api_keys"].get("newsapi", ""))
GEMINI_API_KEY      : str = os.getenv("GEMINI_API_KEY", _cfg["api_keys"].get("gemini", ""))

# ── Weather ───────────────────────────────────────────────────────────────────
DEFAULT_CITY  : str = _cfg["weather"]["default_city"]
WEATHER_UNITS : str = _cfg["weather"]["units"]

# ── App Paths ──────────────────────────────────────────────────────────────────
APP_PATHS : dict = _cfg["apps"]

# ── Music ──────────────────────────────────────────────────────────────────────
MUSIC_DIR : str = _cfg.get("music", {}).get("folder", r"D:\R09\Music")

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL      : str = _cfg["logging"]["level"]
LOG_MAX_BYTES  : int = _cfg["logging"]["max_bytes"]
LOG_BACKUP_CNT : int = _cfg["logging"]["backup_count"]

# ── v2.0: Screen Utilities ────────────────────────────────────────────────────
_v2 = _cfg.get("v2", {})

SCREENSHOTS_DIR : str = _v2.get("screenshots_dir", "")
"""Directory to save screenshots. Empty = ~/Pictures/MantraScreenshots."""

RECORDINGS_DIR  : str = _v2.get("recordings_dir", "")
"""Directory to save screen recordings. Empty = ~/Videos/MantraRecordings."""

# ── v2.0: Control Steps ───────────────────────────────────────────────────────
VOLUME_STEP     : float = float(_v2.get("volume_step", 0.1))
"""Volume change per command (0.0–1.0 scale). Default: 0.1 = 10%."""

BRIGHTNESS_STEP : int = int(_v2.get("brightness_step", 10))
"""Brightness change per command (0–100 scale). Default: 10%."""

# ── v2.0: Browser Bookmarks ────────────────────────────────────────────────────
BOOKMARKS : dict = _v2.get("bookmarks", {})
"""Named bookmark URLs loaded from config.json v2.bookmarks."""

# ── Persona / System Prompt ────────────────────────────────────────────────────
_persona = _cfg.get("persona", {})

PERSONA_LANGUAGE    : str = _persona.get("default_language", "hinglish")
"""Default response language: 'hinglish', 'english', 'hindi'."""

PERSONA_MAX_HISTORY : int = int(_persona.get("max_history_turns", 10))
"""Max conversation turns kept in memory for Gemini context."""

PERSONA_SYSTEM_PROMPT : str = _persona.get(
    "system_prompt",
    (
        f"You are {_cfg['assistant']['name']}, a helpful Hindi/Hinglish voice assistant. "
        "Speak in Hinglish by default. Keep replies short and TTS-friendly. "
        "No bullet points, no markdown, no special characters."
    )
)
"""Full system prompt sent to Gemini API as personality context."""

# ── v3.0: Local LLM (Ollama) ──────────────────────────────────────────────────
_v3 = _cfg.get("v3", {})

LOCAL_LLM_URL   : str = _v3.get("local_llm_url", "http://localhost:11434")
"""Ollama server URL. Default is localhost. Change if Ollama runs on another machine."""

LOCAL_LLM_MODEL : str = _v3.get("local_llm_model", "llama3")
"""Which Ollama model to use as the local LLM fallback (e.g. 'llama3', 'mistral', 'phi3')."""

# ── v3.0: Memory ──────────────────────────────────────────────────────────────
MEMORY_FILE : str = _v3.get("memory_file", str(DATA_DIR / "memory.json"))
"""Path to the JSON file used by memory/memory.py to store persistent facts."""

# ── v3.0: Updater ─────────────────────────────────────────────────────────────
UPDATER_REPO : str = _v3.get(
    "updater_repo",
    "https://api.github.com/repos/YourUsername/MantraAI"
)
"""GitHub API repo URL for checking updates (set to your actual repo)."""
