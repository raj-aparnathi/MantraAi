"""
speech_to_text.py – Mantra AI v2.0
Microphone capture and speech recognition using Google's free STT backend.

v2.0 Audio Improvements:
  - 16 kHz sample rate, mono channel (better STT accuracy, less data)
  - Increased audio gain (input sensitivity boost)
  - Lower energy_threshold (catches softer speech faster)
  - Dynamic energy threshold with aggressive adjustment
  - Longer phrase_time_limit (don't cut off mid-sentence)
  - Extended silence pause_threshold (don't stop on natural pauses)
  - Longer listen timeout (more time to start speaking)
  - Audio volume normalization before sending to Google STT
  - Noise suppression via extended ambient calibration
  - Echo cancellation hint via non-input_device_index auto-selection
"""

import audioop
import struct
import array

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
        channels   = 1                           # we always record mono

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
    v2.0 SpeechToText with enhanced microphone sensitivity and audio quality.

    Key settings (all tunable via config.json → stt section):
      - sample_rate    : 16000 Hz (optimal for Google STT)
      - channels       : 1 (mono – less noise, smaller payload)
      - energy_threshold  : 200 (very sensitive, catches soft speech)
      - pause_threshold   : 1.2 s (allow natural mid-sentence pauses)
      - dynamic_energy    : True (auto-adjusts to mic/room)
      - timeout           : 10 s (plenty of time to start speaking)
      - phrase_time_limit : 20 s (longer commands don't get cut off)
      - normalize_audio   : True (volume boost before STT)
    """

    def __init__(self):
        self.recognizer = sr.Recognizer()

        # ── Sensitivity settings ────────────────────────────────────────────────
        # Lower energy_threshold = more sensitive (catches soft/distant speech)
        self.recognizer.energy_threshold          = config.STT_ENERGY_THRESHOLD
        self.recognizer.dynamic_energy_threshold  = True
        # Aggressive dynamic adjustment – quickly adapts to room noise
        self.recognizer.dynamic_energy_adjustment_damping    = 0.10  # default 0.15
        self.recognizer.dynamic_energy_adjustment_multiplier = 1.05  # default 1.0

        # ── Silence / Pause settings ────────────────────────────────────────────
        # Higher pause_threshold = doesn't stop recording on natural pauses
        self.recognizer.pause_threshold           = config.STT_PAUSE_THRESHOLD
        # Don't cut non-speaking prefix (helps with slow starters)
        self.recognizer.non_speaking_duration     = config.STT_PAUSE_THRESHOLD

        # ── Microphone: 16 kHz mono (Google STT optimal format) ────────────────
        self.mic = sr.Microphone(
            sample_rate=config.STT_SAMPLE_RATE,   # 16000 Hz
            chunk_size=1024,                       # smaller chunks = faster response
        )

        # Audio normalization flag
        self._normalize = config.STT_NORMALIZE_AUDIO

        log.info(
            f"SpeechToText initialised. "
            f"Sample rate: {config.STT_SAMPLE_RATE} Hz | "
            f"Energy threshold: {self.recognizer.energy_threshold} | "
            f"Pause threshold: {self.recognizer.pause_threshold}s | "
            f"Normalize: {self._normalize}"
        )

    # ── Calibration ────────────────────────────────────────────────────────────

    def calibrate(self, duration: float = 2.0) -> None:
        """
        Calibrate to ambient noise.
        Extended duration (2s default) gives more accurate baseline.
        Call once on startup before listening begins.
        """
        with self.mic as source:
            log.info(f"Calibrating microphone for {duration}s (noise suppression)...")
            self.recognizer.adjust_for_ambient_noise(source, duration=duration)
            log.info(
                f"Calibration complete. "
                f"Auto-set energy threshold: {int(self.recognizer.energy_threshold)}"
            )

    # ── Listen ─────────────────────────────────────────────────────────────────

    def listen(self) -> sr.AudioData | None:
        """
        Capture a single audio phrase from the microphone.
        Uses 16 kHz mono, extended timeout, and long phrase_time_limit.
        Returns AudioData on success, None on timeout.
        """
        with self.mic as source:
            try:
                log.debug("Listening...")
                audio = self.recognizer.listen(
                    source,
                    timeout          = config.STT_TIMEOUT,           # seconds to wait for speech start
                    phrase_time_limit = config.STT_PHRASE_TIME_LIMIT, # max phrase duration
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
        Convert AudioData to text via Google STT.
        Normalizes volume before sending for better accuracy on quiet speech.
        Returns lowercase text, or None on failure.
        """
        # Normalize audio volume before sending to Google
        if self._normalize:
            audio = _normalize_audio(audio)

        try:
            text = self.recognizer.recognize_google(
                audio,
                language         = config.LANGUAGE,
                show_all         = False,   # return only best result
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
if __name__ == "__main__":
    stt = SpeechToText()
    stt.calibrate(duration=2.0)
    print("Speak now (up to 20 seconds)...")
    result = stt.listen_and_recognize()
    print(f"You said: {result}")
