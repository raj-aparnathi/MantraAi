"""
voice/speaker_verify.py – Mantra AI v3.0
──────────────────────────────────────────
Speaker verification — confirms that only YOUR voice can activate Mantra.

Location : voice/speaker_verify.py
Status   : OPTIONAL — Mantra works perfectly without this.
           Enable it only when you want to restrict access to your voice only.

What it does:
  1. Records a short sample of YOUR voice (one-time setup)
  2. Saves your "voiceprint" as a fingerprint file
  3. Before every session, quickly compares the speaker's voice to your voiceprint
  4. Only allows the session to start if the voice matches

How speaker verification works:
  - Record your voice speaking a phrase (e.g. "Hello Mantra")
  - Extract audio features (MFCCs — Mel-Frequency Cepstral Coefficients)
    These are like a fingerprint of your voice's unique characteristics.
  - When someone speaks the wake word, extract their MFCCs too
  - Compare: if the similarity is above a threshold → it's you → allow
  - If below the threshold → it's someone else → deny

Library needed:
  pip install resemblyzer
  (This is a Python library specifically built for speaker verification)

NOTE: This feature is NOT enabled by default.
      To enable it, set SPEAKER_VERIFY = True in your data/config.json
      under a "v3" section, and run the enrollment step first.

HOW TO USE:
  Step 1 – Enroll (first time only):
      python voice/speaker_verify.py --enroll

  Step 2 – Enable in agent/agent.py:
      Import SpeakerVerifier and call verifier.is_authorized(audio) before run_session()
"""

from pathlib import Path
import json

from utils import log


# ── Configuration ─────────────────────────────────────────────────────────────

# Where to save your voiceprint (the audio fingerprint of your voice)
VOICEPRINT_FILE = Path(__file__).resolve().parent.parent / "data" / "voiceprint.json"

# Similarity threshold (0.0 to 1.0)
# Higher = stricter (fewer false positives, but might reject you on a bad day)
# Lower  = more lenient (accepts more variation, but might accept others)
SIMILARITY_THRESHOLD = 0.75


class SpeakerVerifier:
    """
    Verifies that the speaker is the enrolled user.

    REQUIRES: pip install resemblyzer numpy

    Usage (after enrolling):
        verifier = SpeakerVerifier()
        if verifier.is_enrolled():
            is_me = verifier.verify(audio_data)
            if not is_me:
                print("Access denied — voice not recognized.")
    """

    def __init__(self):
        self._voiceprint = self._load_voiceprint()
        self._encoder = None  # Loaded lazily (only when actually needed)
        log.info(
            f"SpeakerVerifier ready. "
            f"Enrolled: {self.is_enrolled()} | "
            f"Threshold: {SIMILARITY_THRESHOLD}"
        )

    # ── Public ─────────────────────────────────────────────────────────────────

    def is_enrolled(self) -> bool:
        """Return True if a voiceprint has been saved (enrollment has been done)."""
        return self._voiceprint is not None

    def enroll(self, audio_file_path: str) -> str:
        """
        Enroll your voice by processing a WAV audio file of you speaking.

        Steps:
          1. Record a 5-10 second WAV file of you saying the wake word repeatedly
          2. Call this method with the path to that WAV file
          3. Your voiceprint will be saved to data/voiceprint.json

        Args:
            audio_file_path: Path to a WAV file of your voice.

        Returns:
            A status message.
        """
        try:
            encoder = self._get_encoder()
            if encoder is None:
                return (
                    "Speaker verification requires 'resemblyzer'. "
                    "Install it with: pip install resemblyzer"
                )

            import numpy as np
            from resemblyzer import preprocess_wav

            wav = preprocess_wav(audio_file_path)
            embedding = encoder.embed_utterance(wav)

            # Save the embedding (as a list, since JSON can't store numpy arrays)
            voiceprint_data = {
                "embedding": embedding.tolist(),
                "threshold": SIMILARITY_THRESHOLD,
            }
            VOICEPRINT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(VOICEPRINT_FILE, "w") as f:
                json.dump(voiceprint_data, f)

            self._voiceprint = voiceprint_data
            log.info(f"SpeakerVerifier: Voiceprint enrolled. Saved to {VOICEPRINT_FILE}")
            return "Enrollment successful! Mantra will now recognize your voice."

        except ImportError:
            return (
                "resemblyzer is not installed. "
                "Run: pip install resemblyzer"
            )
        except Exception as e:
            log.error(f"SpeakerVerifier enrollment error: {e}")
            return f"Enrollment failed: {e}"

    def verify(self, audio_file_path: str) -> bool:
        """
        Check if the given audio matches the enrolled voiceprint.

        Args:
            audio_file_path: Path to a WAV file to verify.

        Returns:
            True if the voice matches (it's you), False otherwise.
        """
        if not self.is_enrolled():
            log.warning("SpeakerVerifier: Not enrolled yet. Allowing all speakers.")
            return True  # If no voiceprint is saved, allow everyone (fail-open)

        try:
            encoder = self._get_encoder()
            if encoder is None:
                return True  # resemblyzer not installed → allow (fail-open)

            import numpy as np
            from resemblyzer import preprocess_wav

            # Process the audio to verify
            wav = preprocess_wav(audio_file_path)
            test_embedding = encoder.embed_utterance(wav)

            # Compare with stored voiceprint using cosine similarity
            stored = np.array(self._voiceprint["embedding"])
            threshold = self._voiceprint.get("threshold", SIMILARITY_THRESHOLD)

            # Cosine similarity: 1.0 = identical, 0.0 = completely different
            similarity = float(np.dot(test_embedding, stored) / (
                np.linalg.norm(test_embedding) * np.linalg.norm(stored)
            ))

            log.info(f"SpeakerVerifier: similarity = {similarity:.3f} (threshold: {threshold})")
            return similarity >= threshold

        except ImportError:
            return True  # resemblyzer not installed → allow
        except Exception as e:
            log.error(f"SpeakerVerifier error: {e}")
            return True  # On error → allow (fail-open for safety)

    # ── Private ────────────────────────────────────────────────────────────────

    def _get_encoder(self):
        """Load the voice encoder model (lazy, only when first needed)."""
        if self._encoder is not None:
            return self._encoder
        try:
            from resemblyzer import VoiceEncoder
            self._encoder = VoiceEncoder()
            log.info("SpeakerVerifier: VoiceEncoder loaded.")
            return self._encoder
        except ImportError:
            return None
        except Exception as e:
            log.error(f"SpeakerVerifier: Could not load VoiceEncoder: {e}")
            return None

    def _load_voiceprint(self) -> dict | None:
        """Load the saved voiceprint from disk, or None if not enrolled."""
        if not VOICEPRINT_FILE.exists():
            return None
        try:
            with open(VOICEPRINT_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            log.error(f"SpeakerVerifier: Could not load voiceprint: {e}")
            return None


# ── Enrollment script ─────────────────────────────────────────────────────────
# To enroll your voice:
#   python voice/speaker_verify.py --enroll path/to/your_voice.wav
#
# To test verification:
#   python voice/speaker_verify.py --verify path/to/test_audio.wav
if __name__ == "__main__":
    import sys

    verifier = SpeakerVerifier()

    if "--enroll" in sys.argv:
        if len(sys.argv) < 3:
            print("Usage: python voice/speaker_verify.py --enroll path/to/voice.wav")
            print()
            print("How to record your voice:")
            print("  1. Open Windows Voice Recorder (search in Start menu)")
            print("  2. Record yourself saying 'Hello Mantra' 5-10 times")
            print("  3. Save it as a WAV file")
            print("  4. Run this command with the file path")
        else:
            wav_path = sys.argv[2]
            result = verifier.enroll(wav_path)
            print(result)

    elif "--verify" in sys.argv:
        if len(sys.argv) < 3:
            print("Usage: python voice/speaker_verify.py --verify path/to/audio.wav")
        else:
            wav_path = sys.argv[2]
            if not verifier.is_enrolled():
                print("Not enrolled yet. Run with --enroll first.")
            else:
                is_me = verifier.verify(wav_path)
                print(f"Verification result: {'✓ AUTHORIZED (it is you!)' if is_me else '✗ DENIED (voice not recognized)'}")

    else:
        print("Speaker Verifier Status:")
        print(f"  Enrolled : {verifier.is_enrolled()}")
        print(f"  File     : {VOICEPRINT_FILE}")
        print()
        print("Commands:")
        print("  python voice/speaker_verify.py --enroll path/to/voice.wav")
        print("  python voice/speaker_verify.py --verify path/to/audio.wav")
