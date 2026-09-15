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

# Load .env file if it exists (API keys, secrets)
# This MUST run before any os.getenv() calls below.
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass  # python-dotenv not installed — keys must be in env or config.json

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
# v3.0: primary engine is edge-tts (neural, human-sounding). rate/pitch are
# edge-tts relative offsets: rate is a percent (e.g. 0 → "+0%", -10 → "-10%"),
# pitch is in Hz (e.g. 0 → "+0Hz"). volume (0.0–1.0) is applied at playback.
TTS_ENGINE       : str   = _cfg["tts"].get("engine", "edge-tts")
TTS_RATE         : int   = _cfg["tts"].get("rate", 0)
TTS_PITCH        : int   = int(_cfg["tts"].get("pitch", 0))
TTS_VOLUME       : float = _cfg["tts"].get("volume", 1.0)
TTS_VOICE        : str   = _cfg["tts"].get("voice", "en-US-AvaNeural")      # neural voice id
TTS_VOICE_PREF   : str   = _cfg["tts"].get("voice_preference", "female")   # fallback SAPI pick
TTS_STYLE        : str   = _cfg["tts"].get("style", "friendly")            # reserved (Azure only)
TTS_PAUSE_AFTER  : float = float(_cfg["tts"].get("pause_after_response", 0.3))
TTS_PAUSE_BETWEEN: float = float(_cfg["tts"].get("pause_between_sentences", 0.12))

TTS_ENGLISH_ONLY : bool  = bool(_cfg["tts"].get("english_only", True))
"""Strip non-English (e.g. Devanagari) script and emoji before speaking."""

TTS_CHUNK_REPLIES: bool  = bool(_cfg["tts"].get("chunk_long_replies", True))
"""Speak long replies sentence-by-sentence, synthesizing the next chunk while
the current one plays. Cuts the wait before Mantra starts talking."""

TTS_MAX_CHUNK_CHARS: int = int(_cfg["tts"].get("max_chunk_chars", 240))
"""Soft upper bound on a single spoken chunk (characters)."""

TTS_CACHE_ENABLED  : bool = bool(_cfg["tts"].get("cache_enabled", True))
"""Cache synthesized MP3s for repeated stock phrases in data/voice_cache/.
Each edge-tts call costs ~1–1.5 s of connection setup, so replaying a cached
greeting is effectively instant."""

TTS_CACHE_MAX_CHARS: int = int(_cfg["tts"].get("cache_max_chars", 200))
"""Only cache phrases up to this length (LLM replies are unique — don't cache)."""

TTS_CACHE_MAX_FILES: int = int(_cfg["tts"].get("cache_max_files", 400))
"""Cache size cap. Oldest files are pruned first."""

# ── STT ────────────────────────────────────────────────────────────────
# Recognition locale: 'en-IN' is Google's Indian-English model (best accuracy
# for Indian-accented English). Use 'en-US' or 'en-GB' if you prefer those.
STT_LANGUAGE          : str   = _cfg["stt"].get("language", _cfg["assistant"]["language"])
STT_ENERGY_THRESHOLD  : int   = _cfg["stt"]["energy_threshold"]   # lower = more sensitive
STT_PAUSE_THRESHOLD   : float = _cfg["stt"]["pause_threshold"]    # silence that ends a phrase
STT_TIMEOUT           : int   = _cfg["stt"]["timeout"]             # s to wait for speech start
STT_PHRASE_TIME_LIMIT : int   = _cfg["stt"]["phrase_time_limit"]   # max phrase length
STT_SAMPLE_RATE       : int   = _cfg["stt"].get("sample_rate", 16000)        # 16 kHz mono
STT_NORMALIZE_AUDIO   : bool  = _cfg["stt"].get("normalize_audio", True)     # volume normalization
STT_CALIBRATION_DUR   : float = _cfg["stt"].get("calibration_duration", 1.0) # ambient noise window

STT_NON_SPEAKING      : float = float(_cfg["stt"].get("non_speaking_duration", 0.3))
"""Silence kept around a phrase. Must be <= pause_threshold. Smaller = snappier."""

STT_PHRASE_THRESHOLD  : float = float(_cfg["stt"].get("phrase_threshold", 0.2))
"""Minimum seconds of speech before it counts as a phrase (catches 'stop', 'yes')."""

# ── Wake Word ─────────────────────────────────────────────────────────────────
_wake = _cfg.get("wake", {})

WAKE_LISTEN_TIMEOUT   : float = float(_wake.get("listen_timeout", 1.5))
"""Seconds the wake listener waits for speech before looping (keeps pause snappy)."""

WAKE_PHRASE_LIMIT     : float = float(_wake.get("phrase_time_limit", 3.0))
"""Max seconds recorded per wake-word attempt. The wake phrase is short."""

WAKE_MIN_SPEECH_SECS  : float = float(_wake.get("min_speech_seconds", 0.35))
"""Clips shorter than this are dropped locally instead of sent to Google STT."""

WAKE_FUZZY_THRESHOLD  : float = float(_wake.get("fuzzy_threshold", 0.75))
"""Similarity (0–1) needed to accept a misheard wake word, e.g. 'montra'."""

WAKE_ON_NAME_ONLY     : bool  = bool(_wake.get("wake_on_name_only", True))
"""Also wake on just the assistant name ('Mantra'), not only 'hello mantra'."""

WAKE_EXTRA_VARIANTS   : list  = list(_wake.get("extra_variants", []))
"""Extra exact phrases that should also trigger the wake word."""

# ── API Keys ───────────────────────────────────────────────────────────────────
OPENWEATHER_API_KEY : str = os.getenv("OPENWEATHER_API_KEY", _cfg["api_keys"].get("openweathermap", ""))
NEWSAPI_KEY         : str = os.getenv("NEWSAPI_KEY", _cfg["api_keys"].get("newsapi", ""))
GEMINI_API_KEY      : str = os.getenv("GEMINI_API_KEY", _cfg["api_keys"].get("gemini", ""))
OPENAI_API_KEY      : str = os.getenv("OPENAI_API_KEY", _cfg["api_keys"].get("openai", ""))

# ── Weather ───────────────────────────────────────────────────────────────────
DEFAULT_CITY  : str = _cfg["weather"]["default_city"]
WEATHER_UNITS : str = _cfg["weather"]["units"]

# ── App Paths ──────────────────────────────────────────────────────────────────
APP_PATHS : dict = _cfg["apps"]

# ── Music ──────────────────────────────────────────────────────────────────────
MUSIC_DIR : str = _cfg.get("music", {}).get("folder", r"C:\Users\91816\Music")

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

PERSONA_LANGUAGE    : str = _persona.get("default_language", "english")
"""Response language. Mantra v3.0 is English-only."""

PERSONA_MAX_HISTORY : int = int(_persona.get("max_history_turns", 10))
"""Max conversation turns kept in memory for Gemini context."""

PERSONA_SYSTEM_PROMPT : str = _persona.get(
    "system_prompt",
    (
        f"You are {_cfg['assistant']['name']}, a helpful English voice assistant. "
        "Always reply in English only, even if the user speaks another language. "
        "Keep replies short, natural, and TTS-friendly. "
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

AI_PROVIDER : str = _v3.get("ai_provider", "auto")
"""Which AI provider to use: 'gemini', 'openai', or 'auto' (try all in order)."""

OPENAI_MODEL : str = _v3.get("openai_model", "gpt-4o-mini")
"""Which OpenAI model to use (e.g. 'gpt-4o-mini', 'gpt-4o', 'gpt-3.5-turbo')."""

# ── v3.0: Memory ──────────────────────────────────────────────────────────────
MEMORY_FILE : str = _v3.get("memory_file", str(DATA_DIR / "memory.json"))
"""Path to the JSON file used by memory/memory.py to store persistent facts."""

# ── v3.0: Updater ─────────────────────────────────────────────────────────────
UPDATER_REPO : str = _v3.get(
    "updater_repo",
    "https://api.github.com/repos/YourUsername/MantraAI"
)
"""GitHub API repo URL for checking updates (set to your actual repo)."""
