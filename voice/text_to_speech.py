"""
voice/text_to_speech.py – Mantra AI v3.0
─────────────────────────────────────────
Non-blocking TTS using pyttsx3 with Windows SAPI5 voices.

Location : voice/text_to_speech.py
Talks to  : config.py (settings), utils.py (logging)
Used by   : agent/agent.py, main.py
"""

import threading
import pyttsx3

import config
from utils import log


class TextToSpeech:
    """Thread-safe TTS engine wrapper."""

    def __init__(self):
        self._engine = pyttsx3.init(driverName="sapi5")
        self._lock   = threading.Lock()
        self._apply_settings()
        log.info("TextToSpeech initialised.")

    # ── Private ────────────────────────────────────────────────────────────────

    def _apply_settings(self) -> None:
        """Apply rate, volume, and voice preference from config."""
        self._engine.setProperty("rate",   config.TTS_RATE)
        self._engine.setProperty("volume", config.TTS_VOLUME)
        self._set_voice(config.TTS_VOICE_PREF)

    def _set_voice(self, preference: str) -> None:
        """
        Select voice matching the preference ('female' or 'male').
        Falls back to the first available voice if no match.
        """
        voices = self._engine.getProperty("voices")
        selected = None

        for voice in voices:
            name = voice.name.lower()
            if preference == "female" and any(
                f in name for f in ("zira", "hazel", "helen", "female", "woman")
            ):
                selected = voice
                break
            elif preference == "male" and any(
                m in name for m in ("david", "mark", "james", "male", "man")
            ):
                selected = voice
                break

        if selected:
            self._engine.setProperty("voice", selected.id)
            log.info(f"TTS voice set to: {selected.name}")
        elif voices:
            self._engine.setProperty("voice", voices[0].id)
            log.warning(f"Preferred '{preference}' voice not found. Using: {voices[0].name}")

    # ── Public ─────────────────────────────────────────────────────────────────

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
        log.info(f"Speaking: '{text}'")
        print(f"\n[Mantra]: {text}\n")

        if block:
            with self._lock:
                self._engine.say(text)
                self._engine.runAndWait()
        else:
            t = threading.Thread(target=self._speak_blocking, args=(text,), daemon=True)
            t.start()

    def _speak_blocking(self, text: str) -> None:
        with self._lock:
            self._engine.say(text)
            self._engine.runAndWait()

    def stop(self) -> None:
        """Interrupt current speech."""
        self._engine.stop()


# ── Quick self-test ────────────────────────────────────────────────────────────
# To test:  python voice/text_to_speech.py
if __name__ == "__main__":
    tts = TextToSpeech()
    tts.speak("Hello! I am Mantra version 3. I have been upgraded to a clean architecture!")
