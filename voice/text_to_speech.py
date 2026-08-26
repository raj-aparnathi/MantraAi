"""
voice/text_to_speech.py – Mantra AI v3.0
─────────────────────────────────────────
Human-sounding **English** TTS using Microsoft Edge neural voices (edge-tts)
with in-process MP3 playback via pygame. Falls back to offline pyttsx3 (SAPI5)
if the neural service is unreachable, so Mantra always has a voice.

Location : voice/text_to_speech.py
Talks to  : config.py (voice/rate/pitch/volume/pauses), utils.py (logging)
Used by   : agent/agent.py, main.py

Why edge-tts:
  pyttsx3/SAPI5 voices ("Hazel", "Zira") sound robotic. edge-tts streams the
  same neural voices used by Microsoft Edge's "Read Aloud" — natural prosody,
  free, no API key — it just needs internet (the app already needs it for STT).

English-only (v3.0):
  - `tts.english_only` strips non-Latin script (e.g. Devanagari) and emoji, so
    a stray Hindi word from an LLM can never garble the English voice.
  - Long replies are split into sentence chunks; the next chunk is synthesized
    while the current one plays, so Mantra starts talking almost immediately.

Public API (unchanged, so agent.py / main.py need no edits):
    tts = TextToSpeech()
    tts.speak(text, block=True)
    tts.stop()
"""

import os
import re
import time
import asyncio
import hashlib
import tempfile
import threading
import warnings
from pathlib import Path

import config
from utils import log

# Silence pygame's stdout banner and a noisy 3rd-party deprecation warning it
# emits on import. Both must be set BEFORE `import pygame`.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
warnings.filterwarnings("ignore", message="pkg_resources is deprecated")

try:
    import edge_tts
    _EDGE_AVAILABLE = True
except Exception as e:  # pragma: no cover
    _EDGE_AVAILABLE = False
    log.warning(f"edge-tts not importable: {e}")

try:
    import pygame
    _PYGAME_AVAILABLE = True
except Exception as e:  # pragma: no cover
    _PYGAME_AVAILABLE = False
    log.warning(f"pygame not importable: {e}")


# ── Helpers ──────────────────────────────────────────────────────────────────

# Typographic characters that TTS reads better as plain ASCII.
_ASCII_MAP = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"',
    "–": "-", "—": "-", "−": "-",
    "…": "...", " ": " ", "​": "",
}

# Latin script + ASCII punctuation live below U+0250. Everything above it
# (Devanagari, CJK, emoji, symbols) is dropped when english_only is on.
_LATIN_LIMIT = 0x250


def _to_english_text(text: str) -> str:
    """Drop every non-Latin character so only English is left to speak."""
    for src, dst in _ASCII_MAP.items():
        text = text.replace(src, dst)
    return "".join(ch for ch in text if ord(ch) < _LATIN_LIMIT)


def _clean_for_speech(text: str, english_only: bool = True) -> str:
    """Strip markdown / stray symbols so the voice doesn't read them aloud."""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)   # fenced code blocks
    text = re.sub(r"[*_`#~>|]+", " ", text)              # markdown emphasis / quotes
    if english_only:
        text = _to_english_text(text)
    text = re.sub(r"\s+", " ", text).strip()             # collapse whitespace
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)         # no gap before punctuation
    return text


def _split_chunks(text: str, max_chars: int) -> list[str]:
    """
    Split `text` into speakable chunks of at most ~max_chars, preferring
    sentence boundaries, then clause boundaries, then whole words.
    """
    if len(text) <= max_chars:
        return [text]

    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text) if s]
    chunks: list[str] = []
    buf = ""

    def flush():
        nonlocal buf
        if buf.strip():
            chunks.append(buf.strip())
        buf = ""

    for sentence in sentences:
        # A single over-long sentence: break it on clauses, then on words.
        if len(sentence) > max_chars:
            flush()
            parts = re.split(r"(?<=[,;:])\s+", sentence)
            for part in parts:
                while len(part) > max_chars:
                    cut = part.rfind(" ", 0, max_chars)
                    cut = cut if cut > 0 else max_chars
                    chunks.append(part[:cut].strip())
                    part = part[cut:].lstrip()
                if part:
                    if len(buf) + len(part) + 1 > max_chars:
                        flush()
                    buf = f"{buf} {part}".strip()
            continue

        if len(buf) + len(sentence) + 1 > max_chars:
            flush()
        buf = f"{buf} {sentence}".strip()

    flush()
    return chunks or [text]


def _fmt_signed(value, unit: str) -> str:
    """edge-tts wants signed strings like '+0%', '-10%', '+5Hz'."""
    try:
        return f"{int(round(float(value))):+d}{unit}"
    except (TypeError, ValueError):
        return f"+0{unit}"


def _safe_remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


# ── TTS Engine ─────────────────────────────────────────────────────────────────

class TextToSpeech:
    """Thread-safe neural TTS with an offline fallback. Public API unchanged."""

    _FALLBACK_RATE_WPM = 175   # pyttsx3 words-per-minute when neural is unavailable

    def __init__(self):
        self._lock = threading.Lock()
        self._stop_flag = False

        # ── Config-driven voice settings ────────────────────────────────────
        self._voice   = getattr(config, "TTS_VOICE", "en-US-AvaNeural")
        self._rate    = _fmt_signed(getattr(config, "TTS_RATE", 0), "%")
        self._pitch   = _fmt_signed(getattr(config, "TTS_PITCH", 0), "Hz")
        self._volume  = max(0.0, min(1.0, float(getattr(config, "TTS_VOLUME", 1.0))))
        self._pause_after   = float(getattr(config, "TTS_PAUSE_AFTER", 0.3))
        self._pause_between = float(getattr(config, "TTS_PAUSE_BETWEEN", 0.12))

        # ── English-only + chunked delivery ─────────────────────────────────
        self._english_only = bool(getattr(config, "TTS_ENGLISH_ONLY", True))
        self._chunking     = bool(getattr(config, "TTS_CHUNK_REPLIES", True))
        self._max_chunk    = max(60, int(getattr(config, "TTS_MAX_CHUNK_CHARS", 240)))

        # ── Phrase cache ────────────────────────────────────────────────────
        # Every edge-tts call pays ~1–1.5 s of connection setup no matter how
        # short the text is. Stock lines ("Yes? I'm listening.") are spoken over
        # and over, so we keep their MP3 on disk and replay it instantly.
        self._cache_enabled   = bool(getattr(config, "TTS_CACHE_ENABLED", True))
        self._cache_max_chars = int(getattr(config, "TTS_CACHE_MAX_CHARS", 200))
        self._cache_max_files = int(getattr(config, "TTS_CACHE_MAX_FILES", 400))
        self._cache_dir       = Path(getattr(config, "DATA_DIR", ".")) / "voice_cache"
        if self._cache_enabled:
            try:
                self._cache_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                log.warning(f"Could not create TTS cache dir: {e}")
                self._cache_enabled = False

        # Set while speech is playing – lets prewarm() stay out of the way.
        self._speaking = threading.Event()

        # ── Playback engine (pygame mixer) ──────────────────────────────────
        self._mixer_ok = False
        if _PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
                self._mixer_ok = True
            except Exception as e:
                log.warning(f"pygame mixer init failed: {e}")

        self._neural_ok = _EDGE_AVAILABLE and self._mixer_ok

        # ── Offline fallback engine (lazy init) ─────────────────────────────
        self._pyttsx3 = None

        if self._neural_ok:
            log.info(
                f"TextToSpeech (neural) ready. Voice: {self._voice} "
                f"| rate {self._rate} | pitch {self._pitch} | volume {self._volume}"
            )
        else:
            log.warning(
                "Neural TTS unavailable (edge-tts/pygame) — using offline pyttsx3 voice."
            )
            self._init_pyttsx3()

    # ── Phrase cache ─────────────────────────────────────────────────────────

    def _cached_path(self, text: str) -> Path | None:
        """Where this phrase would live in the cache, or None if not cacheable."""
        if not self._cache_enabled or len(text) > self._cache_max_chars:
            return None
        key = hashlib.sha1(
            f"{self._voice}|{self._rate}|{self._pitch}|{text}".encode("utf-8")
        ).hexdigest()[:20]
        return self._cache_dir / f"{key}.mp3"

    def _prune_cache(self) -> None:
        """Keep the cache bounded: drop the oldest files past the limit."""
        try:
            files = sorted(self._cache_dir.glob("*.mp3"), key=lambda p: p.stat().st_mtime)
            for old in files[:max(0, len(files) - self._cache_max_files)]:
                _safe_remove(str(old))
        except OSError as e:
            log.debug(f"TTS cache prune skipped: {e}")

    def _prepare_audio(self, text: str) -> tuple[str | None, bool]:
        """
        Get playable audio for `text`.

        Returns:
            (path, keep) — `keep` is True when the file lives in the cache and
            must not be deleted after playback.
        """
        cache = self._cached_path(text)
        if cache is not None and cache.exists() and cache.stat().st_size > 0:
            log.debug(f"TTS cache hit: '{text[:40]}'")
            return str(cache), True

        # Synthesize inside the cache dir when we intend to keep the result, so
        # the rename below stays on one volume.
        path = self._synth_to_file(
            text, dest_dir=str(self._cache_dir) if cache is not None else None
        )
        if path is None:
            return None, False

        if cache is not None:
            try:
                os.replace(path, cache)   # move the fresh MP3 into the cache
                self._prune_cache()
                return str(cache), True
            except OSError as e:
                log.debug(f"Could not cache phrase: {e}")

        return path, False

    def prewarm(self, phrases: list[str]) -> None:
        """
        Synthesize stock phrases into the cache in the background, so the first
        time Mantra says them there is no connection delay. Never blocks the
        caller, and yields while Mantra is actually speaking.
        """
        if not self._cache_enabled or not self._neural_ok or not phrases:
            return

        def _worker():
            warmed = 0
            for phrase in phrases:
                clean = _clean_for_speech(phrase, english_only=self._english_only)
                if not clean:
                    continue
                cache = self._cached_path(clean)
                if cache is None or (cache.exists() and cache.stat().st_size > 0):
                    continue
                # Don't compete with live speech for the network.
                while self._speaking.is_set():
                    time.sleep(0.2)
                path, keep = self._prepare_audio(clean)
                if path and not keep:
                    _safe_remove(path)
                if path:
                    warmed += 1
            if warmed:
                log.info(f"TTS cache prewarmed with {warmed} phrase(s).")

        threading.Thread(target=_worker, name="TTSPrewarm", daemon=True).start()

    # ── Neural synthesis + playback ──────────────────────────────────────────

    def _synth_to_file(self, text: str, dest_dir: str | None = None) -> str | None:
        """
        Synthesize `text` to a temp MP3 via edge-tts. Returns path, or None on failure.

        Args:
            dest_dir: Directory for the temp file. Pass the cache dir so the
                      finished file can be moved into place on the same volume
                      (os.replace cannot move across drives on Windows).
        """
        fd, path = tempfile.mkstemp(prefix="mantra_tts_", suffix=".mp3", dir=dest_dir)
        os.close(fd)

        async def _run():
            communicate = edge_tts.Communicate(
                text, self._voice, rate=self._rate, pitch=self._pitch
            )
            await communicate.save(path)

        try:
            asyncio.run(_run())
        except RuntimeError:
            # A loop is already running in this thread (rare) — use a fresh one.
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_run())
            finally:
                loop.close()
        except Exception as e:
            log.warning(f"edge-tts synthesis failed: {e}")
            _safe_remove(path)
            return None

        if not os.path.exists(path) or os.path.getsize(path) == 0:
            _safe_remove(path)
            return None
        return path

    def _play_file(self, path: str, keep: bool = False) -> None:
        """
        Play an MP3 via pygame and block until done (or stop() is called).

        Args:
            path: MP3 file to play.
            keep: True for cached files, which must survive playback.
        """
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self._volume)
            pygame.mixer.music.play()
            clock = pygame.time.Clock()
            while pygame.mixer.music.get_busy() and not self._stop_flag:
                clock.tick(20)   # ~20 fps poll; low CPU, snappy stop()
        finally:
            try:
                pygame.mixer.music.unload()   # release the file handle (Windows)
            except Exception:
                pass
            if not keep:
                _safe_remove(path)

    def _speak_neural(self, text: str) -> bool:
        """
        Speak with the neural voice. Returns False if nothing could be spoken.

        Long replies are split into chunks; while one chunk plays, the next is
        synthesized in a background thread, so playback starts after only the
        first (short) chunk is ready instead of the whole reply. Stock phrases
        come straight from the on-disk cache with no network call at all.
        """
        chunks = _split_chunks(text, self._max_chunk) if self._chunking else [text]

        current, keep = self._prepare_audio(chunks[0])
        if current is None:
            return False   # service unreachable — let the caller use the fallback

        for i in range(len(chunks)):
            # Kick off preparation of the next chunk while this one plays.
            nxt: dict = {}
            worker = None
            if i + 1 < len(chunks) and not self._stop_flag:
                worker = threading.Thread(
                    target=lambda c=chunks[i + 1]: nxt.__setitem__("r", self._prepare_audio(c)),
                    daemon=True,
                )
                worker.start()

            self._play_file(current, keep=keep)

            if worker is not None:
                worker.join()
            current, keep = nxt.get("r", (None, False))

            if self._stop_flag:
                if current and not keep:
                    _safe_remove(current)
                return True   # barge-in: we did speak, just not all of it

            if current is None:
                if i + 1 < len(chunks):
                    # Neural died mid-reply — finish the rest with the offline voice.
                    log.warning("Neural TTS failed mid-reply — finishing offline.")
                    self._speak_fallback(" ".join(chunks[i + 1:]))
                break

            if self._pause_between > 0:
                time.sleep(self._pause_between)   # brief breath between sentences

        if self._pause_after > 0 and not self._stop_flag:
            time.sleep(self._pause_after)   # natural trailing breath
        return True

    # ── Offline fallback (pyttsx3 / SAPI5) ───────────────────────────────────

    def _init_pyttsx3(self) -> None:
        if self._pyttsx3 is not None:
            return
        try:
            import pyttsx3
            eng = pyttsx3.init(driverName="sapi5")
            eng.setProperty("rate", self._FALLBACK_RATE_WPM)
            eng.setProperty("volume", self._volume)
            self._select_sapi_voice(eng, getattr(config, "TTS_VOICE_PREF", "female"))
            self._pyttsx3 = eng
        except Exception as e:
            log.error(f"pyttsx3 fallback init failed: {e}")
            self._pyttsx3 = None

    def _select_sapi_voice(self, eng, preference: str) -> None:
        voices = eng.getProperty("voices")
        female = ("zira", "hazel", "helen", "female", "woman")
        male   = ("david", "mark", "james", "male", "man")
        wanted = female if preference == "female" else male
        for v in voices:
            if any(w in v.name.lower() for w in wanted):
                eng.setProperty("voice", v.id)
                log.info(f"Fallback SAPI voice: {v.name}")
                return
        if voices:
            eng.setProperty("voice", voices[0].id)

    def _speak_fallback(self, text: str) -> None:
        self._init_pyttsx3()
        if self._pyttsx3 is None:
            return
        try:
            self._pyttsx3.say(text)
            self._pyttsx3.runAndWait()
        except Exception as e:
            log.error(f"pyttsx3 speak failed: {e}")

    # ── Public API ───────────────────────────────────────────────────────────

    def speak(self, text: str, block: bool = True) -> None:
        """
        Speak `text` aloud.

        Args:
            text:  The message to speak.
            block: If True, block until speech finishes.
                   If False, speak in a background thread.
        """
        if not text:
            return
        text = _clean_for_speech(text, english_only=self._english_only)
        if not text:
            return

        log.info(f"Speaking: '{text}'")
        print(f"\n[Mantra]: {text}\n")

        if block:
            self._speak_locked(text)
        else:
            threading.Thread(target=self._speak_locked, args=(text,), daemon=True).start()

    def _speak_locked(self, text: str) -> None:
        """Serialize speech; try neural first, fall back to offline voice."""
        with self._lock:
            self._stop_flag = False
            self._speaking.set()
            try:
                spoke = False
                if self._neural_ok:
                    spoke = self._speak_neural(text)
                    if not spoke:
                        log.warning("Neural TTS failed for this line — using offline voice.")
                if not spoke:
                    self._speak_fallback(text)
            finally:
                self._speaking.clear()

    def stop(self) -> None:
        """Interrupt current speech (barge-in)."""
        self._stop_flag = True
        if self._mixer_ok:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        if self._pyttsx3 is not None:
            try:
                self._pyttsx3.stop()
            except Exception:
                pass


# ── Quick self-test ────────────────────────────────────────────────────────────
# To test:  python voice/text_to_speech.py
if __name__ == "__main__":
    tts = TextToSpeech()
    tts.speak(
        "Hi! I'm Mantra, your personal assistant. I speak English only now, "
        "and this neural voice should sound a lot closer to a real person."
    )
    tts.speak(
        "Ask me anything at all. I can open your apps, control your PC, "
        "look things up, and answer your questions. I'm always here to help."
    )
