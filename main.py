"""
main.py – Mantra AI v2.0
Entry point. Starts the wake word detector and the assistant session loop.

Usage:
    python main.py
"""

import sys
import time
import signal

import config
from utils import setup_logger, log
from text_to_speech import TextToSpeech
from speech_to_text import SpeechToText
from wake_word      import WakeWordDetector
from assistant      import Assistant


# ── Graceful Shutdown ──────────────────────────────────────────────────────────

_shutdown = False

def _signal_handler(sig, frame):
    global _shutdown
    print("\n[Mantra] Received interrupt. Shutting down…")
    log.info("Interrupt signal received. Exiting.")
    _shutdown = True

signal.signal(signal.SIGINT,  _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    global _shutdown
    log = setup_logger("MantraAI.main")

    print("=" * 60)
    print(f"  {config.ASSISTANT_NAME} – Version {config.VERSION}  (Desktop Automation Edition)")
    print("  Starting up...")
    print("=" * 60)

    # Initialise core components
    tts = TextToSpeech()
    stt = SpeechToText()

    # Calibrate microphone once
    tts.speak(f"Namaste! Main hoon {config.ASSISTANT_NAME}, version {config.VERSION}. "
              "Microphone calibrate ho rahi hai, ek second ruko.")
    stt.calibrate(duration=config.STT_CALIBRATION_DUR)

    # Wake word detector
    wake_detector = WakeWordDetector()
    wake_detector.start()

    assistant = Assistant(tts=tts, stt=stt)

    tts.speak(
        f"I'm ready. Say '{config.WAKE_WORD.title()}' to wake me up."
    )
    print(f"\n[Mantra] Listening for wake word: '{config.WAKE_WORD}' …")
    print("[Mantra] Press Ctrl+C to exit.\n")

    # ── Main wake-word loop ────────────────────────────────────────────────────
    while not _shutdown:
        # Block until wake word detected (poll every 0.1s)
        detected = wake_detector.detected.wait(timeout=0.1)

        if not detected:
            continue       # still waiting

        log.info("Wake word event received. Starting session.")
        wake_detector.reset()
        wake_detector.pause()   # stop wake word listening during active session

        try:
            assistant.run_session()
        except Exception as e:
            log.error(f"Session error: {e}", exc_info=True)
            tts.speak("I encountered an error. Please try again.")

        # Re-arm wake word detector after session ends
        wake_detector.resume()
        print(f"\n[Mantra] Session ended. Say '{config.WAKE_WORD.title()}' to start again.\n")

    # ── Cleanup ────────────────────────────────────────────────────────────────
    wake_detector.stop()
    tts.speak(f"Goodbye! {config.ASSISTANT_NAME} is shutting down.")
    log.info("MantraAI shutdown complete.")
    sys.exit(0)


if __name__ == "__main__":
    main()
