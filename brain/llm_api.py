"""
brain/llm_api.py – Mantra AI v3.0
──────────────────────────────────
Communicates with the Gemini API (online LLM).

What it does:
  - Sends the user's text to Google Gemini 2.5 Flash
  - Keeps a conversation history so Gemini remembers earlier messages
  - Returns Gemini's reply as plain text
  - Handles errors gracefully (network failure, bad API key, etc.)

Where it fits:
  brain/llm_api.py  ←  called by brain/brain.py
  brain/brain.py    ←  called by agent/agent.py

Does NOT know about:
  - Voice, windows, files, or any tools
  - Whether the user spoke or typed
  - It is ONLY about talking to Gemini
"""

import sys
from pathlib import Path

# Add project root to sys.path if running this file directly
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import requests  # sends HTTP requests to Gemini's web API

import config    # reads GEMINI_API_KEY, PERSONA_SYSTEM_PROMPT, etc. from data/config.json
from utils import log  # for logging what happens (to mantra.log file)


class LLMApi:
    """
    Handles all communication with the Gemini API.

    Usage:
        api = LLMApi()
        reply = api.ask("What is the capital of France?")
        print(reply)  # → "The capital of France is Paris."
    """

    # Gemini 2.5 Flash – fastest and most capable model available on this API
    GEMINI_URL = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-3.6-flash:generateContent?key={api_key}"
    )

    def __init__(self):
        # This list stores the conversation so far (user message → model reply → user message → ...)
        # Each item is a dict like: {"role": "user", "parts": [{"text": "Hello"}]}
        self._history: list[dict] = []

        log.info("LLMApi ready. Using Gemini 3.6 Flash.")

    # ── Public ─────────────────────────────────────────────────────────────────

    def ask(self, user_text: str) -> str | None:
        """
        Send a message to Gemini and get a reply.

        Args:
            user_text: What the user said or typed.

        Returns:
            Gemini's reply as a plain text string.
            Returns None if there's no API key or a network error occurs.
        """
        # If there's no API key configured, we can't call Gemini
        if not config.GEMINI_API_KEY:
            log.warning("LLMApi: GEMINI_API_KEY not set. Skipping API call.")
            return None

        # Add the user's message to the conversation history
        self._history.append({
            "role": "user",
            "parts": [{"text": user_text}]
        })

        # Keep history within the limit (too much history = slower + costs more)
        # Each "turn" = 1 user message + 1 model reply → max_msgs = limit × 2
        max_msgs = config.PERSONA_MAX_HISTORY * 2
        if len(self._history) > max_msgs:
            # Keep only the most recent messages (drop oldest)
            self._history = self._history[-max_msgs:]

        # Build the full request payload (what we send to Gemini)
        payload = {
            # system_instruction = Gemini's "personality" (who is Mantra?)
            "system_instruction": {
                "parts": [{"text": config.PERSONA_SYSTEM_PROMPT}]
            },
            # contents = the whole conversation so far
            "contents": self._history,
            # generationConfig = controls how Gemini generates its reply
            "generationConfig": {
                "temperature":     0.7,   # 0.0 = very predictable, 1.0 = very creative
                "maxOutputTokens": 150,   # short replies → better for text-to-speech
                "topP":            0.9,   # controls word variety in the reply
            },
        }

        try:
            # Send the request to Gemini (wait up to 12 seconds for a reply)
            url = self.GEMINI_URL.format(api_key=config.GEMINI_API_KEY)
            response = requests.post(url, json=payload, timeout=12)

            # If Gemini returned an error code (4xx, 5xx), raise an exception
            response.raise_for_status()

            # Dig out the reply text from Gemini's JSON response structure
            reply = (
                response.json()
                ["candidates"][0]  # Gemini can return multiple candidates; we use the first
                ["content"]
                ["parts"][0]
                ["text"]
                .strip()           # remove leading/trailing whitespace
            )

            # Save Gemini's reply to history so the next message has context
            self._history.append({
                "role": "model",
                "parts": [{"text": reply}]
            })

            # Log a short preview of the reply
            preview = reply[:80] + "..." if len(reply) > 80 else reply
            log.info(f"Gemini reply: '{preview}'")
            return reply

        except requests.HTTPError as e:
            # Gemini rejected our request (e.g. bad API key, quota exceeded)
            log.error(f"Gemini HTTP error {response.status_code}: {e}")
            # Remove the failed user message from history so we don't confuse Gemini next time
            if self._history and self._history[-1]["role"] == "user":
                self._history.pop()
            return None

        except requests.ConnectionError:
            # No internet connection
            log.warning("Gemini API: No internet connection.")
            if self._history and self._history[-1]["role"] == "user":
                self._history.pop()
            return None

        except requests.Timeout:
            # Gemini took too long to reply
            log.warning("Gemini API: Request timed out.")
            if self._history and self._history[-1]["role"] == "user":
                self._history.pop()
            return None

        except Exception as e:
            # Anything else unexpected
            log.error(f"Gemini API unexpected error: {e}")
            if self._history and self._history[-1]["role"] == "user":
                self._history.pop()
            return None

    def reset_history(self) -> None:
        """
        Clear the conversation memory.
        Call this at the start or end of each voice session so Gemini
        doesn't remember things from the previous conversation.
        """
        self._history.clear()
        log.debug("LLMApi: Conversation history cleared.")

    def is_available(self) -> bool:
        """
        Quick check: do we have a Gemini API key configured?
        Returns True if we can try to use the API.
        """
        return bool(config.GEMINI_API_KEY)


# ── Self-test (run this file directly to test it) ─────────────────────────────
# To test:  python brain/llm_api.py
# You will see Gemini's reply printed in the terminal.
if __name__ == "__main__":
    print("Testing brain/llm_api.py...")
    print("=" * 50)

    api = LLMApi()

    if not api.is_available():
        print("ERROR: GEMINI_API_KEY is not set in data/config.json")
        print("Please add your Gemini API key to data/config.json under 'api_keys.gemini'")
    else:
        # Test 1: Simple question
        print("Test 1: Asking 'What is 2 + 2?'")
        reply = api.ask("What is 2 + 2?")
        print(f"Gemini said: {reply}")
        print()

        # Test 2: Follow-up question (tests conversation memory)
        print("Test 2: Follow-up 'And multiply that by 3?'")
        reply = api.ask("And multiply that by 3?")
        print(f"Gemini said: {reply}")
        print()

        # Test 3: Reset history
        api.reset_history()
        print("Test 3: History cleared. Session memory reset.")
        print()

        print("=" * 50)
        print("brain/llm_api.py is working correctly!")
