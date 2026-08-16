"""
brain/brain.py – Mantra AI v3.0
────────────────────────────────
The LLM Router — Mantra's decision-maker for which AI to talk to.

What it does:
  - Tries the Gemini API first (fast, smart, needs internet)
  - If Gemini fails or is unavailable → falls back to the Local LLM (Ollama)
  - If both fail → returns a polite fallback message
  - Manages conversation history across both LLMs

The "brain" of Mantra. Everything asking an AI question goes through here.

Where it fits:
  agent/agent.py  →  brain/brain.py  →  brain/llm_api.py   (online)
                                     →  brain/local_llm.py (offline)

Does NOT know about:
  - Voice, windows, tools, files
  - It is ONLY about routing questions to the right AI
"""

import sys
from pathlib import Path

# Add project root to sys.path if running this file directly
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import config
from utils import log
from brain.llm_api   import LLMApi    # online  Gemini API
from brain.local_llm import LocalLLM  # offline local LLM (Ollama)

class Brain:
    """
    Mantra's LLM router.

    Tries API first → falls back to local LLM → falls back to a default message.

    Usage:
        brain = Brain()
        reply = brain.think("What is the speed of light?")
        print(reply)
    """

    # Message returned if BOTH the API LLM and local LLM fail
    FALLBACK_MESSAGE = (
        "I'm sorry, I can't connect to my AI brain right now. "
        "Please check your internet connection or make sure Ollama is running."
    )

    def __init__(self):
        # Create the two LLM clients
        self._api_llm   = LLMApi()    # Gemini (online)
        self._local_llm = LocalLLM()  # Ollama  (offline)

        log.info(
            f"Brain initialised. "
            f"API LLM available: {self._api_llm.is_available()} | "
            f"Local LLM available: {self._local_llm.is_available()}"
        )

    # ── Public ─────────────────────────────────────────────────────────────────

    def think(self, user_text: str) -> str:
        """
        Send a question/prompt to the best available LLM and return the reply.

        Priority order:
          1. Gemini API  (if API key is set and internet works)
          2. Local LLM   (if Ollama is running)
          3. Fallback message

        Args:
            user_text: The user's question or command text.

        Returns:
            A plain text response string. Never returns None.
        """
        log.info(f"Brain.think called with: '{user_text[:60]}...' " if len(user_text) > 60 else f"Brain.think: '{user_text}'")

        # ── Step 1: Try the Gemini API ─────────────────────────────────────────
        if self._api_llm.is_available():
            log.debug("Brain: Trying Gemini API...")
            reply = self._api_llm.ask(user_text)
            if reply:
                log.info("Brain: Used Gemini API successfully.")
                return reply
            log.warning("Brain: Gemini API returned no reply. Trying local LLM...")
        else:
            log.info("Brain: Gemini API not available (no key). Trying local LLM...")

        # ── Step 2: Fall back to the Local LLM (Ollama) ───────────────────────
        if self._local_llm.is_available():
            log.debug(f"Brain: Trying Local LLM ({self._local_llm.get_model_name()})...")
            reply = self._local_llm.ask(user_text)
            if reply:
                log.info(f"Brain: Used Local LLM ({self._local_llm.get_model_name()}) as fallback.")
                return reply
            log.warning("Brain: Local LLM also returned no reply.")
        else:
            log.info("Brain: Local LLM not available (Ollama not running).")

        # ── Step 3: Both failed – return a safe fallback message ──────────────
        log.error("Brain: Both API and Local LLM failed. Using fallback message.")
        return self.FALLBACK_MESSAGE

    def reset_history(self) -> None:
        """
        Clear conversation memory in BOTH LLMs.
        Call this at the start and end of every voice session.
        """
        self._api_llm.reset_history()
        self._local_llm.reset_history()
        log.debug("Brain: All conversation history cleared.")

    def status(self) -> dict:
        """
        Returns a dict showing which LLMs are currently available.
        Useful for debugging or a "Mantra, what's your status?" command.

        Returns:
            {
                "api_llm_available":   True/False,
                "local_llm_available": True/False,
                "local_llm_model":     "llama3" / "mistral" / ...
            }
        """
        return {
            "api_llm_available":   self._api_llm.is_available(),
            "local_llm_available": self._local_llm.is_available(),
            "local_llm_model":     self._local_llm.get_model_name(),
        }


# ── Self-test ─────────────────────────────────────────────────────────────────
# To test:  python brain/brain.py
if __name__ == "__main__":
    print("Testing brain/brain.py (the LLM router)...")
    print("=" * 50)

    brain = Brain()

    # Show which LLMs are available
    s = brain.status()
    print(f"Gemini API available : {s['api_llm_available']}")
    print(f"Local LLM available  : {s['local_llm_available']}")
    if s["local_llm_available"]:
        print(f"Local LLM model      : {s['local_llm_model']}")
    print()

    # Test a question – brain will automatically pick the best LLM
    question = "In one sentence, what is artificial intelligence?"
    print(f"Asking: '{question}'")
    reply = brain.think(question)
    print(f"Reply : {reply}")
    print()

    # Test follow-up (tests conversation memory)
    followup = "Give me one example of that."
    print(f"Follow-up: '{followup}'")
    reply2 = brain.think(followup)
    print(f"Reply    : {reply2}")
    print()

    # Reset history
    brain.reset_history()
    print("History cleared.")
    print()

    print("=" * 50)
    print("brain/brain.py is working correctly!")
