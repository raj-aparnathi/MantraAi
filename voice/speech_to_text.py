"""
voice/speech_to_text.py – Mantra AI v3.0
──────────────────────────────────────────
Microphone capture and **English** speech recognition using Google's free STT.

Location : voice/speech_to_text.py
Talks to  : config.py (settings), utils.py (logging)
Used by   : agent/agent.py

v2.0 Audio Improvements:
  - 16 kHz sample rate, mono channel (better STT accuracy, less data)
  - Increased audio gain (input sensitivity boost)
  - Dynamic energy threshold with aggressive adjustment
  - Audio volume normalization before sending to Google STT
  - Noise suppression via ambient calibration

v3.0 Latency / Efficiency Improvements:
  - English-only recognition locale (stt.language, default 'en-IN' — Google's
    Indian-English model, the most accurate for Indian-accented English)
  - Persistent mic stream across a session: open_stream() / close_stream()
    avoid re-opening the PyAudio device on every single command (~0.3 s each)
  - Stale audio is drained before each listen, so Mantra never transcribes
    its own TTS output that was buffered while it was speaking
  - non_speaking_duration decoupled from pause_threshold, so a finished
    sentence is submitted to STT much sooner
  - phrase_threshold lowered so one-word commands ("stop", "yes") register
"""

import audioop
from contextlib import ExitStack
import sys
import pyaudiowpatch

sys.modules["pyaudio"] = pyaudiowpatch
import speech_recognition as sr

import config
from utils import log


# ── Audio Normalization ────────────────────────────────────────────────────────

def _normalize_audio(audio: sr.AudioData, target_rms: int = 3000) -> sr.AudioData:
    """
    Normalize the volume of an AudioData sample to a target RMS level.
    Boosts quiet audio and prevents clipping on loud audio.

    Args:
        audio      : The captured AudioData object.
        target_rms : Target RMS amplitude (1–32767). 3000 is a safe loud level.

    Returns:
        A new AudioData with normalized volume.
    """
    try:
        raw        = audio.get_raw_data()
        sample_w   = audio.sample_width          # bytes per sample (usually 2)
        sample_r   = audio.sample_rate

        # Compute current RMS
        current_rms = audioop.rms(raw, sample_w)
        if current_rms == 0:
            return audio   # silence – nothing to normalize

        # Calculate gain factor, cap at 6x to avoid distortion
        gain = min(target_rms / current_rms, 6.0)

        # Apply gain
        boosted = audioop.mul(raw, sample_w, gain)

        log.debug(f"Audio normalized: RMS {current_rms} → {int(current_rms * gain)} (gain {gain:.2f}x)")
        return sr.AudioData(boosted, sample_r, sample_w)

    except Exception as e:
        log.warning(f"Audio normalization failed, using original: {e}")
        return audio


class SpeechToText:
    """
    v3.0 SpeechToText — English-only recognition with a reusable mic stream.

    Key settings (all tunable via config.json → stt section):
      - language              : 'en-IN' (English). Use 'en-US' / 'en-GB' if preferred.
      - sample_rate           : 16000 Hz (optimal for Google STT)
      - energy_threshold      : starting sensitivity (auto-tuned by calibrate())
      - pause_threshold       : 0.7 s of silence ends the phrase
      - non_speaking_duration : 0.3 s of silence kept around the phrase
      - phrase_threshold      : 0.2 s minimum speech to count as a phrase
      - timeout               : 6 s to start speaking
      - phrase_time_limit     : 12 s max phrase length
      - normalize_audio       : volume boost before STT

    Session usage (keeps the mic open — much snappier per command):
        stt.open_stream()
        try:
            text = stt.listen_and_recognize()
        finally:
            stt.close_stream()
    """

    def __init__(self):
        self.recognizer = sr.Recognizer()

        # ── Sensitivity settings ────────────────────────────────────────────────
        # Lower energy_threshold = more sensitive (catches soft/distant speech)
        self.recognizer.energy_threshold          = config.STT_ENERGY_THRESHOLD
        self.recognizer.dynamic_energy_threshold  = True
        # Aggressive dynamic adjustment – quickly adapts to room noise
        self.recognizer.dynamic_energy_adjustment_damping    = 0.15
        self.recognizer.dynamic_energy_adjustment_multiplier = 1.05

        # ── Silence / Pause settings ────────────────────────────────────────────
        # pause_threshold      : how much silence means "the user finished"
        # non_speaking_duration: how much of that silence is kept in the clip.
        #   Must be <= pause_threshold. Keeping it small is what makes Mantra
        #   respond quickly instead of sitting through a full second of silence.
        pause    = float(config.STT_PAUSE_THRESHOLD)
        non_talk = min(float(config.STT_NON_SPEAKING), pause)
        self.recognizer.pause_threshold        = pause
        self.recognizer.non_speaking_duration  = non_talk
        self.recognizer.phrase_threshold       = float(config.STT_PHRASE_THRESHOLD)

        # ── Microphone: 16 kHz mono (Google STT optimal format) ────────────────
        self.mic = sr.Microphone(
            sample_rate=config.STT_SAMPLE_RATE,   # 16000 Hz
            chunk_size=1024,                       # smaller chunks = faster response
        )

        # Persistent-stream state (see open_stream / close_stream)
        self._stack: ExitStack | None = None
        self._source: sr.Microphone | None = None

        # Audio normalization flag + recognition language
        self._normalize = config.STT_NORMALIZE_AUDIO
        self._language  = config.STT_LANGUAGE

        log.info(
            f"SpeechToText initialised. "
            f"Language: {self._language} | "
            f"Sample rate: {config.STT_SAMPLE_RATE} Hz | "
            f"Energy threshold: {self.recognizer.energy_threshold} | "
            f"Pause: {pause}s / non-speaking {non_talk}s | "
            f"Normalize: {self._normalize}"
        )

    # ── Persistent mic stream ──────────────────────────────────────────────────

    def open_stream(self) -> bool:
        """
        Open the microphone once and keep it open for the whole session.
        Saves the PyAudio open/close cost on every command.
        Returns True if a stream is available.
        """
        if self._source is not None:
            return True
        try:
            stack = ExitStack()
            self._source = stack.enter_context(self.mic)
            self._stack = stack
            log.debug("STT mic stream opened for session.")
            return True
        except Exception as e:
            # Mic busy (e.g. wake listener still releasing it) – fall back to
            # opening it per-listen, which still works.
            log.warning(f"Could not hold mic stream open: {e}")
            self._stack, self._source = None, None
            return False

    def close_stream(self) -> None:
        """Release the microphone so other listeners (wake word) can use it."""
        if self._stack is not None:
            try:
                self._stack.close()
            except Exception as e:
                log.debug(f"Error closing mic stream: {e}")
        self._stack, self._source = None, None
        log.debug("STT mic stream closed.")

    def _drain(self, source) -> None:
        """
        Discard audio buffered while we weren't listening (e.g. Mantra's own
        TTS playing through the speakers). Without this, a persistent stream
        would feed stale audio into the next recognition.
        """
        try:
            stream = source.stream.pyaudio_stream
            available = stream.get_read_available()
            while available > 0:
                stream.read(min(available, 4096), exception_on_overflow=False)
                available = stream.get_read_available()
        except Exception as e:
            log.debug(f"Mic drain skipped: {e}")

    # ── Calibration ────────────────────────────────────────────────────────────

    def calibrate(self, duration: float = 1.0) -> None:
        """
        Calibrate to ambient noise and auto-set the energy threshold.
        Call once on startup before listening begins.
        """
        def _run(source):
            log.info(f"Calibrating microphone for {duration}s (noise suppression)...")
            self.recognizer.adjust_for_ambient_noise(source, duration=duration)
            log.info(
                f"Calibration complete. "
                f"Auto-set energy threshold: {int(self.recognizer.energy_threshold)}"
            )

        if self._source is not None:
            _run(self._source)
        else:
            with self.mic as source:
                _run(source)

    # ── Listen ─────────────────────────────────────────────────────────────────

    def listen(self) -> sr.AudioData | None:
        """
        Capture a single audio phrase from the microphone.
        Reuses the session stream when one is open.
        Returns AudioData on success, None on timeout.
        """
        if self._source is not None:
            return self._listen_from(self._source)
        try:
            with self.mic as source:
                return self._listen_from(source)
        except OSError as e:
            log.error(f"Microphone error: {e}")
            return None

    def _listen_from(self, source) -> sr.AudioData | None:
        """Listen on an already-open source, dropping any stale buffered audio."""
        self._drain(source)
        try:
            log.debug("Listening...")
            audio = self.recognizer.listen(
                source,
                timeout           = config.STT_TIMEOUT,            # wait for speech start
                phrase_time_limit = config.STT_PHRASE_TIME_LIMIT,  # max phrase duration
            )
            log.debug(
                f"Audio captured: {len(audio.get_raw_data()) // 1024} KB, "
                f"sample_rate={audio.sample_rate} Hz"
            )
            return audio
        except sr.WaitTimeoutError:
            log.debug("Listen timed out (no speech detected).")
            return None
        except OSError as e:
            log.error(f"Microphone error: {e}")
            return None

    # ── Recognize ──────────────────────────────────────────────────────────────

    def recognize(self, audio: sr.AudioData) -> str | None:
        """
        Convert AudioData to English text via Google STT.
        Normalizes volume before sending for better accuracy on quiet speech.
        Returns lowercase text, or None on failure.
        """
        # Normalize audio volume before sending to Google
        if self._normalize:
            audio = _normalize_audio(audio)

        try:
            text = self.recognizer.recognize_google(
                audio,
                language = self._language,   # English locale only
                show_all = False,            # return only best result
            )
            log.info(f"Recognised: '{text}'")
            return text.lower().strip()
        except sr.UnknownValueError:
            log.debug("STT could not understand audio.")
            return None
        except sr.RequestError as e:
            log.error(f"STT request error: {e}")
            return None

    # ── Convenience ────────────────────────────────────────────────────────────

    def listen_and_recognize(self) -> str | None:
        """Convenience: capture + normalize + recognize in one call."""
        audio = self.listen()
        if audio is None:
            return None
        return self.recognize(audio)


# ── Quick self-test ────────────────────────────────────────────────────────────
# To test:  python voice/speech_to_text.py
if __name__ == "__main__":
    stt = SpeechToText()
    stt.open_stream()
    try:
        stt.calibrate(duration=config.STT_CALIBRATION_DUR)
        print(f"Speak English now (up to {config.STT_PHRASE_TIME_LIMIT} seconds)...")
        result = stt.listen_and_recognize()
        print(f"You said: {result}")
    finally:
        stt.close_stream()
