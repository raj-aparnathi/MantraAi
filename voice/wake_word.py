"""
voice/wake_word.py – Mantra AI v3.0
─────────────────────────────────────
Background thread that continuously listens for the wake word "Hello Mantra".
Signals the main assistant loop via a threading.Event.

Location : voice/wake_word.py
Talks to  : config.py (WAKE_WORD, STT settings), utils.py (logging)
Used by   : main.py

Threading model:
  detected    – set by detector when wake word heard; cleared by main loop
  _paused     – set by main loop to pause listening during active session
  _stop_evt   – set by main loop to permanently shut down the thread
"""

import threading
import time
import speech_recognition as sr

import config
from utils import log


class WakeWordDetector:
    """
    Runs a daemon background thread that listens for the configured wake word.
    On detection, sets `self.detected` Event so the assistant can react.

    Lifecycle:
        detector.start()       → starts background thread
        detector.detected      → wait on this for wake word
        detector.pause()       → pause listening while session is active
        detector.resume()      → resume listening after session ends
        detector.stop()        → permanently shut down thread
        detector.reset()       → clear detected flag (call after handling)
    """

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold         = config.STT_ENERGY_THRESHOLD
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold          = 0.6   # snappier for short phrases

        self.mic = sr.Microphone()

        # Events
        self.detected  = threading.Event()   # set when wake word heard
        self._paused   = threading.Event()   # set = paused (don't listen)
        self._stop_evt = threading.Event()   # set = terminate thread

        # Network backoff state (exponential, caps at 30 s)
        self._backoff_until: float = 0.0
        self._backoff_delay: float = 2.0

        self._thread = threading.Thread(
            target=self._run, name="WakeWordThread", daemon=True
        )
        log.info(f"WakeWordDetector ready. Wake word: '{config.WAKE_WORD}'")

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

    def pause(self) -> None:
        """Pause wake word listening (e.g. while a session is active)."""
        self._paused.set()

    def resume(self) -> None:
        """Resume wake word listening after a session ends."""
        self._paused.clear()

    def reset(self) -> None:
        """Clear the detected event so the detector re-arms for next wake word."""
        self.detected.clear()

    # ── Internal ───────────────────────────────────────────────────────────────

    def _run(self) -> None:
        """Continuous listen loop running in a daemon thread."""
        log.info("Wake word listener active – waiting for wake word…")

        # One-time ambient noise calibration
        try:
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
        except Exception as e:
            log.warning(f"Noise calibration failed: {e}")

        while not self._stop_evt.is_set():

            # If paused (session active), sleep and check again
            if self._paused.is_set():
                self._stop_evt.wait(timeout=0.2)
                continue

            # If we're in a network backoff window, wait and retry later
            now = time.monotonic()
            if now < self._backoff_until:
                remaining = self._backoff_until - now
                log.debug(f"Wake word STT offline – retrying in {remaining:.0f}s…")
                self._stop_evt.wait(timeout=min(remaining, 5.0))
                continue

            try:
                with self.mic as source:
                    audio = self.recognizer.listen(
                        source, timeout=3, phrase_time_limit=4
                    )

                # Skip recognition if we were paused/stopped while listening
                if self._paused.is_set() or self._stop_evt.is_set():
                    continue

                # Directly call STT - network errors are handled in except sr.RequestError
                text = self.recognizer.recognize_google(
                    audio, language=config.LANGUAGE
                ).lower().strip()
                log.debug(f"Wake listener heard: '{text}'")

                # Successful call – reset backoff
                self._backoff_delay = 2.0
                self._backoff_until = 0.0

                if config.WAKE_WORD in text:
                    log.info("Wake word detected!")
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
                # Mic in use by main STT – skip silently
                log.debug(f"Mic busy (expected during session): {e}")
            except Exception as e:
                log.error(f"Unexpected wake word error: {e}")


# ── Quick self-test ────────────────────────────────────────────────────────────
# To test:  python voice/wake_word.py
if __name__ == "__main__":
    print(f"Say '{config.WAKE_WORD}' to test…")
    wwd = WakeWordDetector()
    wwd.start()
    wwd.detected.wait()          # block until wake word heard
    print("Wake word confirmed! ✓")
    wwd.stop()
