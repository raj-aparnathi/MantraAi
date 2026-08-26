"""
voice/wake_word.py – Mantra AI v3.0
─────────────────────────────────────
Background thread that continuously listens for the English wake word
"Hello Mantra". Signals the main assistant loop via a threading.Event.

Location : voice/wake_word.py
Talks to  : config.py (WAKE_* / STT settings), utils.py (logging)
Used by   : main.py

v3.0 Efficiency Improvements:
  - Local pre-gate: clips that are too short or too quiet are discarded here
    instead of being uploaded to Google STT. Most background noise never
    leaves the machine, so detection is faster and uses far less bandwidth.
  - Persistent mic stream while armed, released the moment we pause, so the
    session never fights the wake listener for the microphone.
  - Fuzzy English matching: Google often hears "hello montra" / "hi mantar".
    Those now count as a wake word instead of being silently dropped.
  - Short listen windows (1.5 s timeout / 3 s cap) — the wake phrase is short,
    so there is no reason to record for four seconds.
  - Auto-pauses itself on detection and releases the mic before main.py starts
    the session, which removes the old "mic busy" race entirely.

Threading model:
  detected    – set by detector when wake word heard; cleared by main loop
  _paused     – set on detection or by main loop; detector releases the mic
  _idle       – set by the detector once the mic really is released
  _stop_evt   – set by main loop to permanently shut down the thread
"""

import re
import time
import audioop
import difflib
import threading
from contextlib import ExitStack

import speech_recognition as sr

import config
from utils import log


# ── Wake phrase matching ───────────────────────────────────────────────────────

_WORD_RE = re.compile(r"[a-z]+")


def _words(text: str) -> list[str]:
    """Lowercase word tokens only — drops punctuation and digits."""
    return _WORD_RE.findall(text.lower())


def _similar(a: str, b: str) -> float:
    """Similarity ratio 0.0–1.0 between two strings."""
    return difflib.SequenceMatcher(None, a, b).ratio()


class WakeWordDetector:
    """
    Runs a daemon background thread that listens for the configured wake word.
    On detection, sets `self.detected` and releases the microphone.

    Lifecycle:
        detector.start()          → starts background thread
        detector.detected         → wait on this for wake word
        detector.pause(wait=1.0)  → pause listening, wait for mic release
        detector.resume()         → resume listening after session ends
        detector.stop()           → permanently shut down thread
        detector.reset()          → clear detected flag (call after handling)
    """

    def __init__(self, energy_threshold: float | None = None):
        """
        Args:
            energy_threshold: Pass the value from an already-calibrated
                SpeechToText to skip a second ambient calibration on startup.
        """
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold         = (
            energy_threshold if energy_threshold else config.STT_ENERGY_THRESHOLD
        )
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold          = 0.5   # snappier for short phrases
        self.recognizer.non_speaking_duration    = 0.3

        self.mic = sr.Microphone(sample_rate=config.STT_SAMPLE_RATE)
        self._pre_calibrated = energy_threshold is not None

        # Events
        self.detected  = threading.Event()   # set when wake word heard
        self._paused   = threading.Event()   # set = paused (don't listen)
        self._idle     = threading.Event()   # set = mic released, safe to use
        self._stop_evt = threading.Event()   # set = terminate thread

        # Persistent stream state
        self._stack: ExitStack | None = None
        self._source = None

        # Network backoff state (exponential, caps at 30 s)
        self._backoff_until: float = 0.0
        self._backoff_delay: float = 2.0

        # ── Accepted wake phrases ──────────────────────────────────────────────
        self._wake_phrase = config.WAKE_WORD.lower().strip()
        self._wake_words  = _words(self._wake_phrase)
        self._name        = config.ASSISTANT_NAME.lower().strip()
        self._variants    = [v.lower().strip() for v in config.WAKE_EXTRA_VARIANTS]
        self._fuzzy       = config.WAKE_FUZZY_THRESHOLD
        self._name_only   = config.WAKE_ON_NAME_ONLY

        self._thread = threading.Thread(
            target=self._run, name="WakeWordThread", daemon=True
        )
        log.info(
            f"WakeWordDetector ready. Wake word: '{config.WAKE_WORD}' "
            f"(name-only: {self._name_only}, fuzzy: {self._fuzzy})"
        )

    # ── Control ────────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the background listening thread."""
        self._thread.start()
        log.info("Wake word detector started.")

    def stop(self) -> None:
        """Permanently stop the background thread."""
        self._stop_evt.set()
        self._paused.clear()   # unblock any wait so thread can exit
        log.info("Wake word detector stopped.")

    def pause(self, wait: float = 0.0) -> None:
        """
        Pause wake word listening (e.g. while a session is active).

        Args:
            wait: Seconds to wait for the detector to actually release the
                  microphone. Pass a small value (~2 s) before opening the
                  session mic so the two never collide.
        """
        self._paused.set()
        if wait > 0 and self._thread.is_alive():
            if not self._idle.wait(timeout=wait):
                log.debug("Wake detector did not confirm mic release in time.")

    def resume(self) -> None:
        """Resume wake word listening after a session ends."""
        self._idle.clear()
        self._paused.clear()

    def reset(self) -> None:
        """Clear the detected event so the detector re-arms for next wake word."""
        self.detected.clear()

    # ── Mic stream helpers ─────────────────────────────────────────────────────

    def _open_mic(self) -> bool:
        if self._source is not None:
            return True
        try:
            stack = ExitStack()
            self._source = stack.enter_context(self.mic)
            self._stack = stack
            if not self._pre_calibrated:
                self.recognizer.adjust_for_ambient_noise(self._source, duration=0.5)
                self._pre_calibrated = True
            return True
        except Exception as e:
            log.debug(f"Wake mic unavailable (will retry): {e}")
            self._stack, self._source = None, None
            return False

    def _close_mic(self) -> None:
        if self._stack is not None:
            try:
                self._stack.close()
            except Exception as e:
                log.debug(f"Error closing wake mic: {e}")
        self._stack, self._source = None, None

    # ── Local pre-gate ─────────────────────────────────────────────────────────

    def _worth_recognizing(self, audio: sr.AudioData) -> bool:
        """
        Decide locally whether a clip could plausibly be the wake word.
        Filters out taps, clicks, and distant chatter before spending a
        network round-trip on Google STT.
        """
        try:
            raw = audio.get_raw_data()
            seconds = len(raw) / float(audio.sample_rate * audio.sample_width)
            if seconds < config.WAKE_MIN_SPEECH_SECS:
                log.debug(f"Wake pre-gate: clip too short ({seconds:.2f}s).")
                return False

            rms = audioop.rms(raw, audio.sample_width)
            floor = max(40, int(self.recognizer.energy_threshold * 0.6))
            if rms < floor:
                log.debug(f"Wake pre-gate: too quiet (rms {rms} < {floor}).")
                return False
            return True
        except Exception as e:
            log.debug(f"Wake pre-gate skipped: {e}")
            return True   # if in doubt, let STT decide

    # ── Wake phrase matching ───────────────────────────────────────────────────

    def _matches_wake(self, text: str) -> bool:
        """True if `text` is the wake word, allowing for common mishearings."""
        text = text.lower().strip()
        if self._wake_phrase in text:
            return True
        if any(v and v in text for v in self._variants):
            return True

        tokens = _words(text)
        if not tokens:
            return False

        # Fuzzy match the phrase word-by-word against every same-length window,
        # e.g. heard "hello montra" vs wanted "hello mantra". Comparing each
        # word separately stops a matching "hello" from carrying a bad name
        # through (so "hello mantle" is correctly rejected).
        span = len(self._wake_words)
        if span > 1:
            for i in range(len(tokens) - span + 1):
                window = tokens[i:i + span]
                if all(
                    _similar(heard, wanted) >= self._fuzzy
                    for heard, wanted in zip(window, self._wake_words)
                ):
                    log.debug(f"Fuzzy wake match: '{' '.join(window)}'")
                    return True

        # Name-only wake: any single word close enough to "mantra".
        if self._name_only:
            for token in tokens:
                if _similar(token, self._name) >= self._fuzzy:
                    log.debug(f"Name-only wake match: '{token}'")
                    return True

        return False

    # ── Internal ───────────────────────────────────────────────────────────────

    def _run(self) -> None:
        """Continuous listen loop running in a daemon thread."""
        log.info("Wake word listener active – waiting for wake word…")

        while not self._stop_evt.is_set():

            # If paused (session active), release the mic and idle.
            if self._paused.is_set():
                self._close_mic()
                self._idle.set()
                self._stop_evt.wait(timeout=0.2)
                continue

            # If we're in a network backoff window, wait and retry later
            now = time.monotonic()
            if now < self._backoff_until:
                remaining = self._backoff_until - now
                log.debug(f"Wake word STT offline – retrying in {remaining:.0f}s…")
                self._close_mic()
                self._stop_evt.wait(timeout=min(remaining, 5.0))
                continue

            if not self._open_mic():
                self._stop_evt.wait(timeout=0.5)
                continue

            try:
                audio = self.recognizer.listen(
                    self._source,
                    timeout           = config.WAKE_LISTEN_TIMEOUT,
                    phrase_time_limit = config.WAKE_PHRASE_LIMIT,
                )

                # Skip recognition if we were paused/stopped while listening
                if self._paused.is_set() or self._stop_evt.is_set():
                    continue

                # Cheap local filter — most noise stops here, no network used.
                if not self._worth_recognizing(audio):
                    continue

                text = self.recognizer.recognize_google(
                    audio, language=config.STT_LANGUAGE
                ).lower().strip()
                log.debug(f"Wake listener heard: '{text}'")

                # Successful call – reset backoff
                self._backoff_delay = 2.0
                self._backoff_until = 0.0

                if self._matches_wake(text):
                    log.info(f"Wake word detected in: '{text}'")
                    # Pause ourselves and hand the mic over cleanly.
                    self._paused.set()
                    self._close_mic()
                    self._idle.set()
                    self.detected.set()

            except sr.WaitTimeoutError:
                pass   # silence – keep looping
            except sr.UnknownValueError:
                pass   # unintelligible – keep looping
            except sr.RequestError as e:
                # Network/DNS failure (e.g. getaddrinfo failed) – back off exponentially
                log.warning(
                    f"Wake word STT unavailable (network error): {e}. "
                    f"Retrying in {self._backoff_delay:.0f}s…"
                )
                self._backoff_until = time.monotonic() + self._backoff_delay
                self._backoff_delay = min(self._backoff_delay * 2, 30.0)
            except OSError as e:
                # Mic taken by the session – drop our stream and retry later
                log.debug(f"Wake mic error (expected during session): {e}")
                self._close_mic()
                self._stop_evt.wait(timeout=0.3)
            except Exception as e:
                log.error(f"Unexpected wake word error: {e}")
                self._close_mic()

        self._close_mic()
        self._idle.set()


# ── Quick self-test ────────────────────────────────────────────────────────────
# To test:  python voice/wake_word.py
if __name__ == "__main__":
    print(f"Say '{config.WAKE_WORD}' to test…")
    wwd = WakeWordDetector()
    wwd.start()
    wwd.detected.wait()          # block until wake word heard
    print("Wake word confirmed! ✓")
    wwd.stop()
