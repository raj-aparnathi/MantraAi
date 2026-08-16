"""
main.py – Mantra AI v3.0
──────────────────────────
Entry point. Starts the wake word detector and the agent session loop.

Architecture:
  main.py
    ├→  voice/wake_word.py       → listens for "Hello Mantra"
    ├→  voice/text_to_speech.py → Mantra speaks
    ├→  voice/speech_to_text.py → converts your speech to text
    └→  agent/agent.py          → routes commands to tools or brain

Usage:
    python main.py
"""

import sys
import time
import signal

import config
from utils import setup_logger, log

# v3.0: All voice components now live in the voice/ package
from voice.text_to_speech import TextToSpeech
from voice.speech_to_text import SpeechToText
from voice.wake_word      import WakeWordDetector

# v3.0: The agent now lives in agent/agent.py
from agent.agent import Agent


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
    print(f"  {config.ASSISTANT_NAME} – Version {config.VERSION}  (v3.0 Clean Architecture)")
    print("  Starting up...")
    print("=" * 60)

    # Initialise core voice components
    tts = TextToSpeech()
    stt = SpeechToText()

    # Calibrate microphone once on startup (reduces false positives)
    tts.speak(
        f"Hello! I am {config.ASSISTANT_NAME}, version {config.VERSION}. "
        "Calibrating microphone, please wait a moment."
    )
    stt.calibrate(duration=config.STT_CALIBRATION_DUR)

    # Start wake word detector in the background
    wake_detector = WakeWordDetector()
    wake_detector.start()

    # Create the v3.0 agent (replaces assistant.py)
    agent = Agent(tts=tts, stt=stt)

    tts.speak(
        f"I'm ready. Say '{config.WAKE_WORD.title()}' to wake me up."
    )
    print(f"\n[Mantra] Listening for wake word: '{config.WAKE_WORD}' …")
    print("[Mantra] Press Ctrl+C to exit.\n")

    # ── Main wake-word loop ────────────────────────────────────────────────────
    while not _shutdown:
        # Wait up to 0.1s for wake word event
        detected = wake_detector.detected.wait(timeout=0.1)

        if not detected:
            continue   # still waiting — loop again

        log.info("Wake word event received. Starting session.")
        wake_detector.reset()
        wake_detector.pause()   # stop wake word listening while session is active

        try:
            # Run an active voice session (loops until user says goodbye)
            agent.run_session()
        except Exception as e:
            log.error(f"Session error: {e}", exc_info=True)
            tts.speak("I encountered an error. Please try again.")

        # Re-arm wake word detector after session ends
        wake_detector.resume()
        print(f"\n[Mantra] Session ended. Say '{config.WAKE_WORD.title()}' to start again.\n")

    # ── Cleanup ────────────────────────────────────────────────────────────────
    wake_detector.stop()
    tts.speak(f"Goodbye! {config.ASSISTANT_NAME} is shutting down.")
    log.info("MantraAI v3.0 shutdown complete.")
    sys.exit(0)


if __name__ == "__main__":
    main()
